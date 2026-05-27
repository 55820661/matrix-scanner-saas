from django.contrib import admin

from .models import AgentJob, AgentRegistrationToken, BaselineScan, ScannerAgent, Server


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ("name", "account", "hostname", "public_ip", "status", "agent_status", "last_seen_at")
    list_filter = ("status", "agent_status", "account")
    search_fields = ("name", "hostname", "public_ip", "account__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ScannerAgent)
class ScannerAgentAdmin(admin.ModelAdmin):
    list_display = ("server", "account", "status", "agent_version", "registered_at", "last_seen_at", "revoked_at")
    list_filter = ("status", "account", "registered_at", "last_seen_at")
    search_fields = ("server__name", "server__hostname", "account__name", "agent_version")
    readonly_fields = ("token_hash", "created_at", "updated_at")


@admin.register(AgentRegistrationToken)
class AgentRegistrationTokenAdmin(admin.ModelAdmin):
    list_display = ("server", "account", "expires_at", "used_at", "revoked_at", "created_by", "created_at")
    list_filter = ("expires_at", "used_at", "revoked_at", "account")
    search_fields = ("server__name", "server__hostname", "account__name", "created_by__username")
    readonly_fields = ("token_hash", "created_at", "updated_at")


@admin.register(AgentJob)
class AgentJobAdmin(admin.ModelAdmin):
    list_display = ("tool_key", "server", "agent", "account", "status", "claimed_at", "claim_expires_at", "finished_at")
    list_filter = ("status", "tool_key", "account", "created_at")
    search_fields = ("tool_key", "server__name", "server__hostname", "account__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(BaselineScan)
class BaselineScanAdmin(admin.ModelAdmin):
    list_display = ("server", "account", "status", "started_at", "finished_at", "created_at")
    list_filter = ("status", "account", "created_at")
    search_fields = ("server__name", "server__hostname", "account__name")
    readonly_fields = ("created_at", "updated_at")
