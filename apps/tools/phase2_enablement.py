from dataclasses import dataclass, field

from django.db import transaction

from apps.plans.models import Plan

from .models import PlanTool, ToolDefinition, ToolPolicy
from .setup import PHASE2_DISCOVERY_TOOL_KEYS, SYSTEM_IDENTITY_KEY, ensure_phase2_discovery_tool_contracts


PILOT_POLICY_DEFAULTS = {
    "allow_customer_run": False,
    "allow_admin_run": True,
    "allow_agent_run": True,
    "requires_approved_application": False,
    "allowed_roles": ["owner", "operator"],
    "allowed_server_statuses": ["active"],
    "is_active": True,
}


@dataclass
class Phase2PilotEnablementResult:
    plan_id: int
    plan_name: str
    dry_run: bool
    definition_changes: list[dict] = field(default_factory=list)
    policy_changes: list[dict] = field(default_factory=list)
    plan_tool_changes: list[dict] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    dependency_warnings: list[str] = field(default_factory=list)

    @property
    def changed_count(self):
        return len(self.definition_changes) + len(self.policy_changes) + len(self.plan_tool_changes)


def enable_phase2_pilot_tools(*, plan_id, dry_run=False):
    plan = Plan.objects.get(id=plan_id)
    result = Phase2PilotEnablementResult(
        plan_id=plan.id,
        plan_name=plan.name,
        dry_run=dry_run,
    )
    _record_system_identity_state(result)

    if dry_run:
        _plan_phase2_changes(plan, result)
        return result

    with transaction.atomic():
        ensure_phase2_discovery_tool_contracts(connect_active_plans=False, activate_policy=False)
        _apply_phase2_changes(plan, result)
    return result


def _record_system_identity_state(result):
    definition = ToolDefinition.objects.filter(key=SYSTEM_IDENTITY_KEY).first()
    if definition is None:
        result.dependency_warnings.append("system_identity is missing")
        return
    if definition.status != ToolDefinition.Status.ENABLED:
        result.dependency_warnings.append("system_identity is not enabled")
    if definition.risk_level != ToolDefinition.RiskLevel.READ_ONLY:
        result.dependency_warnings.append("system_identity is not read_only")


def _plan_phase2_changes(plan, result):
    for tool_key in PHASE2_DISCOVERY_TOOL_KEYS:
        definition = ToolDefinition.objects.filter(key=tool_key).first()
        if definition is None:
            result.definition_changes.append({"tool_key": tool_key, "action": "would_create_and_enable"})
            result.policy_changes.append({"tool_key": tool_key, "action": "would_create_active_policy"})
            result.plan_tool_changes.append({"tool_key": tool_key, "action": "would_create_plan_tool", "plan_id": plan.id})
            continue
        if definition.risk_level != ToolDefinition.RiskLevel.READ_ONLY:
            result.skipped.append({"tool_key": tool_key, "reason": "non_read_only"})
            continue
        if definition.status != ToolDefinition.Status.ENABLED:
            result.definition_changes.append(
                {
                    "tool_key": tool_key,
                    "action": "would_update_status",
                    "from": definition.status,
                    "to": ToolDefinition.Status.ENABLED,
                }
            )
        _record_policy_plan(tool_key, definition, result)
        _record_plan_tool_plan(plan, tool_key, definition, result)


def _apply_phase2_changes(plan, result):
    for tool_key in PHASE2_DISCOVERY_TOOL_KEYS:
        definition = ToolDefinition.objects.get(key=tool_key)
        if definition.risk_level != ToolDefinition.RiskLevel.READ_ONLY:
            result.skipped.append({"tool_key": tool_key, "reason": "non_read_only"})
            continue
        if definition.status != ToolDefinition.Status.ENABLED:
            result.definition_changes.append(
                {
                    "tool_key": tool_key,
                    "action": "updated_status",
                    "from": definition.status,
                    "to": ToolDefinition.Status.ENABLED,
                }
            )
            definition.status = ToolDefinition.Status.ENABLED
            definition.save(update_fields=["status", "updated_at"])

        policy, created = ToolPolicy.objects.update_or_create(
            tool_definition=definition,
            defaults=PILOT_POLICY_DEFAULTS,
        )
        result.policy_changes.append(
            {
                "tool_key": tool_key,
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
                "tool_key": tool_key,
                "action": "created_plan_tool" if created else "updated_plan_tool",
                "plan_tool_id": plan_tool.id,
                "plan_id": plan.id,
            }
        )


def _record_policy_plan(tool_key, definition, result):
    policy = ToolPolicy.objects.filter(tool_definition=definition).first()
    if policy is None:
        result.policy_changes.append({"tool_key": tool_key, "action": "would_create_active_policy"})
        return
    current = {
        "allow_customer_run": policy.allow_customer_run,
        "allow_admin_run": policy.allow_admin_run,
        "allow_agent_run": policy.allow_agent_run,
        "requires_approved_application": policy.requires_approved_application,
        "allowed_roles": policy.allowed_roles,
        "allowed_server_statuses": policy.allowed_server_statuses,
        "is_active": policy.is_active,
    }
    if current != PILOT_POLICY_DEFAULTS:
        result.policy_changes.append({"tool_key": tool_key, "action": "would_update_policy"})


def _record_plan_tool_plan(plan, tool_key, definition, result):
    plan_tool = PlanTool.objects.filter(plan=plan, tool_definition=definition).first()
    if plan_tool is None:
        result.plan_tool_changes.append({"tool_key": tool_key, "action": "would_create_plan_tool", "plan_id": plan.id})
    elif not plan_tool.is_enabled:
        result.plan_tool_changes.append({"tool_key": tool_key, "action": "would_enable_plan_tool", "plan_id": plan.id})
