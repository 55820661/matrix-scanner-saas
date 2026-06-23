import json
from time import monotonic

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from chatkit.server import StreamingResult

from apps.accounts.models import Account
from apps.applications.models import Application
from apps.core.redaction import redact_json
from apps.servers.models import Server

from .chatkit_store import AdminChatKitContext
from .live_ai import (
    LIVE_AI_SAFE_ERROR_MESSAGE,
    classify_configuration_error,
    create_live_ai_request_log,
    live_admin_chatkit_server,
    live_ai_configuration_error,
    update_live_ai_request_log,
)
from .models import AdminChatReportDraft, AdminChatSession, AdminLiveAIRequestLog
from .services import (
    add_user_message_and_response,
    approve_tool_request,
    create_admin_chat_session,
    create_chat_report,
    create_chat_report_draft,
    create_tool_build_request_from_chat,
    create_tool_request,
    user_can_write_chat,
)


def _newline_list(value):
    return [line.strip() for line in (value or "").splitlines() if line.strip()]


def _scoped_internal_chat_sessions():
    return (
        AdminChatSession.objects.select_related("account", "server", "application", "user")
        .filter(channel=AdminChatSession.Channel.ADMIN_INTERNAL)
    )


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


@require_POST
@staff_member_required
async def internal_chat_live(request, session_id):
    started_at = monotonic()
    user = await request.auser()
    session = await sync_to_async(
        lambda: get_object_or_404(_scoped_internal_chat_sessions(), id=session_id),
        thread_sensitive=True,
    )()
    audit_log_id = await sync_to_async(create_live_ai_request_log, thread_sensitive=True)(user, session)

    if not settings.ADMIN_LIVE_AI_ENABLED:
        await sync_to_async(update_live_ai_request_log, thread_sensitive=True)(
            audit_log_id,
            status=AdminLiveAIRequestLog.Status.DENIED,
            latency_ms=int((monotonic() - started_at) * 1000),
            error_class=AdminLiveAIRequestLog.ErrorClass.DISABLED,
            fallback_used=True,
        )
        return JsonResponse({"error": LIVE_AI_SAFE_ERROR_MESSAGE}, status=404)
    configuration_error = live_ai_configuration_error()
    if configuration_error:
        await sync_to_async(update_live_ai_request_log, thread_sensitive=True)(
            audit_log_id,
            status=AdminLiveAIRequestLog.Status.FAILED,
            latency_ms=int((monotonic() - started_at) * 1000),
            error_class=classify_configuration_error(configuration_error),
            fallback_used=True,
        )
        return JsonResponse({"error": LIVE_AI_SAFE_ERROR_MESSAGE}, status=503)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        await sync_to_async(update_live_ai_request_log, thread_sensitive=True)(
            audit_log_id,
            status=AdminLiveAIRequestLog.Status.FAILED,
            latency_ms=int((monotonic() - started_at) * 1000),
            error_class=AdminLiveAIRequestLog.ErrorClass.VALIDATION_ERROR,
            fallback_used=True,
        )
        return JsonResponse({"error": LIVE_AI_SAFE_ERROR_MESSAGE}, status=400)
    requested_thread_id = (payload.get("params") or {}).get("thread_id")
    if requested_thread_id and str(requested_thread_id) != str(session.id):
        await sync_to_async(update_live_ai_request_log, thread_sensitive=True)(
            audit_log_id,
            status=AdminLiveAIRequestLog.Status.DENIED,
            latency_ms=int((monotonic() - started_at) * 1000),
            error_class=AdminLiveAIRequestLog.ErrorClass.AUTH_ERROR,
            fallback_used=True,
        )
        return JsonResponse({"error": LIVE_AI_SAFE_ERROR_MESSAGE}, status=403)

    safe_body = json.dumps(redact_json(payload), separators=(",", ":")).encode("utf-8")
    context = AdminChatKitContext(user=user, session=session, audit_log_id=audit_log_id)
    try:
        result = await live_admin_chatkit_server.process(safe_body, context)
    except PermissionDenied:
        await sync_to_async(update_live_ai_request_log, thread_sensitive=True)(
            audit_log_id,
            status=AdminLiveAIRequestLog.Status.DENIED,
            latency_ms=int((monotonic() - started_at) * 1000),
            error_class=AdminLiveAIRequestLog.ErrorClass.AUTH_ERROR,
            fallback_used=True,
        )
        return JsonResponse({"error": LIVE_AI_SAFE_ERROR_MESSAGE}, status=403)
    except Exception:
        await sync_to_async(update_live_ai_request_log, thread_sensitive=True)(
            audit_log_id,
            status=AdminLiveAIRequestLog.Status.FAILED,
            latency_ms=int((monotonic() - started_at) * 1000),
            error_class=AdminLiveAIRequestLog.ErrorClass.VALIDATION_ERROR,
            fallback_used=True,
        )
        return JsonResponse({"error": LIVE_AI_SAFE_ERROR_MESSAGE}, status=400)

    if isinstance(result, StreamingResult):
        response = StreamingHttpResponse(result, content_type="text/event-stream")
        response["Cache-Control"] = "no-cache, no-store"
        response["X-Accel-Buffering"] = "no"
        return response
    await sync_to_async(update_live_ai_request_log, thread_sensitive=True)(
        audit_log_id,
        status=AdminLiveAIRequestLog.Status.SUCCEEDED,
        latency_ms=int((monotonic() - started_at) * 1000),
        response_size_bytes=len(result.json.encode("utf-8")),
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
