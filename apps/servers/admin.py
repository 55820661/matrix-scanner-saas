from django.contrib import admin

from .models import Server


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ("name", "account", "hostname", "public_ip", "status", "agent_status", "last_seen_at")
    list_filter = ("status", "agent_status", "account")
    search_fields = ("name", "hostname", "public_ip", "account__name")
    readonly_fields = ("created_at", "updated_at")
