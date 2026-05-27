from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.accounts.models import Account
from apps.core.models import TimeStampedModel
from apps.core.tokens import generate_raw_token, hash_token


class Server(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        OFFLINE = "offline", "Offline"
        ARCHIVED = "archived", "Archived"

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="servers")
    name = models.CharField(max_length=255)
    hostname = models.CharField(max_length=255, blank=True)
    public_ip = models.GenericIPAddressField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    agent_status = models.CharField(max_length=50, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["account__name", "name"]

    def __str__(self):
        return f"{self.name} ({self.account})"

    @property
    def is_archived(self):
        return self.status == self.Status.ARCHIVED


class ScannerAgent(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        OFFLINE = "offline", "Offline"
        REVOKED = "revoked", "Revoked"

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="scanner_agents")
    server = models.OneToOneField(Server, on_delete=models.PROTECT, related_name="scanner_agent")
    token_hash = models.CharField(max_length=128, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    agent_version = models.CharField(max_length=50, blank=True)
    registered_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["account__name", "server__name"]

    def __str__(self):
        return f"{self.server} agent"

    def issue_token(self):
        raw_token = generate_raw_token()
        self.token_hash = hash_token(raw_token)
        return raw_token

    @property
    def is_active_for_api(self):
        return (
            self.status == self.Status.ACTIVE
            and self.revoked_at is None
            and self.account.status == Account.Status.ACTIVE
            and self.server.status != Server.Status.ARCHIVED
        )


class AgentRegistrationToken(TimeStampedModel):
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="agent_registration_tokens")
    server = models.ForeignKey(Server, on_delete=models.PROTECT, related_name="registration_tokens")
    token_hash = models.CharField(max_length=128, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_agent_registration_tokens",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Registration token for {self.server}"

    @classmethod
    def create_for_server(cls, server, *, created_by=None, ttl_minutes=60):
        raw_token = generate_raw_token()
        token = cls.objects.create(
            account=server.account,
            server=server,
            token_hash=hash_token(raw_token),
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
            created_by=created_by,
        )
        return token, raw_token

    @property
    def is_usable(self):
        now = timezone.now()
        return self.used_at is None and self.revoked_at is None and self.expires_at > now

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at", "updated_at"])


class AgentJob(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CLAIMED = "claimed", "Claimed"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        REJECTED = "rejected", "Rejected"
        TIMEOUT = "timeout", "Timeout"
        CANCELLED = "cancelled", "Cancelled"

    TERMINAL_STATUSES = {
        Status.SUCCEEDED,
        Status.FAILED,
        Status.REJECTED,
        Status.TIMEOUT,
        Status.CANCELLED,
    }

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="agent_jobs")
    server = models.ForeignKey(Server, on_delete=models.PROTECT, related_name="agent_jobs")
    agent = models.ForeignKey(ScannerAgent, on_delete=models.PROTECT, related_name="jobs")
    tool_key = models.CharField(max_length=120)
    params = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    claimed_at = models.DateTimeField(null=True, blank=True)
    claim_expires_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    max_output_bytes = models.PositiveIntegerField(default=65536)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["account", "status", "created_at"]),
            models.Index(fields=["agent", "status", "created_at"]),
            models.Index(fields=["server", "status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.tool_key} for {self.server} ({self.status})"

    @property
    def is_terminal(self):
        return self.status in self.TERMINAL_STATUSES


class BaselineScan(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="baseline_scans")
    server = models.ForeignKey(Server, on_delete=models.PROTECT, related_name="baseline_scans")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Baseline scan for {self.server} ({self.status})"
