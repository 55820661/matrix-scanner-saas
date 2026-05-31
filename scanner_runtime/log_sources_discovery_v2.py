import datetime as dt
import json
from pathlib import Path, PurePosixPath

from apps.core.redaction import redact_secrets


LOG_SOURCES_DISCOVERY_V2_TOOL_KEY = "log_sources_discovery_v2"
MAX_OUTPUT_BYTES = 64 * 1024
OPT_ROOT = Path("/opt")

SYSTEM_CANDIDATES = [
    ("/var/log/nginx", "nginx_log_dir"),
    ("/var/log/postgresql", "postgresql_log_dir"),
    ("/var/log/syslog", "system_log_file"),
    ("/var/log/messages", "system_log_file"),
]

SKIPPED_OPT_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".cache",
    ".config",
    ".npm",
    ".tox",
    "tests",
    "docs",
    "static",
    "staticfiles",
    "templates",
    "scripts",
    "skills",
    "dist",
    "build",
    "tmp",
}


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


def _is_allowed_path(path):
    canonical = canonicalize_path(path)
    if not canonical:
        return False
    if canonical in {"/var/log/nginx", "/var/log/postgresql", "/var/log/syslog", "/var/log/messages"}:
        return True
    if canonical.startswith("/opt/"):
        parts = [part for part in canonical.split("/") if part]
        # /opt/<app>/logs
        if len(parts) == 3 and parts[2] == "logs":
            return True
        # /opt/<suite>/<app>/logs
        if len(parts) == 4 and parts[3] == "logs":
            return True
    return False


def _is_opt_logs_path(path):
    canonical = canonicalize_path(path)
    if not canonical.startswith("/opt/"):
        return False
    parts = [part for part in canonical.split("/") if part]
    return (len(parts) == 3 and parts[2] == "logs") or (len(parts) == 4 and parts[3] == "logs")


def _opt_realpath_within_root(path):
    try:
        resolved = Path(path).resolve(strict=False)
    except (OSError, RuntimeError):
        return False
    resolved_canonical = canonicalize_path(str(resolved))
    return resolved_canonical.startswith("/opt/")


def _iso_mtime(timestamp):
    try:
        return dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc).isoformat()
    except (ValueError, OSError, OverflowError):
        return ""


def _is_skipped_opt_dir(path):
    return path.name in SKIPPED_OPT_DIR_NAMES or path.name.startswith(".")


def _is_existing_dir(path):
    try:
        return path.exists() and path.is_dir()
    except (OSError, PermissionError):
        return False


def _metadata_for_path(path, source_type, stats):
    canonical = canonicalize_path(path)
    if not _is_allowed_path(canonical):
        return None
    if source_type == "app_logs_dir" and _is_opt_logs_path(canonical):
        if not _opt_realpath_within_root(canonical):
            return None
    candidate = Path(canonical)
    exists = False
    is_dir = False
    size_bytes = None
    modified_at = ""

    try:
        stat_result = candidate.stat()
        exists = True
        is_dir = candidate.is_dir()
        size_bytes = stat_result.st_size
        modified_at = _iso_mtime(stat_result.st_mtime)
    except FileNotFoundError:
        exists = False
    except (PermissionError, OSError):
        stats["permission_denied"] += 1
        exists = False

    return {
        "path": redact_secrets(canonical)[:255],
        "type": source_type,
        "exists": exists,
        "is_dir": is_dir,
        "size_bytes": size_bytes,
        "modified_at": redact_secrets(modified_at)[:80] if modified_at else "",
        "metadata": {"source": LOG_SOURCES_DISCOVERY_V2_TOOL_KEY},
    }


def _discover_opt_logs_candidates():
    candidates = []
    opt_root = OPT_ROOT
    try:
        level1 = list(opt_root.iterdir())
    except (FileNotFoundError, PermissionError, OSError):
        return candidates

    for first in level1:
        if _is_skipped_opt_dir(first) or not _is_existing_dir(first):
            continue
        first_logs = first / "logs"
        if _is_existing_dir(first_logs):
            candidates.append(str(first_logs))
        try:
            level2 = list(first.iterdir())
        except (PermissionError, OSError):
            continue
        for second in level2:
            if _is_skipped_opt_dir(second) or not _is_existing_dir(second):
                continue
            second_logs = second / "logs"
            if _is_existing_dir(second_logs):
                candidates.append(str(second_logs))
    return candidates


def collect_log_sources_v2(params=None):
    params = params or {}
    if params:
        raise ValueError("log_sources_discovery_v2 does not accept parameters.")

    stats = {"permission_denied": 0}
    sources = []
    seen = set()

    for path, source_type in SYSTEM_CANDIDATES:
        item = _metadata_for_path(path, source_type, stats)
        if item is None:
            continue
        key = (item["path"], item["type"])
        if key in seen:
            continue
        seen.add(key)
        sources.append(item)

    for path in _discover_opt_logs_candidates():
        item = _metadata_for_path(path, "app_logs_dir", stats)
        if item is None:
            continue
        key = (item["path"], item["type"])
        if key in seen:
            continue
        seen.add(key)
        sources.append(item)

    summary = {
        "sources_total": len(sources),
        "sources_existing": sum(1 for item in sources if item["exists"]),
        "sources_missing": sum(1 for item in sources if not item["exists"]),
        "permission_denied": stats["permission_denied"],
        "notes": ["metadata_only", "no_content_reads"],
    }

    result = {"log_sources": sources, "summary": summary}
    encoded = json.dumps(result, sort_keys=True).encode("utf-8")
    if len(encoded) > MAX_OUTPUT_BYTES:
        raise ValueError("log_sources_discovery_v2 output exceeded the configured cap.")
    return result
