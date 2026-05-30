import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from apps.core.redaction import redact_secrets


OPT_APPS_DISCOVERY_TOOL_KEY = "opt_apps_discovery"

OPT_ROOT = Path("/opt")

# Hard safety caps (tool-level caps can be tightened later via ToolDefinition).
MAX_DIRS_SCANNED = 200
MAX_STAT_CHECKS = 3000
MAX_PER_FILE_READ_BYTES = 64 * 1024
MAX_TOTAL_READ_BYTES = 512 * 1024
MAX_OUTPUT_BYTES = 64 * 1024

HEAVY_DIR_NAMES = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    "tmp",
    "logs",
    ".tox",
}

DENY_READ_FILENAMES = {
    ".env",
    "settings.py",
    "local_settings.py",
}

DENY_READ_SUFFIXES = {
    ".key",
}

DENY_READ_EXACT = {
    "id_rsa",
}

ALLOWED_NAME_FILES = {
    "pyproject.toml",
    "package.json",
    "composer.json",
}


class OptDiscoveryError(Exception):
    pass


@dataclass
class _Caps:
    max_dirs_scanned: int = MAX_DIRS_SCANNED
    max_stat_checks: int = MAX_STAT_CHECKS
    max_per_file_read_bytes: int = MAX_PER_FILE_READ_BYTES
    max_total_read_bytes: int = MAX_TOTAL_READ_BYTES
    max_output_bytes: int = MAX_OUTPUT_BYTES


def _is_hidden(name: str) -> bool:
    return name.startswith(".")


def _safe_realpath(path: Path) -> Path:
    # realpath() resolves symlinks; if it fails we treat as invalid.
    try:
        return Path(os.path.realpath(path))
    except OSError as exc:
        raise OptDiscoveryError(redact_secrets(str(exc))) from exc


def _ensure_under_root(root: Path, path: Path) -> Path:
    root_real = _safe_realpath(root)
    path_real = _safe_realpath(path)
    try:
        path_real.relative_to(root_real)
    except ValueError as exc:
        raise OptDiscoveryError("path_outside_allowlist") from exc
    return path_real


def _read_small_text(path: Path, *, remaining_budget: int, per_file_cap: int) -> tuple[str, int]:
    to_read = min(per_file_cap, max(0, remaining_budget))
    if to_read <= 0:
        return "", 0

    with path.open("rb") as handle:
        data = handle.read(to_read + 1)
    if len(data) > to_read:
        # Truncated: treat as unreadable for name extraction.
        return "", to_read
    try:
        return data.decode("utf-8", errors="replace"), len(data)
    except Exception:
        return "", len(data)


def _extract_name_from_pyproject(contents: str) -> str:
    # Minimal parser: support [project] name= and [tool.poetry] name=
    section = ""
    for raw_line in contents.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line.strip("[]").strip()
            continue
        if section not in ("project", "tool.poetry"):
            continue
        match = re.match(r"^name\s*=\s*([\"'])(.+?)\1\s*$", line)
        if match:
            return match.group(2).strip()
    return ""


def _extract_project_name(candidate_dir: Path, *, caps: _Caps, stats: dict) -> str:
    for filename in ("pyproject.toml", "package.json", "composer.json"):
        path = candidate_dir / filename
        if not path.exists() or not path.is_file():
            continue
        if path.name in DENY_READ_FILENAMES or path.name in DENY_READ_EXACT or path.suffix in DENY_READ_SUFFIXES:
            continue
        if path.name not in ALLOWED_NAME_FILES:
            continue

        remaining = caps.max_total_read_bytes - stats["read_bytes_total"]
        content, read_bytes = _read_small_text(path, remaining_budget=remaining, per_file_cap=caps.max_per_file_read_bytes)
        stats["read_bytes_total"] += read_bytes
        if not content:
            continue

        try:
            if filename in ("package.json", "composer.json"):
                data = json.loads(content)
                name = data.get("name") if isinstance(data, dict) else ""
                if isinstance(name, str) and name.strip():
                    return name.strip()
            else:
                name = _extract_name_from_pyproject(content)
                if name:
                    return name
        except Exception:
            continue
    return ""


def _detect_framework(candidate_dir: Path, *, caps: _Caps, stats: dict) -> tuple[str, list[str]]:
    detection: list[str] = []

    def check(rel: str) -> bool:
        stats["stat_checks"] += 1
        if stats["stat_checks"] > caps.max_stat_checks:
            raise OptDiscoveryError("opt_apps_discovery exceeded stat cap")
        return (candidate_dir / rel).exists()

    markers = {
        "artisan": check("artisan"),
        "manage.py": check("manage.py"),
        "package.json": check("package.json"),
        "composer.json": check("composer.json"),
        "pyproject.toml": check("pyproject.toml"),
        "requirements.txt": check("requirements.txt"),
        "Pipfile": check("Pipfile"),
        "wsgi.py": check("wsgi.py"),
        "asgi.py": check("asgi.py"),
        "bootstrap/": check("bootstrap"),
        "public/": check("public"),
    }

    supporting = [name for name in ("bootstrap/", "public/") if markers[name]]

    if markers["artisan"]:
        return "laravel", ["artisan", *supporting]
    if markers["manage.py"]:
        return "django", ["manage.py", *supporting]
    if markers["package.json"]:
        return "node", ["package.json", *supporting]
    if markers["composer.json"]:
        return "php", ["composer.json", *supporting]

    python_markers = [name for name in ("pyproject.toml", "requirements.txt", "Pipfile", "wsgi.py", "asgi.py") if markers[name]]
    if python_markers:
        return "python", [*python_markers, *supporting]

    return "unknown", detection


def candidate_app_dirs(opt_root: Path, *, caps: _Caps, stats: dict) -> list[Path]:
    candidates: list[Path] = []
    root = _ensure_under_root(opt_root, opt_root)
    try:
        children = list(root.iterdir())
    except (OSError, PermissionError):
        stats["permission_denied"] += 1
        return []

    # Depth 1: /opt/*
    for child in children:
        if len(candidates) >= caps.max_dirs_scanned:
            break
        name = child.name
        if _is_hidden(name) or name in HEAVY_DIR_NAMES:
            stats["dirs_skipped"] += 1
            continue
        try:
            child_real = _ensure_under_root(opt_root, child)
        except OptDiscoveryError:
            stats["dirs_skipped"] += 1
            continue
        if not child_real.is_dir():
            continue
        candidates.append(child_real)

    # Depth 2: /opt/*/*
    depth2: list[Path] = []
    for parent in list(candidates):
        if len(candidates) + len(depth2) >= caps.max_dirs_scanned:
            break
        try:
            for child in parent.iterdir():
                if len(candidates) + len(depth2) >= caps.max_dirs_scanned:
                    break
                name = child.name
                if _is_hidden(name) or name in HEAVY_DIR_NAMES:
                    stats["dirs_skipped"] += 1
                    continue
                try:
                    child_real = _ensure_under_root(opt_root, child)
                except OptDiscoveryError:
                    stats["dirs_skipped"] += 1
                    continue
                if child_real.is_dir():
                    depth2.append(child_real)
        except (OSError, PermissionError):
            stats["permission_denied"] += 1
            continue

    candidates.extend(depth2)
    return candidates


def collect_opt_apps(params=None):
    params = params or {}
    if params:
        raise ValueError("opt_apps_discovery does not accept parameters.")

    caps = _Caps()
    stats = {
        "dirs_skipped": 0,
        "permission_denied": 0,
        "stat_checks": 0,
        "read_bytes_total": 0,
    }

    applications: list[dict] = []
    seen_paths: set[str] = set()
    candidates = candidate_app_dirs(OPT_ROOT, caps=caps, stats=stats)

    for candidate_dir in candidates:
        # Allow symlinks only if they resolve within /opt (enforced by _ensure_under_root).
        try:
            candidate_real = _ensure_under_root(OPT_ROOT, candidate_dir)
        except OptDiscoveryError:
            stats["dirs_skipped"] += 1
            continue

        framework, detection = _detect_framework(candidate_real, caps=caps, stats=stats)
        if not detection:
            continue

        dedupe_key = str(candidate_real)
        if dedupe_key in seen_paths:
            continue
        seen_paths.add(dedupe_key)

        project_name = _extract_project_name(candidate_real, caps=caps, stats=stats) or candidate_real.name

        depth = 2 if candidate_real.parent != _safe_realpath(OPT_ROOT) else 1

        applications.append(
            {
                "path": redact_secrets(str(candidate_real))[:400],
                "name": redact_secrets(project_name)[:120],
                "framework": redact_secrets(framework)[:40],
                "detection": [redact_secrets(item)[:80] for item in detection],
                "has_systemd_unit_hint": False,
                "metadata": {
                    "source": OPT_APPS_DISCOVERY_TOOL_KEY,
                    "scan_root": "/opt",
                    "depth": depth,
                },
            }
        )

    result = {
        "applications": applications,
        "summary": {
            "apps_total": len(applications),
            "candidates_scanned": len(candidates),
            "dirs_skipped": stats["dirs_skipped"],
            "permission_denied": stats["permission_denied"],
            "notes": [
                "depth=2",
                "symlinks=allow_under_opt_only",
                f"stat_checks={stats['stat_checks']}",
            ],
        },
    }

    encoded = json.dumps(result, sort_keys=True).encode("utf-8")
    if len(encoded) > caps.max_output_bytes:
        raise OptDiscoveryError("opt_apps_discovery output exceeded the configured cap.")

    return result
