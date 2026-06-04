from django.db import transaction
from django.utils import timezone

from apps.applications.models import Application
from apps.audit.models import AuditLog
from apps.core.redaction import redact_json, redact_secrets
from apps.tools.models import PlanTool, ToolDefinition, ToolPolicy, ToolRun
from apps.tools.services import ToolPolicyDenied, active_subscription_for, create_tool_run_job
from apps.tools.setup import BASELINE_TOOL_KEYS, ensure_baseline_tools
from apps.tools.validation import ToolParamValidationError, canonicalize_path, path_matches_prefix

from .baseline_profiles import PROFILE_LEGACY_CPANEL, tool_keys_for_profile
from .models import BaselineScan, BaselineScanStep, DiscoveredDomain, DiscoveredService, Finding, LogSource, ScannerAgent


BASELINE_BLOCKED_PATH_PREFIXES = ("/etc/shadow", "/root", "/home/*/.ssh")
LARAVEL_SAFE_ENV_KEYS = {
    "APP_ENV",
    "APP_DEBUG",
    "APP_URL",
    "LOG_CHANNEL",
    "LOG_LEVEL",
    "CACHE_DRIVER",
    "QUEUE_CONNECTION",
    "SESSION_DRIVER",
    "MAIL_MAILER",
    "DB_CONNECTION",
}
LARAVEL_FORBIDDEN_ENV_KEYS = {"APP_KEY", "DB_PASSWORD", "DB_USERNAME", "MAIL_PASSWORD"}
PHASE2_SERVICE_METADATA_FIELDS = (
    "load_state",
    "active_state",
    "sub_state",
    "enabled_state",
    "unit_type",
    "description",
    "process_type",
    "main_pid",
    "user",
    "working_directory",
    "related_app_path",
    "fragment_path",
    "health_check",
)
PHASE2_DOMAIN_METADATA_FIELDS = (
    "listen",
    "ports",
    "proxy_pass",
    "proxy_target",
    "root",
    "document_root",
    "listen_ports",
    "source_path",
    "source_config_path",
    "config_path",
    "is_wildcard",
    "is_default",
)
PHASE2_LOG_METADATA_FIELDS = ("exists", "is_dir", "size_bytes", "modified_at")
PHASE2_APPLICATION_METADATA_FIELDS = (
    "detection",
    "depth",
    "project_package",
    "has_manage_py",
    "has_wsgi",
    "has_asgi",
    "has_systemd_unit_hint",
    "dependency_files",
)
GUNICORN_UVICORN_PROCESS_TYPES = {"gunicorn", "uvicorn", "daphne"}
FRAMEWORK_PRIORITY = {
    "": 0,
    "unknown": 1,
    "php": 2,
    "python": 3,
    "node": 4,
    "laravel": 5,
    "django": 6,
}
SAFE_METADATA_TEXT_LIMIT = 1000


class BaselineScanError(Exception):
    pass


def audit_baseline(scan, action, result=AuditLog.Result.INFO, metadata=None):
    AuditLog.objects.create(
        actor_user=scan.requested_by,
        actor_type=AuditLog.ActorType.ADMIN if scan.requested_by and scan.requested_by.is_staff else AuditLog.ActorType.SYSTEM,
        account=scan.account,
        action=action,
        target_type="BaselineScan",
        target_id=str(scan.id),
        result=result,
        metadata=metadata or {},
    )


def fail_scan(scan, message):
    scan.status = BaselineScan.Status.FAILED
    scan.error_message = redact_secrets(message)[:4000]
    scan.finished_at = timezone.now()
    scan.save(update_fields=["status", "error_message", "finished_at", "updated_at"])
    audit_baseline(scan, "baseline_scan.failed", result=AuditLog.Result.FAILURE, metadata={"scan_id": str(scan.id)})


def clean_path(value):
    if not value:
        return ""
    try:
        path = canonicalize_path(str(value))
    except ToolParamValidationError:
        return ""
    if path.startswith("/home/") and "/.ssh" in path:
        return ""
    for prefix in BASELINE_BLOCKED_PATH_PREFIXES:
        if path_matches_prefix(path, prefix):
            return ""
    return path


def safe_laravel_env(raw_env):
    safe = {}
    for key, value in (raw_env or {}).items():
        normalized = str(key).upper()
        if normalized in LARAVEL_FORBIDDEN_ENV_KEYS or normalized.startswith("AWS_"):
            continue
        if normalized.endswith("_SECRET") or normalized.endswith("_TOKEN"):
            continue
        if "PRIVATE KEY" in str(value).upper():
            continue
        if normalized in LARAVEL_SAFE_ENV_KEYS:
            safe[normalized] = redact_secrets(value)
    return safe


def safe_metadata_value(value):
    if isinstance(value, str):
        return redact_secrets(value)[:SAFE_METADATA_TEXT_LIMIT]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [safe_metadata_value(item) for item in value[:50]]
    if isinstance(value, dict):
        return {
            str(key)[:120]: safe_metadata_value(nested)
            for key, nested in list(value.items())[:50]
        }
    return redact_secrets(str(value))[:SAFE_METADATA_TEXT_LIMIT]


def selected_metadata(item, fields, source_tool):
    metadata = {"source": source_tool}
    for field in fields:
        if field in item:
            metadata[field] = safe_metadata_value(item.get(field))
    nested_metadata = item.get("metadata")
    if isinstance(nested_metadata, dict):
        for key, value in nested_metadata.items():
            normalized_key = str(key)[:120]
            if normalized_key not in metadata:
                metadata[normalized_key] = safe_metadata_value(value)
    return redact_json(metadata)


def merge_metadata(existing, incoming):
    return redact_json({**(existing or {}), **(incoming or {})})


def normalized_framework(value):
    return str(value or "").strip().lower()[:100]


def preferred_framework(existing, incoming):
    existing = normalized_framework(existing)
    incoming = normalized_framework(incoming)
    if FRAMEWORK_PRIORITY.get(incoming, 0) > FRAMEWORK_PRIORITY.get(existing, 0):
        return incoming
    return existing


def preflight_required_baseline_tools(scan):
    if scan.server.account_id != scan.account_id:
        raise BaselineScanError("Server does not belong to scan account.")

    subscription = active_subscription_for(scan.account)
    if subscription is None:
        raise BaselineScanError("No active subscription with an active plan.")

    try:
        agent = ScannerAgent.objects.get(account=scan.account, server=scan.server)
    except ScannerAgent.DoesNotExist as exc:
        raise BaselineScanError("Server has no active scanner agent.") from exc
    if not agent.is_active_for_api:
        raise BaselineScanError("Scanner agent is not active.")

    missing = []
    for tool_key in baseline_tool_keys_for_scan(scan):
        try:
            tool = ToolDefinition.objects.select_related("template").get(key=tool_key)
        except ToolDefinition.DoesNotExist:
            missing.append(tool_key)
            continue
        if not tool.template.is_active or tool.status != ToolDefinition.Status.ENABLED:
            missing.append(tool_key)
            continue
        if tool.risk_level != ToolDefinition.RiskLevel.READ_ONLY:
            missing.append(tool_key)
            continue
        if not ToolPolicy.objects.filter(tool_definition=tool, is_active=True, allow_agent_run=True).exists():
            missing.append(tool_key)
            continue
        if not PlanTool.objects.filter(plan=subscription.plan, tool_definition=tool, is_enabled=True).exists():
            missing.append(tool_key)
    if missing:
        raise BaselineScanError(f"Baseline required tools are not allowed: {', '.join(missing)}")


def start_baseline_scan(scan):
    scan = BaselineScan.objects.select_related("account", "server", "requested_by").get(id=scan.id)
    if scan.status not in {BaselineScan.Status.PENDING, BaselineScan.Status.FAILED}:
        raise BaselineScanError("Baseline scan cannot be started from its current status.")

    ensure_baseline_tools(connect_active_plans=False)
    try:
        preflight_required_baseline_tools(scan)
    except BaselineScanError as exc:
        fail_scan(scan, str(exc))
        raise

    scan.status = BaselineScan.Status.RUNNING
    scan.started_at = timezone.now()
    scan.finished_at = None
    scan.error_message = ""
    scan.current_step = "enqueue_baseline_tools"
    scan.save(update_fields=["status", "started_at", "finished_at", "error_message", "current_step", "updated_at"])
    audit_baseline(scan, "baseline_scan.started", result=AuditLog.Result.SUCCESS, metadata={"scan_id": str(scan.id)})
    enqueue_next_baseline_tools(scan)
    return scan


def enqueue_next_baseline_tools(scan):
    scan = BaselineScan.objects.select_related("account", "server", "requested_by").get(id=scan.id)
    if scan.status != BaselineScan.Status.RUNNING:
        raise BaselineScanError("Baseline scan is not running.")

    try:
        preflight_required_baseline_tools(scan)
        with transaction.atomic():
            locked_scan = BaselineScan.objects.select_for_update().get(id=scan.id)
            for tool_key in baseline_tool_keys_for_scan(locked_scan):
                if BaselineScanStep.objects.filter(baseline_scan=locked_scan, step_key=tool_key).exists():
                    continue
                tool_run, _job = create_tool_run_job(
                    account=scan.account,
                    server=scan.server,
                    tool_key=tool_key,
                    requested_by=scan.requested_by,
                    requested_by_type=ToolRun.RequestedByType.ADMIN,
                )
                BaselineScanStep.objects.create(
                    baseline_scan=locked_scan,
                    tool_run=tool_run,
                    step_key=tool_key,
                    status=BaselineScanStep.Status.QUEUED,
                )
    except (BaselineScanError, ToolPolicyDenied) as exc:
        fail_scan(scan, str(exc))
        raise BaselineScanError(str(exc)) from exc

    scan.current_step = "waiting_for_agent_results"
    scan.save(update_fields=["current_step", "updated_at"])
    return scan


def baseline_tool_keys_for_scan(scan):
    return tool_keys_for_profile(getattr(scan, "profile_key", ""))


def result_for_tool_run(tool_run):
    result = tool_run.result_redacted or {}
    return result if isinstance(result, dict) else {}


def ingest_completed_tool_runs(scan):
    scan = BaselineScan.objects.select_related("account", "server").get(id=scan.id)
    steps = list(scan.steps.select_related("tool_run", "tool_run__tool_definition"))
    if not steps:
        return scan

    for step in steps:
        tool_run = step.tool_run
        if tool_run is None or tool_run.status not in {
            ToolRun.Status.SUCCEEDED,
            ToolRun.Status.FAILED,
            ToolRun.Status.REJECTED,
            ToolRun.Status.TIMEOUT,
            ToolRun.Status.CANCELLED,
        }:
            continue

        step.structured_output = redact_json(result_for_tool_run(tool_run))
        step.finished_at = tool_run.finished_at or timezone.now()
        if tool_run.status == ToolRun.Status.SUCCEEDED:
            step.status = BaselineScanStep.Status.SUCCEEDED
            ingest_tool_result(scan, tool_run.tool_definition.key, step.structured_output)
        else:
            step.status = BaselineScanStep.Status.FAILED
            step.error_message = redact_secrets(tool_run.error_message)[:4000]
        step.save(update_fields=["status", "structured_output", "finished_at", "error_message", "updated_at"])

    refreshed_steps = list(scan.steps.all())
    if refreshed_steps and all(step.status == BaselineScanStep.Status.SUCCEEDED for step in refreshed_steps):
        scan.status = BaselineScan.Status.SUCCEEDED
        scan.current_step = "completed"
        scan.finished_at = timezone.now()
        scan.summary = summarize_scan(scan)
        scan.save(update_fields=["status", "current_step", "finished_at", "summary", "updated_at"])
        audit_baseline(scan, "baseline_scan.completed", result=AuditLog.Result.SUCCESS, metadata={"scan_id": str(scan.id)})
    elif any(step.status == BaselineScanStep.Status.FAILED for step in refreshed_steps):
        fail_scan(scan, "One or more baseline steps failed.")
    return scan


def ingest_tool_result(scan, tool_key, result):
    if tool_key == "services_status":
        ingest_services(scan, result.get("services", []))
    elif tool_key in {
        "systemd_services_discovery",
        "gunicorn_uvicorn_services_discovery",
        "postgres_status_discovery",
    }:
        ingest_phase2_services(scan, result.get("services", []), tool_key)
    elif tool_key == "cpanel_domain_scanner":
        ingest_domains(scan, result.get("domains", []))
    elif tool_key == "nginx_sites_discovery":
        ingest_phase2_domains(scan, result.get("domains", []), tool_key)
    elif tool_key == "application_discovery":
        ingest_applications(scan, result.get("applications", []))
    elif tool_key == "laravel_discovery":
        ingest_applications(scan, result.get("applications", []), framework_hint="laravel")
    elif tool_key in {"opt_apps_discovery", "django_apps_discovery"}:
        ingest_phase2_applications(scan, result.get("applications", []), tool_key)
    elif tool_key == "log_sources_discovery":
        ingest_log_sources(scan, result.get("log_sources", []))
    elif tool_key == "log_sources_discovery_v2":
        ingest_phase2_log_sources(scan, result.get("log_sources", []), tool_key)
    elif tool_key == "webroot_risk_checker":
        ingest_findings(scan, result.get("findings", []))


def ingest_services(scan, services):
    for item in services or []:
        name = str(item.get("name", "")).strip()[:160]
        if not name:
            continue
        DiscoveredService.objects.update_or_create(
            account=scan.account,
            server=scan.server,
            name=name,
            defaults={
                "baseline_scan": scan,
                "status": str(item.get("status", ""))[:80],
                "version": str(item.get("version", ""))[:160],
                "metadata": redact_json(item.get("metadata", {})),
            },
        )


def ingest_phase2_services(scan, services, source_tool):
    for item in services or []:
        if not isinstance(item, dict):
            continue
        if source_tool == "gunicorn_uvicorn_services_discovery":
            process_type = str(item.get("process_type", "")).strip().lower()
            if process_type not in GUNICORN_UVICORN_PROCESS_TYPES:
                continue
        name = str(item.get("service_name") or item.get("name") or "").strip()[:160]
        if not name:
            continue
        status = str(item.get("active_state") or item.get("status") or "")[:80]
        metadata = selected_metadata(item, PHASE2_SERVICE_METADATA_FIELDS, source_tool)
        service, created = DiscoveredService.objects.get_or_create(
            account=scan.account,
            server=scan.server,
            name=name,
            defaults={
                "baseline_scan": scan,
                "status": status,
                "version": "",
                "metadata": metadata,
            },
        )
        if created:
            continue
        service.baseline_scan = scan
        if status:
            service.status = status
        service.metadata = merge_metadata(service.metadata, metadata)
        service.save(update_fields=["baseline_scan", "status", "metadata", "updated_at"])


def ingest_domains(scan, domains):
    for item in domains or []:
        domain = str(item.get("domain", "")).strip().lower()[:255]
        if not domain:
            continue
        DiscoveredDomain.objects.update_or_create(
            account=scan.account,
            server=scan.server,
            domain=domain,
            defaults={
                "baseline_scan": scan,
                "document_root": clean_path(item.get("document_root", "")),
                "owner": str(item.get("owner", ""))[:120],
                "metadata": redact_json(item.get("metadata", {})),
            },
        )


def ingest_phase2_domains(scan, domains, source_tool):
    for item in domains or []:
        if not isinstance(item, dict):
            continue
        domain = str(item.get("domain") or item.get("server_name") or "").strip().lower()[:255]
        if not domain or domain in {"_", "default", "default_server"}:
            continue
        document_root = clean_path(item.get("root") or item.get("document_root") or "")
        metadata = selected_metadata(item, PHASE2_DOMAIN_METADATA_FIELDS, source_tool)
        discovered, created = DiscoveredDomain.objects.get_or_create(
            account=scan.account,
            server=scan.server,
            domain=domain,
            defaults={
                "baseline_scan": scan,
                "document_root": document_root,
                "owner": "",
                "metadata": metadata,
            },
        )
        if created:
            continue
        discovered.baseline_scan = scan
        if document_root:
            discovered.document_root = document_root
        discovered.metadata = merge_metadata(discovered.metadata, metadata)
        discovered.save(update_fields=["baseline_scan", "document_root", "metadata", "updated_at"])


def ingest_applications(scan, applications, framework_hint=""):
    for item in applications or []:
        path = clean_path(item.get("path", ""))
        if not path:
            continue
        domain = str(item.get("domain", "")).strip().lower()[:255]
        framework = (framework_hint or str(item.get("framework", ""))).strip()[:100]
        name = str(item.get("name") or domain or path).strip()[:255]
        metadata = redact_json(item.get("metadata", {}))
        safe_env = safe_laravel_env(item.get("env", {}))
        if safe_env:
            metadata["laravel_env"] = safe_env

        app, created = Application.objects.get_or_create(
            account=scan.account,
            server=scan.server,
            domain=domain,
            path=path,
            defaults={
                "baseline_scan": scan,
                "name": name,
                "framework": framework,
                "review_status": Application.ReviewStatus.PENDING_REVIEW,
                "metadata": metadata,
            },
        )
        if created:
            continue
        app.baseline_scan = scan
        app.metadata = {**(app.metadata or {}), **metadata}
        update_fields = ["baseline_scan", "metadata", "updated_at"]
        if app.review_status != Application.ReviewStatus.APPROVED:
            app.name = name
            app.framework = framework
            app.review_status = Application.ReviewStatus.PENDING_REVIEW
            update_fields.extend(["name", "framework", "review_status"])
        elif not app.framework and framework:
            app.framework = framework
            update_fields.append("framework")
        app.save(update_fields=update_fields)


def ingest_phase2_applications(scan, applications, source_tool):
    for item in applications or []:
        if not isinstance(item, dict):
            continue
        path = clean_path(item.get("path", ""))
        if not path:
            continue
        domain = str(item.get("domain", "")).strip().lower()[:255]
        default_framework = "django" if source_tool == "django_apps_discovery" else ""
        framework = normalized_framework(item.get("framework") or default_framework or "unknown")
        name = str(item.get("name") or domain or path.rsplit("/", 1)[-1] or path).strip()[:255]
        metadata = selected_metadata(item, PHASE2_APPLICATION_METADATA_FIELDS, source_tool)

        app, created = Application.objects.get_or_create(
            account=scan.account,
            server=scan.server,
            domain=domain,
            path=path,
            defaults={
                "baseline_scan": scan,
                "name": name,
                "framework": framework,
                "review_status": Application.ReviewStatus.PENDING_REVIEW,
                "metadata": metadata,
            },
        )
        if created:
            continue

        app.baseline_scan = scan
        app.metadata = merge_metadata(app.metadata, metadata)
        update_fields = ["baseline_scan", "metadata", "updated_at"]
        if app.review_status != Application.ReviewStatus.APPROVED:
            app.framework = preferred_framework(app.framework, framework)
            app.review_status = Application.ReviewStatus.PENDING_REVIEW
            if name and (not app.name or app.name == app.path or app.name == app.path.rsplit("/", 1)[-1]):
                app.name = name
            update_fields.extend(["framework", "review_status", "name"])
        app.save(update_fields=update_fields)


def ingest_log_sources(scan, log_sources):
    for item in log_sources or []:
        path = clean_path(item.get("path", ""))
        if not path:
            continue
        LogSource.objects.update_or_create(
            account=scan.account,
            server=scan.server,
            path=path,
            defaults={
                "baseline_scan": scan,
                "source_type": str(item.get("type", item.get("source_type", "")))[:120],
                "exists": bool(item.get("exists", False)),
                "size_bytes": item.get("size_bytes") if isinstance(item.get("size_bytes"), int) else None,
                "metadata": redact_json(item.get("metadata", {})),
            },
        )


def ingest_phase2_log_sources(scan, log_sources, source_tool):
    for item in log_sources or []:
        if not isinstance(item, dict):
            continue
        path = clean_path(item.get("path", ""))
        if not path:
            continue
        metadata = selected_metadata(item, PHASE2_LOG_METADATA_FIELDS, source_tool)
        log_source, created = LogSource.objects.get_or_create(
            account=scan.account,
            server=scan.server,
            path=path,
            defaults={
                "baseline_scan": scan,
                "source_type": str(item.get("type", item.get("source_type", "")))[:120],
                "exists": bool(item.get("exists", False)),
                "size_bytes": item.get("size_bytes") if isinstance(item.get("size_bytes"), int) else None,
                "metadata": metadata,
            },
        )
        if created:
            continue
        log_source.baseline_scan = scan
        log_source.source_type = str(item.get("type", item.get("source_type", log_source.source_type)))[:120]
        log_source.exists = bool(item.get("exists", log_source.exists))
        if isinstance(item.get("size_bytes"), int):
            log_source.size_bytes = item.get("size_bytes")
        log_source.metadata = merge_metadata(log_source.metadata, metadata)
        log_source.save(update_fields=["baseline_scan", "source_type", "exists", "size_bytes", "metadata", "updated_at"])


def ingest_findings(scan, findings):
    for item in findings or []:
        path = clean_path(item.get("path", "")) if item.get("path") else ""
        title = str(item.get("title", "")).strip()[:255]
        if not title:
            continue
        severity = str(item.get("severity", "info")).strip()[:40] or "info"
        fingerprint = str(item.get("fingerprint") or f"{scan.server_id}:{title}:{path}")[:255]
        Finding.objects.update_or_create(
            account=scan.account,
            server=scan.server,
            fingerprint=fingerprint,
            defaults={
                "baseline_scan": scan,
                "status": Finding.Status.OPEN,
                "severity": severity,
                "title": title,
                "description": redact_secrets(item.get("description", ""))[:4000],
                "evidence_summary": redact_secrets(item.get("evidence_summary", ""))[:4000],
                "metadata": redact_json({"path": path, **(item.get("metadata", {}) or {})}),
            },
        )


def summarize_scan(scan):
    scan_applications = Application.objects.filter(baseline_scan=scan)
    if scan_applications.exists():
        application_count = scan_applications.count()
    elif getattr(scan, "profile_key", "") == PROFILE_LEGACY_CPANEL:
        application_count = Application.objects.filter(account=scan.account, server=scan.server).count()
    else:
        application_count = 0
    return {
        "services": DiscoveredService.objects.filter(baseline_scan=scan).count(),
        "domains": DiscoveredDomain.objects.filter(baseline_scan=scan).count(),
        "applications": application_count,
        "log_sources": LogSource.objects.filter(baseline_scan=scan).count(),
        "findings": Finding.objects.filter(baseline_scan=scan).count(),
    }
