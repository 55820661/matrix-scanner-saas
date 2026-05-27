from django.contrib import admin

from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "account",
        "plan",
        "status",
        "current_period_start",
        "current_period_end",
        "trial_ends_at",
        "auto_renew",
    )
    list_filter = ("status", "auto_renew", "plan")
    search_fields = ("account__name", "plan__name")
    readonly_fields = ("created_at", "updated_at")
