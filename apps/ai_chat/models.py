from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.accounts.models import Account
from apps.applications.models import Application
from apps.core.models import TimeStampedModel
from apps.reports.models import Report
from apps.servers.models import Server
from apps.tools.models import ToolDefinition, ToolRun


class AdminChatSession(TimeStampedModel):
    class Channel(models.TextChoices):
        PORTAL_CUSTOMER = "portal_customer", "Portal customer"
        ADMIN_INTERNAL = "admin_internal", "Admin internal"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ARCHIVED = "archived", "Archived"

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="admin_chat_sessions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="admin_chat_sessions", null=True, blank=True)
    server = models.ForeignKey(Server, on_delete=models.SET_NULL, related_name="admin_chat_sessions", null=True, blank=True)
    application = models.ForeignKey(Application, on_delete=models.SET_NULL, related_name="admin_chat_sessions", null=True, blank=True)
    channel = models.CharField(max_length=30, choices=Channel.choices, default=Channel.PORTAL_CUSTOMER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    title_redacted = models.CharField(max_length=255, blank=True)
    context_snapshot_redacted = models.JSONField(default=dict, blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_message_at", "-created_at"]
        indexes = [
            models.Index(fields=["account", "channel", "status", "last_message_at"]),
            models.Index(fields=["account", "created_at"]),
        ]

    def clean(self):
        errors = {}
        if self.user_id and self.user.account_id and self.user.account_id != self.account_id:
            errors["user"] = "Chat user must belong to the same account."
        if self.server_id and self.server.account_id != self.account_id:
            errors["server"] = "Chat server must belong to the same account."
        if self.application_id and self.application.account_id != self.account_id:
            errors["application"] = "Chat application must belong to the same account."
        if self.application_id and self.server_id and self.application.server_id != self.server_id:
            errors["application"] = "Chat application must belong to the selected server."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.title_redacted or f"Chat session {self.pk}"


class AdminChatMessage(TimeStampedModel):
    class SenderType(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    session = models.ForeignKey(AdminChatSession, on_delete=models.CASCADE, related_name="messages")
    sender_type = models.CharField(max_length=20, choices=SenderType.choices)
    body_redacted = models.TextField(blank=True)
    metadata_redacted = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["session", "created_at"]),
        ]

    def __str__(self):
        return f"{self.sender_type} message for {self.session_id}"


class AdminLiveAIRequestLog(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        DENIED = "denied", "Denied"

    class ErrorClass(models.TextChoices):
        DISABLED = "disabled", "Disabled"
        MISSING_CONFIG = "missing_config", "Missing config"
        AUTH_ERROR = "auth_error", "Auth error"
        RATE_LIMITED = "rate_limited", "Rate limited"
        TIMEOUT = "timeout", "Timeout"
        UPSTREAM_ERROR = "upstream_error", "Upstream error"
        VALIDATION_ERROR = "validation_error", "Validation error"
        UNKNOWN_ERROR = "unknown_error", "Unknown error"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="admin_live_ai_request_logs",
        null=True,
        blank=True,
    )
    user_identifier = models.CharField(max_length=320, blank=True)
    session = models.ForeignKey(
        AdminChatSession,
        on_delete=models.SET_NULL,
        related_name="live_ai_request_logs",
        null=True,
        blank=True,
    )
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, related_name="admin_live_ai_request_logs", null=True, blank=True)
    server = models.ForeignKey(Server, on_delete=models.SET_NULL, related_name="admin_live_ai_request_logs", null=True, blank=True)
    application = models.ForeignKey(Application, on_delete=models.SET_NULL, related_name="admin_live_ai_request_logs", null=True, blank=True)
    model = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    latency_ms = models.PositiveIntegerField(default=0)
    safe_context_size_bytes = models.PositiveIntegerField(default=0)
    response_size_bytes = models.PositiveIntegerField(default=0)
    error_class = models.CharField(max_length=40, choices=ErrorClass.choices, blank=True)
    fallback_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["model", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["account", "created_at"]),
            models.Index(fields=["session", "created_at"]),
            models.Index(fields=["error_class", "created_at"]),
        ]

    def __str__(self):
        return f"Live AI request {self.pk} ({self.status})"


class AdminChatDecision(TimeStampedModel):
    class DecisionType(models.TextChoices):
        ANSWER = "answer", "Answer"
        TOOL_SUGGESTION = "tool_suggestion", "Tool suggestion"
        TOOL_REQUEST = "tool_request", "Tool request"
        REPORT_REQUEST = "report_request", "Report request"
        TOOL_BUILD_REQUEST = "tool_build_request", "Tool build request"

    session = models.ForeignKey(AdminChatSession, on_delete=models.CASCADE, related_name="decisions")
    decision_type = models.CharField(max_length=40, choices=DecisionType.choices)
    input_context_redacted = models.JSONField(default=dict, blank=True)
    output_json_redacted = models.JSONField(default=dict, blank=True)
    reasoning_summary = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["session", "decision_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.decision_type} decision for {self.session_id}"


class AdminChatToolRequest(TimeStampedModel):
    class Status(models.TextChoices):
        SUGGESTED = "suggested", "Suggested"
        APPROVED = "approved", "Approved"
        QUEUED = "queued", "Queued"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    session = models.ForeignKey(AdminChatSession, on_delete=models.CASCADE, related_name="tool_requests")
    message = models.ForeignKey(AdminChatMessage, on_delete=models.SET_NULL, related_name="tool_requests", null=True, blank=True)
    tool_definition = models.ForeignKey(ToolDefinition, on_delete=models.PROTECT, related_name="chat_tool_requests")
    params_redacted = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUGGESTED)
    tool_run = models.ForeignKey(ToolRun, on_delete=models.SET_NULL, related_name="chat_tool_requests", null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_chat_tool_requests",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    error_summary = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["session", "status", "created_at"]),
            models.Index(fields=["tool_definition", "status"]),
        ]

    def clean(self):
        errors = {}
        if self.session_id and self.tool_run_id and self.tool_run.account_id != self.session.account_id:
            errors["tool_run"] = "ToolRun must belong to the chat account."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.tool_definition.key} request for {self.session_id} ({self.status})"


class AdminChatReportDraft(TimeStampedModel):
    class DraftType(models.TextChoices):
        TECHNICAL_INTERNAL = "technical_internal", "Technical/internal"
        CUSTOMER_SUMMARY = "customer_summary", "Customer summary"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_REVIEW = "pending_review", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CONVERTED = "converted", "Converted"

    session = models.ForeignKey(AdminChatSession, on_delete=models.CASCADE, related_name="report_drafts")
    message = models.ForeignKey(AdminChatMessage, on_delete=models.SET_NULL, related_name="report_drafts", null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_chat_report_drafts",
        null=True,
        blank=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_chat_report_drafts",
        null=True,
        blank=True,
    )
    report_type = models.CharField(max_length=40, choices=DraftType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    title_redacted = models.CharField(max_length=255, blank=True)
    summary_redacted = models.TextField(blank=True)
    sections_redacted = models.JSONField(default=list, blank=True)
    source_snapshot_redacted = models.JSONField(default=dict, blank=True)
    review_notes_redacted = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    converted_report = models.ForeignKey(
        Report,
        on_delete=models.SET_NULL,
        related_name="chat_report_drafts",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["session", "status", "created_at"]),
            models.Index(fields=["report_type", "status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.report_type} draft for {self.session_id} ({self.status})"
