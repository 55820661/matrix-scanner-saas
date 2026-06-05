import json

from django.core.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.applications.models import Application
from apps.core.redaction import redact_json, redact_secrets
from apps.reports.models import KnowledgeEntry, Recommendation, Report
from apps.servers.models import BaselineScan, DiscoveredDomain, DiscoveredService, Finding, LogSource, Server
from apps.subscriptions.models import Subscription
from apps.tools.models import PlanTool, ToolDefinition, ToolPolicy, ToolRun
from apps.tools.services import ACTIVE_SUBSCRIPTION_STATUSES


CONTEXT_VERSION = "1.0"
DEFAULT_MAX_ITEMS = 10
MAX_TEXT_LENGTH = 500
MAX_CONTEXT_BYTES = 65536


def _safe_text(value, *, limit=MAX_TEXT_LENGTH):
    return redact_secrets(value or "")[:limit]


def _safe_json(value):
    return redact_json(value or {})


def _iso(value):
    return value.isoformat() if value else None


def _limited(queryset, limit=DEFAULT_MAX_ITEMS):
    return list(queryset[:limit])


def _active_subscription(account):
    return (
        Subscription.objects.select_related("plan")
        .filter(account=account, status__in=ACTIVE_SUBSCRIPTION_STATUSES, plan__is_active=True)
        .order_by("-created_at")
        .first()
    )


def _assert_scope(user, account, server):
    if user and not user.is_staff and user.account_id != account.id:
        raise PermissionDenied("Safe context account access denied.")
    if server and server.account_id != account.id:
        raise PermissionDenied("Safe context server access denied.")


def _role_for(user):
    if not user:
        return ""
    if user.is_staff:
        return "matrix_admin"
    return user.role or ""


def _account_summary(account):
    return {
        "id": str(account.id),
        "name": _safe_text(account.name, limit=255),
        "type": account.type,
        "status": account.status,
    }


def _server_summary(server):
    if not server:
        return {}
    return {
        "id": str(server.id),
        "name": _safe_text(server.name, limit=255),
        "hostname": _safe_text(server.hostname, limit=255),
        "status": server.status,
        "agent_status": _safe_text(server.agent_status, limit=80),
        "last_seen_at": _iso(server.last_seen_at),
    }


def _latest_baseline_summary(account, server):
    queryset = BaselineScan.objects.filter(account=account)
    if server:
        queryset = queryset.filter(server=server)
    scan = queryset.order_by("-created_at").first()
    if not scan:
        return {}
    return {
        "id": str(scan.id),
        "server_id": str(scan.server_id),
        "profile_key": scan.profile_key,
        "status": scan.status,
        "summary": _safe_json(scan.summary),
        "started_at": _iso(scan.started_at),
        "finished_at": _iso(scan.finished_at),
        "created_at": _iso(scan.created_at),
    }


def _applications_summary(account, server):
    queryset = Application.objects.filter(account=account).order_by("name")
    if server:
        queryset = queryset.filter(server=server)
    return [
        {
            "id": str(app.id),
            "server_id": str(app.server_id),
            "name": _safe_text(app.name, limit=255),
            "framework": _safe_text(app.framework, limit=80),
            "domain": _safe_text(app.domain, limit=255),
            "path": _safe_text(app.path, limit=512),
            "review_status": app.review_status,
            "metadata": _safe_json(app.metadata),
        }
        for app in _limited(queryset)
    ]


def _services_summary(account, server):
    queryset = DiscoveredService.objects.filter(account=account).order_by("name")
    if server:
        queryset = queryset.filter(server=server)
    return [
        {
            "id": str(service.id),
            "server_id": str(service.server_id),
            "name": _safe_text(service.name, limit=160),
            "status": _safe_text(service.status, limit=80),
            "version": _safe_text(service.version, limit=160),
            "metadata": _safe_json(service.metadata),
        }
        for service in _limited(queryset)
    ]


def _domains_summary(account, server):
    queryset = DiscoveredDomain.objects.filter(account=account).order_by("domain")
    if server:
        queryset = queryset.filter(server=server)
    return [
        {
            "id": str(domain.id),
            "server_id": str(domain.server_id),
            "domain": _safe_text(domain.domain, limit=255),
            "document_root": _safe_text(domain.document_root, limit=512),
            "owner": _safe_text(domain.owner, limit=120),
            "metadata": _safe_json(domain.metadata),
        }
        for domain in _limited(queryset)
    ]


def _log_sources_summary(account, server):
    queryset = LogSource.objects.filter(account=account).order_by("path")
    if server:
        queryset = queryset.filter(server=server)
    return [
        {
            "id": str(source.id),
            "server_id": str(source.server_id),
            "path": _safe_text(source.path, limit=512),
            "source_type": _safe_text(source.source_type, limit=120),
            "exists": source.exists,
            "size_bytes": source.size_bytes,
            "metadata": _safe_json(source.metadata),
        }
        for source in _limited(queryset)
    ]


def _findings_summary(account, server):
    queryset = Finding.objects.filter(account=account).order_by("-created_at")
    if server:
        queryset = queryset.filter(server=server)
    return [
        {
            "id": str(finding.id),
            "server_id": str(finding.server_id),
            "application_id": str(finding.application_id) if finding.application_id else "",
            "title": _safe_text(finding.title, limit=255),
            "severity": finding.severity,
            "status": finding.status,
            "evidence_summary": _safe_text(finding.evidence_summary),
            "created_at": _iso(finding.created_at),
        }
        for finding in _limited(queryset)
    ]


def _reports_summary(account, server):
    queryset = Report.objects.filter(account=account).order_by("-created_at")
    if server:
        queryset = queryset.filter(server=server)
    return [
        {
            "id": str(report.id),
            "server_id": str(report.server_id) if report.server_id else "",
            "report_type": report.report_type,
            "status": report.status,
            "title": _safe_text(report.title, limit=255),
            "summary": _safe_text(report.summary_redacted),
            "generated_at": _iso(report.generated_at),
            "created_at": _iso(report.created_at),
        }
        for report in _limited(queryset)
    ]


def _knowledge_summary(account, server, user):
    queryset = KnowledgeEntry.objects.filter(status=KnowledgeEntry.Status.APPROVED).order_by("scope", "title")
    if user and user.is_staff:
        queryset = queryset.filter(account__in=[account, None])
    else:
        queryset = queryset.filter(visibility=KnowledgeEntry.Visibility.CUSTOMER_VISIBLE).filter(account=account)
    if server:
        queryset = queryset.filter(server__in=[server, None])
    return [
        {
            "id": str(entry.id),
            "scope": entry.scope,
            "visibility": entry.visibility,
            "title": _safe_text(entry.title, limit=255),
            "category": _safe_text(entry.category, limit=80),
            "body_summary": _safe_text(entry.body_redacted),
        }
        for entry in _limited(queryset)
    ]


def _recommendations_summary(account, server):
    queryset = Recommendation.objects.filter(account=account).order_by("-created_at")
    if server:
        queryset = queryset.filter(server=server)
    return [
        {
            "id": str(recommendation.id),
            "server_id": str(recommendation.server_id) if recommendation.server_id else "",
            "application_id": str(recommendation.application_id) if recommendation.application_id else "",
            "title": _safe_text(recommendation.title, limit=255),
            "body_summary": _safe_text(recommendation.body_redacted),
            "priority": recommendation.priority,
            "status": recommendation.status,
            "category": _safe_text(recommendation.category, limit=80),
        }
        for recommendation in _limited(queryset)
    ]


def _recent_tool_runs(account, server):
    queryset = ToolRun.objects.select_related("tool_definition").filter(account=account).order_by("-created_at")
    if server:
        queryset = queryset.filter(server=server)
    return [
        {
            "id": str(tool_run.id),
            "server_id": str(tool_run.server_id),
            "tool_key": tool_run.tool_definition.key,
            "tool_name": _safe_text(tool_run.tool_definition.name, limit=160),
            "status": tool_run.status,
            "requested_by_type": tool_run.requested_by_type,
            "started_at": _iso(tool_run.started_at),
            "finished_at": _iso(tool_run.finished_at),
            "error_summary": _safe_text(tool_run.error_message),
            "has_result": bool(tool_run.result_redacted),
        }
        for tool_run in _limited(queryset)
    ]


def _tool_allowed_for_user(policy, user):
    if user and user.is_staff:
        return policy.allow_admin_run
    if not policy.allow_customer_run:
        return False
    if not user or not user.role:
        return False
    if policy.allowed_roles and user.role not in policy.allowed_roles:
        return False
    if user.role == User.CustomerRole.VIEWER:
        return False
    return True


def _available_tools(account, server, user):
    subscription = _active_subscription(account)
    if not subscription:
        return []
    queryset = (
        PlanTool.objects.select_related("tool_definition", "tool_definition__template", "tool_definition__policy")
        .filter(plan=subscription.plan, is_enabled=True)
        .filter(
            tool_definition__status=ToolDefinition.Status.ENABLED,
            tool_definition__risk_level=ToolDefinition.RiskLevel.READ_ONLY,
            tool_definition__template__is_active=True,
            tool_definition__policy__is_active=True,
        )
        .order_by("tool_definition__key")
    )
    tools = []
    for plan_tool in queryset:
        definition = plan_tool.tool_definition
        try:
            policy = definition.policy
        except ToolPolicy.DoesNotExist:
            continue
        if server and policy.allowed_server_statuses and server.status not in policy.allowed_server_statuses:
            continue
        if not _tool_allowed_for_user(policy, user):
            continue
        tools.append(
            {
                "key": definition.key,
                "name": _safe_text(definition.name, limit=160),
                "description": _safe_text(definition.description),
                "category": _safe_text(definition.category, limit=80),
                "risk_level": definition.risk_level,
                "timeout_seconds": definition.timeout_seconds,
                "max_output_bytes": definition.max_output_bytes,
            }
        )
        if len(tools) >= DEFAULT_MAX_ITEMS:
            break
    return tools


def _risk_summary(findings):
    counts = {}
    for finding in findings:
        severity = finding.get("severity") or "info"
        counts[severity] = counts.get(severity, 0) + 1
    return {"finding_counts_by_severity": counts}


def _cap_context(context):
    payload = json.dumps(context, sort_keys=True, default=str)
    context["metadata"]["context_size_bytes"] = len(payload.encode("utf-8"))
    context["metadata"]["max_context_bytes"] = MAX_CONTEXT_BYTES
    if context["metadata"]["context_size_bytes"] > MAX_CONTEXT_BYTES:
        context["metadata"]["truncated"] = True
    return context


def build_safe_context(*, account, user=None, server=None):
    _assert_scope(user, account, server)

    findings = _findings_summary(account, server)
    context = {
        "context_version": CONTEXT_VERSION,
        "metadata": {
            "source": "safe_context_builder",
            "truncated": False,
            "max_items_per_section": DEFAULT_MAX_ITEMS,
            "role": _role_for(user),
        },
        "account_summary": _account_summary(account),
        "server_summary": _server_summary(server),
        "baseline_summary": _latest_baseline_summary(account, server),
        "applications_summary": _applications_summary(account, server),
        "services_summary": _services_summary(account, server),
        "domains_summary": _domains_summary(account, server),
        "log_sources_summary": _log_sources_summary(account, server),
        "findings_summary": findings,
        "reports_summary": _reports_summary(account, server),
        "knowledge_summary": _knowledge_summary(account, server, user),
        "recommendations_summary": _recommendations_summary(account, server),
        "available_tools": _available_tools(account, server, user),
        "recent_tool_runs": _recent_tool_runs(account, server),
        "risk_summary": _risk_summary(findings),
    }
    return _cap_context(_safe_json(context))
