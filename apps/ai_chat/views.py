from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import Account
from apps.applications.models import Application
from apps.servers.models import Server

from .models import AdminChatReportDraft, AdminChatSession
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
        },
    )


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
