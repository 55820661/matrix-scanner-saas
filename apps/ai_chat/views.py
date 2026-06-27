import json
import logging
from time import monotonic

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from chatkit.server import StreamingResult

from apps.accounts.models import Account
from apps.applications.models import Application
from apps.core.redaction import redact_json
from apps.servers.models import Server

from .chatkit_store import AdminChatKitContext
from .live_ai import (
    LIVE_AI_SAFE_ERROR_MESSAGE,
    classify_live_ai_exception,
    classify_configuration_error,
    create_live_ai_request_log,
    live_admin_chatkit_server,
    live_ai_configuration_error,
    update_live_ai_request_log,
)
from .models import AdminChatMessage, AdminChatReportDraft, AdminChatSession, AdminLiveAIRequestLog
from .services import (
    add_user_message_and_response,
    approve_tool_request,
    create_admin_chat_session,
    create_chat_report,
    create_chat_report_draft,
    create_tool_build_request_from_chat,
    create_tool_request,
    reject_tool_request,
    user_can_write_chat,
)


logger = logging.getLogger(__name__)


def _newline_list(value):
    return [line.strip() for line in (value or "").splitlines() if line.strip()]


def _scoped_internal_chat_sessions():
    return (
        AdminChatSession.objects.select_related("account", "server", "application", "user")
        .filter(channel=AdminChatSession.Channel.ADMIN_INTERNAL)
    )


def _elapsed_ms(started_at):
    return max(1, int((monotonic() - started_at) * 1000))


def _live_ai_failure_log_extra(*, session_id, audit_log_id, status, error_class, model, latency_ms):
    return {
        "session_id": str(session_id),
        "audit_id": str(audit_log_id or ""),
        "status": status,
        "error_class": error_class,
        "model": model or "",
        "latency_ms": latency_ms,
    }


LIVE_AI_GENERATION_REQUEST_TYPES = {"threads.create", "threads.add_user_message", "threads.retry_after_item"}


def _is_live_ai_generation_request(payload):
    return payload.get("type") in LIVE_AI_GENERATION_REQUEST_TYPES


def _response_size_bytes(value):
    if isinstance(value, bytes):
        return len(value)
    return len(str(value).encode("utf-8"))


async def _stream_live_ai_result(result, *, audit_log_id, session_id, started_at):
    try:
        async for chunk in result:
            yield chunk
    except Exception as exc:
        error_class = classify_live_ai_exception(exc)
        latency_ms = _elapsed_ms(started_at)
        await sync_to_async(update_live_ai_request_log, thread_sensitive=True)(
            audit_log_id,
            status=AdminLiveAIRequestLog.Status.FAILED,
            latency_ms=latency_ms,
            response_size_bytes=0,
            error_class=error_class,
            fallback_used=True,
        )
        logger.error(
            "Live AI streaming request failed",
            extra=_live_ai_failure_log_extra(
                session_id=session_id,
                audit_log_id=audit_log_id,
                status=AdminLiveAIRequestLog.Status.FAILED,
                error_class=error_class,
                model=settings.OPENAI_MODEL,
                latency_ms=latency_ms,
            ),
        )
        yield (
            "data: "
            + json.dumps({"type": "error", "error": LIVE_AI_SAFE_ERROR_MESSAGE}, separators=(",", ":"))
            + "\n\n"
        ).encode("utf-8")


@staff_member_required
def internal_chat_sessions(request):
    sessions = _scoped_internal_chat_sessions().order_by("-last_message_at", "-created_at")
    return render(
        request,
        "admin_chat/list.html",
        {
            "sessions": sessions,
            "accounts": Account.objects.filter(status=Account.Status.ACTIVE).order_by("name"),
            "servers": Server.objects.select_related("account").order_by("account__name", "name"),
            "applications": Application.objects.select_related("account", "server").order_by("account__name", "name"),
            "report_types": AdminChatReportDraft.DraftType.choices,
        },
    )


@require_POST
@staff_member_required
def internal_chat_session_start(request):
    session = create_admin_chat_session(
        user=request.user,
        account_id=request.POST.get("account_id") or None,
        title=request.POST.get("title", ""),
        server_id=request.POST.get("server_id") or None,
        application_id=request.POST.get("application_id") or None,
    )
    messages.success(request, "Internal chat session created.")
    return redirect("admin_chat:session_detail", session_id=session.id)


@staff_member_required
def internal_chat_session_detail(request, session_id):
    session = get_object_or_404(_scoped_internal_chat_sessions(), id=session_id)
    if request.method == "POST":
        if not user_can_write_chat(request.user, session):
            raise PermissionDenied
        add_user_message_and_response(user=request.user, session=session, body=request.POST.get("body", ""), metadata={"source": "admin_internal"})
        messages.success(request, "Message saved and response generated.")
        return redirect("admin_chat:session_detail", session_id=session.id)
    return render(
        request,
        "admin_chat/detail.html",
        {
            "session": session,
            "chat_messages": session.messages.order_by("created_at"),
            "tool_requests": session.tool_requests.select_related("tool_definition", "tool_run").order_by("-created_at"),
            "tool_build_requests": session.tool_build_requests.prefetch_related("proposals").order_by("-created_at"),
            "report_drafts": session.report_drafts.select_related("converted_report").order_by("-created_at"),
            "available_tools": (session.context_snapshot_redacted or {}).get("available_tools", []),
            "can_write": user_can_write_chat(request.user, session),
            "chat_report_types": AdminChatReportDraft.DraftType.choices,
            "live_ai_enabled": settings.ADMIN_LIVE_AI_ENABLED,
            "live_ai_available": settings.ADMIN_LIVE_AI_ENABLED and not live_ai_configuration_error(),
            "live_ai_error": live_ai_configuration_error() if settings.ADMIN_LIVE_AI_ENABLED else "",
            "live_ai_status": "Enabled" if settings.ADMIN_LIVE_AI_ENABLED else "Disabled",
            "live_ai_model": settings.OPENAI_MODEL or "not configured",
            "live_ai_rate_limit_per_hour": settings.ADMIN_LIVE_AI_RATE_LIMIT_PER_HOUR,
            "live_ai_safe_context_max_bytes": settings.AI_SAFE_CONTEXT_MAX_BYTES,
            "chatkit_domain_key": settings.OPENAI_CHATKIT_DOMAIN_KEY,
        },
    )


@require_GET
@staff_member_required
def internal_chat_bundle_status(request, session_id):
    session = get_object_or_404(_scoped_internal_chat_sessions(), id=session_id)
    bundle_messages = AdminChatMessage.objects.filter(
        session=session,
        metadata_redacted__source="diagnostic_bundle",
    )
    result_execution_ids = set(
        bundle_messages.exclude(metadata_redacted__state="running").values_list(
            "metadata_redacted__bundle_execution_id", flat=True
        )
    )
    running = bundle_messages.filter(metadata_redacted__state="running").exclude(
        metadata_redacted__bundle_execution_id__in=result_execution_ids
    ).exists()
    running_message = (
        bundle_messages.filter(metadata_redacted__state="running")
        .exclude(metadata_redacted__bundle_execution_id__in=result_execution_ids)
        .order_by("-created_at", "-id")
        .first()
    )
    latest_result = (
        bundle_messages
        .exclude(metadata_redacted__state="running")
        .order_by("-created_at", "-id")
        .first()
    )
    latest_result_metadata = latest_result.metadata_redacted or {} if latest_result else {}
    running_metadata = running_message.metadata_redacted or {} if running_message else {}
    return JsonResponse(
        {
            "running": running,
            "running_execution_id": str(running_metadata.get("bundle_execution_id") or ""),
            "running_item_id": str(running_metadata.get("chatkit_item_id") or ""),
            "latest_result_id": str(latest_result_metadata.get("chatkit_item_id") or ""),
            "latest_result_execution_id": str(latest_result_metadata.get("bundle_execution_id") or ""),
            "latest_result_state": str(latest_result_metadata.get("state") or ""),
        }
    )


@require_POST
@staff_member_required
async def internal_chat_live(request, session_id):
    started_at = monotonic()
    user = await request.auser()
    session = await sync_to_async(
        lambda: get_object_or_404(_scoped_internal_chat_sessions(), id=session_id),
        thread_sensitive=True,
    )()

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": LIVE_AI_SAFE_ERROR_MESSAGE}, status=400)
    requested_thread_id = (payload.get("params") or {}).get("thread_id")
    if requested_thread_id and str(requested_thread_id) != str(session.id):
        return JsonResponse({"error": LIVE_AI_SAFE_ERROR_MESSAGE}, status=403)

    is_generation_request = _is_live_ai_generation_request(payload)
    audit_log_id = None

    if not settings.ADMIN_LIVE_AI_ENABLED:
        if is_generation_request:
            audit_log_id = await sync_to_async(create_live_ai_request_log, thread_sensitive=True)(user, session)
            await sync_to_async(update_live_ai_request_log, thread_sensitive=True)(
                audit_log_id,
                status=AdminLiveAIRequestLog.Status.DENIED,
                latency_ms=_elapsed_ms(started_at),
                error_class=AdminLiveAIRequestLog.ErrorClass.DISABLED,
                fallback_used=True,
            )
        return JsonResponse({"error": LIVE_AI_SAFE_ERROR_MESSAGE}, status=404)
    configuration_error = live_ai_configuration_error()
    if configuration_error:
        if is_generation_request:
            audit_log_id = await sync_to_async(create_live_ai_request_log, thread_sensitive=True)(user, session)
            await sync_to_async(update_live_ai_request_log, thread_sensitive=True)(
                audit_log_id,
                status=AdminLiveAIRequestLog.Status.FAILED,
                latency_ms=_elapsed_ms(started_at),
                error_class=classify_configuration_error(configuration_error),
                fallback_used=True,
            )
        return JsonResponse({"error": LIVE_AI_SAFE_ERROR_MESSAGE}, status=503)

    if is_generation_request:
        audit_log_id = await sync_to_async(create_live_ai_request_log, thread_sensitive=True)(user, session)

    safe_body = json.dumps(redact_json(payload), separators=(",", ":")).encode("utf-8")
    context = AdminChatKitContext(user=user, session=session, audit_log_id=audit_log_id)
    try:
        result = await live_admin_chatkit_server.process(safe_body, context)
    except PermissionDenied:
        await sync_to_async(update_live_ai_request_log, thread_sensitive=True)(
            audit_log_id,
            status=AdminLiveAIRequestLog.Status.DENIED,
            latency_ms=_elapsed_ms(started_at),
            error_class=AdminLiveAIRequestLog.ErrorClass.AUTH_ERROR,
            fallback_used=True,
        )
        return JsonResponse({"error": LIVE_AI_SAFE_ERROR_MESSAGE}, status=403)
    except Exception as exc:
        error_class = classify_live_ai_exception(exc)
        latency_ms = _elapsed_ms(started_at)
        await sync_to_async(update_live_ai_request_log, thread_sensitive=True)(
            audit_log_id,
            status=AdminLiveAIRequestLog.Status.FAILED,
            latency_ms=latency_ms,
            error_class=error_class,
            fallback_used=True,
        )
        logger.error(
            "Live AI request failed before streaming",
            extra=_live_ai_failure_log_extra(
                session_id=session.id,
                audit_log_id=audit_log_id,
                status=AdminLiveAIRequestLog.Status.FAILED,
                error_class=error_class,
                model=settings.OPENAI_MODEL,
                latency_ms=latency_ms,
            ),
        )
        return JsonResponse({"error": LIVE_AI_SAFE_ERROR_MESSAGE}, status=400)

    if isinstance(result, StreamingResult):
        response = StreamingHttpResponse(
            _stream_live_ai_result(
                result,
                audit_log_id=audit_log_id,
                session_id=session.id,
                started_at=started_at,
            ),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache, no-store"
        response["X-Accel-Buffering"] = "no"
        return response
    await sync_to_async(update_live_ai_request_log, thread_sensitive=True)(
        audit_log_id,
        status=AdminLiveAIRequestLog.Status.SUCCEEDED,
        latency_ms=_elapsed_ms(started_at),
        response_size_bytes=_response_size_bytes(result.json),
    )
    return HttpResponse(result.json, content_type="application/json")


@require_POST
@staff_member_required
def internal_chat_tool_request_create(request, session_id):
    session = get_object_or_404(_scoped_internal_chat_sessions(), id=session_id)
    create_tool_request(user=request.user, session=session, tool_key=request.POST.get("tool_key", ""))
    messages.success(request, "Tool request created. Approval is required before execution.")
    return redirect("admin_chat:session_detail", session_id=session.id)


@require_POST
@staff_member_required
def internal_chat_tool_request_approve(request, session_id, request_id):
    session = get_object_or_404(_scoped_internal_chat_sessions(), id=session_id)
    tool_request = get_object_or_404(session.tool_requests.select_related("tool_definition"), id=request_id)
    approve_tool_request(user=request.user, tool_request=tool_request)
    messages.success(request, "Tool request approved and queued.")
    return redirect("admin_chat:session_detail", session_id=session.id)


@require_POST
@staff_member_required
def internal_chat_tool_request_reject(request, session_id, request_id):
    session = get_object_or_404(_scoped_internal_chat_sessions(), id=session_id)
    tool_request = get_object_or_404(session.tool_requests.select_related("tool_definition"), id=request_id)
    reject_tool_request(user=request.user, tool_request=tool_request)
    messages.warning(request, "Tool request rejected. No execution was created.")
    return redirect("admin_chat:session_detail", session_id=session.id)


@require_POST
@staff_member_required
def internal_chat_tool_build_create(request, session_id):
    session = get_object_or_404(_scoped_internal_chat_sessions(), id=session_id)
    create_tool_build_request_from_chat(
        user=request.user,
        session=session,
        title=request.POST.get("title", ""),
        desired_tool_key=request.POST.get("desired_tool_key", ""),
        command_argv_template=_newline_list(request.POST.get("command_argv_template", "")),
        allowed_binaries=_newline_list(request.POST.get("allowed_binaries", "")),
        blocked_tokens=_newline_list(request.POST.get("blocked_tokens", "")),
        description=request.POST.get("description", ""),
        expected_output_description=request.POST.get("expected_output_description", ""),
    )
    messages.success(request, "Tool builder proposal created for internal review.")
    return redirect("admin_chat:session_detail", session_id=session.id)


@require_POST
@staff_member_required
def internal_chat_report_create(request, session_id):
    session = get_object_or_404(_scoped_internal_chat_sessions(), id=session_id)
    create_chat_report(
        user=request.user,
        session=session,
        report_type=request.POST.get("report_type", ""),
    )
    messages.success(request, "Chat report created and converted.")
    return redirect("admin_chat:session_detail", session_id=session.id)


@require_POST
@staff_member_required
def internal_chat_report_draft_create(request, session_id):
    session = get_object_or_404(_scoped_internal_chat_sessions(), id=session_id)
    create_chat_report_draft(
        user=request.user,
        session=session,
        report_type=request.POST.get("report_type", ""),
    )
    messages.success(request, "Report draft created for manual internal review.")
    return redirect("admin_chat:session_detail", session_id=session.id)
