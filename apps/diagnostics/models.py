from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.accounts.models import Account
from apps.applications.models import Application
from apps.core.models import TimeStampedModel
from apps.servers.models import Server


class DiagnosticSession(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        RUNNING = "running", "Running"
        WAITING_FOR_APPROVAL = "waiting_for_approval", "Waiting for approval"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class ProblemType(models.TextChoices):
        SLOWNESS = "slowness", "Slowness"
        HTTP_500 = "http_500", "HTTP 500"
        SECURITY_SCAN = "security_scan", "Security scan"
        LARAVEL_PRODUCTION_AUDIT = "laravel_production_audit", "Laravel production audit"
        CUSTOM = "custom", "Custom"

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="diagnostic_sessions")
    server = models.ForeignKey(Server, on_delete=models.PROTECT, related_name="diagnostic_sessions")
    application = models.ForeignKey(
        Application,
        on_delete=models.SET_NULL,
        related_name="diagnostic_sessions",
        null=True,
        blank=True,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="requested_diagnostic_sessions",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    problem_type = models.CharField(max_length=40, choices=ProblemType.choices, default=ProblemType.CUSTOM)
    user_prompt_redacted = models.TextField(blank=True)
    summary_redacted = models.TextField(blank=True)
    final_report_redacted = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    tool_run_count = models.PositiveIntegerField(default=0)
    max_tool_runs = models.PositiveIntegerField(default=10)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["account", "status", "created_at"]),
            models.Index(fields=["server", "status", "created_at"]),
        ]

    def __str__(self):
        return f"Diagnostic session for {self.server} ({self.status})"

    def clean(self):
        super().clean()
        if self.server_id and self.account_id and self.server.account_id != self.account_id:
            raise ValidationError({"server": "Server must belong to the selected account."})
        if self.application_id:
            if self.application.account_id != self.account_id:
                raise ValidationError({"application": "Application must belong to the selected account."})
            if self.application.server_id != self.server_id:
                raise ValidationError({"application": "Application must belong to the selected server."})
        if self.max_tool_runs > 10:
            raise ValidationError({"max_tool_runs": "Sprint 8 diagnostic sessions allow at most 10 tool runs."})


class DiagnosticStep(TimeStampedModel):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting approval"
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"
        CANCELLED = "cancelled", "Cancelled"

    class StepType(models.TextChoices):
        RUN_TOOL = "run_tool", "Run tool"
        ASK_USER = "ask_user", "Ask user"
        FINAL_REPORT = "final_report", "Final report"
        STOP = "stop", "Stop"

    session = models.ForeignKey(DiagnosticSession, on_delete=models.CASCADE, related_name="steps")
    tool_run = models.OneToOneField(
        "tools.ToolRun",
        on_delete=models.SET_NULL,
        related_name="diagnostic_step",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PLANNED)
    step_type = models.CharField(max_length=30, choices=StepType.choices, default=StepType.RUN_TOOL)
    tool_key = models.CharField(max_length=120, blank=True)
    params_redacted = models.JSONField(default=dict, blank=True)
    result_summary_redacted = models.TextField(blank=True)
    requires_approval = models.BooleanField(default=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_diagnostic_steps",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["session", "status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.step_type}:{self.tool_key or self.status} for {self.session}"


class DiagnosticDecision(models.Model):
    class DecisionType(models.TextChoices):
        PLAN_STEP = "plan_step", "Plan step"
        APPROVE_STEP = "approve_step", "Approve step"
        INGEST_RESULT = "ingest_result", "Ingest result"
        FINAL_REPORT = "final_report", "Final report"
        STOP = "stop", "Stop"

    class CreatedByType(models.TextChoices):
        DETERMINISTIC = "deterministic", "Deterministic"
        SYSTEM = "system", "System"

    session = models.ForeignKey(DiagnosticSession, on_delete=models.CASCADE, related_name="decisions")
    step = models.ForeignKey(
        DiagnosticStep,
        on_delete=models.SET_NULL,
        related_name="decisions",
        null=True,
        blank=True,
    )
    decision_type = models.CharField(max_length=40, choices=DecisionType.choices)
    input_context_redacted = models.JSONField(default=dict, blank=True)
    output_json_redacted = models.JSONField(default=dict, blank=True)
    reasoning_summary = models.TextField(blank=True)
    created_by_type = models.CharField(max_length=30, choices=CreatedByType.choices, default=CreatedByType.DETERMINISTIC)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["session", "decision_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.decision_type} for {self.session}"
