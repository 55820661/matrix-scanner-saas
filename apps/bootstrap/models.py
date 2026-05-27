from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.accounts.models import Account
from apps.core.models import TimeStampedModel
from apps.servers.models import ScannerAgent, Server


DEFAULT_CREDENTIAL_TTL_MINUTES = 30
DEFAULT_INSTALL_PATH = "/opt/matrix_scanner"
DEFAULT_SERVICE_NAME = "matrix-scanner-agent.service"


class BootstrapSession(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONNECTING = "connecting", "Connecting"
        PROBING = "probing", "Probing"
        AWAITING_PACKAGE_CONFIRMATION = "awaiting_package_confirmation", "Awaiting package confirmation"
        INSTALLING = "installing", "Installing"
        DEPLOYING = "deploying", "Deploying"
        CONFIGURING = "configuring", "Configuring"
        STARTING = "starting", "Starting"
        VERIFYING_HEARTBEAT = "verifying_heartbeat", "Verifying heartbeat"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    class AuthMethod(models.TextChoices):
        PASSWORD = "password", "Password"
        PRIVATE_KEY = "private_key", "Private key"

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="bootstrap_sessions")
    server = models.ForeignKey(Server, on_delete=models.PROTECT, related_name="bootstrap_sessions")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_bootstrap_sessions",
    )
    status = models.CharField(max_length=40, choices=Status.choices, default=Status.PENDING)
    target_host = models.CharField(max_length=255, blank=True)
    ssh_port = models.PositiveIntegerField(default=22)
    ssh_user = models.CharField(max_length=120)
    auth_method = models.CharField(max_length=20, choices=AuthMethod.choices)
    confirm_package_install = models.BooleanField(default=False)
    install_path = models.CharField(max_length=255, default=DEFAULT_INSTALL_PATH)
    service_name = models.CharField(max_length=120, default=DEFAULT_SERVICE_NAME)
    agent_version = models.CharField(max_length=50, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["account", "status", "created_at"]),
            models.Index(fields=["server", "status", "created_at"]),
        ]

    def __str__(self):
        return f"Bootstrap {self.server} ({self.status})"

    def clean(self):
        super().clean()
        if self.server_id and self.account_id and self.server.account_id != self.account_id:
            raise ValidationError({"server": "Server must belong to the selected account."})
        if self.install_path != DEFAULT_INSTALL_PATH:
            raise ValidationError({"install_path": "Sprint 3 install path is fixed."})
        if self.service_name != DEFAULT_SERVICE_NAME:
            raise ValidationError({"service_name": "Sprint 3 service name is fixed."})

    @property
    def is_terminal(self):
        return self.status in {
            self.Status.COMPLETED,
            self.Status.FAILED,
            self.Status.CANCELLED,
            self.Status.EXPIRED,
        }


class BootstrapStep(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"
        CANCELLED = "cancelled", "Cancelled"

    session = models.ForeignKey(BootstrapSession, on_delete=models.CASCADE, related_name="steps")
    step_key = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    command_template_key = models.CharField(max_length=120, blank=True)
    requires_confirmation = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    summary = models.TextField(blank=True)
    stdout_redacted = models.TextField(blank=True)
    stderr_redacted = models.TextField(blank=True)
    exit_code = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    structured_output = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["session", "status", "created_at"]),
            models.Index(fields=["step_key", "status"]),
        ]

    def __str__(self):
        return f"{self.step_key} ({self.status})"


class BootstrapCredential(TimeStampedModel):
    class CredentialType(models.TextChoices):
        SSH_PASSWORD = "ssh_password", "SSH password"
        SSH_PRIVATE_KEY = "ssh_private_key", "SSH private key"

    session = models.ForeignKey(BootstrapSession, on_delete=models.CASCADE, related_name="credentials")
    credential_type = models.CharField(max_length=30, choices=CredentialType.choices)
    encrypted_payload = models.TextField(blank=True)
    expires_at = models.DateTimeField()
    destroyed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.credential_type} for bootstrap {self.session_id}"

    @classmethod
    def default_expiry(cls):
        return timezone.now() + timedelta(minutes=DEFAULT_CREDENTIAL_TTL_MINUTES)

    @property
    def is_usable(self):
        return bool(self.encrypted_payload) and self.destroyed_at is None and self.expires_at > timezone.now()

    def cleanup(self):
        self.encrypted_payload = ""
        self.destroyed_at = timezone.now()
        self.save(update_fields=["encrypted_payload", "destroyed_at", "updated_at"])


class AgentInstallation(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        INSTALLED = "installed", "Installed"
        FAILED = "failed", "Failed"
        ARCHIVED = "archived", "Archived"

    INSTALL_METHOD_REMOTE_BOOTSTRAP = "remote_bootstrap"

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="agent_installations")
    server = models.ForeignKey(Server, on_delete=models.PROTECT, related_name="agent_installations")
    agent = models.ForeignKey(
        ScannerAgent,
        on_delete=models.PROTECT,
        related_name="installations",
        null=True,
        blank=True,
    )
    bootstrap_session = models.ForeignKey(
        BootstrapSession,
        on_delete=models.PROTECT,
        related_name="agent_installations",
    )
    install_method = models.CharField(max_length=40, default=INSTALL_METHOD_REMOTE_BOOTSTRAP)
    install_path = models.CharField(max_length=255, default=DEFAULT_INSTALL_PATH)
    service_name = models.CharField(max_length=120, default=DEFAULT_SERVICE_NAME)
    agent_version = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    installed_at = models.DateTimeField(null=True, blank=True)
    last_verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["account", "status", "created_at"]),
            models.Index(fields=["server", "status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.server} installation ({self.status})"

    def clean(self):
        super().clean()
        if self.server_id and self.account_id and self.server.account_id != self.account_id:
            raise ValidationError({"server": "Server must belong to the selected account."})
        if self.agent_id and self.agent.server_id != self.server_id:
            raise ValidationError({"agent": "Agent must belong to the selected server."})
