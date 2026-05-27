SYSTEM_IDENTITY = "system_identity"
MAX_SYSTEM_IDENTITY_OUTPUT_BYTES = 64 * 1024

ALLOWED_TOOL_KEYS = {SYSTEM_IDENTITY}


def is_allowed_tool(tool_key):
    try:
        from apps.tools.models import ToolDefinition

        return ToolDefinition.objects.filter(
            key=tool_key,
            status=ToolDefinition.Status.ENABLED,
            risk_level=ToolDefinition.RiskLevel.READ_ONLY,
            template__is_active=True,
            policy__is_active=True,
            policy__allow_agent_run=True,
        ).exists() or tool_key in ALLOWED_TOOL_KEYS
    except Exception:
        # Temporary Sprint 2 fallback during registry transition.
        return tool_key in ALLOWED_TOOL_KEYS
