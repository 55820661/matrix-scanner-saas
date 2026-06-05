from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.ai_context.services import build_safe_context
from apps.applications.models import Application
from apps.core.redaction import redact_json, redact_secrets
from apps.servers.models import Server

from .models import AdminChatDecision, AdminChatMessage, AdminChatSession


MAX_MESSAGE_LENGTH = 4000
MAX_TITLE_LENGTH = 160
MAX_RESPONSE_LENGTH = 3000


def _safe_text(value, *, limit):
    text = redact_secrets(value or "").strip()
    if len(text) > limit:
        return f"{text[:limit]}..."
    return text


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


def user_can_view_chat(user, session):
    if not user or not user.is_authenticated or user.account_id is None:
        return False
    return user.account_id == session.account_id and user.role in {
        User.CustomerRole.OWNER,
        User.CustomerRole.OPERATOR,
        User.CustomerRole.VIEWER,
    }


def user_can_write_chat(user, session):
    return user_can_view_chat(user, session) and user.role in {User.CustomerRole.OWNER, User.CustomerRole.OPERATOR}


def _resolve_server(user, server_id):
    if not server_id:
        return None
    return Server.objects.filter(account=user.account, id=server_id).first()


def _resolve_application(user, application_id, server=None):
    if not application_id:
        return None
    queryset = Application.objects.filter(account=user.account, id=application_id)
    if server:
        queryset = queryset.filter(server=server)
    return queryset.first()


def create_chat_session(*, user, title="", server_id=None, application_id=None):
    _require_chat_writer(user)
    server = _resolve_server(user, server_id)
    if server_id and server is None:
        raise ValidationError("Selected server is not available.")
    application = _resolve_application(user, application_id, server=server)
    if application_id and application is None:
        raise ValidationError("Selected application is not available.")
    if application and server is None:
        server = application.server

    title_redacted = _safe_text(title or "New chat", limit=MAX_TITLE_LENGTH)
    context_snapshot = build_safe_context(account=user.account, user=user, server=server)
    session = AdminChatSession(
        account=user.account,
        user=user,
        server=server,
        application=application,
        title_redacted=title_redacted,
        context_snapshot_redacted=redact_json(context_snapshot),
        last_message_at=timezone.now(),
    )
    session.full_clean()
    session.save()
    return session


def add_user_message(*, user, session, body, metadata=None):
    _require_chat_writer(user)
    if not user_can_write_chat(user, session):
        raise PermissionDenied
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


def _deterministic_response(intent, context):
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
