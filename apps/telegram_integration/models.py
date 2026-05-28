from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.accounts.models import Account
from apps.core.models import TimeStampedModel
from apps.core.tokens import generate_raw_token, hash_token
from apps.servers.models import Finding, Server


class TelegramChatLink(TimeStampedModel):
    class ChatType(models.TextChoices):
        PRIVATE = "private", "Private"
        GROUP = "group", "Group"
        SUPERGROUP = "supergroup", "Supergroup"
        CHANNEL = "channel", "Channel"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="telegram_chat_links")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="telegram_chat_links",
        null=True,
        blank=True,
    )
    server = models.ForeignKey(
        Server,
        on_delete=models.PROTECT,
        related_name="telegram_chat_links",
        null=True,
        blank=True,
    )
    telegram_chat_id = models.BigIntegerField(unique=True)
    telegram_user_id = models.BigIntegerField(null=True, blank=True)
    chat_type = models.CharField(max_length=20, choices=ChatType.choices)
    title = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    allowed_notifications = models.JSONField(default=list, blank=True)
    linked_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["account__name", "telegram_chat_id"]
        indexes = [
            models.Index(fields=["account", "status"]),
            models.Index(fields=["telegram_chat_id", "status"]),
        ]

    def __str__(self):
        return f"{self.telegram_chat_id} ({self.account})"

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE and self.revoked_at is None and self.account.status == Account.Status.ACTIVE


class TelegramLinkToken(models.Model):
    class ChatScope(models.TextChoices):
        PRIVATE = "private", "Private"
        GROUP = "group", "Group"

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="telegram_link_tokens")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_telegram_link_tokens",
        null=True,
        blank=True,
    )
    token_hash = models.CharField(max_length=128, unique=True)
    chat_scope = models.CharField(max_length=20, choices=ChatScope.choices)
    server = models.ForeignKey(
        Server,
        on_delete=models.PROTECT,
        related_name="telegram_link_tokens",
        null=True,
        blank=True,
    )
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["account", "created_at"]),
            models.Index(fields=["token_hash"]),
        ]

    def __str__(self):
        return f"Telegram link token for {self.account}"

    @classmethod
    def create_for_account(cls, *, account, created_by, chat_scope, server=None, ttl_minutes=30):
        raw_token = generate_raw_token()
        token = cls.objects.create(
            account=account,
            created_by=created_by,
            token_hash=hash_token(raw_token),
            chat_scope=chat_scope,
            server=server,
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
        )
        return token, raw_token

    @property
    def is_usable(self):
        return self.used_at is None and self.revoked_at is None and self.expires_at > timezone.now()

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])


class TelegramNotification(TimeStampedModel):
    class NotificationType(models.TextChoices):
        BASELINE_COMPLETED = "baseline_completed", "Baseline completed"
        FINDING_CREATED = "finding_created", "Finding created"
        AGENT_OFFLINE = "agent_offline", "Agent offline"
        AGENT_RECOVERED = "agent_recovered", "Agent recovered"
        BOOTSTRAP_COMPLETED = "bootstrap_completed", "Bootstrap completed"
        BOOTSTRAP_FAILED = "bootstrap_failed", "Bootstrap failed"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SUPPRESSED = "suppressed", "Suppressed"

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="telegram_notifications")
    server = models.ForeignKey(
        Server,
        on_delete=models.PROTECT,
        related_name="telegram_notifications",
        null=True,
        blank=True,
    )
    finding = models.ForeignKey(
        Finding,
        on_delete=models.SET_NULL,
        related_name="telegram_notifications",
        null=True,
        blank=True,
    )
    chat_link = models.ForeignKey(TelegramChatLink, on_delete=models.PROTECT, related_name="notifications")
    notification_type = models.CharField(max_length=40, choices=NotificationType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    dedupe_key = models.CharField(max_length=255, blank=True)
    payload_redacted = models.JSONField(default=dict, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["account", "notification_type", "created_at"]),
            models.Index(fields=["chat_link", "dedupe_key", "created_at"]),
        ]

    def __str__(self):
        return f"{self.notification_type} for {self.chat_link}"
