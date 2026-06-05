from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.ai_context.services import build_safe_context
from apps.applications.models import Application
from apps.core.redaction import redact_json, redact_secrets
from apps.servers.models import Server
from apps.tools.models import ToolBuildProposal, ToolBuildRequest, ToolDefinition, ToolRun, ToolTemplate
from apps.tools.services import (
    ToolPolicyDenied,
    create_tool_run_job,
    generate_tool_build_proposal,
    redacted_json,
    sanitize_builder_text,
)

from .models import AdminChatDecision, AdminChatMessage, AdminChatSession, AdminChatToolRequest


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


def _available_tool_keys_for_session(user, session):
    context = build_safe_context(account=session.account, user=user, server=session.server)
    return {tool.get("key") for tool in context.get("available_tools", []) if tool.get("key")}


def create_tool_request(*, user, session, tool_key, params=None, message=None):
    _require_chat_writer(user)
    if not user_can_write_chat(user, session):
        raise PermissionDenied
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


def approve_tool_request(*, user, tool_request):
    _require_chat_writer(user)
    session = tool_request.session
    if not user_can_write_chat(user, session):
        raise PermissionDenied
    if tool_request.status != AdminChatToolRequest.Status.SUGGESTED:
        raise ValidationError("Only suggested tool requests can be approved.")
    if not session.server_id:
        raise ValidationError("Tool request is not server-scoped.")
    params = tool_request.params_redacted or {}
    try:
        tool_run, _job = create_tool_run_job(
            account=session.account,
            server=session.server,
            tool_key=tool_request.tool_definition.key,
            params=params,
            requested_by=user,
            requested_by_type=ToolRun.RequestedByType.USER,
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
        body_redacted=f"Tool request queued: {tool_request.tool_definition.key}",
        metadata_redacted={"source": "tool_orchestrator", "tool_request_id": str(tool_request.id), "tool_run_id": str(tool_run.id)},
    )
    AdminChatDecision.objects.create(
        session=session,
        decision_type=AdminChatDecision.DecisionType.TOOL_REQUEST,
        input_context_redacted={"tool_request_id": str(tool_request.id), "tool_key": tool_request.tool_definition.key},
        output_json_redacted={"status": tool_request.status, "tool_run_id": str(tool_run.id)},
        reasoning_summary="Approved chat tool request queued through create_tool_run_job.",
    )
    return tool_run


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
    _require_chat_writer(user)
    if not user_can_write_chat(user, session):
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
