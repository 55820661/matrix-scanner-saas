from django.db import migrations


BASELINE_TOOL_SPECS = {
    "system_identity": ("System identity", "Collect basic host identity from the scanner runtime.", "core", 30, 64 * 1024),
    "services_status": ("Services status", "Read service status metadata from the scanner host.", "baseline", 30, 64 * 1024),
    "panel_detector": ("Panel detector", "Detect common hosting control panel markers.", "baseline", 30, 64 * 1024),
    "cpanel_domain_scanner": (
        "cPanel domain scanner",
        "Read cPanel domain metadata without storing raw files.",
        "baseline",
        45,
        256 * 1024,
    ),
    "application_discovery": ("Application discovery", "Discover web applications from known webroots.", "baseline", 45, 64 * 1024),
    "laravel_discovery": (
        "Laravel discovery",
        "Discover Laravel apps and approved safe environment keys only.",
        "baseline",
        45,
        64 * 1024,
    ),
    "log_sources_discovery": (
        "Log sources discovery",
        "Discover log source metadata without reading raw logs.",
        "baseline",
        30,
        64 * 1024,
    ),
    "webroot_risk_checker": (
        "Webroot risk checker",
        "Detect read-only webroot risk indicators using evidence summaries.",
        "baseline",
        30,
        64 * 1024,
    ),
}


def seed_baseline_tools(apps, schema_editor):
    ToolTemplate = apps.get_model("tools", "ToolTemplate")
    ToolDefinition = apps.get_model("tools", "ToolDefinition")
    ToolPolicy = apps.get_model("tools", "ToolPolicy")
    PlanTool = apps.get_model("tools", "PlanTool")
    Plan = apps.get_model("plans", "Plan")

    for key, (name, description, category, timeout_seconds, max_output_bytes) in BASELINE_TOOL_SPECS.items():
        template, _created = ToolTemplate.objects.update_or_create(
            key=key,
            defaults={
                "name": name,
                "description": description,
                "runtime_handler_key": key,
                "input_schema": {"fields": {}},
                "output_schema": {"type": "object"},
                "default_timeout_seconds": timeout_seconds,
                "default_max_output_bytes": max_output_bytes,
                "is_active": True,
            },
        )
        definition, _created = ToolDefinition.objects.update_or_create(
            key=key,
            defaults={
                "template": template,
                "name": name,
                "description": description,
                "status": "enabled",
                "risk_level": "read_only",
                "category": category,
                "input_schema": {"fields": {}},
                "default_params": {},
                "timeout_seconds": timeout_seconds,
                "max_output_bytes": max_output_bytes,
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
        ("tools", "0002_seed_system_identity"),
        ("plans", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_baseline_tools, migrations.RunPython.noop),
    ]
