import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from apps.core.redaction import redact_secrets


DJANGO_APPS_DISCOVERY_TOOL_KEY = "django_apps_discovery"

OPT_ROOT = Path("/opt")

MAX_DIRS_SCANNED = 200
MAX_STAT_CHECKS = 3000
MAX_PER_FILE_READ_BYTES = 64 * 1024
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

STRONG_ROOT_MARKERS = (
    "pyproject.toml",
    "requirements.txt",
    "Pipfile",
    "poetry.lock",
    "uv.lock",
)

SUPPORTING_MARKERS = (
    "wsgi.py",
    "asgi.py",
    "urls.py",
    "apps.py",
)


class DjangoDiscoveryError(Exception):
    pass


@dataclass
class _Caps:
    max_dirs_scanned: int = MAX_DIRS_SCANNED
    max_stat_checks: int = MAX_STAT_CHECKS
    max_per_file_read_bytes: int = MAX_PER_FILE_READ_BYTES
    max_output_bytes: int = MAX_OUTPUT_BYTES


def _is_hidden(name: str) -> bool:
    return name.startswith(".")


def _safe_realpath(path: Path) -> Path:
    try:
        return Path(os.path.realpath(path))
    except OSError as exc:
        raise DjangoDiscoveryError(redact_secrets(str(exc))) from exc


def _ensure_under_root(root: Path, path: Path) -> Path:
    root_real = _safe_realpath(root)
    path_real = _safe_realpath(path)
    try:
        path_real.relative_to(root_real)
    except ValueError as exc:
        raise DjangoDiscoveryError("path_outside_allowlist") from exc
    return path_real


def _safe_exists(path: Path, *, caps: _Caps, stats: dict) -> bool:
    stats["stat_checks"] += 1
    if stats["stat_checks"] > caps.max_stat_checks:
        raise DjangoDiscoveryError("django_apps_discovery exceeded stat cap")
    try:
        return path.exists()
    except OSError:
        return False


def _safe_is_dir(path: Path) -> bool:
    try:
        return path.is_dir()
    except OSError:
        return False


def _extract_name_from_pyproject(contents: str) -> str:
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


def _extract_safe_project_name(candidate_dir: Path, *, caps: _Caps) -> str:
    path = candidate_dir / "pyproject.toml"
    try:
        if not path.exists() or not path.is_file() or path.stat().st_size > caps.max_per_file_read_bytes:
            return ""
        with path.open("rb") as handle:
            data = handle.read(caps.max_per_file_read_bytes + 1)
        if len(data) > caps.max_per_file_read_bytes:
            return ""
        return _extract_name_from_pyproject(data.decode("utf-8", errors="replace"))
    except OSError:
        return ""


def candidate_app_dirs(opt_root: Path, *, caps: _Caps, stats: dict) -> list[Path]:
    candidates: list[Path] = []
    root = _ensure_under_root(opt_root, opt_root)
    try:
        children = list(root.iterdir())
    except (OSError, PermissionError):
        stats["permission_denied"] += 1
        return []

    for child in children:
        if len(candidates) >= caps.max_dirs_scanned:
            break
        if _is_hidden(child.name) or child.name in HEAVY_DIR_NAMES:
            stats["dirs_skipped"] += 1
            continue
        try:
            child_real = _ensure_under_root(opt_root, child)
        except DjangoDiscoveryError:
            stats["dirs_skipped"] += 1
            continue
        if _safe_is_dir(child_real):
            candidates.append(child_real)

    depth2: list[Path] = []
    for parent in list(candidates):
        if len(candidates) + len(depth2) >= caps.max_dirs_scanned:
            break
        try:
            children = list(parent.iterdir())
        except (OSError, PermissionError):
            stats["permission_denied"] += 1
            continue
        for child in children:
            if len(candidates) + len(depth2) >= caps.max_dirs_scanned:
                break
            if _is_hidden(child.name) or child.name in HEAVY_DIR_NAMES:
                stats["dirs_skipped"] += 1
                continue
            try:
                child_real = _ensure_under_root(opt_root, child)
            except DjangoDiscoveryError:
                stats["dirs_skipped"] += 1
                continue
            if _safe_is_dir(child_real):
                depth2.append(child_real)

    candidates.extend(depth2)
    return candidates


def _find_project_package(candidate_dir: Path, *, caps: _Caps, stats: dict) -> tuple[str, list[str], bool, bool]:
    try:
        children = list(candidate_dir.iterdir())
    except (OSError, PermissionError):
        stats["permission_denied"] += 1
        return "", [], False, False

    for child in children:
        if _is_hidden(child.name) or child.name in HEAVY_DIR_NAMES or not _safe_is_dir(child):
            continue
        markers: list[str] = []
        has_wsgi = _safe_exists(child / "wsgi.py", caps=caps, stats=stats)
        has_asgi = _safe_exists(child / "asgi.py", caps=caps, stats=stats)
        if has_wsgi:
            markers.append(f"{child.name}/wsgi.py")
        if has_asgi:
            markers.append(f"{child.name}/asgi.py")
        for marker in ("urls.py", "apps.py"):
            if _safe_exists(child / marker, caps=caps, stats=stats):
                markers.append(f"{child.name}/{marker}")
        if markers:
            return child.name, markers, has_wsgi, has_asgi
    return "", [], False, False


def _inspect_candidate(candidate_dir: Path, *, caps: _Caps, stats: dict) -> dict | None:
    has_manage_py = _safe_exists(candidate_dir / "manage.py", caps=caps, stats=stats)
    dependency_files = [marker for marker in STRONG_ROOT_MARKERS if _safe_exists(candidate_dir / marker, caps=caps, stats=stats)]

    direct_supporting = [marker for marker in SUPPORTING_MARKERS if _safe_exists(candidate_dir / marker, caps=caps, stats=stats)]
    project_package, package_supporting, package_has_wsgi, package_has_asgi = _find_project_package(
        candidate_dir,
        caps=caps,
        stats=stats,
    )
    all_supporting = [*direct_supporting, *package_supporting]

    is_valid = has_manage_py or (bool(dependency_files) and bool(all_supporting))
    if not is_valid:
        return None

    detection: list[str] = []
    if has_manage_py:
        detection.append("manage.py")
    detection.extend(dependency_files)
    detection.extend(all_supporting)

    project_name = _extract_safe_project_name(candidate_dir, caps=caps) or candidate_dir.name
    root_real = _safe_realpath(OPT_ROOT)
    depth = 2 if candidate_dir.parent != root_real else 1

    return {
        "path": candidate_dir,
        "payload": {
            "path": redact_secrets(str(candidate_dir))[:400],
            "name": redact_secrets(project_name)[:120],
            "framework": "django",
            "detection": [redact_secrets(item)[:120] for item in detection],
            "project_package": redact_secrets(project_package)[:120],
            "has_manage_py": has_manage_py,
            "has_wsgi": ("wsgi.py" in direct_supporting) or package_has_wsgi,
            "has_asgi": ("asgi.py" in direct_supporting) or package_has_asgi,
            "dependency_files": [redact_secrets(item)[:80] for item in dependency_files],
            "metadata": {
                "source": DJANGO_APPS_DISCOVERY_TOOL_KEY,
                "scan_root": "/opt",
                "depth": depth,
            },
        },
    }


def _is_nested_under_selected(candidate: Path, selected_paths: list[Path]) -> bool:
    for selected in selected_paths:
        if candidate == selected:
            continue
        try:
            candidate.relative_to(selected)
            return True
        except ValueError:
            continue
    return False


def collect_django_apps(params=None):
    params = params or {}
    if params:
        raise ValueError("django_apps_discovery does not accept parameters.")

    caps = _Caps()
    stats = {
        "dirs_skipped": 0,
        "permission_denied": 0,
        "stat_checks": 0,
        "nested_candidates_skipped": 0,
    }

    inspected: list[dict] = []
    seen_paths: set[str] = set()
    candidates = candidate_app_dirs(OPT_ROOT, caps=caps, stats=stats)

    for candidate_dir in candidates:
        try:
            candidate_real = _ensure_under_root(OPT_ROOT, candidate_dir)
        except DjangoDiscoveryError:
            stats["dirs_skipped"] += 1
            continue
        dedupe_key = str(candidate_real)
        if dedupe_key in seen_paths:
            continue
        seen_paths.add(dedupe_key)

        candidate = _inspect_candidate(candidate_real, caps=caps, stats=stats)
        if candidate:
            inspected.append(candidate)

    selected_paths: list[Path] = []
    applications: list[dict] = []
    for candidate in sorted(inspected, key=lambda item: len(item["path"].parts)):
        if _is_nested_under_selected(candidate["path"], selected_paths):
            stats["nested_candidates_skipped"] += 1
            continue
        selected_paths.append(candidate["path"])
        applications.append(candidate["payload"])

    result = {
        "applications": applications,
        "summary": {
            "apps_total": len(applications),
            "candidates_scanned": len(candidates),
            "dirs_skipped": stats["dirs_skipped"],
            "permission_denied": stats["permission_denied"],
            "nested_candidates_skipped": stats["nested_candidates_skipped"],
            "notes": [
                "depth=2",
                "symlinks=allow_under_opt_only",
                f"stat_checks={stats['stat_checks']}",
            ],
        },
    }

    encoded = json.dumps(result, sort_keys=True).encode("utf-8")
    if len(encoded) > caps.max_output_bytes:
        raise DjangoDiscoveryError("django_apps_discovery output exceeded the configured cap.")
    return result

