import re

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.core.redaction import redact_json, redact_secrets
from apps.servers.models import AgentJob, ScannerAgent, Server
from apps.subscriptions.models import Subscription

from .models import (
    PlanTool,
    ToolBuildProposal,
    ToolBuildRequest,
    ToolBuildReview,
    ToolDefinition,
    ToolPolicy,
    ToolRun,
    ToolTemplate,
    ToolTestResult,
)
from .setup import BASELINE_TOOL_KEYS, ensure_system_identity_tool
from .validation import ToolParamValidationError, validate_params, validate_path_policy


class ToolPolicyDenied(Exception):
    pass


class ToolBuildValidationError(Exception):
    pass


ACTIVE_SUBSCRIPTION_STATUSES = {Subscription.Status.ACTIVE, Subscription.Status.TRIAL}
ALLOWED_BUILDER_HANDLER_KEYS = set(BASELINE_TOOL_KEYS)
DEFAULT_COMMAND_BLOCKED_TOKENS = (";", "&&", "||", "|", ">", "<", "`", "$", "\n", "\r")
FORBIDDEN_BUILDER_FIELD_PARTS = (
    "command",
    "shell",
    "script",
    "code",
    "exec",
    "write",
    "delete",
    "remove",
    "restart",
    "install",
    "package",
    "chmod",
    "chown",
    "remediation",
    "destructive",
)


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


def _deny_command_template(account, reason, *, actor_user=None, tool_key="", server=None):
    deny(account, reason, actor_user=actor_user, tool_key=tool_key, server=server)


def _render_command_arg(arg, params):
    rendered = arg
    for key, value in params.items():
        if isinstance(value, bool):
            safe_value = "true" if value else "false"
        elif isinstance(value, (str, int, float)):
            safe_value = str(value)
        elif value is None:
            safe_value = ""
        else:
            raise ToolParamValidationError("Command template parameters must be scalar values.")
        rendered = rendered.replace("{" + str(key) + "}", safe_value)
    if "{" in rendered or "}" in rendered:
        raise ToolParamValidationError("Command template contains unresolved placeholders.")
    return rendered


def build_execution_payload(tool_definition, validated_params, *, account, server, actor_user=None):
    execution_type = tool_definition.execution_type or ToolTemplate.ExecutionType.RUNTIME_HANDLER
    if execution_type == ToolTemplate.ExecutionType.RUNTIME_HANDLER:
        return {
            "execution_type": ToolTemplate.ExecutionType.RUNTIME_HANDLER,
            "runtime_handler_key": tool_definition.template.runtime_handler_key,
        }
    if execution_type == ToolTemplate.ExecutionType.SCRIPT_TEMPLATE:
        _deny_command_template(
            account,
            "Script template execution is deferred.",
            actor_user=actor_user,
            tool_key=tool_definition.key,
            server=server,
        )
    if execution_type != ToolTemplate.ExecutionType.COMMAND_TEMPLATE:
        _deny_command_template(
            account,
            "Unsupported tool execution type.",
            actor_user=actor_user,
            tool_key=tool_definition.key,
            server=server,
        )

    template = tool_definition.command_argv_template or tool_definition.template.command_argv_template
    if not isinstance(template, list) or not template or not all(isinstance(part, str) and part for part in template):
        _deny_command_template(
            account,
            "Command template must be a non-empty argv list.",
            actor_user=actor_user,
            tool_key=tool_definition.key,
            server=server,
        )
    blocked_tokens = tuple(tool_definition.blocked_tokens or tool_definition.template.blocked_tokens or DEFAULT_COMMAND_BLOCKED_TOKENS)
    allowed_binaries = tool_definition.allowed_binaries or tool_definition.template.allowed_binaries
    argv = []
    try:
        for part in template:
            rendered = _render_command_arg(part, validated_params)
            if any(token and token in rendered for token in blocked_tokens):
                raise ToolParamValidationError("Command template contains a blocked token.")
            if redact_secrets(rendered) != rendered:
                raise ToolParamValidationError("Command template rendered a secret-like value.")
            argv.append(rendered)
    except ToolParamValidationError as exc:
        _deny_command_template(
            account,
            str(exc),
            actor_user=actor_user,
            tool_key=tool_definition.key,
            server=server,
        )

    binary = argv[0]
    binary_name = binary.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if allowed_binaries and binary not in allowed_binaries and binary_name not in allowed_binaries:
        _deny_command_template(
            account,
            "Command binary is not allowlisted.",
            actor_user=actor_user,
            tool_key=tool_definition.key,
            server=server,
        )
    return {
        "execution_type": ToolTemplate.ExecutionType.COMMAND_TEMPLATE,
        "argv": argv,
        "timeout_seconds": tool_definition.timeout_seconds,
        "max_output_bytes": tool_definition.max_output_bytes,
    }


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

    execution_payload = build_execution_payload(
        tool_definition,
        validated_params,
        account=account,
        server=server,
        actor_user=requested_by,
    )

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
            execution_payload=execution_payload,
        )
        tool_run.agent_job = job
        tool_run.status = ToolRun.Status.QUEUED
        tool_run.save(update_fields=["agent_job", "status", "updated_at"])
    return tool_run, job


def audit_tool_builder(*, actor_user, action, target=None, result=AuditLog.Result.INFO, metadata=None):
    AuditLog.objects.create(
        actor_user=actor_user,
        actor_type=AuditLog.ActorType.ADMIN,
        account=None,
        action=action,
        target_type=target.__class__.__name__ if target else "",
        target_id=str(target.id) if target else "",
        result=result,
        metadata=metadata or {},
    )


def sanitize_builder_text(value, *, limit=4000):
    return redact_secrets(value or "")[:limit]


def sanitize_builder_json(value):
    return redact_json(value or {})


def contains_forbidden_builder_key(value):
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).lower()
            tokens = {token for token in re.split(r"[^a-z0-9]+", normalized) if token}
            if any(part in tokens for part in FORBIDDEN_BUILDER_FIELD_PARTS):
                return True
            if contains_forbidden_builder_key(nested):
                return True
    elif isinstance(value, list):
        return any(contains_forbidden_builder_key(item) for item in value)
    return False


def default_builder_policy():
    return {
        "allow_customer_run": False,
        "allow_admin_run": False,
        "allow_agent_run": False,
        "requires_approved_application": False,
        "allowed_roles": ["owner", "operator"],
        "allowed_server_statuses": ["active"],
        "is_active": False,
    }


def build_definition_payload_from_request(build_request):
    tool_key = build_request.desired_tool_key.strip().lower().replace(" ", "_")
    handler_key = build_request.desired_handler_key.strip()
    return {
        "template": {
            "key": handler_key,
            "name": build_request.title.strip(),
            "description": build_request.description_redacted,
            "runtime_handler_key": handler_key,
            "input_schema": {"fields": {}},
            "output_schema": {"type": "object"},
            "default_timeout_seconds": 30,
            "default_max_output_bytes": 65536,
            "is_active": True,
        },
        "definition": {
            "key": tool_key,
            "name": build_request.title.strip(),
            "description": build_request.description_redacted,
            "status": ToolDefinition.Status.DRAFT,
            "risk_level": ToolDefinition.RiskLevel.READ_ONLY,
            "category": "custom_read_only",
            "input_schema": {"fields": {}},
            "default_params": {},
            "timeout_seconds": 30,
            "max_output_bytes": 65536,
            "requires_path_policy": False,
            "allowed_path_prefixes": [],
            "blocked_path_prefixes": ["/etc/shadow", "/root", "/home/*/.ssh"],
            "redaction_rules": ["password", "secret", "token", "api_key", "private_key", "authorization"],
        },
    }


def generate_tool_build_proposal(build_request, *, actor_user=None):
    build_request.description_redacted = sanitize_builder_text(build_request.description_redacted)
    build_request.status = ToolBuildRequest.Status.SUBMITTED
    build_request.save(update_fields=["description_redacted", "status", "updated_at"])
    audit_tool_builder(
        actor_user=actor_user or build_request.requested_by,
        action="tool_builder.request_submitted",
        target=build_request,
        result=AuditLog.Result.INFO,
        metadata={"request_id": str(build_request.id)},
    )

    payload = sanitize_builder_json(build_definition_payload_from_request(build_request))
    proposal = ToolBuildProposal.objects.create(
        request=build_request,
        proposed_by=actor_user or build_request.requested_by,
        proposed_definition=payload,
        proposed_policy=sanitize_builder_json(default_builder_policy()),
    )
    validate_tool_build_proposal(proposal, actor_user=actor_user or build_request.requested_by)
    build_request.status = ToolBuildRequest.Status.PROPOSED
    build_request.validation_summary = {
        "proposal_id": str(proposal.id),
        "status": proposal.status,
        "error_count": len(proposal.validation_errors),
    }
    build_request.save(update_fields=["status", "validation_summary", "updated_at"])
    audit_tool_builder(
        actor_user=actor_user or build_request.requested_by,
        action="tool_builder.proposal_generated",
        target=proposal,
        result=AuditLog.Result.SUCCESS if proposal.status == ToolBuildProposal.Status.PENDING_REVIEW else AuditLog.Result.FAILURE,
        metadata={"request_id": str(build_request.id), "proposal_id": str(proposal.id), "status": proposal.status},
    )
    return proposal


def validate_builder_schema(schema, errors):
    fields = (schema or {}).get("fields", {})
    if not isinstance(fields, dict):
        errors.append("Input schema fields must be an object.")
        return
    for name, spec in fields.items():
        normalized = str(name).lower()
        if any(part in normalized for part in FORBIDDEN_BUILDER_FIELD_PARTS):
            errors.append("Unsafe parameter names are not allowed.")
        if not isinstance(spec, dict):
            errors.append("Input schema field specs must be objects.")
            continue
        if spec.get("type") not in {"string", "integer", "number", "boolean", "object", "array", "path"}:
            errors.append("Unsupported parameter type.")


def validate_tool_build_proposal(proposal, *, actor_user=None):
    errors = []
    data = proposal.proposed_definition or {}
    template_data = data.get("template") or {}
    definition_data = data.get("definition") or {}
    policy_data = proposal.proposed_policy or {}

    handler_key = template_data.get("runtime_handler_key")
    if handler_key not in ALLOWED_BUILDER_HANDLER_KEYS:
        errors.append("Unknown runtime handler key.")
    if definition_data.get("risk_level") != ToolDefinition.RiskLevel.READ_ONLY:
        errors.append("Only read-only tool proposals are allowed.")
    if contains_forbidden_builder_key(data):
        errors.append("Shell, code, command, write, install, restart, remediation, or destructive fields are not allowed.")
    if not definition_data.get("timeout_seconds"):
        errors.append("Timeout is required.")
    if not definition_data.get("max_output_bytes"):
        errors.append("Max output cap is required.")
    if definition_data.get("status") not in {ToolDefinition.Status.DRAFT, ToolDefinition.Status.PENDING_REVIEW}:
        errors.append("Proposal conversion status must remain draft or pending_review.")
    if not isinstance(definition_data.get("redaction_rules"), list) or not definition_data.get("redaction_rules"):
        errors.append("Redaction rules are required.")
    validate_builder_schema(definition_data.get("input_schema"), errors)
    if definition_data.get("requires_path_policy") and not isinstance(definition_data.get("allowed_path_prefixes"), list):
        errors.append("Allowed path prefixes must be a list.")
    if not isinstance(definition_data.get("blocked_path_prefixes"), list):
        errors.append("Blocked path prefixes must be a list.")
    if policy_data.get("is_active") is not False:
        errors.append("Generated ToolPolicy proposals must be inactive.")
    if any(policy_data.get(flag) for flag in ("allow_customer_run", "allow_admin_run", "allow_agent_run")):
        errors.append("Generated ToolPolicy proposals must not allow live execution automatically.")

    proposal.proposed_definition = sanitize_builder_json(data)
    proposal.proposed_policy = sanitize_builder_json(policy_data)
    proposal.validation_errors = errors
    proposal.status = ToolBuildProposal.Status.VALIDATION_FAILED if errors else ToolBuildProposal.Status.PENDING_REVIEW
    proposal.save(
        update_fields=[
            "proposed_definition",
            "proposed_policy",
            "validation_errors",
            "status",
            "updated_at",
        ]
    )
    ToolTestResult.objects.create(
        proposal=proposal,
        status=ToolTestResult.Status.FAILED if errors else ToolTestResult.Status.PASSED,
        test_type="mock_validation",
        summary_redacted="Validation failed." if errors else "Validation passed.",
        result_redacted={"error_count": len(errors), "status": proposal.status},
    )
    audit_tool_builder(
        actor_user=actor_user or proposal.proposed_by,
        action="tool_builder.validation_failed" if errors else "tool_builder.validation_passed",
        target=proposal,
        result=AuditLog.Result.FAILURE if errors else AuditLog.Result.SUCCESS,
        metadata={"proposal_id": str(proposal.id), "error_count": len(errors)},
    )
    return not errors


def review_tool_build_proposal(proposal, *, reviewer, decision, notes=""):
    notes_redacted = sanitize_builder_text(notes)
    review = ToolBuildReview.objects.create(
        proposal=proposal,
        reviewer=reviewer,
        decision=decision,
        notes_redacted=notes_redacted,
    )
    if decision == ToolBuildReview.Decision.APPROVED:
        if proposal.validation_errors:
            raise ToolBuildValidationError(f"Cannot approve a proposal with validation errors: {proposal.validation_errors}")
        proposal.status = ToolBuildProposal.Status.APPROVED
        audit_action = "tool_builder.proposal_approved"
        audit_result = AuditLog.Result.SUCCESS
    elif decision == ToolBuildReview.Decision.REJECTED:
        proposal.status = ToolBuildProposal.Status.REJECTED
        audit_action = "tool_builder.proposal_rejected"
        audit_result = AuditLog.Result.DENIED
    else:
        proposal.status = ToolBuildProposal.Status.PENDING_REVIEW
        audit_action = "tool_builder.proposal_needs_changes"
        audit_result = AuditLog.Result.INFO
    proposal.save(update_fields=["status", "updated_at"])
    audit_tool_builder(
        actor_user=reviewer,
        action=audit_action,
        target=proposal,
        result=audit_result,
        metadata={"proposal_id": str(proposal.id), "decision": decision},
    )
    return review


def convert_tool_build_proposal(proposal, *, actor_user=None, target_status=ToolDefinition.Status.DRAFT):
    if proposal.status != ToolBuildProposal.Status.APPROVED:
        raise ToolBuildValidationError("Only approved proposals can be converted.")
    if target_status not in {ToolDefinition.Status.DRAFT, ToolDefinition.Status.PENDING_REVIEW}:
        raise ToolBuildValidationError("Converted tools must remain draft or pending_review.")
    if not validate_tool_build_proposal(proposal, actor_user=actor_user or proposal.proposed_by):
        raise ToolBuildValidationError("Proposal validation failed.")

    data = proposal.proposed_definition
    template_data = data["template"]
    definition_data = data["definition"]
    policy_data = proposal.proposed_policy or default_builder_policy()

    with transaction.atomic():
        template, _created = ToolTemplate.objects.get_or_create(
            key=template_data["key"],
            defaults={
                "name": template_data.get("name", template_data["key"]),
                "description": template_data.get("description", ""),
                "runtime_handler_key": template_data["runtime_handler_key"],
                "input_schema": template_data.get("input_schema", {}),
                "output_schema": template_data.get("output_schema", {}),
                "default_timeout_seconds": template_data.get("default_timeout_seconds", 30),
                "default_max_output_bytes": template_data.get("default_max_output_bytes", 65536),
                "is_active": template_data.get("is_active", True),
            },
        )
        tool_definition = ToolDefinition.objects.create(
            template=template,
            key=definition_data["key"],
            name=definition_data.get("name", definition_data["key"]),
            description=definition_data.get("description", ""),
            status=target_status,
            risk_level=ToolDefinition.RiskLevel.READ_ONLY,
            category=definition_data.get("category", ""),
            input_schema=definition_data.get("input_schema", {}),
            default_params=definition_data.get("default_params", {}),
            timeout_seconds=definition_data["timeout_seconds"],
            max_output_bytes=definition_data["max_output_bytes"],
            requires_path_policy=definition_data.get("requires_path_policy", False),
            allowed_path_prefixes=definition_data.get("allowed_path_prefixes", []),
            blocked_path_prefixes=definition_data.get("blocked_path_prefixes", []),
            redaction_rules=definition_data.get("redaction_rules", []),
            created_by=actor_user or proposal.proposed_by,
        )
        ToolPolicy.objects.create(
            tool_definition=tool_definition,
            allow_customer_run=False,
            allow_admin_run=False,
            allow_agent_run=False,
            requires_approved_application=policy_data.get("requires_approved_application", False),
            allowed_roles=policy_data.get("allowed_roles", []),
            allowed_server_statuses=policy_data.get("allowed_server_statuses", []),
            is_active=False,
        )
        proposal.converted_tool_definition = tool_definition
        proposal.status = ToolBuildProposal.Status.CONVERTED
        proposal.save(update_fields=["converted_tool_definition", "status", "updated_at"])

    audit_tool_builder(
        actor_user=actor_user or proposal.proposed_by,
        action="tool_builder.proposal_converted",
        target=proposal,
        result=AuditLog.Result.SUCCESS,
        metadata={"proposal_id": str(proposal.id), "tool_definition_id": str(tool_definition.id), "status": target_status},
    )
    return tool_definition
