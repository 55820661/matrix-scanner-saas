import json
import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, urlunsplit

from apps.core.redaction import redact_secrets


NGINX_SITES_DISCOVERY_TOOL_KEY = "nginx_sites_discovery"
NGINX_CONF_PATH = Path("/etc/nginx/nginx.conf")
NGINX_SITES_ENABLED_DIR = Path("/etc/nginx/sites-enabled")
NGINX_SITES_AVAILABLE_DIR = Path("/etc/nginx/sites-available")
NGINX_CONF_D_DIR = Path("/etc/nginx/conf.d")
MAX_CONFIG_FILE_BYTES = 128 * 1024
MAX_TOTAL_CONFIG_BYTES = 512 * 1024
MAX_OUTPUT_BYTES = 64 * 1024

SENSITIVE_DIRECTIVE_PARTS = ("certificate", "key", "auth", "password", "secret", "token")
BLOCKED_PATH_PREFIXES = ("/etc/shadow", "/etc/ssl/private", "/root", "/home/*/.ssh", "/opt/*/.env")
VARIABLE_PATTERN = re.compile(r"\$[A-Za-z0-9_]+")


class NginxDiscoveryError(Exception):
    pass


def strip_comments(text):
    lines = []
    for line in (text or "").splitlines():
        in_single = False
        in_double = False
        kept = []
        for char in line:
            if char == "'" and not in_double:
                in_single = not in_single
            elif char == '"' and not in_single:
                in_double = not in_double
            elif char == "#" and not in_single and not in_double:
                break
            kept.append(char)
        lines.append("".join(kept))
    return "\n".join(lines)


def server_blocks(text):
    text = strip_comments(text)
    blocks = []
    index = 0
    while True:
        match = re.search(r"\bserver\s*\{", text[index:])
        if not match:
            break
        open_brace = index + match.end() - 1
        depth = 0
        for position in range(open_brace, len(text)):
            if text[position] == "{":
                depth += 1
            elif text[position] == "}":
                depth -= 1
                if depth == 0:
                    blocks.append(text[open_brace + 1 : position])
                    index = position + 1
                    break
        else:
            break
    return blocks


def parse_directives(block):
    directives = []
    for match in re.finditer(r"(?<![\w])([A-Za-z_][A-Za-z0-9_]*)\s+([^;{}]+);", block or ""):
        name = match.group(1).strip().lower()
        if any(part in name for part in SENSITIVE_DIRECTIVE_PARTS):
            continue
        directives.append((name, redact_secrets(match.group(2).strip())))
    return directives


def canonicalize_config_path(path):
    resolved = Path(path).resolve(strict=True)
    return resolved


def is_relative_to(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def source_allowed(candidate):
    try:
        resolved = canonicalize_config_path(candidate)
    except OSError:
        return None

    nginx_conf = NGINX_CONF_PATH.resolve(strict=False)
    sites_enabled = NGINX_SITES_ENABLED_DIR.resolve(strict=False)
    sites_available = NGINX_SITES_AVAILABLE_DIR.resolve(strict=False)
    conf_d = NGINX_CONF_D_DIR.resolve(strict=False)
    candidate_path = Path(candidate)
    candidate_location = candidate_path if candidate_path.is_absolute() else Path.cwd() / candidate_path

    if candidate_location == nginx_conf and resolved == nginx_conf:
        return resolved
    if is_relative_to(candidate_location, conf_d) and is_relative_to(resolved, conf_d):
        return resolved
    if is_relative_to(candidate_location, sites_enabled):
        if is_relative_to(resolved, sites_enabled) or is_relative_to(resolved, sites_available) or is_relative_to(resolved, conf_d):
            return resolved
    return None


def candidate_config_files():
    candidates = []
    if NGINX_CONF_PATH.exists() and NGINX_CONF_PATH.is_file():
        candidates.append(NGINX_CONF_PATH)
    if NGINX_SITES_ENABLED_DIR.exists() and NGINX_SITES_ENABLED_DIR.is_dir():
        candidates.extend(path for path in NGINX_SITES_ENABLED_DIR.iterdir() if path.is_file() or path.is_symlink())
    if NGINX_CONF_D_DIR.exists() and NGINX_CONF_D_DIR.is_dir():
        candidates.extend(path for path in NGINX_CONF_D_DIR.glob("*.conf") if path.is_file() or path.is_symlink())
    return candidates


def read_config_file(path):
    allowed = source_allowed(path)
    if allowed is None:
        return None, "outside_allowlist"
    try:
        size = allowed.stat().st_size
        if size > MAX_CONFIG_FILE_BYTES:
            return None, "file_too_large"
        content = allowed.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None, "read_error"
    return {"source_path": str(allowed), "content": content, "bytes": len(content.encode("utf-8"))}, ""


def canonicalize_nginx_path(value):
    value = (value or "").strip().strip('"').strip("'")
    if not value or VARIABLE_PATTERN.search(value) or not value.startswith("/"):
        return ""
    parts = []
    for part in PurePosixPath(value).parts:
        if part in {"", "/", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    path = "/" + "/".join(parts)
    if path.endswith("/.env"):
        return ""
    for prefix in BLOCKED_PATH_PREFIXES:
        if path_matches_prefix(path, prefix):
            return ""
    if "private key" in path.lower() or path.lower().endswith((".key", ".pem")):
        return ""
    return redact_secrets(path)


def normalize_prefix(prefix):
    parts = []
    for part in PurePosixPath(prefix).parts:
        if part in {"", "/", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/" + "/".join(parts)


def path_matches_prefix(path, prefix):
    if prefix.endswith("/*"):
        base = normalize_prefix(prefix[:-2])
        return path == base or path.startswith(f"{base}/")
    base = normalize_prefix(prefix)
    return path == base or path.startswith(f"{base}/")


def parse_listen(value):
    raw = redact_secrets(value.strip())[:120]
    tokens = value.split()
    first = tokens[0] if tokens else ""
    port = None
    if first.startswith("[") and "]:" in first:
        candidate = first.rsplit(":", 1)[-1]
    elif ":" in first:
        candidate = first.rsplit(":", 1)[-1]
    else:
        candidate = first
    if candidate.isdigit():
        port = int(candidate)
    return {
        "raw": raw,
        "port": port,
        "ssl": "ssl" in tokens,
        "default_server": "default_server" in tokens,
    }


def safe_proxy_pass(value):
    value = redact_secrets((value or "").strip().strip('"').strip("'"))
    if not value or VARIABLE_PATTERN.search(value):
        return ""
    parsed = urlsplit(value)
    if parsed.username or parsed.password:
        return ""
    if parsed.scheme not in {"http", "https"}:
        return ""
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    safe = urlunsplit((parsed.scheme, netloc, parsed.path or "", "", ""))
    return safe[:255]


def normalize_server_name(value):
    name = redact_secrets(value.strip().lower())
    if not name or name == "_":
        return ""
    return name[:255]


def parse_server_block(block, source_path):
    directives = parse_directives(block)
    site = {
        "source_path": source_path,
        "server_names": [],
        "listen": [],
        "root": "",
        "proxy_pass": "",
        "access_log": "",
        "error_log": "",
        "is_default": False,
        "metadata": {"source": "nginx_config", "has_include": False, "has_wildcard": False},
    }
    for name, value in directives:
        if name == "server_name":
            for item in value.split():
                server_name = normalize_server_name(item)
                if not server_name:
                    continue
                if server_name.startswith("*."):
                    site["metadata"]["has_wildcard"] = True
                site["server_names"].append(server_name)
        elif name == "listen":
            listen = parse_listen(value)
            if listen["default_server"]:
                site["is_default"] = True
            site["listen"].append(listen)
        elif name == "root" and not site["root"]:
            site["root"] = canonicalize_nginx_path(value)
        elif name == "access_log" and not site["access_log"]:
            site["access_log"] = canonicalize_nginx_path(value.split()[0] if value.split() else "")
        elif name == "error_log" and not site["error_log"]:
            site["error_log"] = canonicalize_nginx_path(value.split()[0] if value.split() else "")
        elif name == "proxy_pass" and not site["proxy_pass"]:
            site["proxy_pass"] = safe_proxy_pass(value)
        elif name == "include":
            site["metadata"]["has_include"] = True
    site["server_names"] = sorted(set(site["server_names"]))
    site["listen_ports"] = sorted({item["port"] for item in site["listen"] if item["port"] is not None})
    return site


def domains_for_site(site):
    domains = []
    for domain in site["server_names"]:
        domains.append(
            {
                "domain": domain,
                "document_root": site.get("root", ""),
                "source_path": site["source_path"],
                "listen_ports": site.get("listen_ports", []),
                "proxy_pass": site.get("proxy_pass", ""),
                "metadata": {
                    "source": "nginx_config",
                    "is_wildcard": domain.startswith("*."),
                    "is_default": site.get("is_default", False),
                },
            }
        )
    return domains


def collect_nginx_sites(params=None):
    if params:
        raise ValueError("nginx_sites_discovery does not accept parameters.")

    files_scanned = 0
    rejected_files = 0
    total_bytes = 0
    sites = []
    domains = []
    for candidate in candidate_config_files():
        payload, error = read_config_file(candidate)
        if error:
            rejected_files += 1
            continue
        total_bytes += payload["bytes"]
        if total_bytes > MAX_TOTAL_CONFIG_BYTES:
            rejected_files += 1
            continue
        files_scanned += 1
        for block in server_blocks(payload["content"]):
            site = parse_server_block(block, payload["source_path"])
            sites.append(site)
            domains.extend(domains_for_site(site))

    result = {
        "sites": sites,
        "domains": domains,
        "summary": {
            "files_scanned": files_scanned,
            "sites": len(sites),
            "domains": len(domains),
            "default_sites": sum(1 for site in sites if site.get("is_default")),
            "proxied_sites": sum(1 for site in sites if site.get("proxy_pass")),
            "rejected_files": rejected_files,
        },
    }
    if len(json.dumps(result, separators=(",", ":")).encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise NginxDiscoveryError("nginx_sites_discovery output exceeded the configured cap.")
    return result
