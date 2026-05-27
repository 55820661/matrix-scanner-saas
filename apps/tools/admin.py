from django.contrib import admin

from .models import PlanTool, ToolDefinition, ToolPolicy, ToolRun, ToolTemplate


@admin.register(ToolTemplate)
class ToolTemplateAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "runtime_handler_key", "default_timeout_seconds", "default_max_output_bytes", "is_active")
    list_filter = ("is_active", "created_at")
    search_fields = ("key", "name", "runtime_handler_key", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ToolDefinition)
class ToolDefinitionAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "template", "status", "risk_level", "category", "timeout_seconds", "max_output_bytes")
    list_filter = ("status", "risk_level", "category", "requires_path_policy", "created_at")
    search_fields = ("key", "name", "description", "template__key")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ToolPolicy)
class ToolPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "tool_definition",
        "allow_customer_run",
        "allow_admin_run",
        "allow_agent_run",
        "requires_approved_application",
        "is_active",
    )
    list_filter = (
        "allow_customer_run",
        "allow_admin_run",
        "allow_agent_run",
        "requires_approved_application",
        "is_active",
    )
    search_fields = ("tool_definition__key", "tool_definition__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PlanTool)
class PlanToolAdmin(admin.ModelAdmin):
    list_display = ("plan", "tool_definition", "is_enabled", "monthly_limit")
    list_filter = ("is_enabled", "plan", "tool_definition")
    search_fields = ("plan__name", "tool_definition__key", "tool_definition__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ToolRun)
class ToolRunAdmin(admin.ModelAdmin):
    list_display = (
        "tool_definition",
        "server",
        "account",
        "agent",
        "status",
        "requested_by_type",
        "timeout_seconds",
        "max_output_bytes",
        "created_at",
    )
    list_filter = ("status", "requested_by_type", "tool_definition", "account", "created_at")
    search_fields = ("tool_definition__key", "server__name", "server__hostname", "account__name", "agent_job__id")
    readonly_fields = (
        "account",
        "server",
        "agent",
        "tool_definition",
        "agent_job",
        "requested_by",
        "requested_by_type",
        "params_redacted",
        "result_redacted",
        "error_message",
        "timeout_seconds",
        "max_output_bytes",
        "started_at",
        "finished_at",
        "created_at",
        "updated_at",
    )
