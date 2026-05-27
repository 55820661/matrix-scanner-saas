import os
import platform
from pathlib import Path, PurePosixPath


BASELINE_TOOL_KEYS = {
    "services_status",
    "panel_detector",
    "cpanel_domain_scanner",
    "application_discovery",
    "laravel_discovery",
    "log_sources_discovery",
    "webroot_risk_checker",
}
SAFE_LARAVEL_ENV_KEYS = {
    "APP_ENV",
    "APP_DEBUG",
    "APP_URL",
    "LOG_CHANNEL",
    "LOG_LEVEL",
    "CACHE_DRIVER",
    "QUEUE_CONNECTION",
    "SESSION_DRIVER",
    "MAIL_MAILER",
    "DB_CONNECTION",
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
        else:
            parts.append(part)
    return "/" + "/".join(parts)


def file_metadata(path):
    candidate = Path(path)
    exists = candidate.exists()
    size = None
    if exists and candidate.is_file():
        try:
            size = candidate.stat().st_size
        except OSError:
            size = None
    return {"path": canonicalize_path(path), "exists": exists, "size_bytes": size}


def collect_services_status(_params=None):
    services = []
    for name in ("httpd", "apache2", "nginx", "mysql", "mariadb", "php-fpm", "cpanel"):
        paths = [Path("/run") / f"{name}.pid", Path("/var/run") / f"{name}.pid"]
        services.append(
            {
                "name": name,
                "status": "present" if any(path.exists() for path in paths) else "unknown",
                "version": "",
                "metadata": {},
            }
        )
    return {"services": services, "platform": platform.platform()}


def collect_panel_detector(_params=None):
    markers = {
        "cpanel": Path("/usr/local/cpanel").exists() or Path("/var/cpanel").exists(),
        "plesk": Path("/usr/local/psa").exists(),
    }
    detected = [name for name, present in markers.items() if present]
    return {"panels": detected, "primary_panel": detected[0] if detected else "unknown"}


def collect_cpanel_domains(_params=None):
    domains = []
    userdomains = Path("/etc/userdomains")
    if userdomains.exists() and userdomains.is_file():
        try:
            for line in userdomains.read_text(encoding="utf-8", errors="replace").splitlines():
                if ":" not in line:
                    continue
                domain, owner = [part.strip() for part in line.split(":", 1)]
                if domain and owner:
                    domains.append(
                        {
                            "domain": domain.lower(),
                            "owner": owner,
                            "document_root": canonicalize_path(f"/home/{owner}/public_html"),
                            "metadata": {"source": "/etc/userdomains"},
                        }
                    )
        except OSError:
            pass
    return {"domains": domains}


def discover_webroots():
    roots = []
    home = Path("/home")
    if home.exists():
        try:
            for user_dir in home.iterdir():
                public_html = user_dir / "public_html"
                if public_html.exists() and public_html.is_dir():
                    roots.append(canonicalize_path(str(public_html)))
        except OSError:
            pass
    return roots


def detect_framework(path):
    root = Path(path)
    if (root / "artisan").exists() and (root / "composer.json").exists():
        return "laravel"
    if (root / "wp-config.php").exists():
        return "wordpress"
    return "unknown"


def collect_application_discovery(_params=None):
    applications = []
    for root in discover_webroots():
        framework = detect_framework(root)
        applications.append(
            {
                "name": Path(root).name,
                "domain": "",
                "path": root,
                "framework": framework,
                "metadata": {},
            }
        )
    return {"applications": applications}


def read_laravel_env(path):
    env_path = Path(path) / ".env"
    safe = {}
    if not env_path.exists() or not env_path.is_file():
        return safe
    try:
        lines = env_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return safe
    for line in lines:
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        key = key.strip().upper()
        if key in SAFE_LARAVEL_ENV_KEYS:
            safe[key] = value.strip().strip("\"'")
    return safe


def collect_laravel_discovery(_params=None):
    applications = []
    for root in discover_webroots():
        if detect_framework(root) != "laravel":
            continue
        applications.append(
            {
                "name": Path(root).name,
                "domain": "",
                "path": root,
                "framework": "laravel",
                "env": read_laravel_env(root),
                "metadata": {},
            }
        )
    return {"applications": applications}


def collect_log_sources(_params=None):
    candidates = [
        ("/usr/local/apache/domlogs", "apache_domlogs"),
        ("/var/log/apache2", "apache"),
        ("/var/log/httpd", "httpd"),
        ("/var/log/nginx", "nginx"),
    ]
    log_sources = []
    for path, source_type in candidates:
        metadata = file_metadata(path)
        metadata["type"] = source_type
        log_sources.append(metadata)
    for root in discover_webroots():
        log_sources.append({**file_metadata(os.path.join(root, "storage", "logs", "laravel.log")), "type": "laravel"})
    return {"log_sources": log_sources}


def collect_webroot_risks(_params=None):
    findings = []
    risk_files = {
        ".env": "Environment file appears under a webroot.",
        ".git": "Git metadata appears under a webroot.",
        "composer.lock": "Composer lock file appears under a webroot.",
    }
    for root in discover_webroots():
        for filename, summary in risk_files.items():
            candidate = Path(root) / filename
            if candidate.exists():
                findings.append(
                    {
                        "title": f"Webroot risk: {filename}",
                        "severity": "high" if filename in {".env", ".git"} else "medium",
                        "path": canonicalize_path(str(candidate)),
                        "evidence_summary": summary,
                        "fingerprint": f"webroot-risk:{canonicalize_path(str(candidate))}",
                    }
                )
    return {"findings": findings}


def execute_baseline_tool(tool_key, params=None):
    handlers = {
        "services_status": collect_services_status,
        "panel_detector": collect_panel_detector,
        "cpanel_domain_scanner": collect_cpanel_domains,
        "application_discovery": collect_application_discovery,
        "laravel_discovery": collect_laravel_discovery,
        "log_sources_discovery": collect_log_sources,
        "webroot_risk_checker": collect_webroot_risks,
    }
    handler = handlers.get(tool_key)
    if handler is None:
        raise ValueError("Unsupported baseline tool.")
    return handler(params or {})
