from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "actor_type", "actor_user", "account", "target_type", "target_id", "result")
    list_filter = ("actor_type", "result", "action", "created_at")
    search_fields = ("action", "target_type", "target_id", "actor_user__username", "actor_user__email", "account__name")
    readonly_fields = (
        "actor_user",
        "actor_type",
        "account",
        "action",
        "target_type",
        "target_id",
        "result",
        "ip_address",
        "user_agent",
        "metadata",
        "created_at",
    )
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
