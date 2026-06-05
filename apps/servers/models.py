from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.accounts.models import Account
from apps.core.models import TimeStampedModel
from apps.core.tokens import generate_raw_token, hash_token

from .baseline_profiles import BASELINE_PROFILE_CHOICES, DEFAULT_BASELINE_PROFILE


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
    execution_payload = models.JSONField(default=dict, blank=True)

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
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="requested_baseline_scans",
        null=True,
        blank=True,
    )
    profile_key = models.CharField(
        max_length=80,
        choices=BASELINE_PROFILE_CHOICES,
        default=DEFAULT_BASELINE_PROFILE,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    current_step = models.CharField(max_length=120, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Baseline scan for {self.server} ({self.status})"


class BaselineScanStep(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"
        CANCELLED = "cancelled", "Cancelled"

    baseline_scan = models.ForeignKey(BaselineScan, on_delete=models.CASCADE, related_name="steps")
    tool_run = models.OneToOneField(
        "tools.ToolRun",
        on_delete=models.SET_NULL,
        related_name="baseline_step",
        null=True,
        blank=True,
    )
    step_key = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    summary = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    structured_output = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(fields=["baseline_scan", "step_key"], name="unique_baseline_scan_step"),
        ]

    def __str__(self):
        return f"{self.step_key} for {self.baseline_scan} ({self.status})"


class DiscoveredService(TimeStampedModel):
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="discovered_services")
    server = models.ForeignKey(Server, on_delete=models.PROTECT, related_name="discovered_services")
    baseline_scan = models.ForeignKey(
        BaselineScan,
        on_delete=models.SET_NULL,
        related_name="discovered_services",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=160)
    status = models.CharField(max_length=80, blank=True)
    version = models.CharField(max_length=160, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["server__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["account", "server", "name"], name="unique_discovered_service"),
        ]

    def __str__(self):
        return f"{self.name} on {self.server}"


class DiscoveredDomain(TimeStampedModel):
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="discovered_domains")
    server = models.ForeignKey(Server, on_delete=models.PROTECT, related_name="discovered_domains")
    baseline_scan = models.ForeignKey(
        BaselineScan,
        on_delete=models.SET_NULL,
        related_name="discovered_domains",
        null=True,
        blank=True,
    )
    domain = models.CharField(max_length=255)
    document_root = models.CharField(max_length=1024, blank=True)
    owner = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["server__name", "domain"]
        constraints = [
            models.UniqueConstraint(fields=["account", "server", "domain"], name="unique_discovered_domain"),
        ]

    def __str__(self):
        return f"{self.domain} on {self.server}"


class LogSource(TimeStampedModel):
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="log_sources")
    server = models.ForeignKey(Server, on_delete=models.PROTECT, related_name="log_sources")
    baseline_scan = models.ForeignKey(
        BaselineScan,
        on_delete=models.SET_NULL,
        related_name="log_sources",
        null=True,
        blank=True,
    )
    path = models.CharField(max_length=1024)
    source_type = models.CharField(max_length=120, blank=True)
    exists = models.BooleanField(default=False)
    size_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["server__name", "path"]
        constraints = [
            models.UniqueConstraint(fields=["account", "server", "path"], name="unique_log_source"),
        ]

    def __str__(self):
        return f"{self.source_type or 'log'}: {self.path}"


class Finding(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RESOLVED = "resolved", "Resolved"
        IGNORED = "ignored", "Ignored"

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="findings")
    server = models.ForeignKey(Server, on_delete=models.PROTECT, related_name="findings")
    baseline_scan = models.ForeignKey(
        BaselineScan,
        on_delete=models.SET_NULL,
        related_name="findings",
        null=True,
        blank=True,
    )
    application = models.ForeignKey(
        "applications.Application",
        on_delete=models.SET_NULL,
        related_name="findings",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    severity = models.CharField(max_length=40, default="info")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    evidence_summary = models.TextField(blank=True)
    fingerprint = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["account", "server", "fingerprint"], name="unique_finding_fingerprint"),
        ]

    def __str__(self):
        return f"{self.title} ({self.status})"
