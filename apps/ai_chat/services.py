import json
import re
import time

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.ai_context.services import build_safe_context
from apps.applications.models import Application
from apps.core.redaction import redact_json, redact_secrets
from apps.reports.models import Report, ReportSection
from apps.servers.models import Server
from apps.tools.models import ToolBuildProposal, ToolBuildRequest, ToolDefinition, ToolPolicy, ToolRun, ToolTemplate
from apps.tools.result_summaries import summarize_tool_result_for_chat, summarize_tool_run_result
from apps.tools.services import (
    ToolPolicyDenied,
    create_tool_run_job,
    generate_tool_build_proposal,
    redacted_json,
    sanitize_builder_text,
)

from .models import AdminChatDecision, AdminChatMessage, AdminChatReportDraft, AdminChatSession, AdminChatToolRequest


MAX_MESSAGE_LENGTH = 4000
MAX_TITLE_LENGTH = 160
MAX_RESPONSE_LENGTH = 3000
AUTO_TOOL_FOLLOWUP_MAX_WAIT_SECONDS = 45
AUTO_TOOL_FOLLOWUP_POLL_INTERVAL_SECONDS = 2
AUTO_TOOL_SINGLE_MAX_WAIT_SECONDS = 45
AUTO_TOOL_MULTI_BASE_WAIT_SECONDS = 45
AUTO_TOOL_MULTI_EXTRA_WAIT_SECONDS = 20
AUTO_TOOL_MULTI_MAX_WAIT_SECONDS = 120
AUTO_TOOL_FINAL_GRACE_SECONDS = 5
TOOL_REQUEST_PROPOSAL_RE = re.compile(
    r"<TOOL_REQUEST_PROPOSAL>\s*(?P<payload>\{.*?\})\s*</TOOL_REQUEST_PROPOSAL>",
    re.IGNORECASE | re.DOTALL,
)
AI_READ_ONLY_TOOL_ALLOWLIST = {
    "system_identity",
    "services_status",
    "latest_baseline_summary",
    "log_sources_discovery_v2",
    "systemd_services_discovery",
    "nginx_sites_discovery",
    "postgres_status_discovery",
}
DIRECT_EXECUTION_TERMS = (
    "افحص",
    "نفذ",
    "ابدأ",
    "شغل",
    "تابع",
    "متابعة",
    "اعمل فحص",
    "راجع",
    "check",
    "run",
    "execute",
    "start",
    "continue",
)
DIRECT_EXECUTION_ADVICE_TERMS = (
    "ماذا تقترح",
    "ماذا تنصح",
    "ايه الفحوصات",
    "إيه الفحوصات",
    "هل نحتاج",
    "what do you suggest",
    "what should",
    "should we",
)
DIRECT_EXECUTION_TOOL_SCOPES = (
    (
        "log_sources_discovery_v2",
        (
            "مصادر السجلات",
            "السجلات",
            "logs",
            "log sources",
            "log_sources",
        ),
        "فحص مصادر السجلات بناءً على طلب مباشر من المستخدم.",
    ),
    (
        "services_status",
        (
            "حالة السيرفر",
            "حالة الخادم",
            "services",
            "service status",
            "server status",
            "system status",
        ),
        "فحص حالة الخدمات بناءً على طلب مباشر من المستخدم.",
    ),
    (
        "systemd_services_discovery",
        (
            "systemd",
            "خدمات systemd",
            "systemctl",
            "الخدمات",
        ),
        "فحص خدمات systemd بناءً على طلب مباشر من المستخدم.",
    ),
    (
        "nginx_sites_discovery",
        (
            "nginx",
            "مواقع nginx",
            "nginx sites",
        ),
        "فحص إعدادات nginx بناءً على طلب مباشر من المستخدم.",
    ),
    (
        "postgres_status_discovery",
        (
            "postgres",
            "postgresql",
            "قاعدة البيانات",
            "database",
        ),
        "فحص حالة PostgreSQL بناءً على طلب مباشر من المستخدم.",
    ),
    (
        "system_identity",
        (
            "هوية النظام",
            "system identity",
            "server identity",
        ),
        "فحص هوية النظام بناءً على طلب مباشر من المستخدم.",
    ),
)


def _safe_text(value, *, limit):
    text = redact_secrets(value or "").strip()
    if len(text) > limit:
        return f"{text[:limit]}..."
    return text


def strip_tool_request_proposals(text):
    return _safe_text(TOOL_REQUEST_PROPOSAL_RE.sub("", text or ""), limit=MAX_RESPONSE_LENGTH)


def extract_tool_request_proposal(text):
    proposals = extract_tool_request_proposals(text)
    return proposals[0] if proposals else None


def extract_tool_request_proposals(text):
    proposals = []
    for match in TOOL_REQUEST_PROPOSAL_RE.finditer(text or ""):
        proposal = _parse_tool_request_proposal(match.group("payload"))
        if proposal:
            proposals.append(proposal)
    return proposals


def resolve_direct_execution_tool_proposals(*, latest_user_text, conversation_text=""):
    normalized_user = (latest_user_text or "").casefold()
    if not normalized_user:
        return []
    if any(term.casefold() in normalized_user for term in DIRECT_EXECUTION_ADVICE_TERMS):
        return []
    has_execution_intent = any(term.casefold() in normalized_user for term in DIRECT_EXECUTION_TERMS)
    if not has_execution_intent:
        return []

    search_text = normalized_user
    if normalized_user.strip() in {"تابع", "متابعة", "continue"}:
        search_text = f"{normalized_user}\n{(conversation_text or '').casefold()}"

    proposals = []
    seen = set()
    for tool_slug, scope_terms, reason in DIRECT_EXECUTION_TOOL_SCOPES:
        if tool_slug in seen:
            continue
        if any(term.casefold() in search_text for term in scope_terms):
            proposals.append(
                {
                    "tool_slug": tool_slug,
                    "reason": reason,
                    "params": {"scope": "selected_server"},
                }
            )
            seen.add(tool_slug)
    return proposals


def _parse_tool_request_proposal(payload_text):
    try:
        payload = json.loads(payload_text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    tool_slug = _safe_text(str(payload.get("tool_slug") or ""), limit=120)
    reason = _safe_text(str(payload.get("reason") or ""), limit=500)
    params = payload.get("params") or {}
    if not isinstance(params, dict):
        return None
    return {
        "tool_slug": tool_slug,
        "reason": reason,
        "params": redact_json(params),
    }


def _require_portal_account_user(user):
    if not user or not user.is_authenticated:
        raise PermissionDenied
    if user.account_id is None:
        raise PermissionDenied
    if user.account.status != Account.Status.ACTIVE:
        raise PermissionDenied
    if user.role not in {User.CustomerRole.OWNER, User.CustomerRole.OPERATOR, User.CustomerRole.VIEWER}:
        raise PermissionDenied


def _require_chat_writer(user):
    _require_portal_account_user(user)
    if user.role not in {User.CustomerRole.OWNER, User.CustomerRole.OPERATOR}:
        raise PermissionDenied


def _require_matrix_admin(user):
    if not user or not user.is_authenticated or not user.is_staff:
        raise PermissionDenied


def user_can_view_chat(user, session):
    if not user or not user.is_authenticated:
        return False
    if session.channel == AdminChatSession.Channel.ADMIN_INTERNAL:
        return user.is_staff
    if user.account_id is None:
        return False
    return user.account_id == session.account_id and user.role in {
        User.CustomerRole.OWNER,
        User.CustomerRole.OPERATOR,
        User.CustomerRole.VIEWER,
    }


def user_can_write_chat(user, session):
    if session.channel == AdminChatSession.Channel.ADMIN_INTERNAL:
        return bool(user and user.is_authenticated and user.is_staff)
    return user_can_view_chat(user, session) and user.role in {User.CustomerRole.OWNER, User.CustomerRole.OPERATOR}


def _require_session_writer(user, session):
    if session.channel == AdminChatSession.Channel.ADMIN_INTERNAL:
        _require_matrix_admin(user)
    else:
        _require_chat_writer(user)
    if not user_can_write_chat(user, session):
        raise PermissionDenied


def _resolve_server(account, server_id):
    if not server_id:
        return None
    return Server.objects.filter(account=account, id=server_id).first()


def _resolve_application(account, application_id, server=None):
    if not application_id:
        return None
    queryset = Application.objects.filter(account=account, id=application_id)
    if server:
        queryset = queryset.filter(server=server)
    return queryset.first()


def create_chat_session(*, user, title="", server_id=None, application_id=None, channel=AdminChatSession.Channel.PORTAL_CUSTOMER, account_id=None):
    if channel == AdminChatSession.Channel.ADMIN_INTERNAL:
        _require_matrix_admin(user)
        account = Account.objects.filter(id=account_id, status=Account.Status.ACTIVE).first()
        if account is None:
            raise ValidationError("Selected account is not available.")
    else:
        _require_chat_writer(user)
        account = user.account
    server = _resolve_server(account, server_id)
    if server_id and server is None:
        raise ValidationError("Selected server is not available.")
    application = _resolve_application(account, application_id, server=server)
    if application_id and application is None:
        raise ValidationError("Selected application is not available.")
    if application and server is None:
        server = application.server

    default_title = "New internal chat" if channel == AdminChatSession.Channel.ADMIN_INTERNAL else "New chat"
    title_redacted = _safe_text(title or default_title, limit=MAX_TITLE_LENGTH)
    context_snapshot = build_safe_context(account=account, user=user, server=server)
    session = AdminChatSession(
        account=account,
        user=user,
        server=server,
        application=application,
        channel=channel,
        title_redacted=title_redacted,
        context_snapshot_redacted=redact_json(context_snapshot),
        last_message_at=timezone.now(),
    )
    session.full_clean()
    session.save()
    return session


def create_portal_chat_session(*, user, title="", server_id=None, application_id=None):
    return create_chat_session(
        user=user,
        title=title,
        server_id=server_id,
        application_id=application_id,
        channel=AdminChatSession.Channel.PORTAL_CUSTOMER,
    )


def create_admin_chat_session(*, user, account_id, title="", server_id=None, application_id=None):
    return create_chat_session(
        user=user,
        title=title,
        server_id=server_id,
        application_id=application_id,
        channel=AdminChatSession.Channel.ADMIN_INTERNAL,
        account_id=account_id,
    )


def add_user_message(*, user, session, body, metadata=None):
    _require_session_writer(user, session)
    if session.status != AdminChatSession.Status.OPEN:
        raise ValidationError("Chat session is archived.")
    body_redacted = _safe_text(body, limit=MAX_MESSAGE_LENGTH)
    message = AdminChatMessage.objects.create(
        session=session,
        sender_type=AdminChatMessage.SenderType.USER,
        body_redacted=body_redacted,
        metadata_redacted=redact_json(metadata or {}),
    )
    session.last_message_at = message.created_at
    session.save(update_fields=["last_message_at", "updated_at"])
    return message


def _detect_intent(question):
    normalized = (question or "").lower()
    if any(word in normalized for word in ("result", "latest tool", "last tool", "apache", "5xx")):
        return "tool_results"
    if any(word in normalized for word in ("finding", "risk", "issue", "critical", "high")):
        return "findings"
    if any(word in normalized for word in ("report", "summary report", "health report")):
        return "reports"
    if any(word in normalized for word in ("tool", "check", "scan", "available")):
        return "available_tools"
    if any(word in normalized for word in ("status", "health", "baseline", "service", "server")):
        return "status"
    return "summary"


def _section_count(context, key):
    value = context.get(key)
    if isinstance(value, list):
        return len(value)
    if value:
        return 1
    return 0


def _format_status_response(context):
    server = context.get("server_summary") or {}
    baseline = context.get("baseline_summary") or {}
    risk = context.get("risk_summary") or {}
    return (
        f"Server status: {server.get('status') or 'not selected'}. "
        f"Agent status: {server.get('agent_status') or 'unknown'}. "
        f"Latest baseline: {baseline.get('status') or 'not available'}. "
        f"Open risk counts: {risk.get('finding_counts_by_severity') or {}}."
    )


def _format_findings_response(context):
    findings = context.get("findings_summary") or []
    if not findings:
        return "No findings are present in the safe context."
    lines = [
        f"{finding.get('severity', 'info')}: {finding.get('title', 'Finding')} ({finding.get('status', 'open')})"
        for finding in findings[:5]
    ]
    return "Findings in safe context: " + "; ".join(lines)


def _format_reports_response(context):
    reports = context.get("reports_summary") or []
    if not reports:
        return "No reports are present in the safe context."
    lines = [
        f"{report.get('report_type', 'report')}: {report.get('title', 'Untitled')} ({report.get('status', 'unknown')})"
        for report in reports[:5]
    ]
    return "Reports in safe context: " + "; ".join(lines)


def _format_tools_response(context):
    tools = context.get("available_tools") or []
    if not tools:
        return "No tools are currently available to this role and server through policy."
    keys = [tool.get("key", "tool") for tool in tools[:10]]
    return "Available read-only tools through policy: " + ", ".join(keys)


def _format_tool_results_response(context):
    tool_runs = context.get("recent_tool_runs") or []
    for tool_run in tool_runs:
        if tool_run.get("result_summary"):
            return tool_run["result_summary"]
    if tool_runs:
        latest = tool_runs[0]
        return f"Latest tool run {latest.get('tool_key', 'tool')} is {latest.get('status', 'unknown')}."
    return "No recent tool run results are present in the safe context."


def _format_summary_response(context):
    baseline = context.get("baseline_summary") or {}
    return (
        "Safe context summary: "
        f"baseline={baseline.get('status') or 'not available'}, "
        f"applications={_section_count(context, 'applications_summary')}, "
        f"services={_section_count(context, 'services_summary')}, "
        f"domains={_section_count(context, 'domains_summary')}, "
        f"findings={_section_count(context, 'findings_summary')}, "
        f"reports={_section_count(context, 'reports_summary')}."
    )


def _technical_report_sections(context):
    server = context.get("server_summary") or {}
    baseline = context.get("baseline_summary") or {}
    sections = [
        {
            "section_type": ReportSection.SectionType.SUMMARY,
            "title": "Technical summary",
            "body": (
                f"Server status: {server.get('status') or 'unknown'}\n"
                f"Agent status: {server.get('agent_status') or 'unknown'}\n"
                f"Latest baseline: {baseline.get('status') or 'not available'}\n"
                f"Profile: {baseline.get('profile_key') or 'not available'}"
            ),
            "data": {},
        }
    ]
    sections.append(
        {
            "section_type": ReportSection.SectionType.TOOLS_EXECUTED,
            "title": "Recent tool activity",
            "body": _technical_tool_activity_body(context),
            "data": {},
        }
    )
    sections.append(
        {
            "section_type": ReportSection.SectionType.FINDINGS,
            "title": "Findings snapshot",
            "body": _technical_findings_body(context),
            "data": {},
        }
    )
    sections.append(
        {
            "section_type": ReportSection.SectionType.DEVELOPER_NOTES,
            "title": "Draft notes",
            "body": (
                "This draft is based on redacted safe context only. Raw ToolRun output, AgentJob output, logs, "
                "and environment data are intentionally excluded."
            ),
            "data": {},
        }
    )
    return sections


def _customer_report_sections(context):
    server = context.get("server_summary") or {}
    findings = context.get("findings_summary") or []
    open_findings = [item for item in findings if item.get("status") == "open"]
    sections = [
        {
            "section_type": ReportSection.SectionType.SUMMARY,
            "title": "Customer summary",
            "body": (
                f"The server is currently {server.get('status') or 'under review'}. "
                f"There are {len(open_findings)} open finding(s) in the current safe summary."
            ),
            "data": {},
        },
        {
            "section_type": ReportSection.SectionType.FINDINGS,
            "title": "Customer-visible findings",
            "body": _customer_findings_body(context),
            "data": {},
        },
        {
            "section_type": ReportSection.SectionType.RECOMMENDATIONS,
            "title": "Recommended next review",
            "body": (
                "Advisory only: review the summarized findings and confirm priorities in the normal operational workflow. "
                "No automated action is performed from this report."
            ),
            "data": {},
        },
    ]
    return sections


def _render_multiline_rows(rows, *, empty_text):
    cleaned = [redact_secrets((row or "").strip()) for row in rows if (row or "").strip()]
    return "\n".join(cleaned) if cleaned else empty_text


def _safe_tool_result_summary(tool_run):
    result = tool_run.result_redacted if isinstance(tool_run.result_redacted, dict) else {}
    if result:
        chat_summary = summarize_tool_result_for_chat(tool_run.tool_definition, result, language="ar")
        if chat_summary:
            return _safe_text(chat_summary, limit=MAX_RESPONSE_LENGTH)
    base_summary = _safe_text(summarize_tool_run_result(tool_run), limit=MAX_RESPONSE_LENGTH)
    result = tool_run.result_redacted if isinstance(tool_run.result_redacted, dict) else {}
    bullets = []
    if result:
        status = result.get("status") or result.get("result") or ""
        if status:
            bullets.append(f"- حالة نتيجة الأداة: {_safe_text(str(status), limit=120)}")
        summary = result.get("summary") or result.get("message") or result.get("description") or ""
        if isinstance(summary, str) and summary.strip():
            bullets.append(f"- {_safe_text(summary, limit=500)}")
        output = result.get("output") if isinstance(result.get("output"), dict) else {}
        if output:
            for key, value in list(output.items())[:5]:
                if isinstance(value, (str, int, float, bool)) and str(value).strip():
                    bullets.append(f"- {_safe_text(str(key), limit=80)}: {_safe_text(str(value), limit=240)}")
    if not bullets and base_summary:
        bullets.append(f"- {base_summary}")
    if not bullets:
        bullets.append("- تم تنفيذ الفحص بنجاح، لكن النتيجة التفصيلية محفوظة في سجل التشغيل وتحتاج مراجعة من صفحة ToolRun.")
    return _safe_text("\n".join(bullets[:6]), limit=MAX_RESPONSE_LENGTH)


def _technical_tool_activity_body(context):
    tool_runs = context.get("recent_tool_runs") or []
    lines = ["Recent read-only tool activity:"]
    for item in tool_runs[:10]:
        line = f"- {item.get('tool_key', 'tool')}: {item.get('status', 'unknown')}"
        finished_at = item.get("finished_at") or ""
        result_summary = item.get("result_summary") or ""
        if finished_at:
            line += f" at {finished_at}"
        if result_summary:
            line += f" - {result_summary}"
        lines.append(line)
    return _render_multiline_rows(lines, empty_text="No recent read-only tool activity is currently included.")


def _technical_findings_body(context):
    findings = context.get("findings_summary") or []
    lines = []
    for item in findings[:10]:
        line = f"- {item.get('title', 'Finding')}: {item.get('severity', 'info')} ({item.get('status', 'open')})"
        evidence = item.get("evidence_summary") or ""
        if evidence:
            line += f" - {evidence}"
        lines.append(line)
    return _render_multiline_rows(lines, empty_text="No safe finding summary rows are currently included.")


def _customer_findings_body(context):
    findings = context.get("findings_summary") or []
    lines = []
    for item in findings[:8]:
        lines.append(f"- {item.get('title', 'Finding')}: {item.get('severity', 'info')} ({item.get('status', 'open')})")
    return _render_multiline_rows(lines, empty_text="No customer-visible findings are currently listed in the safe summary.")


def _report_draft_content(session, report_type, context):
    server_summary = context.get("server_summary") or {}
    server_name = server_summary.get("name") or (session.server.name if session.server_id else "selected scope")
    if report_type == AdminChatReportDraft.DraftType.TECHNICAL_INTERNAL:
        return {
            "title": f"Technical internal report for {server_name}",
            "summary": (
                "Technical internal draft generated from safe context with read-only tool summaries and current findings."
            ),
            "sections": _technical_report_sections(context),
        }
    return {
        "title": f"Customer summary for {server_name}",
        "summary": "Customer-facing draft generated from safe context using high-level redacted summaries only.",
        "sections": _customer_report_sections(context),
    }


def _deterministic_response(intent, context):
    if intent == "tool_results":
        return _format_tool_results_response(context)
    if intent == "status":
        return _format_status_response(context)
    if intent == "findings":
        return _format_findings_response(context)
    if intent == "reports":
        return _format_reports_response(context)
    if intent == "available_tools":
        return _format_tools_response(context)
    return _format_summary_response(context)


def respond_to_message(*, user, session, user_message):
    if not user_can_write_chat(user, session):
        raise PermissionDenied
    context = build_safe_context(account=session.account, user=user, server=session.server)
    safe_context = redact_json(context)
    intent = _detect_intent(user_message.body_redacted)
    response_body = _safe_text(_deterministic_response(intent, safe_context), limit=MAX_RESPONSE_LENGTH)
    assistant_message = AdminChatMessage.objects.create(
        session=session,
        sender_type=AdminChatMessage.SenderType.ASSISTANT,
        body_redacted=response_body,
        metadata_redacted={"source": "deterministic_responder", "intent": intent},
    )
    decision_output = {
        "intent": intent,
        "response": response_body,
        "context_version": safe_context.get("context_version"),
        "section_counts": {
            "applications": _section_count(safe_context, "applications_summary"),
            "services": _section_count(safe_context, "services_summary"),
            "domains": _section_count(safe_context, "domains_summary"),
            "findings": _section_count(safe_context, "findings_summary"),
            "reports": _section_count(safe_context, "reports_summary"),
            "available_tools": _section_count(safe_context, "available_tools"),
        },
    }
    AdminChatDecision.objects.create(
        session=session,
        decision_type=AdminChatDecision.DecisionType.ANSWER,
        input_context_redacted=redact_json(
            {
                "message_id": str(user_message.id),
                "question": user_message.body_redacted,
                "context_version": safe_context.get("context_version"),
                "server_id": str(session.server_id) if session.server_id else "",
            }
        ),
        output_json_redacted=redact_json(decision_output),
        reasoning_summary="Deterministic context-only response.",
    )
    session.context_snapshot_redacted = safe_context
    session.last_message_at = assistant_message.created_at
    session.save(update_fields=["context_snapshot_redacted", "last_message_at", "updated_at"])
    return assistant_message


def add_user_message_and_response(*, user, session, body, metadata=None):
    user_message = add_user_message(user=user, session=session, body=body, metadata=metadata)
    assistant_message = respond_to_message(user=user, session=session, user_message=user_message)
    return user_message, assistant_message


def _available_tool_keys_for_session(user, session):
    context = build_safe_context(account=session.account, user=user, server=session.server)
    return {tool.get("key") for tool in context.get("available_tools", []) if tool.get("key")}


def _validate_ai_tool_params(params):
    params = params or {}
    if not isinstance(params, dict):
        raise ValidationError("Tool proposal parameters must be an object.")
    allowed_keys = {"scope"}
    if set(params) - allowed_keys:
        raise ValidationError("Tool proposal parameters are not allowed for this read-only flow.")
    scope = params.get("scope", "selected_server")
    if scope not in {"selected_server", ""}:
        raise ValidationError("Tool proposal scope must be selected_server.")
    return {}


def _execution_params_for_request(tool_request):
    params = tool_request.params_redacted or {}
    if isinstance(params, dict) and isinstance(params.get("tool_params"), dict):
        return params.get("tool_params") or {}
    return params


def tool_followup_timeout_for_count(tool_count):
    count = max(1, int(tool_count or 1))
    if count == 1:
        return AUTO_TOOL_SINGLE_MAX_WAIT_SECONDS
    return min(
        AUTO_TOOL_MULTI_MAX_WAIT_SECONDS,
        AUTO_TOOL_MULTI_BASE_WAIT_SECONDS + ((count - 1) * AUTO_TOOL_MULTI_EXTRA_WAIT_SECONDS),
    )


def _is_live_ai_tool_request(tool_request):
    return (tool_request.params_redacted or {}).get("source") == "live_ai_tool_proposal"


def _validate_ai_tool_definition(user, session, tool_key):
    if session.channel != AdminChatSession.Channel.ADMIN_INTERNAL:
        raise PermissionDenied
    if not session.server_id:
        raise ValidationError("A server-scoped chat session is required before requesting a tool.")
    if tool_key not in AI_READ_ONLY_TOOL_ALLOWLIST:
        raise ValidationError("Tool is not allowlisted for AI proposals.")
    if tool_key not in _available_tool_keys_for_session(user, session):
        raise ValidationError("Tool is not available to this role, plan, policy, and server.")
    try:
        tool_definition = ToolDefinition.objects.select_related("template", "policy").get(key=tool_key)
    except ToolDefinition.DoesNotExist as exc:
        raise ValidationError("Tool is not registered.") from exc
    if not tool_definition.is_enabled_for_mvp:
        raise ValidationError("Only enabled read-only tools can be proposed.")
    try:
        policy = tool_definition.policy
    except ToolPolicy.DoesNotExist as exc:
        raise ValidationError("Tool policy is missing.") from exc
    if not policy.is_active or not policy.allow_admin_run:
        raise ValidationError("Tool policy does not allow admin approval for this tool.")
    if policy.allowed_server_statuses and session.server.status not in policy.allowed_server_statuses:
        raise ValidationError("Server status is not allowed for this tool.")
    return tool_definition


def create_tool_request(*, user, session, tool_key, params=None, message=None):
    _require_session_writer(user, session)
    if session.status != AdminChatSession.Status.OPEN:
        raise ValidationError("Chat session is archived.")
    if not session.server_id:
        raise ValidationError("A server-scoped chat session is required before requesting a tool.")
    params = params or {}
    if params:
        raise ValidationError("Chat tool requests do not accept parameters in C5.")
    if tool_key not in _available_tool_keys_for_session(user, session):
        raise ValidationError("Tool is not available to this role, plan, policy, and server.")
    try:
        tool_definition = ToolDefinition.objects.get(key=tool_key)
    except ToolDefinition.DoesNotExist as exc:
        raise ValidationError("Tool is not registered.") from exc
    if not tool_definition.is_enabled_for_mvp:
        raise ValidationError("Only enabled read-only tools can be requested from chat.")
    request = AdminChatToolRequest.objects.create(
        session=session,
        message=message,
        tool_definition=tool_definition,
        params_redacted=redacted_json(params),
        status=AdminChatToolRequest.Status.SUGGESTED,
    )
    AdminChatDecision.objects.create(
        session=session,
        decision_type=AdminChatDecision.DecisionType.TOOL_REQUEST,
        input_context_redacted={"tool_key": redact_secrets(tool_key), "params": redacted_json(params)},
        output_json_redacted={"status": request.status, "tool_request_id": str(request.id)},
        reasoning_summary="Tool request created from available Safe Context tools; approval is required before execution.",
    )
    return request


def create_ai_tool_request_from_proposal(*, user, session, message, proposal, timeout_seconds=None):
    _require_session_writer(user, session)
    if session.status != AdminChatSession.Status.OPEN:
        raise ValidationError("Chat session is archived.")
    tool_key = _safe_text((proposal or {}).get("tool_slug") or "", limit=120)
    tool_params = _validate_ai_tool_params((proposal or {}).get("params") or {})
    tool_definition = _validate_ai_tool_definition(user, session, tool_key)
    reason = _safe_text((proposal or {}).get("reason") or "فحص قراءة فقط اقترحه Live AI.", limit=500)
    if AdminChatToolRequest.objects.filter(
        session=session,
        message=message,
        tool_definition=tool_definition,
        status=AdminChatToolRequest.Status.SUGGESTED,
    ).exists():
        return None
    request = AdminChatToolRequest.objects.create(
        session=session,
        message=message,
        tool_definition=tool_definition,
        params_redacted=redact_json(
            {
                "tool_params": tool_params,
                "scope": "selected_server",
                "reason": reason,
                "source": "live_ai_tool_proposal",
            }
        ),
        status=AdminChatToolRequest.Status.SUGGESTED,
    )
    AdminChatDecision.objects.create(
        session=session,
        decision_type=AdminChatDecision.DecisionType.TOOL_REQUEST,
        input_context_redacted=redact_json(
            {
                "source": "live_ai_tool_proposal",
                "message_id": str(message.id),
                "tool_key": tool_key,
            }
        ),
        output_json_redacted=redact_json(
            {
                "status": request.status,
                "tool_request_id": str(request.id),
                "tool_key": tool_definition.key,
                "reason": reason,
            }
        ),
        reasoning_summary="Live AI proposed an allowlisted read-only tool request. The backend will execute it through policy checks.",
    )
    return execute_ai_tool_request_with_followup(user=user, tool_request=request, timeout_seconds=timeout_seconds)


def create_ai_tool_requests_from_proposals(*, user, session, message, proposals):
    results = []
    timeout_seconds = tool_followup_timeout_for_count(len(proposals or []))
    for proposal in proposals or []:
        try:
            result = create_ai_tool_request_from_proposal(
                user=user,
                session=session,
                message=message,
                proposal=proposal,
                timeout_seconds=timeout_seconds,
            )
        except (PermissionDenied, ValidationError, ValueError):
            continue
        if result:
            results.append(result)
    if len(results) > 1:
        combined_message = _record_combined_tool_followup_message(session=session, results=results)
        _assign_chatkit_item_id(combined_message, f"tool_result_combined_{message.id}")
        results.append(
            {
                "tool_request": None,
                "tool_run": None,
                "start_message": None,
                "followup_message": combined_message,
                "outcome": {"state": "combined", "status": "completed", "tool_run_id": ""},
            }
        )
    return results


def approve_tool_request(*, user, tool_request):
    session = tool_request.session
    _require_session_writer(user, session)
    if tool_request.status != AdminChatToolRequest.Status.SUGGESTED:
        raise ValidationError("Only suggested tool requests can be approved.")
    if not session.server_id:
        raise ValidationError("Tool request is not server-scoped.")
    if _is_live_ai_tool_request(tool_request):
        tool_definition = _validate_ai_tool_definition(user, session, tool_request.tool_definition.key)
    else:
        tool_definition = tool_request.tool_definition
    params = _execution_params_for_request(tool_request)
    try:
        tool_run, _job = create_tool_run_job(
            account=session.account,
            server=session.server,
            tool_key=tool_definition.key,
            params=params,
            requested_by=user,
            requested_by_type=ToolRun.RequestedByType.ADMIN
            if session.channel == AdminChatSession.Channel.ADMIN_INTERNAL
            else ToolRun.RequestedByType.USER,
        )
    except ToolPolicyDenied as exc:
        tool_request.status = AdminChatToolRequest.Status.FAILED
        tool_request.error_summary = _safe_text(str(exc), limit=500)
        tool_request.save(update_fields=["status", "error_summary", "updated_at"])
        raise
    tool_request.status = AdminChatToolRequest.Status.QUEUED
    tool_request.tool_run = tool_run
    tool_request.approved_by = user
    tool_request.approved_at = timezone.now()
    tool_request.save(update_fields=["status", "tool_run", "approved_by", "approved_at", "updated_at"])
    AdminChatMessage.objects.create(
        session=session,
        sender_type=AdminChatMessage.SenderType.SYSTEM,
        body_redacted=(
            f'بدأت فحص قراءة فقط: "{tool_request.tool_definition.key}".\n'
            "سأتابع التنفيذ وأعرض النتيجة عند اكتماله."
        ),
        metadata_redacted={
            "source": "tool_orchestrator",
            "tool_request_id": str(tool_request.id),
            "tool_run_id": str(tool_run.id),
            "execution_started": True,
        },
    )
    AdminChatDecision.objects.create(
        session=session,
        decision_type=AdminChatDecision.DecisionType.TOOL_REQUEST,
        input_context_redacted={"tool_request_id": str(tool_request.id), "tool_key": tool_request.tool_definition.key},
        output_json_redacted={"status": tool_request.status, "tool_run_id": str(tool_run.id)},
        reasoning_summary="Approved chat tool request queued through create_tool_run_job.",
    )
    return tool_run


def _terminal_tool_outcome(tool_run):
    summary = _safe_tool_result_summary(tool_run)
    if tool_run.status == ToolRun.Status.SUCCEEDED:
        return {
            "state": "succeeded",
            "status": tool_run.status,
            "summary": summary,
            "tool_run_id": tool_run.id,
        }
    return {
        "state": "failed",
        "status": tool_run.status,
        "summary": summary or _safe_text(tool_run.error_message, limit=MAX_RESPONSE_LENGTH) or "لم يكتمل الفحص بنجاح.",
        "tool_run_id": tool_run.id,
    }


def wait_for_tool_execution_result(
    tool_run,
    *,
    timeout_seconds=AUTO_TOOL_FOLLOWUP_MAX_WAIT_SECONDS,
    poll_interval_seconds=AUTO_TOOL_FOLLOWUP_POLL_INTERVAL_SECONDS,
):
    deadline = time.monotonic() + max(0, timeout_seconds)
    grace_seconds = AUTO_TOOL_FINAL_GRACE_SECONDS
    terminal_statuses = {
        ToolRun.Status.SUCCEEDED,
        ToolRun.Status.FAILED,
        ToolRun.Status.REJECTED,
        ToolRun.Status.TIMEOUT,
        ToolRun.Status.CANCELLED,
    }
    while True:
        tool_run.refresh_from_db()
        if tool_run.status in terminal_statuses:
            return _terminal_tool_outcome(tool_run)
        if time.monotonic() >= deadline:
            if grace_seconds > 0:
                time.sleep(grace_seconds)
                tool_run.refresh_from_db()
                if tool_run.status in terminal_statuses:
                    return _terminal_tool_outcome(tool_run)
            return {
                "state": "timeout",
                "status": tool_run.status,
                "summary": (
                    "لم يكتمل الفحص خلال مدة الانتظار. قد يكون التنفيذ ما زال في قائمة الانتظار "
                    "أو أن عامل التنفيذ لم ينه المهمة بعد."
                ),
                "tool_run_id": tool_run.id,
            }
        time.sleep(max(0.1, poll_interval_seconds))


def _summary_is_full_chat_body(summary):
    normalized = summary or ""
    heading_markers = (
        "\u0627\u0644\u062e\u0644\u0627\u0635\u0629:",
        "\u0627\u0644\u062a\u0641\u0633\u064a\u0631:",
        "Ø§Ù„Ø®Ù„Ø§ØµØ©:",
        "Ø§Ù„ØªÙØ³ÙŠØ±:",
    )
    return any(marker in normalized for marker in heading_markers)


def _tool_followup_body(tool_request, outcome):
    tool_key = tool_request.tool_definition.key
    state = outcome.get("state")
    status = outcome.get("status") or "unknown"
    summary = _safe_text(outcome.get("summary") or "", limit=MAX_RESPONSE_LENGTH)
    if state == "succeeded":
        if _summary_is_full_chat_body(summary):
            return _safe_text(summary, limit=MAX_RESPONSE_LENGTH)
        return _safe_text(
            f'اكتمل الفحص بنجاح: "{tool_key}".\n\n'
            f"الخلاصة:\n{summary}\n\n"
            "التفسير:\nهذا فحص قراءة فقط ولم يغير أي إعدادات على السيرفر.",
            limit=MAX_RESPONSE_LENGTH,
        )
    if state == "failed":
        return _safe_text(
            f'فشل تنفيذ الفحص: "{tool_key}".\n\n'
            f"السبب:\n{summary or status}",
            limit=MAX_RESPONSE_LENGTH,
        )
    if state == "timeout":
        return _safe_text(
            "بدأ الفحص، لكنه لم يكتمل خلال مدة الانتظار.\n\n"
            f"الحالة الحالية:\n{status}\n\n"
            "التفسير:\nقد يكون التنفيذ ما زال في قائمة الانتظار أو أن عامل التنفيذ لم ينه المهمة بعد.",
            limit=MAX_RESPONSE_LENGTH,
        )
    return _safe_text(
        f'لم أتمكن من بدء الفحص: "{tool_key}".\n\n'
        f"السبب:\n{summary or status}",
        limit=MAX_RESPONSE_LENGTH,
    )


def _record_tool_followup_message(tool_request, outcome):
    body = _tool_followup_body(tool_request, outcome)
    source_by_state = {
        "succeeded": "tool_result_summary",
        "failed": "tool_result_failed",
        "timeout": "tool_result_timeout",
        "not_started": "tool_result_not_started",
    }
    source = source_by_state.get(outcome.get("state"), "tool_result_timeout")
    message = AdminChatMessage.objects.create(
        session=tool_request.session,
        sender_type=AdminChatMessage.SenderType.ASSISTANT,
        body_redacted=body,
        metadata_redacted=redact_json(
            {
                "source": source,
                "tool_request_id": str(tool_request.id),
                "tool_run_id": str(outcome.get("tool_run_id") or ""),
                "tool_key": tool_request.tool_definition.key,
                "state": outcome.get("state"),
                "status": outcome.get("status"),
            }
        ),
    )
    tool_request.session.last_message_at = message.created_at
    tool_request.session.save(update_fields=["last_message_at", "updated_at"])
    AdminChatDecision.objects.create(
        session=tool_request.session,
        decision_type=AdminChatDecision.DecisionType.TOOL_REQUEST,
        input_context_redacted={
            "tool_request_id": str(tool_request.id),
            "tool_key": tool_request.tool_definition.key,
            "tool_run_id": str(outcome.get("tool_run_id") or ""),
        },
        output_json_redacted=redact_json(
            {
                "state": outcome.get("state"),
                "status": outcome.get("status"),
                "summary": body,
            }
        ),
        reasoning_summary="Automatic read-only tool execution follow-up stored a safe chat summary.",
    )
    return message


def _latest_tool_start_message(tool_request):
    return (
        AdminChatMessage.objects.filter(
            session=tool_request.session,
            metadata_redacted__source="tool_orchestrator",
            metadata_redacted__tool_request_id=str(tool_request.id),
        )
        .order_by("-created_at")
        .first()
    )


def _assign_chatkit_item_id(message, item_id):
    if not message:
        return None
    metadata = dict(message.metadata_redacted or {})
    metadata["chatkit_item_id"] = item_id
    message.metadata_redacted = redact_json(metadata)
    message.save(update_fields=["metadata_redacted", "updated_at"])
    return message


def _record_combined_tool_followup_message(*, session, results):
    lines = ["اكتملت متابعة الفحوصات التالية:", "", "النتائج:"]
    for result in results:
        tool_request = result.get("tool_request")
        outcome = result.get("outcome") or {}
        tool_key = tool_request.tool_definition.key if tool_request else "tool"
        state = outcome.get("state") or "unknown"
        status = outcome.get("status") or "unknown"
        state_label = {
            "succeeded": "نجح",
            "failed": "فشل",
            "timeout": "لم يكتمل خلال المهلة",
            "not_started": "لم يبدأ",
        }.get(state, state)
        lines.append(f"- {tool_key}: {state_label} ({status})")
    lines.extend(["", "الخلاصة العامة:", "تم تنفيذ الفحوصات الصالحة فقط عبر المسار المعتمد للأدوات read-only."])
    message = AdminChatMessage.objects.create(
        session=session,
        sender_type=AdminChatMessage.SenderType.ASSISTANT,
        body_redacted=_safe_text("\n".join(lines), limit=MAX_RESPONSE_LENGTH),
        metadata_redacted=redact_json(
            {
                "source": "tool_result_summary",
                "mode": "combined",
                "tool_request_ids": [str((result.get("tool_request")).id) for result in results if result.get("tool_request")],
                "states": [(result.get("outcome") or {}).get("state") for result in results],
            }
        ),
    )
    session.last_message_at = message.created_at
    session.save(update_fields=["last_message_at", "updated_at"])
    return message


def execute_ai_tool_request_with_followup(*, user, tool_request, timeout_seconds=None):
    if not _is_live_ai_tool_request(tool_request):
        raise ValidationError("Only Live AI tool proposals can be auto-executed.")
    try:
        tool_run = approve_tool_request(user=user, tool_request=tool_request)
    except (ToolPolicyDenied, ValidationError, PermissionDenied) as exc:
        tool_request.refresh_from_db()
        if tool_request.status == AdminChatToolRequest.Status.SUGGESTED:
            tool_request.status = AdminChatToolRequest.Status.FAILED
            tool_request.error_summary = _safe_text(str(exc), limit=500)
            tool_request.save(update_fields=["status", "error_summary", "updated_at"])
        outcome = {
            "state": "not_started",
            "status": tool_request.status,
            "summary": _safe_text(str(exc), limit=MAX_RESPONSE_LENGTH),
            "tool_run_id": "",
        }
        followup_message = _record_tool_followup_message(tool_request, outcome)
        _assign_chatkit_item_id(followup_message, f"tool_result_{tool_request.id}")
        return {
            "tool_request": tool_request,
            "tool_run": None,
            "start_message": None,
            "followup_message": followup_message,
            "outcome": outcome,
        }
    start_message = _assign_chatkit_item_id(_latest_tool_start_message(tool_request), f"tool_start_{tool_request.id}")
    outcome = wait_for_tool_execution_result(
        tool_run,
        timeout_seconds=timeout_seconds or AUTO_TOOL_FOLLOWUP_MAX_WAIT_SECONDS,
    )
    outcome["tool_run_id"] = outcome.get("tool_run_id") or tool_run.id
    tool_request.refresh_from_db()
    if outcome["state"] == "succeeded":
        tool_request.status = AdminChatToolRequest.Status.SUCCEEDED
    elif outcome["state"] == "failed":
        tool_request.status = AdminChatToolRequest.Status.FAILED
        tool_request.error_summary = _safe_text(outcome.get("summary") or "", limit=500)
    else:
        tool_request.status = AdminChatToolRequest.Status.QUEUED
    tool_request.save(update_fields=["status", "error_summary", "updated_at"])
    followup_message = _record_tool_followup_message(tool_request, outcome)
    _assign_chatkit_item_id(followup_message, f"tool_result_{tool_request.id}")
    return {
        "tool_request": tool_request,
        "tool_run": tool_run,
        "start_message": start_message,
        "followup_message": followup_message,
        "outcome": outcome,
    }


def reject_tool_request(*, user, tool_request):
    session = tool_request.session
    _require_session_writer(user, session)
    if tool_request.status != AdminChatToolRequest.Status.SUGGESTED:
        raise ValidationError("Only suggested tool requests can be rejected.")
    tool_request.status = AdminChatToolRequest.Status.CANCELLED
    tool_request.approved_by = user
    tool_request.approved_at = timezone.now()
    tool_request.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    AdminChatMessage.objects.create(
        session=session,
        sender_type=AdminChatMessage.SenderType.SYSTEM,
        body_redacted=f"Read-only tool request rejected: {tool_request.tool_definition.key}",
        metadata_redacted={"source": "tool_request_approval", "tool_request_id": str(tool_request.id), "decision": "rejected"},
    )
    AdminChatDecision.objects.create(
        session=session,
        decision_type=AdminChatDecision.DecisionType.TOOL_REQUEST,
        input_context_redacted={"tool_request_id": str(tool_request.id), "tool_key": tool_request.tool_definition.key},
        output_json_redacted={"status": tool_request.status, "decision": "rejected"},
        reasoning_summary="Matrix Admin rejected the read-only chat tool request. No ToolRun or AgentJob was created.",
    )
    return tool_request


def sync_chat_tool_requests_for_tool_run(tool_run):
    if not tool_run:
        return
    terminal_status_map = {
        ToolRun.Status.SUCCEEDED: AdminChatToolRequest.Status.SUCCEEDED,
        ToolRun.Status.FAILED: AdminChatToolRequest.Status.FAILED,
        ToolRun.Status.REJECTED: AdminChatToolRequest.Status.FAILED,
        ToolRun.Status.TIMEOUT: AdminChatToolRequest.Status.FAILED,
        ToolRun.Status.CANCELLED: AdminChatToolRequest.Status.CANCELLED,
    }
    request_status = terminal_status_map.get(tool_run.status)
    if not request_status:
        return
    result_summary = _safe_text(summarize_tool_run_result(tool_run), limit=MAX_RESPONSE_LENGTH)
    for tool_request in tool_run.chat_tool_requests.select_related("session", "tool_definition"):
        update_fields = ["status", "updated_at"]
        tool_request.status = request_status
        if tool_run.error_message:
            tool_request.error_summary = _safe_text(tool_run.error_message, limit=500)
            update_fields.append("error_summary")
        tool_request.save(update_fields=update_fields)
        body = result_summary or f"Tool result received for {tool_request.tool_definition.key}."
        message = AdminChatMessage.objects.create(
            session=tool_request.session,
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            body_redacted=body,
            metadata_redacted={
                "source": "tool_result_summary",
                "tool_request_id": str(tool_request.id),
                "tool_run_id": str(tool_run.id),
                "tool_key": tool_request.tool_definition.key,
                "tool_status": tool_run.status,
            },
        )
        tool_request.session.last_message_at = message.created_at
        tool_request.session.save(update_fields=["last_message_at", "updated_at"])
        AdminChatDecision.objects.create(
            session=tool_request.session,
            decision_type=AdminChatDecision.DecisionType.TOOL_REQUEST,
            input_context_redacted={"tool_run_id": str(tool_run.id), "tool_key": tool_request.tool_definition.key},
            output_json_redacted={
                "tool_request_id": str(tool_request.id),
                "status": request_status,
                "tool_status": tool_run.status,
                "result_summary": body,
            },
            reasoning_summary="Safe summary generated from the redacted tool result for chat display.",
        )


def create_tool_build_request_from_chat(
    *,
    user,
    session,
    title,
    desired_tool_key,
    command_argv_template,
    allowed_binaries,
    blocked_tokens=None,
    description="",
    expected_output_description="",
    message=None,
):
    _require_session_writer(user, session)
    if session.channel != AdminChatSession.Channel.ADMIN_INTERNAL:
        raise PermissionDenied
    if session.status != AdminChatSession.Status.OPEN:
        raise ValidationError("Chat session is archived.")
    build_request = ToolBuildRequest.objects.create(
        requested_by=user,
        source_chat_session=session,
        source_chat_message=message,
        title=sanitize_builder_text(title, limit=160),
        description_redacted=sanitize_builder_text(description),
        desired_tool_key=desired_tool_key,
        desired_handler_key="",
        desired_execution_type=ToolTemplate.ExecutionType.COMMAND_TEMPLATE,
        command_argv_template=redact_json(command_argv_template or []),
        allowed_binaries=redact_json(allowed_binaries or []),
        blocked_tokens=redact_json(blocked_tokens or []),
        expected_output_description_redacted=sanitize_builder_text(expected_output_description, limit=500),
        status=ToolBuildRequest.Status.DRAFT,
    )
    proposal = generate_tool_build_proposal(build_request, actor_user=user)
    AdminChatMessage.objects.create(
        session=session,
        sender_type=AdminChatMessage.SenderType.SYSTEM,
        body_redacted=f"Tool builder proposal created: {build_request.desired_tool_key}",
        metadata_redacted={
            "source": "tool_builder_chat",
            "tool_build_request_id": str(build_request.id),
            "tool_build_proposal_id": str(proposal.id),
            "status": proposal.status,
        },
    )
    AdminChatDecision.objects.create(
        session=session,
        decision_type=AdminChatDecision.DecisionType.TOOL_BUILD_REQUEST,
        input_context_redacted=redact_json(
            {
                "title": title,
                "desired_tool_key": desired_tool_key,
                "execution_type": ToolTemplate.ExecutionType.COMMAND_TEMPLATE,
                "command_argv_template": command_argv_template or [],
                "allowed_binaries": allowed_binaries or [],
                "blocked_tokens": blocked_tokens or [],
                "expected_output_description": expected_output_description,
            }
        ),
        output_json_redacted=redact_json(
            {
                "tool_build_request_id": str(build_request.id),
                "tool_build_proposal_id": str(proposal.id),
                "proposal_status": proposal.status,
                "validation_errors": proposal.validation_errors,
            }
        ),
        reasoning_summary="Chat-created command_template proposal stored for Matrix Admin review only.",
    )
    return build_request, proposal


def create_chat_report_draft(*, user, session, report_type, message=None):
    _require_session_writer(user, session)
    if session.channel != AdminChatSession.Channel.ADMIN_INTERNAL:
        raise PermissionDenied
    if session.status != AdminChatSession.Status.OPEN:
        raise ValidationError("Chat session is archived.")
    if report_type not in AdminChatReportDraft.DraftType.values:
        raise ValidationError("Unsupported chat report type.")
    return _create_report_draft_record(
        user=user,
        session=session,
        report_type=report_type,
        message=message,
        status=AdminChatReportDraft.Status.PENDING_REVIEW,
        reasoning_summary="Deterministic chat report draft created from safe context for Matrix Admin review.",
        system_message=f"Report draft created: {report_type}",
    )


def _create_report_draft_record(*, user, session, report_type, message=None, status, reasoning_summary, system_message):
    context = build_safe_context(account=session.account, user=user, server=session.server)
    safe_context = redact_json(context)
    content = _report_draft_content(session, report_type, safe_context)
    draft = AdminChatReportDraft.objects.create(
        session=session,
        message=message,
        created_by=user,
        report_type=report_type,
        status=AdminChatReportDraft.Status.PENDING_REVIEW,
        title_redacted=_safe_text(content["title"], limit=255),
        summary_redacted=_safe_text(content["summary"], limit=MAX_RESPONSE_LENGTH),
        sections_redacted=redact_json(content["sections"]),
        source_snapshot_redacted=redact_json(
            {
                "context_version": safe_context.get("context_version"),
                "server_id": str(session.server_id) if session.server_id else "",
                "application_id": str(session.application_id) if session.application_id else "",
                "report_type": report_type,
            }
        ),
    )
    AdminChatMessage.objects.create(
        session=session,
        sender_type=AdminChatMessage.SenderType.SYSTEM,
        body_redacted=_safe_text(system_message, limit=255),
        metadata_redacted={
            "source": "chat_report_draft",
            "report_draft_id": str(draft.id),
            "status": draft.status,
        },
    )
    AdminChatDecision.objects.create(
        session=session,
        decision_type=AdminChatDecision.DecisionType.REPORT_REQUEST,
        input_context_redacted=redact_json(
            {
                "report_type": report_type,
                "server_id": str(session.server_id) if session.server_id else "",
                "application_id": str(session.application_id) if session.application_id else "",
            }
        ),
        output_json_redacted=redact_json(
            {
                "report_draft_id": str(draft.id),
                "status": draft.status,
                "title": draft.title_redacted,
            }
        ),
        reasoning_summary=reasoning_summary,
    )
    return draft


def create_chat_report(*, user, session, report_type, message=None):
    _require_session_writer(user, session)
    if session.status != AdminChatSession.Status.OPEN:
        raise ValidationError("Chat session is archived.")
    if report_type not in AdminChatReportDraft.DraftType.values:
        raise ValidationError("Unsupported chat report type.")
    if session.channel == AdminChatSession.Channel.PORTAL_CUSTOMER and report_type != AdminChatReportDraft.DraftType.CUSTOMER_SUMMARY:
        raise ValidationError("Portal chat can create customer summary reports only.")
    draft = _create_report_draft_record(
        user=user,
        session=session,
        report_type=report_type,
        message=message,
        status=AdminChatReportDraft.Status.APPROVED,
        reasoning_summary="Safe chat report created for immediate conversion after safety validation.",
        system_message=f"Report prepared: {report_type}",
    )
    note = (
        "Portal self-service chat report auto-converted after safety validation."
        if session.channel == AdminChatSession.Channel.PORTAL_CUSTOMER
        else "Matrix Admin internal chat report auto-converted after safety validation."
    )
    report = _convert_chat_report_draft_record(draft, reviewer=user if user.is_staff else None, review_notes=note)
    return draft, report


def review_chat_report_draft(draft, *, reviewer, decision, notes=""):
    _require_matrix_admin(reviewer)
    if decision not in {AdminChatReportDraft.Status.APPROVED, AdminChatReportDraft.Status.REJECTED}:
        raise ValidationError("Unsupported report draft review decision.")
    draft.status = decision
    draft.reviewed_by = reviewer
    draft.reviewed_at = timezone.now()
    draft.review_notes_redacted = _safe_text(notes, limit=1000)
    draft.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_notes_redacted", "updated_at"])
    AdminChatDecision.objects.create(
        session=draft.session,
        decision_type=AdminChatDecision.DecisionType.REPORT_REQUEST,
        input_context_redacted={"report_draft_id": str(draft.id), "report_type": draft.report_type},
        output_json_redacted={"status": draft.status, "reviewed_by": str(reviewer.id)},
        reasoning_summary="Matrix Admin reviewed chat report draft before conversion.",
    )
    return draft


def convert_chat_report_draft(draft, *, reviewer):
    _require_matrix_admin(reviewer)
    if draft.status != AdminChatReportDraft.Status.APPROVED:
        raise ValidationError("Only approved report drafts can be converted.")
    return _convert_chat_report_draft_record(draft, reviewer=reviewer, review_notes="")


def _convert_chat_report_draft_record(draft, *, reviewer=None, review_notes=""):
    report = Report.objects.create(
        account=draft.session.account,
        server=draft.session.server,
        application=draft.session.application,
        generated_by=reviewer,
        report_type=draft.report_type,
        title=draft.title_redacted,
        summary_redacted=draft.summary_redacted,
        source_snapshot_redacted=redact_json(
            {
                **(draft.source_snapshot_redacted or {}),
                "chat_session_id": str(draft.session_id),
                "chat_report_draft_id": str(draft.id),
                "reviewed_by": str(reviewer.id) if reviewer else "",
            }
        ),
        generated_at=timezone.now(),
    )
    for index, section in enumerate(draft.sections_redacted or [], start=1):
        ReportSection.objects.create(
            report=report,
            section_type=section.get("section_type") or ReportSection.SectionType.SUMMARY,
            title=_safe_text(section.get("title", ""), limit=255),
            body_redacted=_safe_text(section.get("body", ""), limit=8000),
            data_redacted=redact_json(section.get("data", {})),
            order=index * 10,
    )
    draft.status = AdminChatReportDraft.Status.CONVERTED
    draft.converted_report = report
    draft.reviewed_by = reviewer
    draft.reviewed_at = timezone.now()
    if review_notes:
        draft.review_notes_redacted = _safe_text(review_notes, limit=1000)
        draft.save(
            update_fields=[
                "status",
                "converted_report",
                "reviewed_by",
                "reviewed_at",
                "review_notes_redacted",
                "updated_at",
            ]
        )
    else:
        draft.save(update_fields=["status", "converted_report", "reviewed_by", "reviewed_at", "updated_at"])
    AdminChatDecision.objects.create(
        session=draft.session,
        decision_type=AdminChatDecision.DecisionType.REPORT_REQUEST,
        input_context_redacted={"report_draft_id": str(draft.id), "report_type": draft.report_type},
        output_json_redacted={"status": draft.status, "report_id": str(report.id), "report_type": report.report_type},
        reasoning_summary="Approved chat report draft converted to final report with redacted sections only.",
    )
    return report
