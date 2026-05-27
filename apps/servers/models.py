from django.db import models

from apps.accounts.models import Account
from apps.core.models import TimeStampedModel


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
