from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.applications.models import Application
from apps.portal.permissions import portal_required
from apps.reports.models import Report
from apps.servers.models import Server

from .models import DiagnosticSession, DiagnosticStep
from .services import (
    DiagnosticError,
    approve_diagnostic_step,
    start_diagnostic_session,
    sync_completed_tool_runs,
    user_can_start_or_approve,
)


def account_for(request):
    return request.user.account


def scoped_sessions(request):
    return DiagnosticSession.objects.select_related("server", "application", "requested_by").filter(account=account_for(request))


def scoped_servers(request):
    return Server.objects.filter(account=account_for(request))


@portal_required
def diagnostics_list(request):
    sessions = scoped_sessions(request).order_by("-created_at")
    return render(
        request,
        "portal/diagnostics/list.html",
        {"sessions": sessions, "can_start": user_can_start_or_approve(request.user)},
    )


@portal_required
def diagnostics_start(request):
    if not user_can_start_or_approve(request.user):
        raise PermissionDenied
    account = account_for(request)
    servers = scoped_servers(request).order_by("name")
    applications = Application.objects.filter(account=account).select_related("server").order_by("name")
    if request.method == "POST":
        server = get_object_or_404(scoped_servers(request), id=request.POST.get("server_id"))
        application = None
        application_id = request.POST.get("application_id") or None
        if application_id:
            application = get_object_or_404(Application.objects.filter(account=account, server=server), id=application_id)
        try:
            session = start_diagnostic_session(
                user=request.user,
                server=server,
                application=application,
                problem_type=request.POST.get("problem_type") or DiagnosticSession.ProblemType.CUSTOM,
                user_prompt=request.POST.get("user_prompt", ""),
            )
            messages.success(request, "Diagnostic session started. Approve the next read-only tool step to continue.")
            return redirect("portal:diagnostic_detail", session_id=session.id)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
    return render(
        request,
        "portal/diagnostics/start.html",
        {
            "servers": servers,
            "applications": applications,
            "problem_types": DiagnosticSession.ProblemType.choices,
        },
    )


@portal_required
def diagnostic_detail(request, session_id):
    session = get_object_or_404(scoped_sessions(request), id=session_id)
    sync_completed_tool_runs(session)
    session.refresh_from_db()
    steps = session.steps.select_related("tool_run", "approved_by").order_by("created_at")
    next_approval_step = steps.filter(status=DiagnosticStep.Status.AWAITING_APPROVAL, requires_approval=True).first()
    return render(
        request,
        "portal/diagnostics/detail.html",
        {
            "session": session,
            "steps": steps,
            "next_approval_step": next_approval_step,
            "can_approve": user_can_start_or_approve(request.user),
            "viewer_role": User.CustomerRole.VIEWER,
            "reports": Report.objects.filter(account=account_for(request), diagnostic_session=session).order_by(
                "-generated_at", "-created_at"
            ),
        },
    )


@require_POST
@portal_required
def diagnostic_step_approve(request, session_id, step_id):
    session = get_object_or_404(scoped_sessions(request), id=session_id)
    step = get_object_or_404(session.steps, id=step_id)
    try:
        approve_diagnostic_step(user=request.user, session=session, step=step)
        messages.success(request, "Diagnostic step approved and queued through ToolPolicy.")
    except PermissionDenied:
        raise
    except DiagnosticError as exc:
        messages.error(request, str(exc))
    return redirect("portal:diagnostic_detail", session_id=session.id)
