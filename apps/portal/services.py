from django.utils import timezone

from apps.accounts.models import Account
from apps.applications.models import Application
from apps.audit.models import AuditLog
from apps.core.redaction import redact_json, redact_secrets
from apps.servers.models import AgentRegistrationToken, Finding, Server


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


def audit_portal_action(*, user, action, target_type="", target_id="", result=AuditLog.Result.SUCCESS, metadata=None):
    AuditLog.objects.create(
        actor_user=user,
        actor_type=AuditLog.ActorType.USER,
        account=user.account,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else "",
        result=result,
        metadata=metadata or {},
    )


def safe_application_metadata(application):
    metadata = application.metadata or {}
    laravel_env = metadata.get("laravel_env", {})
    safe = {
        key: redact_secrets(value)
        for key, value in laravel_env.items()
        if str(key).upper() in LARAVEL_SAFE_ENV_KEYS
    }
    return {"laravel_env": safe} if safe else {}


def safe_finding_evidence(finding):
    return redact_secrets(finding.evidence_summary)


def safe_baseline_summary(scan):
    summary = scan.summary if isinstance(scan.summary, dict) else {}
    return redact_json(
        {
            "services": summary.get("services", 0),
            "domains": summary.get("domains", 0),
            "applications": summary.get("applications", 0),
            "log_sources": summary.get("log_sources", 0),
            "findings": summary.get("findings", 0),
        }
    )


def create_registration_token_for_portal(user, server):
    if user.account.status != Account.Status.ACTIVE:
        raise ValueError("Registration tokens are only available for active accounts.")
    if server.status == Server.Status.ARCHIVED:
        raise ValueError("Registration tokens are not available for archived servers.")
    token, raw_token = AgentRegistrationToken.create_for_server(server, created_by=user, ttl_minutes=60)
    audit_portal_action(
        user=user,
        action="portal.registration_issued",
        target_type="AgentRegistrationToken",
        target_id=token.id,
        metadata={
            "server_id": str(server.id),
            "registration_id": str(token.id),
            "expires_at": token.expires_at.isoformat(),
        },
    )
    return token, raw_token


def apply_application_action(user, application, action):
    status_map = {
        "approve": Application.ReviewStatus.APPROVED,
        "ignore": Application.ReviewStatus.IGNORED,
        "archive": Application.ReviewStatus.ARCHIVED,
    }
    if action not in status_map:
        raise ValueError("Unsupported application action.")
    application.review_status = status_map[action]
    application.save(update_fields=["review_status", "updated_at"])
    audit_portal_action(
        user=user,
        action=f"portal.application.{action}",
        target_type="Application",
        target_id=application.id,
        metadata={"application_id": str(application.id), "server_id": str(application.server_id)},
    )


def apply_finding_action(user, finding, action):
    status_map = {
        "acknowledge": Finding.Status.ACKNOWLEDGED,
        "ignore": Finding.Status.IGNORED,
    }
    if action not in status_map:
        raise ValueError("Unsupported finding action.")
    finding.status = status_map[action]
    finding.save(update_fields=["status", "updated_at"])
    audit_portal_action(
        user=user,
        action=f"portal.finding.{action}",
        target_type="Finding",
        target_id=finding.id,
        metadata={"finding_id": str(finding.id), "server_id": str(finding.server_id)},
    )


def active_subscription_for_display(account):
    now = timezone.now()
    return (
        account.subscriptions.select_related("plan")
        .filter(status__in=["active", "trial"], plan__is_active=True)
        .filter(current_period_end__isnull=True)
        .order_by("-created_at")
        .first()
        or account.subscriptions.select_related("plan")
        .filter(status__in=["active", "trial"], plan__is_active=True, current_period_end__gt=now)
        .order_by("-created_at")
        .first()
    )
