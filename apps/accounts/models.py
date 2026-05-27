from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimeStampedModel


class Account(TimeStampedModel):
    class AccountType(models.TextChoices):
        COMPANY = "company", "Company"
        INDIVIDUAL = "individual", "Individual"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(max_length=255)
    type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.COMPANY,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_archived(self):
        return self.status == self.Status.ARCHIVED


class User(AbstractUser):
    class CustomerRole(models.TextChoices):
        OWNER = "owner", "Owner"
        OPERATOR = "operator", "Operator"
        VIEWER = "viewer", "Viewer"

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
    )
    role = models.CharField(max_length=20, choices=CustomerRole.choices, blank=True)
    email = models.EmailField(unique=True)

    class Meta:
        ordering = ["username"]

    def clean(self):
        super().clean()
        if self.is_staff or self.is_superuser:
            if self.account_id is None and self.role:
                raise ValidationError({"role": "Matrix Admin users without an account must not have a customer role."})
            return

        if self.account_id is None:
            raise ValidationError({"account": "Customer users must belong to an account."})
        if not self.role:
            raise ValidationError({"role": "Customer users must have a role."})

    @property
    def is_customer_user(self):
        return self.account_id is not None and not self.is_staff
