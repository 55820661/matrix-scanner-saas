from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.accounts.models import Account
from apps.core.redaction import redact_json


SENSITIVE_METADATA_KEYS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "private_key",
    "authorization",
    "bearer",
    "credential",
)


def metadata_contains_sensitive_key(value):
    if isinstance(value, dict):
        for key, nested_value in value.items():
            normalized = str(key).lower()
            if any(pattern in normalized for pattern in SENSITIVE_METADATA_KEYS):
                return True
            if metadata_contains_sensitive_key(nested_value):
                return True
    elif isinstance(value, list):
        return any(metadata_contains_sensitive_key(item) for item in value)
    return False


class AuditLog(models.Model):
    class ActorType(models.TextChoices):
        USER = "user", "User"
        ADMIN = "admin", "Admin"
        AGENT = "agent", "Agent"
        SYSTEM = "system", "System"

    class Result(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILURE = "failure", "Failure"
        DENIED = "denied", "Denied"
        INFO = "info", "Info"

    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    actor_type = models.CharField(max_length=20, choices=ActorType.choices)
    account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=120)
    target_type = models.CharField(max_length=120, blank=True)
    target_id = models.CharField(max_length=120, blank=True)
    result = models.CharField(max_length=20, choices=Result.choices, default=Result.INFO)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["account", "created_at"]),
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["target_type", "target_id"]),
        ]

    def __str__(self):
        return f"{self.action} ({self.result})"

    def clean(self):
        super().clean()
        if metadata_contains_sensitive_key(self.metadata):
            raise ValidationError({"metadata": "Audit metadata must not contain secret-like keys."})

    def save(self, *args, **kwargs):
        self.metadata = redact_json(self.metadata or {})
        self.full_clean()
        return super().save(*args, **kwargs)
