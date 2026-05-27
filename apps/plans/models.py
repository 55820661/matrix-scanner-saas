from django.db import models

from apps.core.models import TimeStampedModel


class Plan(TimeStampedModel):
    class BillingCycle(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"
        MANUAL = "manual", "Manual"

    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="USD")
    billing_cycle = models.CharField(
        max_length=20,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY,
    )
    max_servers = models.PositiveIntegerField(default=1)
    max_applications = models.PositiveIntegerField(default=5)
    max_users = models.PositiveIntegerField(default=1)
    max_diagnostic_sessions_per_month = models.PositiveIntegerField(default=0)
    retention_days = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
