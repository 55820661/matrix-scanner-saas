import json
from pathlib import PurePosixPath

from apps.core.redaction import redact_secrets

from .safe_exec import SafeExecError, run_fixed_command


GUNICORN_UVICORN_SERVICES_DISCOVERY_TOOL_KEY = "gunicorn_uvicorn_services_discovery"

SYSTEMD_LIST_UNITS_COMMAND = ["systemctl", "list-units", "--type=service", "--all", "--no-pager", "--plain", "--no-legend"]
SYSTEMD_SHOW_BASE_COMMAND = [
    "systemctl",
    "show",
    "--property=Id,Description,LoadState,ActiveState,SubState,UnitFileState,MainPID,FragmentPath,User,WorkingDirectory",
]

MAX_SYSTEMD_SHOW_UNITS = 120
MAX_OUTPUT_BYTES = 64 * 1024

FRAGMENT_PATH_PREFIXES = ("/etc/systemd/system/", "/lib/systemd/system/")


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
        names.append(unit_name[:160])
    unique = []
    seen = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        unique.append(name)
    return unique


def _safe_fragment_path(path):
    candidate = canonicalize_path(path)
    if not candidate:
        return ""
    if candidate.startswith(FRAGMENT_PATH_PREFIXES):
        return candidate
    return ""


def _safe_working_directory(path):
    candidate = canonicalize_path(path)
    if not candidate.startswith("/opt/"):
        return ""
    return candidate


def _infer_related_app_path(working_directory):
    if not working_directory.startswith("/opt/"):
        return ""
    parts = [part for part in working_directory.split("/") if part]
    if len(parts) < 2:
        return ""
    if len(parts) == 2:
        return f"/opt/{parts[1]}"

    # /opt/<app>/current or /opt/<app>/releases/<id> -> /opt/<app>
    if len(parts) >= 3 and parts[2] in {"current", "releases"}:
        return f"/opt/{parts[1]}"

    # /opt/<suite>/<app>/current or /opt/<suite>/<app>/releases/<id> -> /opt/<suite>/<app>
    if len(parts) >= 4 and parts[3] in {"current", "releases"}:
        return f"/opt/{parts[1]}/{parts[2]}"

    # Default normalization to /opt/<suite>/<app> for deeper paths.
    return f"/opt/{parts[1]}/{parts[2]}"


def detect_process_type(service_name, description):
    text = f"{service_name} {description}".lower()
    if "gunicorn" in text:
        return "gunicorn"
    if "uvicorn" in text:
        return "uvicorn"
    if "daphne" in text:
        return "daphne"
    return "unknown"


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


def build_service_item(raw):
    service_name = redact_secrets(raw.get("Id", ""))[:160]
    description = redact_secrets(raw.get("Description", ""))[:255]
    process_type = detect_process_type(service_name, description)

    try:
        main_pid = int((raw.get("MainPID", "0") or "0").strip() or "0")
    except (TypeError, ValueError):
        main_pid = 0

    working_directory = _safe_working_directory(raw.get("WorkingDirectory", ""))
    related_app_path = _infer_related_app_path(working_directory)

    item = {
        "service_name": service_name,
        "process_type": process_type,
        "active_state": redact_secrets(raw.get("ActiveState", ""))[:80],
        "sub_state": redact_secrets(raw.get("SubState", ""))[:80],
        "load_state": redact_secrets(raw.get("LoadState", ""))[:80],
        "enabled_state": redact_secrets(raw.get("UnitFileState", ""))[:80],
        "main_pid": main_pid,
        "user": redact_secrets(raw.get("User", ""))[:120],
        "working_directory": redact_secrets(working_directory)[:255] if working_directory else "",
        "fragment_path": redact_secrets(_safe_fragment_path(raw.get("FragmentPath", "")))[:255],
        "related_app_path": redact_secrets(related_app_path)[:255] if related_app_path else "",
        "metadata": {"source": "systemctl"},
    }
    return item


def summarize_services(services):
    matched = sum(1 for item in services if item.get("process_type") in {"gunicorn", "uvicorn", "daphne"})
    return {
        "services_total": len(services),
        "services_matched": matched,
    }


def summarize_applications(services):
    by_path = {}
    for service in services:
        app_path = service.get("related_app_path", "")
        if not app_path:
            continue
        entry = by_path.setdefault(
            app_path,
            {
                "path": app_path,
                "name": redact_secrets(app_path.rstrip("/").split("/")[-1])[:120],
                "service_names": [],
                "process_types": [],
                "metadata": {"source": "gunicorn_uvicorn_services_discovery"},
            },
        )
        if service["service_name"] and service["service_name"] not in entry["service_names"]:
            entry["service_names"].append(service["service_name"])
        process_type = service.get("process_type", "unknown")
        if process_type not in entry["process_types"]:
            entry["process_types"].append(process_type)
    return list(by_path.values())


def collect_gunicorn_uvicorn_services(params=None):
    params = params or {}
    if params:
        raise ValueError("gunicorn_uvicorn_services_discovery does not accept parameters.")

    units_result = run_fixed_command(SYSTEMD_LIST_UNITS_COMMAND, timeout_seconds=20, max_output_bytes=MAX_OUTPUT_BYTES)
    if units_result.returncode != 0:
        error = redact_secrets(units_result.stderr or "systemctl list-units returned a non-zero status.")
        raise SafeExecError(f"gunicorn_uvicorn_services_discovery failed: {error}")

    unit_names = parse_list_units_names(units_result.stdout)[:MAX_SYSTEMD_SHOW_UNITS]
    if not unit_names:
        result = {
            "services": [],
            "applications": [],
            "summary": {
                "services_total": 0,
                "services_matched": 0,
                "applications_total": 0,
                "units_listed": 0,
                "units_shown": 0,
                "notes": ["no_service_units_found"],
            },
        }
        encoded = json.dumps(result, sort_keys=True).encode("utf-8")
        if len(encoded) > MAX_OUTPUT_BYTES:
            raise SafeExecError("gunicorn_uvicorn_services_discovery output exceeded the configured cap.")
        return result

    show_result = run_fixed_command(
        [*SYSTEMD_SHOW_BASE_COMMAND, *unit_names],
        timeout_seconds=20,
        max_output_bytes=MAX_OUTPUT_BYTES,
    )
    if show_result.returncode != 0:
        error = redact_secrets(show_result.stderr or "systemctl show returned a non-zero status.")
        raise SafeExecError(f"gunicorn_uvicorn_services_discovery failed: {error}")

    parsed = parse_systemctl_show_output(show_result.stdout)
    services = [build_service_item(item) for item in parsed if item.get("Id", "").endswith(".service")]
    applications = summarize_applications(services)
    summary = summarize_services(services)
    summary["applications_total"] = len(applications)
    summary["units_listed"] = len(unit_names)
    summary["units_shown"] = len(parsed)
    summary["notes"] = [f"unit_cap={MAX_SYSTEMD_SHOW_UNITS}"]

    result = {
        "services": services,
        "applications": applications,
        "summary": summary,
    }

    encoded = json.dumps(result, sort_keys=True).encode("utf-8")
    if len(encoded) > MAX_OUTPUT_BYTES:
        raise SafeExecError("gunicorn_uvicorn_services_discovery output exceeded the configured cap.")
    return result
