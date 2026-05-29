from django.db import migrations


PHASE2_DISCOVERY_TOOL_SPECS = {
    "systemd_services_discovery": (
        "systemd services discovery",
        "Discover systemd service metadata for Debian/Nginx style hosts without reading unit secrets.",
        "phase2_discovery",
        45,
        64 * 1024,
        {"type": "object", "fields": {"services": "array", "summary": "object"}},
    ),
    "nginx_sites_discovery": (
        "Nginx sites discovery",
        "Discover enabled Nginx server names, listen ports, and document roots without storing raw config.",
        "phase2_discovery",
        45,
        64 * 1024,
        {"type": "object", "fields": {"domains": "array", "sites": "array", "summary": "object"}},
    ),
    "opt_apps_discovery": (
        "/opt applications discovery",
        "Discover application directories under allowlisted /opt paths using metadata summaries only.",
        "phase2_discovery",
        45,
        64 * 1024,
        {"type": "object", "fields": {"applications": "array", "summary": "object"}},
    ),
    "django_apps_discovery": (
        "Django applications discovery",
        "Detect Django application metadata from safe project markers without reading secrets or full settings.",
        "phase2_discovery",
        45,
        64 * 1024,
        {"type": "object", "fields": {"applications": "array", "summary": "object"}},
    ),
    "gunicorn_uvicorn_services_discovery": (
        "Gunicorn/Uvicorn services discovery",
        "Summarize Gunicorn and Uvicorn service metadata without storing raw command lines containing secrets.",
        "phase2_discovery",
        45,
        64 * 1024,
        {"type": "object", "fields": {"services": "array", "applications": "array", "summary": "object"}},
    ),
    "postgres_status_discovery": (
        "PostgreSQL status discovery",
        "Discover PostgreSQL service and socket metadata without reading credentials or database contents.",
        "phase2_discovery",
        30,
        64 * 1024,
        {"type": "object", "fields": {"services": "array", "summary": "object"}},
    ),
    "log_sources_discovery_v2": (
        "Log sources discovery for Debian/Nginx",
        "Discover Nginx, Django, Gunicorn/Uvicorn, PostgreSQL, and systemd log source metadata without raw logs.",
        "phase2_discovery",
        45,
        64 * 1024,
        {"type": "object", "fields": {"log_sources": "array", "summary": "object"}},
    ),
}

BLOCKED_PATH_PREFIXES = ["/etc/shadow", "/etc/ssl/private", "/root", "/home/*/.ssh", "/opt/*/.env", "/opt/*/secrets"]
REDACTION_RULES = [
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "private_key",
    "authorization",
    "credential",
    "database_url",
]


def seed_phase2_discovery_tool_contracts(apps, schema_editor):
    ToolTemplate = apps.get_model("tools", "ToolTemplate")
    ToolDefinition = apps.get_model("tools", "ToolDefinition")
    ToolPolicy = apps.get_model("tools", "ToolPolicy")

    for key, (name, description, category, timeout_seconds, max_output_bytes, output_schema) in PHASE2_DISCOVERY_TOOL_SPECS.items():
        template, _created = ToolTemplate.objects.update_or_create(
            key=key,
            defaults={
                "name": name,
                "description": description,
                "runtime_handler_key": key,
                "input_schema": {"fields": {}, "required": []},
                "output_schema": output_schema,
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
                "status": "approved",
                "risk_level": "read_only",
                "category": category,
                "input_schema": {"fields": {}, "required": []},
                "default_params": {},
                "timeout_seconds": timeout_seconds,
                "max_output_bytes": max_output_bytes,
                "requires_path_policy": False,
                "allowed_path_prefixes": [],
                "blocked_path_prefixes": BLOCKED_PATH_PREFIXES,
                "redaction_rules": REDACTION_RULES,
            },
        )
        ToolPolicy.objects.update_or_create(
            tool_definition=definition,
            defaults={
                "allow_customer_run": False,
                "allow_admin_run": False,
                "allow_agent_run": False,
                "requires_approved_application": False,
                "allowed_roles": ["owner", "operator"],
                "allowed_server_statuses": ["active"],
                "is_active": False,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("tools", "0004_toolbuildrequest_toolbuildproposal_toolbuildreview_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_phase2_discovery_tool_contracts, migrations.RunPython.noop),
    ]
