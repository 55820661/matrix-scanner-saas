from pathlib import PurePosixPath


class ToolParamValidationError(Exception):
    pass


PRIMITIVE_TYPES = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "object": dict,
    "array": list,
    "path": str,
}


def canonicalize_path(value):
    if not isinstance(value, str) or not value.startswith("/"):
        raise ToolParamValidationError("Path parameters must be absolute paths.")
    parts = []
    for part in PurePosixPath(value).parts:
        if part in {"", "/"}:
            continue
        if part == ".":
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/" + "/".join(parts)


def path_matches_prefix(path, prefix):
    if prefix.endswith("/*"):
        base = canonicalize_path(prefix[:-2])
        return path == base or path.startswith(f"{base}/")
    canonical_prefix = canonicalize_path(prefix)
    return path == canonical_prefix or path.startswith(f"{canonical_prefix}/")


def validate_params(schema, params):
    schema = schema or {}
    params = params or {}
    fields = schema.get("fields", {})
    required = set(schema.get("required", []))
    if not isinstance(params, dict):
        raise ToolParamValidationError("Tool params must be an object.")
    unknown = set(params) - set(fields)
    if unknown:
        raise ToolParamValidationError("Unknown tool params are not allowed.")
    missing = required - set(params)
    if missing:
        raise ToolParamValidationError("Required tool params are missing.")

    validated = {}
    path_values = {}
    for name, spec in fields.items():
        if name not in params:
            continue
        expected_type = spec.get("type")
        python_type = PRIMITIVE_TYPES.get(expected_type)
        if python_type is None:
            raise ToolParamValidationError("Unsupported tool param type.")
        value = params[name]
        if expected_type == "number":
            valid_type = isinstance(value, python_type) and not isinstance(value, bool)
        elif expected_type == "integer":
            valid_type = isinstance(value, int) and not isinstance(value, bool)
        else:
            valid_type = isinstance(value, python_type)
        if not valid_type:
            raise ToolParamValidationError("Tool param has invalid type.")
        if expected_type == "path":
            value = canonicalize_path(value)
            path_values[name] = value
        validated[name] = value
    return validated, path_values


def validate_path_policy(tool_definition, path_values):
    blocked = tool_definition.blocked_path_prefixes or []
    allowed = tool_definition.allowed_path_prefixes or []
    for path in path_values.values():
        for prefix in blocked:
            if path_matches_prefix(path, prefix):
                raise ToolParamValidationError("Tool path is blocked by policy.")
        if tool_definition.requires_path_policy and not any(path_matches_prefix(path, prefix) for prefix in allowed):
            raise ToolParamValidationError("Tool path is not allowed by policy.")
