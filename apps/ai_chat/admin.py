from django.contrib import admin

from .models import AdminChatDecision, AdminChatMessage, AdminChatSession, AdminChatToolRequest


class AdminChatMessageInline(admin.TabularInline):
    model = AdminChatMessage
    extra = 0
    readonly_fields = ("sender_type", "body_redacted", "metadata_redacted", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class AdminChatDecisionInline(admin.TabularInline):
    model = AdminChatDecision
    extra = 0
    readonly_fields = ("decision_type", "input_context_redacted", "output_json_redacted", "reasoning_summary", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class AdminChatToolRequestInline(admin.TabularInline):
    model = AdminChatToolRequest
    extra = 0
    readonly_fields = ("tool_definition", "params_redacted", "status", "tool_run", "approved_by", "approved_at", "error_summary", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(AdminChatSession)
class AdminChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "account", "server", "application", "status", "title_redacted", "last_message_at", "created_at")
    list_filter = ("status", "account", "server")
    search_fields = ("title_redacted", "account__name", "server__name", "application__name")
    readonly_fields = ("context_snapshot_redacted", "last_message_at", "created_at", "updated_at")
    inlines = [AdminChatMessageInline, AdminChatDecisionInline, AdminChatToolRequestInline]


@admin.register(AdminChatMessage)
class AdminChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "sender_type", "created_at")
    list_filter = ("sender_type",)
    search_fields = ("body_redacted", "session__title_redacted")
    readonly_fields = ("session", "sender_type", "body_redacted", "metadata_redacted", "created_at", "updated_at")


@admin.register(AdminChatDecision)
class AdminChatDecisionAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "decision_type", "created_at")
    list_filter = ("decision_type",)
    search_fields = ("session__title_redacted", "reasoning_summary")
    readonly_fields = ("session", "decision_type", "input_context_redacted", "output_json_redacted", "reasoning_summary", "created_at", "updated_at")


@admin.register(AdminChatToolRequest)
class AdminChatToolRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "tool_definition", "status", "tool_run", "approved_by", "approved_at", "created_at")
    list_filter = ("status", "tool_definition")
    search_fields = ("session__title_redacted", "tool_definition__key", "error_summary")
    readonly_fields = (
        "session",
        "message",
        "tool_definition",
        "params_redacted",
        "status",
        "tool_run",
        "approved_by",
        "approved_at",
        "error_summary",
        "created_at",
        "updated_at",
    )
