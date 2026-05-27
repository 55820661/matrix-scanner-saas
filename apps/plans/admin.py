from django.contrib import admin

from .models import Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "price",
        "currency",
        "billing_cycle",
        "max_servers",
        "max_applications",
        "max_users",
        "is_active",
    )
    list_filter = ("billing_cycle", "currency", "is_active")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")
