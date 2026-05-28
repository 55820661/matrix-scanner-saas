from django.contrib import admin
from django.contrib import messages

from .models import (
    PlanTool,
    ToolBuildProposal,
    ToolBuildRequest,
    ToolBuildReview,
    ToolDefinition,
    ToolPolicy,
    ToolRun,
    ToolTemplate,
    ToolTestResult,
)
from .services import (
    ToolBuildValidationError,
    convert_tool_build_proposal,
    generate_tool_build_proposal,
    review_tool_build_proposal,
    validate_tool_build_proposal,
)


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


class ToolBuildProposalInline(admin.TabularInline):
    model = ToolBuildProposal
    extra = 0
    fields = ("status", "proposed_by", "validation_errors", "converted_tool_definition", "created_at")
    readonly_fields = fields
    can_delete = False


@admin.register(ToolBuildRequest)
class ToolBuildRequestAdmin(admin.ModelAdmin):
    list_display = ("desired_tool_key", "title", "desired_handler_key", "status", "requested_by", "created_at")
    list_filter = ("status", "desired_handler_key", "created_at")
    search_fields = ("desired_tool_key", "desired_handler_key", "title", "description_redacted")
    readonly_fields = ("validation_summary", "created_at", "updated_at")
    inlines = (ToolBuildProposalInline,)
    actions = ("generate_proposal",)

    @admin.action(description="Generate deterministic proposal")
    def generate_proposal(self, request, queryset):
        for build_request in queryset:
            proposal = generate_tool_build_proposal(build_request, actor_user=request.user)
            level = messages.SUCCESS if not proposal.validation_errors else messages.WARNING
            self.message_user(request, f"Generated proposal {proposal.id} for {build_request}.", level=level)


class ToolBuildReviewInline(admin.TabularInline):
    model = ToolBuildReview
    extra = 0
    fields = ("decision", "reviewer", "notes_redacted", "created_at")
    readonly_fields = fields
    can_delete = False


class ToolTestResultInline(admin.TabularInline):
    model = ToolTestResult
    extra = 0
    fields = ("test_type", "status", "summary_redacted", "result_redacted", "created_at")
    readonly_fields = fields
    can_delete = False


@admin.register(ToolBuildProposal)
class ToolBuildProposalAdmin(admin.ModelAdmin):
    list_display = ("request", "status", "proposed_by", "converted_tool_definition", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("request__desired_tool_key", "request__title", "proposed_definition")
    readonly_fields = (
        "proposed_by",
        "validation_errors",
        "validation_warnings",
        "converted_tool_definition",
        "created_at",
        "updated_at",
    )
    inlines = (ToolBuildReviewInline, ToolTestResultInline)
    actions = ("validate_proposals", "approve_proposals", "reject_proposals", "convert_to_draft_tool_definition")

    @admin.action(description="Validate selected proposals")
    def validate_proposals(self, request, queryset):
        for proposal in queryset:
            passed = validate_tool_build_proposal(proposal, actor_user=request.user)
            level = messages.SUCCESS if passed else messages.ERROR
            self.message_user(request, f"Validation {'passed' if passed else 'failed'} for proposal {proposal.id}.", level=level)

    @admin.action(description="Approve selected proposals")
    def approve_proposals(self, request, queryset):
        for proposal in queryset:
            try:
                review_tool_build_proposal(
                    proposal,
                    reviewer=request.user,
                    decision=ToolBuildReview.Decision.APPROVED,
                )
                self.message_user(request, f"Approved proposal {proposal.id}.", level=messages.SUCCESS)
            except ToolBuildValidationError as exc:
                self.message_user(request, f"Could not approve proposal {proposal.id}: {exc}", level=messages.ERROR)

    @admin.action(description="Reject selected proposals")
    def reject_proposals(self, request, queryset):
        for proposal in queryset:
            review_tool_build_proposal(
                proposal,
                reviewer=request.user,
                decision=ToolBuildReview.Decision.REJECTED,
            )
            self.message_user(request, f"Rejected proposal {proposal.id}.", level=messages.WARNING)

    @admin.action(description="Convert approved proposals to draft ToolDefinition")
    def convert_to_draft_tool_definition(self, request, queryset):
        for proposal in queryset:
            try:
                tool_definition = convert_tool_build_proposal(proposal, actor_user=request.user)
                self.message_user(
                    request,
                    f"Converted proposal {proposal.id} to draft ToolDefinition {tool_definition.key}.",
                    level=messages.SUCCESS,
                )
            except ToolBuildValidationError as exc:
                self.message_user(request, f"Could not convert proposal {proposal.id}: {exc}", level=messages.ERROR)


@admin.register(ToolBuildReview)
class ToolBuildReviewAdmin(admin.ModelAdmin):
    list_display = ("proposal", "decision", "reviewer", "created_at")
    list_filter = ("decision", "created_at")
    search_fields = ("proposal__request__desired_tool_key", "notes_redacted")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ToolTestResult)
class ToolTestResultAdmin(admin.ModelAdmin):
    list_display = ("proposal", "test_type", "status", "created_at")
    list_filter = ("status", "test_type", "created_at")
    search_fields = ("proposal__request__desired_tool_key", "summary_redacted")
    readonly_fields = ("created_at", "updated_at")
