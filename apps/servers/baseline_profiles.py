PROFILE_LEGACY_CPANEL = "legacy_cpanel"
PROFILE_DEBIAN_NGINX_OPT = "debian_nginx_opt"
PROFILE_MINIMAL_LINUX = "minimal_linux"

DEFAULT_BASELINE_PROFILE = PROFILE_LEGACY_CPANEL

LEGACY_CPANEL_TOOL_KEYS = (
    "system_identity",
    "services_status",
    "panel_detector",
    "cpanel_domain_scanner",
    "application_discovery",
    "laravel_discovery",
    "log_sources_discovery",
    "webroot_risk_checker",
)

DEBIAN_NGINX_OPT_TOOL_KEYS = (
    "system_identity",
    "systemd_services_discovery",
    "nginx_sites_discovery",
    "opt_apps_discovery",
    "django_apps_discovery",
    "gunicorn_uvicorn_services_discovery",
    "postgres_status_discovery",
    "log_sources_discovery_v2",
)

MINIMAL_LINUX_TOOL_KEYS = (
    "system_identity",
    "systemd_services_discovery",
    "log_sources_discovery_v2",
)

BASELINE_PROFILE_CHOICES = (
    (PROFILE_LEGACY_CPANEL, "Legacy cPanel"),
    (PROFILE_DEBIAN_NGINX_OPT, "Debian / Nginx / opt"),
    (PROFILE_MINIMAL_LINUX, "Minimal Linux"),
)

BASELINE_PROFILE_TOOL_KEYS = {
    PROFILE_LEGACY_CPANEL: LEGACY_CPANEL_TOOL_KEYS,
    PROFILE_DEBIAN_NGINX_OPT: DEBIAN_NGINX_OPT_TOOL_KEYS,
    PROFILE_MINIMAL_LINUX: MINIMAL_LINUX_TOOL_KEYS,
}


def normalize_baseline_profile(profile_key):
    if profile_key in BASELINE_PROFILE_TOOL_KEYS:
        return profile_key
    return DEFAULT_BASELINE_PROFILE


def tool_keys_for_profile(profile_key):
    return BASELINE_PROFILE_TOOL_KEYS[normalize_baseline_profile(profile_key)]
