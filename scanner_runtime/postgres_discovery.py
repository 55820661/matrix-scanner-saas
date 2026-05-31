import json
from pathlib import PurePosixPath

from apps.core.redaction import redact_secrets

from .safe_exec import SafeExecError, run_fixed_command


POSTGRES_STATUS_DISCOVERY_TOOL_KEY = "postgres_status_discovery"

SYSTEMD_LIST_UNITS_COMMAND = ["systemctl", "list-units", "--type=service", "--all", "--no-pager", "--plain", "--no-legend"]
SYSTEMD_SHOW_BASE_COMMAND = [
    "systemctl",
    "show",
    "--property=Id,Description,LoadState,ActiveState,SubState,UnitFileState,MainPID,FragmentPath",
]
PG_ISREADY_COMMAND = ["pg_isready"]

MAX_SYSTEMD_SHOW_UNITS = 80
MAX_OUTPUT_BYTES = 64 * 1024
SAFE_FRAGMENT_PREFIXES = ("/etc/systemd/system/", "/lib/systemd/system/")

POSTGRES_SERVICE_KEYWORDS = (
    "postgresql.service",
    "postgresql@",
    "postgres.service",
    "postgre.service",
)


def canonicalize_path(value):
    if not value or not str(value).startswith("/"):
        return ""
    parts = []
    for part in PurePosixPath(str(value)).parts:
        if part in {"", "/", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/" + "/".join(parts)


def parse_list_units_names(output):
    names = []
    for line in (output or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split(None, 1)
        if not parts:
            continue
        unit_name = parts[0]
        if not unit_name.endswith(".service"):
            continue
        lower = unit_name.lower()
        if any(keyword in lower for keyword in POSTGRES_SERVICE_KEYWORDS):
            names.append(unit_name[:160])
    unique = []
    seen = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        unique.append(name)
    return unique


def parse_systemctl_show_output(output):
    services = []
    current = {}
    for line in (output or "").splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                services.append(current)
                current = {}
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key == "Id" and current.get("Id"):
            services.append(current)
            current = {}
        current[key] = value
    if current:
        services.append(current)
    return services


def _safe_fragment_path(path):
    candidate = canonicalize_path(path)
    if not candidate:
        return ""
    if candidate.startswith(SAFE_FRAGMENT_PREFIXES):
        return candidate
    return ""


def _normalize_pg_isready_status():
    try:
        result = run_fixed_command(PG_ISREADY_COMMAND, timeout_seconds=10, max_output_bytes=8 * 1024)
    except (SafeExecError, OSError):
        return "not_available", False

    if result.returncode == 0:
        return "ok", True
    return "failed", True


def build_service_item(raw, health_status):
    service_name = redact_secrets(raw.get("Id", ""))[:160]
    try:
        main_pid = int((raw.get("MainPID", "0") or "0").strip() or "0")
    except (TypeError, ValueError):
        main_pid = 0

    item = {
        "service_name": service_name,
        "active_state": redact_secrets(raw.get("ActiveState", ""))[:80],
        "sub_state": redact_secrets(raw.get("SubState", ""))[:80],
        "load_state": redact_secrets(raw.get("LoadState", ""))[:80],
        "enabled_state": redact_secrets(raw.get("UnitFileState", ""))[:80],
        "main_pid": main_pid,
        "fragment_path": redact_secrets(_safe_fragment_path(raw.get("FragmentPath", "")))[:255],
        "health_check": health_status,
        "metadata": {"source": "systemctl"},
    }
    return item


def collect_postgres_status(params=None):
    params = params or {}
    if params:
        raise ValueError("postgres_status_discovery does not accept parameters.")

    units_result = run_fixed_command(SYSTEMD_LIST_UNITS_COMMAND, timeout_seconds=20, max_output_bytes=MAX_OUTPUT_BYTES)
    if units_result.returncode != 0:
        error = redact_secrets(units_result.stderr or "systemctl list-units returned a non-zero status.")
        raise SafeExecError(f"postgres_status_discovery failed: {error}")

    unit_names = parse_list_units_names(units_result.stdout)
    capped_units = unit_names[:MAX_SYSTEMD_SHOW_UNITS]
    health_status, pg_isready_available = _normalize_pg_isready_status()

    if not capped_units:
        result = {
            "services": [],
            "summary": {
                "services_total": 0,
                "services_matched": 0,
                "postgres_detected": False,
                "pg_isready_available": pg_isready_available,
                "pg_isready_ok": health_status == "ok",
                "notes": ["no_postgres_units_found"],
            },
        }
        encoded = json.dumps(result, sort_keys=True).encode("utf-8")
        if len(encoded) > MAX_OUTPUT_BYTES:
            raise SafeExecError("postgres_status_discovery output exceeded the configured cap.")
        return result

    show_result = run_fixed_command(
        [*SYSTEMD_SHOW_BASE_COMMAND, *capped_units],
        timeout_seconds=20,
        max_output_bytes=MAX_OUTPUT_BYTES,
    )
    if show_result.returncode != 0:
        error = redact_secrets(show_result.stderr or "systemctl show returned a non-zero status.")
        raise SafeExecError(f"postgres_status_discovery failed: {error}")

    parsed = parse_systemctl_show_output(show_result.stdout)
    services = [build_service_item(item, health_status) for item in parsed if item.get("Id", "").endswith(".service")]

    result = {
        "services": services,
        "summary": {
            "services_total": len(services),
            "services_matched": len(capped_units),
            "postgres_detected": len(services) > 0,
            "pg_isready_available": pg_isready_available,
            "pg_isready_ok": health_status == "ok",
            "notes": [f"unit_cap={MAX_SYSTEMD_SHOW_UNITS}"],
        },
    }

    encoded = json.dumps(result, sort_keys=True).encode("utf-8")
    if len(encoded) > MAX_OUTPUT_BYTES:
        raise SafeExecError("postgres_status_discovery output exceeded the configured cap.")
    return result
