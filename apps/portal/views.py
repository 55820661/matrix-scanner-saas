from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.models import User
from apps.applications.models import Application
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
    findings = scoped_findings(request).order_by("status", "-created_at")
    return render(request, "portal/findings/list.html", {"findings": findings})


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
def placeholder(request, page):
    titles = {
        "telegram": "Telegram Settings",
        "diagnostics": "Diagnostic Sessions",
        "reports": "Reports",
    }
    return render(request, "portal/placeholder.html", {"title": titles[page]})
