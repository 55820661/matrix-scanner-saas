from django.db import models

from apps.accounts.models import Account
from apps.core.models import TimeStampedModel
from apps.servers.models import Server


class Application(TimeStampedModel):
    class ReviewStatus(models.TextChoices):
        PENDING_REVIEW = "pending_review", "Pending review"
        APPROVED = "approved", "Approved"
        IGNORED = "ignored", "Ignored"
        ARCHIVED = "archived", "Archived"

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="applications")
    server = models.ForeignKey(Server, on_delete=models.PROTECT, related_name="applications")
    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, blank=True)
    path = models.CharField(max_length=1024, blank=True)
    framework = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING_REVIEW,
    )

    class Meta:
        ordering = ["account__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["account", "server", "domain", "path"], name="unique_application_location"),
        ]

    def __str__(self):
        return f"{self.name} ({self.server})"

    @property
    def is_archived(self):
        return self.review_status == self.ReviewStatus.ARCHIVED
