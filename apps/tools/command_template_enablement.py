from dataclasses import dataclass, field

from django.db import transaction

from apps.plans.models import Plan

from .models import PlanTool, ToolBuildProposal, ToolDefinition, ToolPolicy, ToolTemplate


CHAT_COMMAND_TEMPLATE_POLICY_DEFAULTS = {
    "allow_customer_run": True,
    "allow_admin_run": True,
    "allow_agent_run": True,
    "requires_approved_application": False,
    "allowed_roles": ["owner", "operator"],
    "allowed_server_statuses": ["active"],
    "is_active": True,
}


@dataclass
class CommandTemplatePilotEnablementResult:
    plan_id: int
    plan_name: str
    tool_key: str
    dry_run: bool
    definition_changes: list[dict] = field(default_factory=list)
    policy_changes: list[dict] = field(default_factory=list)
    plan_tool_changes: list[dict] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)


def enable_command_template_pilot_tool(*, plan_id, tool_key, dry_run=False):
    plan = Plan.objects.get(id=plan_id)
    definition = ToolDefinition.objects.select_related("template").get(key=tool_key)
    _validate_enablement_target(definition)
    result = CommandTemplatePilotEnablementResult(
        plan_id=plan.id,
        plan_name=plan.name,
        tool_key=tool_key,
        dry_run=dry_run,
    )
    if dry_run:
        _plan_changes(plan, definition, result)
        return result
    with transaction.atomic():
        _apply_changes(plan, definition, result)
    return result


def _validate_enablement_target(definition):
    if definition.risk_level != ToolDefinition.RiskLevel.READ_ONLY:
        raise ValueError("Only read-only tools can be enabled for chat pilot use.")
    if definition.execution_type != ToolTemplate.ExecutionType.COMMAND_TEMPLATE:
        raise ValueError("Only command_template tools can be enabled in Sprint C8.")
    if definition.template.execution_type != ToolTemplate.ExecutionType.COMMAND_TEMPLATE:
        raise ValueError("Tool template must also be command_template.")
    if not ToolBuildProposal.objects.filter(
        converted_tool_definition=definition,
        status=ToolBuildProposal.Status.CONVERTED,
    ).exists():
        raise ValueError("Tool must come from a converted approved ToolBuildProposal.")
    if definition.status in {ToolDefinition.Status.REJECTED, ToolDefinition.Status.DEPRECATED, ToolDefinition.Status.DISABLED}:
        raise ValueError("Tool status does not allow pilot enablement.")


def _plan_changes(plan, definition, result):
    if definition.status != ToolDefinition.Status.ENABLED:
        result.definition_changes.append(
            {
                "tool_key": definition.key,
                "action": "would_update_status",
                "from": definition.status,
                "to": ToolDefinition.Status.ENABLED,
            }
        )
    policy = ToolPolicy.objects.filter(tool_definition=definition).first()
    if policy is None:
        result.policy_changes.append({"tool_key": definition.key, "action": "would_create_active_policy"})
    else:
        current = {
            "allow_customer_run": policy.allow_customer_run,
            "allow_admin_run": policy.allow_admin_run,
            "allow_agent_run": policy.allow_agent_run,
            "requires_approved_application": policy.requires_approved_application,
            "allowed_roles": policy.allowed_roles,
            "allowed_server_statuses": policy.allowed_server_statuses,
            "is_active": policy.is_active,
        }
        if current != CHAT_COMMAND_TEMPLATE_POLICY_DEFAULTS:
            result.policy_changes.append({"tool_key": definition.key, "action": "would_update_policy"})
    plan_tool = PlanTool.objects.filter(plan=plan, tool_definition=definition).first()
    if plan_tool is None:
        result.plan_tool_changes.append({"tool_key": definition.key, "action": "would_create_plan_tool", "plan_id": plan.id})
    elif not plan_tool.is_enabled:
        result.plan_tool_changes.append({"tool_key": definition.key, "action": "would_enable_plan_tool", "plan_id": plan.id})


def _apply_changes(plan, definition, result):
    if definition.status != ToolDefinition.Status.ENABLED:
        result.definition_changes.append(
            {
                "tool_key": definition.key,
                "action": "updated_status",
                "from": definition.status,
                "to": ToolDefinition.Status.ENABLED,
            }
        )
        definition.status = ToolDefinition.Status.ENABLED
        definition.save(update_fields=["status", "updated_at"])

    policy, created = ToolPolicy.objects.update_or_create(
        tool_definition=definition,
        defaults=CHAT_COMMAND_TEMPLATE_POLICY_DEFAULTS,
    )
    result.policy_changes.append(
        {
            "tool_key": definition.key,
            "action": "created_policy" if created else "updated_policy",
            "policy_id": policy.id,
        }
    )

    plan_tool, created = PlanTool.objects.update_or_create(
        plan=plan,
        tool_definition=definition,
        defaults={"is_enabled": True},
    )
    result.plan_tool_changes.append(
        {
            "tool_key": definition.key,
            "action": "created_plan_tool" if created else "updated_plan_tool",
            "plan_tool_id": plan_tool.id,
            "plan_id": plan.id,
        }
    )
