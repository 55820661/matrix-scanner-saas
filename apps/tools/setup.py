from apps.plans.models import Plan

from .models import PlanTool, ToolDefinition, ToolPolicy, ToolTemplate


SYSTEM_IDENTITY_KEY = "system_identity"
BASELINE_TOOL_KEYS = (
    "system_identity",
    "services_status",
    "panel_detector",
    "cpanel_domain_scanner",
    "application_discovery",
    "laravel_discovery",
    "log_sources_discovery",
    "webroot_risk_checker",
)

BASELINE_TOOL_SPECS = {
    "system_identity": {
        "name": "System identity",
        "description": "Collect basic host identity from the scanner runtime.",
        "category": "core",
        "timeout_seconds": 30,
        "max_output_bytes": 64 * 1024,
    },
    "services_status": {
        "name": "Services status",
        "description": "Read service status metadata from the scanner host.",
        "category": "baseline",
        "timeout_seconds": 30,
        "max_output_bytes": 64 * 1024,
    },
    "panel_detector": {
        "name": "Panel detector",
        "description": "Detect common hosting control panel markers.",
        "category": "baseline",
        "timeout_seconds": 30,
        "max_output_bytes": 64 * 1024,
    },
    "cpanel_domain_scanner": {
        "name": "cPanel domain scanner",
        "description": "Read cPanel domain metadata without storing raw files.",
        "category": "baseline",
        "timeout_seconds": 45,
        "max_output_bytes": 256 * 1024,
    },
    "application_discovery": {
        "name": "Application discovery",
        "description": "Discover web applications from known webroots.",
        "category": "baseline",
        "timeout_seconds": 45,
        "max_output_bytes": 64 * 1024,
    },
    "laravel_discovery": {
        "name": "Laravel discovery",
        "description": "Discover Laravel apps and approved safe environment keys only.",
        "category": "baseline",
        "timeout_seconds": 45,
        "max_output_bytes": 64 * 1024,
    },
    "log_sources_discovery": {
        "name": "Log sources discovery",
        "description": "Discover log source metadata without reading raw logs.",
        "category": "baseline",
        "timeout_seconds": 30,
        "max_output_bytes": 64 * 1024,
    },
    "webroot_risk_checker": {
        "name": "Webroot risk checker",
        "description": "Detect read-only webroot risk indicators using evidence summaries.",
        "category": "baseline",
        "timeout_seconds": 30,
        "max_output_bytes": 64 * 1024,
    },
}

PHASE2_DISCOVERY_TOOL_KEYS = (
    "systemd_services_discovery",
    "nginx_sites_discovery",
    "opt_apps_discovery",
    "django_apps_discovery",
    "gunicorn_uvicorn_services_discovery",
    "postgres_status_discovery",
    "log_sources_discovery_v2",
)

PHASE2_DISCOVERY_TOOL_SPECS = {
    "systemd_services_discovery": {
        "name": "systemd services discovery",
        "description": "Discover systemd service metadata for Debian/Nginx style hosts without reading unit secrets.",
        "category": "phase2_discovery",
        "timeout_seconds": 45,
        "max_output_bytes": 64 * 1024,
        "output_schema": {
            "type": "object",
            "fields": {
                "services": "array",
                "summary": "object",
            },
        },
    },
    "nginx_sites_discovery": {
        "name": "Nginx sites discovery",
        "description": "Discover enabled Nginx server names, listen ports, and document roots without storing raw config.",
        "category": "phase2_discovery",
        "timeout_seconds": 45,
        "max_output_bytes": 64 * 1024,
        "output_schema": {
            "type": "object",
            "fields": {
                "domains": "array",
                "sites": "array",
                "summary": "object",
            },
        },
    },
    "opt_apps_discovery": {
        "name": "/opt applications discovery",
        "description": "Discover application directories under allowlisted /opt paths using metadata summaries only.",
        "category": "phase2_discovery",
        "timeout_seconds": 45,
        "max_output_bytes": 64 * 1024,
        "output_schema": {
            "type": "object",
            "fields": {
                "applications": "array",
                "summary": "object",
            },
        },
    },
    "django_apps_discovery": {
        "name": "Django applications discovery",
        "description": "Detect Django application metadata from safe project markers without reading secrets or full settings.",
        "category": "phase2_discovery",
        "timeout_seconds": 45,
        "max_output_bytes": 64 * 1024,
        "output_schema": {
            "type": "object",
            "fields": {
                "applications": "array",
                "summary": "object",
            },
        },
    },
    "gunicorn_uvicorn_services_discovery": {
        "name": "Gunicorn/Uvicorn services discovery",
        "description": "Summarize Gunicorn and Uvicorn service metadata without storing raw command lines containing secrets.",
        "category": "phase2_discovery",
        "timeout_seconds": 45,
        "max_output_bytes": 64 * 1024,
        "output_schema": {
            "type": "object",
            "fields": {
                "services": "array",
                "applications": "array",
                "summary": "object",
            },
        },
    },
    "postgres_status_discovery": {
        "name": "PostgreSQL status discovery",
        "description": "Discover PostgreSQL service and socket metadata without reading credentials or database contents.",
        "category": "phase2_discovery",
        "timeout_seconds": 30,
        "max_output_bytes": 64 * 1024,
        "output_schema": {
            "type": "object",
            "fields": {
                "services": "array",
                "summary": "object",
            },
        },
    },
    "log_sources_discovery_v2": {
        "name": "Log sources discovery for Debian/Nginx",
        "description": "Discover Nginx, Django, Gunicorn/Uvicorn, PostgreSQL, and systemd log source metadata without raw logs.",
        "category": "phase2_discovery",
        "timeout_seconds": 45,
        "max_output_bytes": 64 * 1024,
        "output_schema": {
            "type": "object",
            "fields": {
                "log_sources": "array",
                "summary": "object",
            },
        },
    },
}

PHASE2_DISCOVERY_BLOCKED_PATH_PREFIXES = [
    "/etc/shadow",
    "/etc/ssl/private",
    "/root",
    "/home/*/.ssh",
    "/opt/*/.env",
    "/opt/*/secrets",
]

PHASE2_DISCOVERY_REDACTION_RULES = [
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


def ensure_system_identity_tool(*, connect_active_plans=True, reset_existing=False):
    return ensure_tool(SYSTEM_IDENTITY_KEY, connect_active_plans=connect_active_plans, reset_existing=reset_existing)


def ensure_tool(tool_key, *, connect_active_plans=True, reset_existing=False):
    spec = BASELINE_TOOL_SPECS[tool_key]
    template_defaults = {
        "name": spec["name"],
        "description": spec["description"],
        "runtime_handler_key": tool_key,
        "input_schema": {"fields": {}},
        "output_schema": {"type": "object"},
        "default_timeout_seconds": spec["timeout_seconds"],
        "default_max_output_bytes": spec["max_output_bytes"],
        "is_active": True,
    }
    if reset_existing:
        template, _created = ToolTemplate.objects.update_or_create(key=tool_key, defaults=template_defaults)
    else:
        template, _created = ToolTemplate.objects.get_or_create(key=tool_key, defaults=template_defaults)

    definition_defaults = {
        "template": template,
        "name": spec["name"],
        "description": spec["description"],
        "status": ToolDefinition.Status.ENABLED,
        "risk_level": ToolDefinition.RiskLevel.READ_ONLY,
        "category": spec["category"],
        "input_schema": {"fields": {}},
        "default_params": {},
        "timeout_seconds": spec["timeout_seconds"],
        "max_output_bytes": spec["max_output_bytes"],
        "requires_path_policy": False,
        "allowed_path_prefixes": [],
        "blocked_path_prefixes": ["/etc/shadow", "/root", "/home/*/.ssh"],
        "redaction_rules": [],
    }
    if reset_existing:
        definition, _created = ToolDefinition.objects.update_or_create(
            key=tool_key,
            defaults=definition_defaults,
        )
    else:
        definition, _created = ToolDefinition.objects.get_or_create(
            key=tool_key,
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


def ensure_baseline_tools(*, connect_active_plans=True, reset_existing=False):
    tools = {}
    for tool_key in BASELINE_TOOL_KEYS:
        tools[tool_key] = ensure_tool(
            tool_key,
            connect_active_plans=connect_active_plans,
            reset_existing=reset_existing,
        )
    return tools


def ensure_phase2_discovery_tool_contracts(
    *,
    connect_active_plans=False,
    activate_policy=False,
    definition_status=ToolDefinition.Status.APPROVED,
    reset_existing=False,
):
    tools = {}
    for tool_key in PHASE2_DISCOVERY_TOOL_KEYS:
        spec = PHASE2_DISCOVERY_TOOL_SPECS[tool_key]
        template_defaults = {
            "name": spec["name"],
            "description": spec["description"],
            "runtime_handler_key": tool_key,
            "input_schema": {"fields": {}, "required": []},
            "output_schema": spec["output_schema"],
            "default_timeout_seconds": spec["timeout_seconds"],
            "default_max_output_bytes": spec["max_output_bytes"],
            "is_active": True,
        }
        if reset_existing:
            template, _created = ToolTemplate.objects.update_or_create(key=tool_key, defaults=template_defaults)
        else:
            template, _created = ToolTemplate.objects.get_or_create(key=tool_key, defaults=template_defaults)

        definition_defaults = {
            "template": template,
            "name": spec["name"],
            "description": spec["description"],
            "status": definition_status,
            "risk_level": ToolDefinition.RiskLevel.READ_ONLY,
            "category": spec["category"],
            "input_schema": {"fields": {}, "required": []},
            "default_params": {},
            "timeout_seconds": spec["timeout_seconds"],
            "max_output_bytes": spec["max_output_bytes"],
            "requires_path_policy": False,
            "allowed_path_prefixes": [],
            "blocked_path_prefixes": PHASE2_DISCOVERY_BLOCKED_PATH_PREFIXES,
            "redaction_rules": PHASE2_DISCOVERY_REDACTION_RULES,
        }
        if reset_existing:
            definition, _created = ToolDefinition.objects.update_or_create(
                key=tool_key,
                defaults=definition_defaults,
            )
        else:
            definition, _created = ToolDefinition.objects.get_or_create(
                key=tool_key,
                defaults=definition_defaults,
            )

        policy_defaults = {
            "allow_customer_run": activate_policy,
            "allow_admin_run": activate_policy,
            "allow_agent_run": activate_policy,
            "requires_approved_application": False,
            "allowed_roles": ["owner", "operator"],
            "allowed_server_statuses": ["active"],
            "is_active": activate_policy,
        }
        if reset_existing:
            ToolPolicy.objects.update_or_create(tool_definition=definition, defaults=policy_defaults)
        else:
            ToolPolicy.objects.get_or_create(tool_definition=definition, defaults=policy_defaults)

        if connect_active_plans:
            for plan in Plan.objects.filter(is_active=True):
                plan_tool_defaults = {"is_enabled": activate_policy and definition_status == ToolDefinition.Status.ENABLED}
                if reset_existing:
                    PlanTool.objects.update_or_create(
                        plan=plan,
                        tool_definition=definition,
                        defaults=plan_tool_defaults,
                    )
                else:
                    PlanTool.objects.get_or_create(
                        plan=plan,
                        tool_definition=definition,
                        defaults=plan_tool_defaults,
                    )
        tools[tool_key] = (template, definition)
    return tools
