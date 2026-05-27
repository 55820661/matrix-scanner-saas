from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.core.redaction import redact_json, redact_secrets
from apps.servers.models import AgentJob, ScannerAgent, Server
from apps.subscriptions.models import Subscription

from .models import PlanTool, ToolDefinition, ToolPolicy, ToolRun
from .setup import ensure_system_identity_tool
from .validation import ToolParamValidationError, validate_params, validate_path_policy


class ToolPolicyDenied(Exception):
    pass


ACTIVE_SUBSCRIPTION_STATUSES = {Subscription.Status.ACTIVE, Subscription.Status.TRIAL}


def audit_policy_denied(*, account, actor_user=None, tool_key="", reason="", server=None):
    AuditLog.objects.create(
        actor_user=actor_user,
        actor_type=AuditLog.ActorType.USER if actor_user and not actor_user.is_staff else AuditLog.ActorType.ADMIN,
        account=account,
        action="tool_policy.denied",
        target_type="ToolDefinition",
        target_id=tool_key,
        result=AuditLog.Result.DENIED,
        metadata={
            "tool_key": tool_key,
            "server_id": str(server.id) if server else "",
            "reason": reason,
        },
    )


def deny(account, reason, *, actor_user=None, tool_key="", server=None):
    audit_policy_denied(account=account, actor_user=actor_user, tool_key=tool_key, reason=reason, server=server)
    raise ToolPolicyDenied(reason)


def active_subscription_for(account):
    now = timezone.now()
    return (
        Subscription.objects.select_related("plan")
        .filter(account=account, status__in=ACTIVE_SUBSCRIPTION_STATUSES, plan__is_active=True)
        .filter(current_period_end__isnull=True)
        .order_by("-created_at")
        .first()
        or Subscription.objects.select_related("plan")
        .filter(account=account, status__in=ACTIVE_SUBSCRIPTION_STATUSES, plan__is_active=True, current_period_end__gt=now)
        .order_by("-created_at")
        .first()
    )


def redacted_json(value):
    return redact_json(value or {})


def update_tool_run_from_job(job):
    try:
        tool_run = job.tool_run
    except ToolRun.DoesNotExist:
        return None

    status_map = {
        AgentJob.Status.SUCCEEDED: ToolRun.Status.SUCCEEDED,
        AgentJob.Status.FAILED: ToolRun.Status.FAILED,
        AgentJob.Status.REJECTED: ToolRun.Status.REJECTED,
        AgentJob.Status.TIMEOUT: ToolRun.Status.TIMEOUT,
        AgentJob.Status.CANCELLED: ToolRun.Status.CANCELLED,
        AgentJob.Status.RUNNING: ToolRun.Status.RUNNING,
        AgentJob.Status.CLAIMED: ToolRun.Status.QUEUED,
        AgentJob.Status.PENDING: ToolRun.Status.QUEUED,
    }
    tool_run.status = status_map.get(job.status, tool_run.status)
    tool_run.result_redacted = redacted_json(job.result)
    tool_run.error_message = redact_secrets(job.error_message)[:4000]
    tool_run.finished_at = job.finished_at
    if tool_run.status == ToolRun.Status.RUNNING and tool_run.started_at is None:
        tool_run.started_at = timezone.now()
    tool_run.save(update_fields=["status", "result_redacted", "error_message", "finished_at", "started_at", "updated_at"])
    return tool_run


def create_tool_run_job(*, account, server, tool_key, params=None, requested_by=None, requested_by_type=ToolRun.RequestedByType.SYSTEM):
    if tool_key == "system_identity" and not ToolDefinition.objects.filter(key=tool_key).exists():
        ensure_system_identity_tool()
    params = params or {}
    if server.account_id != account.id:
        deny(account, "Server does not belong to account.", actor_user=requested_by, tool_key=tool_key, server=server)

    try:
        tool_definition = ToolDefinition.objects.select_related("template").get(key=tool_key)
    except ToolDefinition.DoesNotExist:
        deny(account, "Tool is not registered.", actor_user=requested_by, tool_key=tool_key, server=server)

    if not tool_definition.template.is_active:
        deny(account, "Tool template is inactive.", actor_user=requested_by, tool_key=tool_key, server=server)
    if tool_definition.status != ToolDefinition.Status.ENABLED:
        deny(account, "Tool is not enabled.", actor_user=requested_by, tool_key=tool_key, server=server)
    if tool_definition.risk_level != ToolDefinition.RiskLevel.READ_ONLY:
        deny(account, "Only read-only tools are allowed in MVP.", actor_user=requested_by, tool_key=tool_key, server=server)

    try:
        policy = tool_definition.policy
    except ToolPolicy.DoesNotExist:
        deny(account, "Tool policy is missing.", actor_user=requested_by, tool_key=tool_key, server=server)
    if not policy.is_active:
        deny(account, "Tool policy does not allow this run.", actor_user=requested_by, tool_key=tool_key, server=server)
    if requested_by_type == ToolRun.RequestedByType.ADMIN and not policy.allow_admin_run:
        deny(account, "Tool policy does not allow admin runs.", actor_user=requested_by, tool_key=tool_key, server=server)
    if requested_by_type == ToolRun.RequestedByType.SYSTEM and not policy.allow_agent_run:
        deny(account, "Tool policy does not allow system runs.", actor_user=requested_by, tool_key=tool_key, server=server)
    if requested_by_type == ToolRun.RequestedByType.USER:
        if not policy.allow_customer_run:
            deny(account, "Tool policy does not allow customer runs.", actor_user=requested_by, tool_key=tool_key, server=server)
        if policy.allowed_roles and (not requested_by or requested_by.role not in policy.allowed_roles):
            deny(account, "User role is not allowed for this tool.", actor_user=requested_by, tool_key=tool_key, server=server)
    if policy.allowed_server_statuses and server.status not in policy.allowed_server_statuses:
        deny(account, "Server status is not allowed for this tool.", actor_user=requested_by, tool_key=tool_key, server=server)

    subscription = active_subscription_for(account)
    if subscription is None:
        deny(account, "No active subscription with an active plan.", actor_user=requested_by, tool_key=tool_key, server=server)
    if not PlanTool.objects.filter(plan=subscription.plan, tool_definition=tool_definition, is_enabled=True).exists():
        deny(account, "Tool is not enabled in the active plan.", actor_user=requested_by, tool_key=tool_key, server=server)

    try:
        validated_params, path_values = validate_params(tool_definition.input_schema, {**tool_definition.default_params, **params})
        validate_path_policy(tool_definition, path_values)
    except ToolParamValidationError as exc:
        deny(account, str(exc), actor_user=requested_by, tool_key=tool_key, server=server)

    try:
        agent = ScannerAgent.objects.get(server=server, account=account)
    except ScannerAgent.DoesNotExist:
        deny(account, "Server has no scanner agent.", actor_user=requested_by, tool_key=tool_key, server=server)
    if not agent.is_active_for_api:
        deny(account, "Scanner agent is not active.", actor_user=requested_by, tool_key=tool_key, server=server)

    with transaction.atomic():
        tool_run = ToolRun.objects.create(
            account=account,
            server=server,
            agent=agent,
            tool_definition=tool_definition,
            requested_by=requested_by,
            requested_by_type=requested_by_type,
            status=ToolRun.Status.PENDING,
            params=validated_params,
            params_redacted=redacted_json(validated_params),
            timeout_seconds=tool_definition.timeout_seconds,
            max_output_bytes=tool_definition.max_output_bytes,
        )
        job = AgentJob.objects.create(
            account=account,
            server=server,
            agent=agent,
            tool_key=tool_definition.key,
            params=validated_params,
            max_output_bytes=tool_definition.max_output_bytes,
        )
        tool_run.agent_job = job
        tool_run.status = ToolRun.Status.QUEUED
        tool_run.save(update_fields=["agent_job", "status", "updated_at"])
    return tool_run, job
