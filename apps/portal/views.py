from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.models import User
from apps.ai_chat.models import AdminChatSession
from apps.ai_chat.services import add_user_message_and_response, create_chat_session, user_can_write_chat
from apps.applications.models import Application
from apps.reports.models import FindingGroup, KnowledgeEntry, Report
from apps.reports.services import (
    create_baseline_report,
    create_diagnostic_report,
    create_findings_summary,
    create_server_health_summary,
    visible_knowledge_for_account,
)
from apps.servers.models import (
    AgentRegistrationToken,
    BaselineScan,
    DiscoveredDomain,
    DiscoveredService,
    Finding,
    LogSource,
    Server,
)
from apps.subscriptions.models import Subscription
from apps.telegram_integration.models import TelegramChatLink, TelegramLinkToken
from apps.telegram_integration.services import create_link_token_for_portal

from .forms import ServerCreateForm
from .permissions import (
    application_action_allowed,
    finding_acknowledge_allowed,
    finding_ignore_allowed,
    owner_required,
    portal_required,
)
from .services import (
    active_subscription_for_display,
    apply_application_action,
    apply_finding_action,
    create_registration_token_for_portal,
    safe_application_metadata,
    safe_baseline_summary,
    safe_finding_evidence,
)


class PortalLoginView(LoginView):
    template_name = "portal/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("portal:dashboard")


class PortalLogoutView(LogoutView):
    next_page = reverse_lazy("portal:login")


def access_denied(request):
    return render(request, "portal/access_denied.html", status=403)


def account_for(request):
    return request.user.account


def scoped_servers(request):
    return Server.objects.filter(account=account_for(request))


def scoped_applications(request):
    return Application.objects.select_related("server").filter(account=account_for(request))


def scoped_findings(request):
    return Finding.objects.select_related("server", "application").filter(account=account_for(request))


def scoped_reports(request):
    return Report.objects.select_related("server", "application", "baseline_scan", "diagnostic_session").filter(
        account=account_for(request)
    )


def scoped_finding_groups(request):
    return FindingGroup.objects.select_related("server", "application", "latest_finding").filter(account=account_for(request))


def scoped_chat_sessions(request):
    return AdminChatSession.objects.select_related("server", "application", "user").filter(account=account_for(request))


def can_generate_reports(user):
    return user.role in {User.CustomerRole.OWNER, User.CustomerRole.OPERATOR}


@portal_required
def dashboard(request):
    account = account_for(request)
    servers = scoped_servers(request)
    applications = scoped_applications(request)
    findings = scoped_findings(request)
    latest_scans = (
        BaselineScan.objects.filter(account=account)
        .select_related("server")
        .order_by("-created_at")[:5]
    )
    context = {
        "server_count": servers.count(),
        "active_server_count": servers.filter(status=Server.Status.ACTIVE).count(),
        "offline_agent_count": servers.filter(Q(agent_status="offline") | Q(agent_status="")).count(),
        "application_count": applications.count(),
        "pending_application_count": applications.filter(review_status=Application.ReviewStatus.PENDING_REVIEW).count(),
        "open_finding_count": findings.filter(status=Finding.Status.OPEN).count(),
        "critical_finding_count": findings.filter(status=Finding.Status.OPEN, severity__iexact="critical").count(),
        "latest_scans": latest_scans,
        "subscription": active_subscription_for_display(account),
    }
    return render(request, "portal/dashboard.html", context)


@portal_required
def servers_list(request):
    servers = (
        scoped_servers(request)
        .annotate(application_count=Count("applications"), finding_count=Count("findings"))
        .order_by("name")
    )
    return render(request, "portal/servers/list.html", {"servers": servers})


@owner_required
def server_add(request):
    if request.method == "POST":
        form = ServerCreateForm(request.POST)
        if form.is_valid():
            server = form.save(commit=False)
            server.account = account_for(request)
            server.status = Server.Status.PENDING
            server.save()
            messages.success(request, "Server added. Generate a registration token when you are ready.")
            return redirect("portal:server_detail", server_id=server.id)
    else:
        form = ServerCreateForm()
    return render(request, "portal/servers/add.html", {"form": form})


@portal_required
def server_detail(request, server_id):
    server = get_object_or_404(scoped_servers(request), id=server_id)
    context = {
        "server": server,
        "applications": server.applications.filter(account=account_for(request)).order_by("name")[:20],
        "findings": server.findings.filter(account=account_for(request)).order_by("-created_at")[:20],
        "domains": DiscoveredDomain.objects.filter(account=account_for(request), server=server).order_by("domain"),
        "services": DiscoveredService.objects.filter(account=account_for(request), server=server).order_by("name"),
        "log_sources": LogSource.objects.filter(account=account_for(request), server=server).order_by("path")[:20],
        "baseline_scans": server.baseline_scans.filter(account=account_for(request)).order_by("-created_at")[:10],
        "latest_report": Report.objects.filter(account=account_for(request), server=server).order_by("-generated_at", "-created_at").first(),
        "finding_groups": FindingGroup.objects.filter(account=account_for(request), server=server).order_by("-last_seen_at")[:10],
        "can_generate_registration": request.user.role == User.CustomerRole.OWNER,
    }
    return render(request, "portal/servers/detail.html", context)


@owner_required
def registration_token(request, server_id):
    server = get_object_or_404(scoped_servers(request), id=server_id)
    raw_token = None
    token = None
    error = ""
    if request.method == "POST":
        try:
            token, raw_token = create_registration_token_for_portal(request.user, server)
            messages.success(request, "Registration token generated. It is shown once on this page.")
        except ValueError as exc:
            error = str(exc)
            messages.error(request, error)
    recent_tokens = AgentRegistrationToken.objects.filter(account=account_for(request), server=server).order_by("-created_at")[:5]
    return render(
        request,
        "portal/servers/registration_token.html",
        {"server": server, "token": token, "raw_token": raw_token, "recent_tokens": recent_tokens, "error": error},
    )


@portal_required
def applications_list(request):
    applications = scoped_applications(request).order_by("review_status", "name")
    return render(request, "portal/applications/list.html", {"applications": applications, "title": "Applications"})


@portal_required
def pending_applications(request):
    applications = scoped_applications(request).filter(review_status=Application.ReviewStatus.PENDING_REVIEW).order_by("name")
    return render(request, "portal/applications/list.html", {"applications": applications, "title": "Pending Applications"})


@portal_required
def application_detail(request, application_id):
    application = get_object_or_404(scoped_applications(request), id=application_id)
    return render(
        request,
        "portal/applications/detail.html",
        {
            "application": application,
            "safe_metadata": safe_application_metadata(application),
            "can_act": application_action_allowed(request.user),
        },
    )


@require_POST
@portal_required
def application_action(request, application_id, action):
    if action not in {"approve", "ignore", "archive"}:
        raise Http404
    if not application_action_allowed(request.user):
        raise PermissionDenied
    application = get_object_or_404(scoped_applications(request), id=application_id)
    apply_application_action(request.user, application, action)
    messages.success(request, "Application updated.")
    return redirect("portal:application_detail", application_id=application.id)


@portal_required
def findings_list(request):
    findings = scoped_findings(request)
    severity = request.GET.get("severity") or ""
    status = request.GET.get("status") or ""
    server_id = request.GET.get("server") or ""
    application_id = request.GET.get("application") or ""
    if severity:
        findings = findings.filter(severity=severity)
    if status:
        findings = findings.filter(status=status)
    if server_id:
        findings = findings.filter(server_id=server_id)
    if application_id:
        findings = findings.filter(application_id=application_id)
    findings = findings.order_by("status", "-created_at")
    return render(
        request,
        "portal/findings/list.html",
        {
            "findings": findings,
            "servers": scoped_servers(request).order_by("name"),
            "applications": scoped_applications(request).order_by("name"),
            "selected_severity": severity,
            "selected_status": status,
            "selected_server": server_id,
            "selected_application": application_id,
            "severity_choices": ["critical", "high", "medium", "low", "info"],
            "status_choices": Finding.Status.choices,
        },
    )


@portal_required
def finding_detail(request, finding_id):
    finding = get_object_or_404(scoped_findings(request), id=finding_id)
    return render(
        request,
        "portal/findings/detail.html",
        {
            "finding": finding,
            "evidence_summary": safe_finding_evidence(finding),
            "can_acknowledge": finding_acknowledge_allowed(request.user),
            "can_ignore": finding_ignore_allowed(request.user),
        },
    )


@require_POST
@portal_required
def finding_action(request, finding_id, action):
    if action not in {"acknowledge", "ignore"}:
        raise Http404
    if action == "acknowledge" and not finding_acknowledge_allowed(request.user):
        raise PermissionDenied
    if action == "ignore" and not finding_ignore_allowed(request.user):
        raise PermissionDenied
    finding = get_object_or_404(scoped_findings(request), id=finding_id)
    apply_finding_action(request.user, finding, action)
    messages.success(request, "Finding updated.")
    return redirect("portal:finding_detail", finding_id=finding.id)


@portal_required
def baseline_scans(request):
    scans = BaselineScan.objects.select_related("server").filter(account=account_for(request)).order_by("-created_at")
    safe_scans = [(scan, safe_baseline_summary(scan)) for scan in scans]
    return render(request, "portal/baseline/list.html", {"safe_scans": safe_scans})


@require_GET
@portal_required
def subscription_usage(request):
    account = account_for(request)
    subscription = active_subscription_for_display(account) or account.subscriptions.select_related("plan").order_by("-created_at").first()
    plan = subscription.plan if subscription else None
    context = {
        "subscription": subscription,
        "plan": plan,
        "server_count": Server.objects.filter(account=account).count(),
        "application_count": Application.objects.filter(account=account).count(),
        "user_count": account.users.count(),
        "diagnostic_sessions_used": 0,
    }
    return render(request, "portal/subscription.html", context)


@portal_required
def telegram_settings(request):
    raw_code = None
    token = None
    error = ""
    account = account_for(request)
    if request.method == "POST":
        chat_scope = request.POST.get("chat_scope", TelegramLinkToken.ChatScope.PRIVATE)
        server_id = request.POST.get("server_id") or None
        server = get_object_or_404(scoped_servers(request), id=server_id) if server_id else None
        try:
            token, raw_code = create_link_token_for_portal(user=request.user, chat_scope=chat_scope, server=server)
            messages.success(request, "Telegram link code generated. It is shown once on this page.")
        except PermissionDenied:
            raise
        except ValueError as exc:
            error = str(exc)
            messages.error(request, error)
    links = TelegramChatLink.objects.filter(account=account).select_related("server", "user").order_by("-created_at")
    recent_tokens = TelegramLinkToken.objects.filter(account=account).select_related("server", "created_by").order_by("-created_at")[:5]
    context = {
        "links": links,
        "recent_tokens": recent_tokens,
        "servers": scoped_servers(request).order_by("name"),
        "raw_code": raw_code,
        "token": token,
        "error": error,
        "can_generate_private": request.user.role in {User.CustomerRole.OWNER, User.CustomerRole.OPERATOR},
        "can_generate_group": request.user.role == User.CustomerRole.OWNER,
    }
    return render(request, "portal/telegram.html", context)


@portal_required
def reports_list(request):
    reports = scoped_reports(request).order_by("-generated_at", "-created_at")
    return render(
        request,
        "portal/reports/list.html",
        {
            "reports": reports,
            "servers": scoped_servers(request).order_by("name"),
            "baseline_scans": BaselineScan.objects.filter(account=account_for(request)).select_related("server").order_by("-created_at")[:20],
            "can_generate": can_generate_reports(request.user),
            "knowledge_entries": visible_knowledge_for_account(account_for(request))[:10],
        },
    )


@portal_required
def chat_sessions(request):
    sessions = scoped_chat_sessions(request).order_by("-last_message_at", "-created_at")
    return render(
        request,
        "portal/chat/list.html",
        {
            "sessions": sessions,
            "servers": scoped_servers(request).order_by("name"),
            "applications": scoped_applications(request).order_by("name"),
            "can_start_chat": request.user.role in {User.CustomerRole.OWNER, User.CustomerRole.OPERATOR},
        },
    )


@require_POST
@portal_required
def chat_session_start(request):
    if request.user.role not in {User.CustomerRole.OWNER, User.CustomerRole.OPERATOR}:
        raise PermissionDenied
    session = create_chat_session(
        user=request.user,
        title=request.POST.get("title", ""),
        server_id=request.POST.get("server_id") or None,
        application_id=request.POST.get("application_id") or None,
    )
    messages.success(request, "Chat session created.")
    return redirect("portal:chat_session_detail", session_id=session.id)


@portal_required
def chat_session_detail(request, session_id):
    session = get_object_or_404(scoped_chat_sessions(request), id=session_id)
    if request.method == "POST":
        if not user_can_write_chat(request.user, session):
            raise PermissionDenied
        add_user_message_and_response(user=request.user, session=session, body=request.POST.get("body", ""), metadata={"source": "portal"})
        messages.success(request, "Message saved and response generated.")
        return redirect("portal:chat_session_detail", session_id=session.id)
    return render(
        request,
        "portal/chat/detail.html",
        {
            "session": session,
            "chat_messages": session.messages.order_by("created_at"),
            "can_write": user_can_write_chat(request.user, session),
        },
    )


@portal_required
def report_detail(request, report_id):
    report = get_object_or_404(scoped_reports(request), id=report_id)
    sections = report.sections.order_by("order", "created_at")
    recommendations = report.recommendations.order_by("-created_at")
    return render(
        request,
        "portal/reports/detail.html",
        {"report": report, "sections": sections, "recommendations": recommendations},
    )


@require_POST
@portal_required
def report_generate(request):
    if not can_generate_reports(request.user):
        raise PermissionDenied
    account = account_for(request)
    report_type = request.POST.get("report_type")
    server = None
    server_id = request.POST.get("server_id") or None
    if server_id:
        server = get_object_or_404(scoped_servers(request), id=server_id)
    if report_type == Report.ReportType.FINDINGS:
        report = create_findings_summary(account, user=request.user, server=server)
    elif report_type == Report.ReportType.SERVER_HEALTH:
        if not server:
            raise Http404
        report = create_server_health_summary(server, user=request.user)
    elif report_type == Report.ReportType.BASELINE:
        scan = get_object_or_404(BaselineScan.objects.filter(account=account), id=request.POST.get("baseline_scan_id"))
        report = create_baseline_report(scan, user=request.user)
    else:
        raise Http404
    messages.success(request, "Report generated.")
    return redirect("portal:report_detail", report_id=report.id)


@portal_required
def finding_groups_list(request):
    groups = scoped_finding_groups(request)
    severity = request.GET.get("severity") or ""
    status = request.GET.get("status") or ""
    server_id = request.GET.get("server") or ""
    application_id = request.GET.get("application") or ""
    if severity:
        groups = groups.filter(severity=severity)
    if status:
        groups = groups.filter(status=status)
    if server_id:
        groups = groups.filter(server_id=server_id)
    if application_id:
        groups = groups.filter(application_id=application_id)
    groups = groups.order_by("-last_seen_at", "-created_at")
    return render(
        request,
        "portal/finding_groups/list.html",
        {
            "groups": groups,
            "servers": scoped_servers(request).order_by("name"),
            "applications": scoped_applications(request).order_by("name"),
            "severity_choices": ["critical", "high", "medium", "low", "info"],
            "status_choices": Finding.Status.choices,
            "selected_severity": severity,
            "selected_status": status,
            "selected_server": server_id,
            "selected_application": application_id,
        },
    )


@portal_required
def finding_group_detail(request, group_id):
    group = get_object_or_404(scoped_finding_groups(request), id=group_id)
    findings = scoped_findings(request).filter(
        server=group.server,
        application=group.application,
        fingerprint=group.fingerprint,
    ).order_by("-created_at")
    return render(request, "portal/finding_groups/detail.html", {"group": group, "findings": findings})


@portal_required
def placeholder(request, page):
    titles = {
        "diagnostics": "Diagnostic Sessions",
        "reports": "Reports",
    }
    return render(request, "portal/placeholder.html", {"title": titles[page]})
