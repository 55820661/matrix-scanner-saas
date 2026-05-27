from apps.plans.models import Plan

from .models import PlanTool, ToolDefinition, ToolPolicy, ToolTemplate


SYSTEM_IDENTITY_KEY = "system_identity"


def ensure_system_identity_tool(*, connect_active_plans=True, reset_existing=False):
    template_defaults = {
        "name": "System identity",
        "description": "Collect basic host identity from the scanner runtime.",
        "runtime_handler_key": SYSTEM_IDENTITY_KEY,
        "input_schema": {"fields": {}},
        "output_schema": {"type": "object"},
        "default_timeout_seconds": 30,
        "default_max_output_bytes": 64 * 1024,
        "is_active": True,
    }
    if reset_existing:
        template, _created = ToolTemplate.objects.update_or_create(key=SYSTEM_IDENTITY_KEY, defaults=template_defaults)
    else:
        template, _created = ToolTemplate.objects.get_or_create(key=SYSTEM_IDENTITY_KEY, defaults=template_defaults)

    definition_defaults = {
        "template": template,
        "name": "System identity",
        "description": "Read-only host identity check.",
        "status": ToolDefinition.Status.ENABLED,
        "risk_level": ToolDefinition.RiskLevel.READ_ONLY,
        "category": "core",
        "input_schema": {"fields": {}},
        "default_params": {},
        "timeout_seconds": 30,
        "max_output_bytes": 64 * 1024,
        "requires_path_policy": False,
        "allowed_path_prefixes": [],
        "blocked_path_prefixes": ["/etc/shadow", "/root", "/home/*/.ssh"],
        "redaction_rules": [],
    }
    if reset_existing:
        definition, _created = ToolDefinition.objects.update_or_create(
            key=SYSTEM_IDENTITY_KEY,
            defaults=definition_defaults,
        )
    else:
        definition, _created = ToolDefinition.objects.get_or_create(
            key=SYSTEM_IDENTITY_KEY,
            defaults=definition_defaults,
        )

    ToolPolicy.objects.get_or_create(
        tool_definition=definition,
        defaults={
            "allow_customer_run": True,
            "allow_admin_run": True,
            "allow_agent_run": True,
            "requires_approved_application": False,
            "allowed_roles": ["owner", "operator"],
            "allowed_server_statuses": ["active"],
            "is_active": True,
        },
    )
    if connect_active_plans:
        for plan in Plan.objects.filter(is_active=True):
            PlanTool.objects.update_or_create(
                plan=plan,
                tool_definition=definition,
                defaults={"is_enabled": True},
            )
    return template, definition
