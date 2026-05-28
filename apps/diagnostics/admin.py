from django.contrib import admin

from .models import DiagnosticDecision, DiagnosticSession, DiagnosticStep


class DiagnosticStepInline(admin.TabularInline):
    model = DiagnosticStep
    extra = 0
    fields = ("step_type", "tool_key", "status", "requires_approval", "approved_by", "approved_at", "tool_run")
    readonly_fields = ("approved_at",)


@admin.register(DiagnosticSession)
class DiagnosticSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "account", "server", "application", "problem_type", "status", "tool_run_count", "created_at")
    list_filter = ("status", "problem_type", "account", "created_at")
    search_fields = ("account__name", "server__name", "application__name", "user_prompt_redacted", "final_report_redacted")
    readonly_fields = ("created_at", "updated_at", "started_at", "finished_at", "final_report_redacted")
    inlines = [DiagnosticStepInline]


@admin.register(DiagnosticStep)
class DiagnosticStepAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "step_type", "tool_key", "status", "requires_approval", "approved_by", "created_at")
    list_filter = ("status", "step_type", "requires_approval", "tool_key")
    search_fields = ("session__server__name", "session__account__name", "tool_key", "result_summary_redacted")
    readonly_fields = ("created_at", "updated_at", "approved_at", "result_summary_redacted")


@admin.register(DiagnosticDecision)
class DiagnosticDecisionAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "step", "decision_type", "created_by_type", "created_at")
    list_filter = ("decision_type", "created_by_type", "created_at")
    search_fields = ("session__server__name", "session__account__name", "reasoning_summary")
    readonly_fields = ("input_context_redacted", "output_json_redacted", "created_at")
