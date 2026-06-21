import re


SECRET_PATTERNS = (
    re.compile(r"(?i)\bsk-[A-Za-z0-9_-]{10,}\b"),
    re.compile(
        r"(?i)\b(?:sk-[A-Za-z0-9_-]*canary[A-Za-z0-9_-]*|"
        r"[A-Za-z0-9_-]*(?:secret|password|private[_-]?key|token)[A-Za-z0-9_-]*canary[A-Za-z0-9_-]*)\b"
    ),
    re.compile(r"(?i)(password\s*[:=]\s*)\S+"),
    re.compile(r"(?i)(app_key\s*[:=]\s*)\S+"),
    re.compile(r"(?i)(api[_ -]?key\s*[:=]\s*)\S+"),
    re.compile(r"(?i)(private[_ -]?key\s*[:=]\s*)\S+"),
    re.compile(r"(?i)(token\s*[:=]\s*)\S+"),
    re.compile(r"(?i)(authorization\s*[:=]\s*)\S+"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(r"-----BEGIN [^-]+PRIVATE KEY-----.*?-----END [^-]+PRIVATE KEY-----", re.DOTALL),
)

SENSITIVE_KEY_PARTS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "app_key",
    "private_key",
    "authorization",
    "bearer",
    "credential",
)


def redact_secrets(value):
    if value is None:
        return ""
    text = str(value)
    for pattern in SECRET_PATTERNS:
        if pattern.groups:
            text = pattern.sub(lambda match: f"{match.group(1)}[REDACTED]", text)
        else:
            text = pattern.sub("[REDACTED]", text)
    return text


def redact_json(value):
    if isinstance(value, dict):
        redacted = {}
        for key, nested_value in value.items():
            normalized = str(key).lower()
            if any(part in normalized for part in SENSITIVE_KEY_PARTS):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_json(nested_value)
        return redacted
    if isinstance(value, list):
        return [redact_json(item) for item in value]
    if isinstance(value, str):
        return redact_secrets(value)
    return value
