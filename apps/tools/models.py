from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.accounts.models import Account
from apps.core.models import TimeStampedModel
from apps.plans.models import Plan
from apps.servers.models import AgentJob, ScannerAgent, Server


class ToolTemplate(TimeStampedModel):
    key = models.CharField(max_length=120, unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    runtime_handler_key = models.CharField(max_length=120)
    input_schema = models.JSONField(default=dict, blank=True)
    output_schema = models.JSONField(default=dict, blank=True)
    default_timeout_seconds = models.PositiveIntegerField(default=30)
    default_max_output_bytes = models.PositiveIntegerField(default=65536)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.key


class ToolDefinition(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_REVIEW = "pending_review", "Pending review"
        APPROVED = "approved", "Approved"
        ENABLED = "enabled", "Enabled"
        DISABLED = "disabled", "Disabled"
        DEPRECATED = "deprecated", "Deprecated"
        REJECTED = "rejected", "Rejected"

    class RiskLevel(models.TextChoices):
        READ_ONLY = "read_only", "Read only"
        SENSITIVE_READ = "sensitive_read", "Sensitive read"
        BOOTSTRAP_ACTION = "bootstrap_action", "Bootstrap action"
        WRITE_ACTION = "write_action", "Write action"
        DESTRUCTIVE_ACTION = "destructive_action", "Destructive action"

    template = models.ForeignKey(ToolTemplate, on_delete=models.PROTECT, related_name="definitions")
    key = models.CharField(max_length=120, unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    risk_level = models.CharField(max_length=30, choices=RiskLevel.choices, default=RiskLevel.READ_ONLY)
    category = models.CharField(max_length=80, blank=True)
    input_schema = models.JSONField(default=dict, blank=True)
    default_params = models.JSONField(default=dict, blank=True)
    timeout_seconds = models.PositiveIntegerField(default=30)
    max_output_bytes = models.PositiveIntegerField(default=65536)
    requires_path_policy = models.BooleanField(default=False)
    allowed_path_prefixes = models.JSONField(default=list, blank=True)
    blocked_path_prefixes = models.JSONField(default=list, blank=True)
    redaction_rules = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_tool_definitions",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.key

    @property
    def is_enabled_for_mvp(self):
        return self.status == self.Status.ENABLED and self.risk_level == self.RiskLevel.READ_ONLY


class ToolPolicy(TimeStampedModel):
    tool_definition = models.OneToOneField(ToolDefinition, on_delete=models.CASCADE, related_name="policy")
    allow_customer_run = models.BooleanField(default=True)
    allow_admin_run = models.BooleanField(default=True)
    allow_agent_run = models.BooleanField(default=True)
    requires_approved_application = models.BooleanField(default=False)
    allowed_roles = models.JSONField(default=list, blank=True)
    allowed_server_statuses = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["tool_definition__key"]

    def __str__(self):
        return f"Policy for {self.tool_definition}"


class PlanTool(TimeStampedModel):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="plan_tools")
    tool_definition = models.ForeignKey(ToolDefinition, on_delete=models.CASCADE, related_name="plan_tools")
    is_enabled = models.BooleanField(default=True)
    monthly_limit = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["plan__name", "tool_definition__key"]
        constraints = [
            models.UniqueConstraint(fields=["plan", "tool_definition"], name="unique_plan_tool_definition"),
        ]

    def __str__(self):
        return f"{self.plan} -> {self.tool_definition}"


class ToolRun(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        REJECTED = "rejected", "Rejected"
        TIMEOUT = "timeout", "Timeout"
        CANCELLED = "cancelled", "Cancelled"

    class RequestedByType(models.TextChoices):
        USER = "user", "User"
        ADMIN = "admin", "Admin"
        SYSTEM = "system", "System"

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="tool_runs")
    server = models.ForeignKey(Server, on_delete=models.PROTECT, related_name="tool_runs")
    agent = models.ForeignKey(ScannerAgent, on_delete=models.PROTECT, related_name="tool_runs")
    tool_definition = models.ForeignKey(ToolDefinition, on_delete=models.PROTECT, related_name="tool_runs")
    agent_job = models.OneToOneField(
        AgentJob,
        on_delete=models.SET_NULL,
        related_name="tool_run",
        null=True,
        blank=True,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="requested_tool_runs",
        null=True,
        blank=True,
    )
    requested_by_type = models.CharField(max_length=20, choices=RequestedByType.choices, default=RequestedByType.SYSTEM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    params = models.JSONField(default=dict, blank=True)
    params_redacted = models.JSONField(default=dict, blank=True)
    result_redacted = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    timeout_seconds = models.PositiveIntegerField(default=30)
    max_output_bytes = models.PositiveIntegerField(default=65536)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["account", "status", "created_at"]),
            models.Index(fields=["server", "status", "created_at"]),
            models.Index(fields=["tool_definition", "status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.tool_definition} on {self.server} ({self.status})"

    def clean(self):
        super().clean()
        if self.server_id and self.account_id and self.server.account_id != self.account_id:
            raise ValidationError({"server": "Server must belong to the ToolRun account."})
        if self.agent_id and self.agent.server_id != self.server_id:
            raise ValidationError({"agent": "Agent must belong to the ToolRun server."})


class ToolBuildRequest(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        PROPOSED = "proposed", "Proposed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="tool_build_requests",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=160)
    description_redacted = models.TextField(blank=True)
    desired_tool_key = models.CharField(max_length=120)
    desired_handler_key = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    validation_summary = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.desired_tool_key


class ToolBuildProposal(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        VALIDATION_FAILED = "validation_failed", "Validation failed"
        PENDING_REVIEW = "pending_review", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CONVERTED = "converted", "Converted"

    request = models.ForeignKey(ToolBuildRequest, on_delete=models.CASCADE, related_name="proposals")
    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="tool_build_proposals",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    proposed_definition = models.JSONField(default=dict, blank=True)
    proposed_policy = models.JSONField(default=dict, blank=True)
    validation_errors = models.JSONField(default=list, blank=True)
    validation_warnings = models.JSONField(default=list, blank=True)
    converted_tool_definition = models.ForeignKey(
        ToolDefinition,
        on_delete=models.SET_NULL,
        related_name="build_proposals",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Proposal for {self.request}"


class ToolBuildReview(TimeStampedModel):
    class Decision(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        NEEDS_CHANGES = "needs_changes", "Needs changes"

    proposal = models.ForeignKey(ToolBuildProposal, on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="tool_build_reviews",
        null=True,
        blank=True,
    )
    decision = models.CharField(max_length=20, choices=Decision.choices)
    notes_redacted = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.decision} for {self.proposal_id}"


class ToolTestResult(TimeStampedModel):
    class Status(models.TextChoices):
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"

    proposal = models.ForeignKey(ToolBuildProposal, on_delete=models.CASCADE, related_name="test_results")
    status = models.CharField(max_length=20, choices=Status.choices)
    test_type = models.CharField(max_length=80, default="mock_validation")
    summary_redacted = models.TextField(blank=True)
    result_redacted = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.test_type}: {self.status}"
