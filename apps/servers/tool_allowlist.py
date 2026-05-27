SYSTEM_IDENTITY = "system_identity"
MAX_SYSTEM_IDENTITY_OUTPUT_BYTES = 64 * 1024

ALLOWED_TOOL_KEYS = {SYSTEM_IDENTITY}


def is_allowed_tool(tool_key):
    return tool_key in ALLOWED_TOOL_KEYS
