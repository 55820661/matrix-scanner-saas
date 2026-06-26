from dataclasses import dataclass


@dataclass(frozen=True)
class DiagnosticBundle:
    slug: str
    label_ar: str
    label_en: str
    tool_keys: tuple[str, ...]
    keywords: tuple[str, ...]


DIAGNOSTIC_BUNDLES = {
    "server_health": DiagnosticBundle(
        slug="server_health",
        label_ar="فحص صحة السيرفر",
        label_en="Server Health Check",
        tool_keys=(
            "log_sources_discovery_v2",
            "systemd_services_discovery",
            "nginx_sites_discovery",
            "gunicorn_uvicorn_services_discovery",
            "postgres_status_discovery",
        ),
        keywords=(
            "حالة السيرفر",
            "صحة السيرفر",
            "فحص شامل",
            "مشاكل السيرفر",
            "راجع السيرفر",
            "افحص السيرفر",
            "server health",
            "check server",
            "server status",
            "diagnose server",
            "full check",
        ),
    ),
    "web_stack_health": DiagnosticBundle(
        slug="web_stack_health",
        label_ar="فحص طبقة الويب",
        label_en="Web Stack Health Check",
        tool_keys=(
            "nginx_sites_discovery",
            "gunicorn_uvicorn_services_discovery",
            "log_sources_discovery_v2",
        ),
        keywords=(
            "الويب ستاك",
            "طبقة الويب",
            "nginx واللوجات",
            "الخدمات والـ nginx واللوجات",
            "web stack",
            "nginx logs services",
        ),
    ),
}


SPECIFIC_TOOL_TERMS = (
    "مصادر السجلات",
    "log sources",
    "logs",
)


ADVICE_TERMS = (
    "ماذا تقترح",
    "ماذا تنصح",
    "ايه الفحوصات",
    "إيه الفحوصات",
    "what do you suggest",
    "what should",
    "should we",
)


EXECUTION_TERMS = (
    "افحص",
    "نفذ",
    "ابدأ",
    "شغل",
    "تابع",
    "متابعة",
    "اعمل فحص",
    "راجع",
    "check",
    "run",
    "execute",
    "start",
    "continue",
)


def get_diagnostic_bundle(slug):
    return DIAGNOSTIC_BUNDLES.get(slug)


def resolve_diagnostic_bundle_intent(text):
    normalized = (text or "").casefold()
    if not normalized:
        return None
    if any(term.casefold() in normalized for term in SPECIFIC_TOOL_TERMS):
        return None
    for bundle in DIAGNOSTIC_BUNDLES.values():
        if any(keyword.casefold() in normalized for keyword in bundle.keywords):
            return bundle
    return None


def has_bundle_execution_intent(text):
    normalized = (text or "").casefold()
    if not normalized:
        return False
    if any(term.casefold() in normalized for term in ADVICE_TERMS):
        return False
    return any(term.casefold() in normalized for term in EXECUTION_TERMS)
