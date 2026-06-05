from django.contrib import admin, messages

from .models import AdminChatDecision, AdminChatMessage, AdminChatReportDraft, AdminChatSession, AdminChatToolRequest
from .services import convert_chat_report_draft, review_chat_report_draft


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


class AdminChatReportDraftInline(admin.TabularInline):
    model = AdminChatReportDraft
    extra = 0
    readonly_fields = (
        "report_type",
        "status",
        "title_redacted",
        "summary_redacted",
        "sections_redacted",
        "reviewed_by",
        "reviewed_at",
        "converted_report",
        "created_at",
    )
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(AdminChatSession)
class AdminChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "account", "server", "application", "status", "title_redacted", "last_message_at", "created_at")
    list_filter = ("status", "account", "server")
    search_fields = ("title_redacted", "account__name", "server__name", "application__name")
    readonly_fields = ("context_snapshot_redacted", "last_message_at", "created_at", "updated_at")
    inlines = [AdminChatMessageInline, AdminChatDecisionInline, AdminChatToolRequestInline, AdminChatReportDraftInline]


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


@admin.register(AdminChatReportDraft)
class AdminChatReportDraftAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "report_type", "status", "created_by", "reviewed_by", "converted_report", "created_at")
    list_filter = ("report_type", "status", "created_at")
    search_fields = ("session__title_redacted", "title_redacted", "summary_redacted")
    readonly_fields = (
        "session",
        "message",
        "created_by",
        "reviewed_by",
        "reviewed_at",
        "converted_report",
        "title_redacted",
        "summary_redacted",
        "sections_redacted",
        "source_snapshot_redacted",
        "review_notes_redacted",
        "created_at",
        "updated_at",
    )
    actions = ("approve_drafts", "reject_drafts", "convert_to_report")

    @admin.action(description="Approve selected chat report drafts")
    def approve_drafts(self, request, queryset):
        for draft in queryset:
            review_chat_report_draft(draft, reviewer=request.user, decision=AdminChatReportDraft.Status.APPROVED)
            self.message_user(request, f"Approved chat report draft {draft.id}.", level=messages.SUCCESS)

    @admin.action(description="Reject selected chat report drafts")
    def reject_drafts(self, request, queryset):
        for draft in queryset:
            review_chat_report_draft(draft, reviewer=request.user, decision=AdminChatReportDraft.Status.REJECTED)
            self.message_user(request, f"Rejected chat report draft {draft.id}.", level=messages.WARNING)

    @admin.action(description="Convert approved drafts to final Report")
    def convert_to_report(self, request, queryset):
        for draft in queryset:
            report = convert_chat_report_draft(draft, reviewer=request.user)
            self.message_user(
                request,
                f"Converted chat report draft {draft.id} to report {report.id} ({report.report_type}).",
                level=messages.SUCCESS,
            )
