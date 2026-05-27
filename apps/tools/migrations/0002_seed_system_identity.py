from django.db import migrations


def seed_system_identity(apps, schema_editor):
    ToolTemplate = apps.get_model("tools", "ToolTemplate")
    ToolDefinition = apps.get_model("tools", "ToolDefinition")
    ToolPolicy = apps.get_model("tools", "ToolPolicy")
    PlanTool = apps.get_model("tools", "PlanTool")
    Plan = apps.get_model("plans", "Plan")

    template, _created = ToolTemplate.objects.update_or_create(
        key="system_identity",
        defaults={
            "name": "System identity",
            "description": "Collect basic host identity from the scanner runtime.",
            "runtime_handler_key": "system_identity",
            "input_schema": {"fields": {}},
            "output_schema": {"type": "object"},
            "default_timeout_seconds": 30,
            "default_max_output_bytes": 64 * 1024,
            "is_active": True,
        },
    )
    definition, _created = ToolDefinition.objects.update_or_create(
        key="system_identity",
        defaults={
            "template": template,
            "name": "System identity",
            "description": "Read-only host identity check.",
            "status": "enabled",
            "risk_level": "read_only",
            "category": "core",
            "input_schema": {"fields": {}},
            "default_params": {},
            "timeout_seconds": 30,
            "max_output_bytes": 64 * 1024,
            "requires_path_policy": False,
            "allowed_path_prefixes": [],
            "blocked_path_prefixes": ["/etc/shadow", "/root", "/home/*/.ssh"],
            "redaction_rules": [],
        },
    )
    ToolPolicy.objects.update_or_create(
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
    for plan in Plan.objects.filter(is_active=True):
        PlanTool.objects.update_or_create(
            plan=plan,
            tool_definition=definition,
            defaults={"is_enabled": True},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0001_initial"),
        ("tools", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_system_identity, migrations.RunPython.noop),
    ]
