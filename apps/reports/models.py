from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.accounts.models import Account
from apps.applications.models import Application
from apps.core.redaction import redact_json, redact_secrets
from apps.core.models import TimeStampedModel
from apps.servers.models import BaselineScan, Finding, Server


class Severity(models.TextChoices):
    CRITICAL = "critical", "Critical"
    HIGH = "high", "High"
    MEDIUM = "medium", "Medium"
    LOW = "low", "Low"
    INFO = "info", "Info"


class Report(TimeStampedModel):
    class ReportType(models.TextChoices):
        BASELINE = "baseline_report", "Baseline report"
        DIAGNOSTIC = "diagnostic_report", "Diagnostic report"
        SERVER_HEALTH = "server_health_summary", "Server health summary"
        FINDINGS = "findings_summary", "Findings summary"

    class Status(models.TextChoices):
        GENERATED = "generated", "Generated"
        ARCHIVED = "archived", "Archived"

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="reports")
    server = models.ForeignKey(Server, on_delete=models.SET_NULL, related_name="reports", null=True, blank=True)
    application = models.ForeignKey(
        Application,
        on_delete=models.SET_NULL,
        related_name="reports",
        null=True,
        blank=True,
    )
    baseline_scan = models.ForeignKey(
        BaselineScan,
        on_delete=models.SET_NULL,
        related_name="reports",
        null=True,
        blank=True,
    )
    diagnostic_session = models.ForeignKey(
        "diagnostics.DiagnosticSession",
        on_delete=models.SET_NULL,
        related_name="reports",
        null=True,
        blank=True,
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="generated_reports",
        null=True,
        blank=True,
    )
    report_type = models.CharField(max_length=40, choices=ReportType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.GENERATED)
    title = models.CharField(max_length=255)
    summary_redacted = models.TextField(blank=True)
    source_snapshot_redacted = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-generated_at", "-created_at"]
        indexes = [
            models.Index(fields=["account", "report_type", "created_at"]),
            models.Index(fields=["server", "report_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.report_type})"

    def clean(self):
        super().clean()
        if self.server_id and self.server.account_id != self.account_id:
            raise ValidationError({"server": "Server must belong to the report account."})
        if self.application_id:
            if self.application.account_id != self.account_id:
                raise ValidationError({"application": "Application must belong to the report account."})
            if self.server_id and self.application.server_id != self.server_id:
                raise ValidationError({"application": "Application must belong to the report server."})
        if self.baseline_scan_id and self.baseline_scan.account_id != self.account_id:
            raise ValidationError({"baseline_scan": "Baseline scan must belong to the report account."})
        if self.diagnostic_session_id and self.diagnostic_session.account_id != self.account_id:
            raise ValidationError({"diagnostic_session": "Diagnostic session must belong to the report account."})

    def save(self, *args, **kwargs):
        self.title = redact_secrets(self.title)[:255]
        self.summary_redacted = redact_secrets(self.summary_redacted)
        self.source_snapshot_redacted = redact_json(self.source_snapshot_redacted or {})
        super().save(*args, **kwargs)


class ReportSection(TimeStampedModel):
    class SectionType(models.TextChoices):
        SUMMARY = "summary", "Summary"
        EVIDENCE = "evidence", "Evidence"
        TIMELINE = "timeline", "Timeline"
        TOOLS_EXECUTED = "tools_executed", "Tools executed"
        FINDINGS = "findings", "Findings"
        RECOMMENDATIONS = "recommendations", "Recommendations"
        DEVELOPER_NOTES = "developer_notes", "Developer notes"

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="sections")
    section_type = models.CharField(max_length=40, choices=SectionType.choices)
    title = models.CharField(max_length=255)
    body_redacted = models.TextField(blank=True)
    data_redacted = models.JSONField(default=dict, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["report", "order", "created_at"]
        indexes = [models.Index(fields=["report", "section_type"])]

    def __str__(self):
        return f"{self.title} for {self.report_id}"

    def save(self, *args, **kwargs):
        self.title = redact_secrets(self.title)[:255]
        self.body_redacted = redact_secrets(self.body_redacted)
        self.data_redacted = redact_json(self.data_redacted or {})
        super().save(*args, **kwargs)


class FindingGroup(TimeStampedModel):
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="finding_groups")
    server = models.ForeignKey(Server, on_delete=models.PROTECT, related_name="finding_groups")
    application = models.ForeignKey(
        Application,
        on_delete=models.SET_NULL,
        related_name="finding_groups",
        null=True,
        blank=True,
    )
    latest_finding = models.ForeignKey(
        Finding,
        on_delete=models.SET_NULL,
        related_name="group_latest_for",
        null=True,
        blank=True,
    )
    fingerprint = models.CharField(max_length=255)
    normalized_fingerprint = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.INFO)
    status = models.CharField(max_length=20, choices=Finding.Status.choices, default=Finding.Status.OPEN)
    first_seen_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    occurrence_count = models.PositiveIntegerField(default=0)
    summary_redacted = models.TextField(blank=True)

    class Meta:
        ordering = ["-last_seen_at", "-created_at"]
        indexes = [
            models.Index(fields=["account", "server", "normalized_fingerprint"]),
            models.Index(fields=["account", "severity", "status"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.occurrence_count})"

    def clean(self):
        super().clean()
        if self.server_id and self.server.account_id != self.account_id:
            raise ValidationError({"server": "Server must belong to the finding group account."})
        if self.application_id:
            if self.application.account_id != self.account_id:
                raise ValidationError({"application": "Application must belong to the finding group account."})
            if self.application.server_id != self.server_id:
                raise ValidationError({"application": "Application must belong to the finding group server."})
        if self.latest_finding_id and self.latest_finding.account_id != self.account_id:
            raise ValidationError({"latest_finding": "Latest finding must belong to the finding group account."})

    def save(self, *args, **kwargs):
        self.fingerprint = redact_secrets(self.fingerprint)[:255]
        self.normalized_fingerprint = redact_secrets(self.normalized_fingerprint)[:255]
        self.title = redact_secrets(self.title)[:255]
        self.summary_redacted = redact_secrets(self.summary_redacted)
        super().save(*args, **kwargs)


class KnowledgeEntry(TimeStampedModel):
    class Scope(models.TextChoices):
        GLOBAL = "global", "Global"
        ACCOUNT = "account", "Account"
        SERVER = "server", "Server"
        APPLICATION = "application", "Application"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        ARCHIVED = "archived", "Archived"

    class Visibility(models.TextChoices):
        INTERNAL = "internal", "Internal"
        CUSTOMER_VISIBLE = "customer_visible", "Customer visible"

    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.GLOBAL)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="knowledge_entries", null=True, blank=True)
    server = models.ForeignKey(Server, on_delete=models.PROTECT, related_name="knowledge_entries", null=True, blank=True)
    application = models.ForeignKey(
        Application,
        on_delete=models.PROTECT,
        related_name="knowledge_entries",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    body_redacted = models.TextField(blank=True)
    category = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    visibility = models.CharField(max_length=30, choices=Visibility.choices, default=Visibility.INTERNAL)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_knowledge_entries",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["scope", "title"]
        indexes = [
            models.Index(fields=["scope", "status", "visibility"]),
            models.Index(fields=["account", "status", "visibility"]),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.scope == self.Scope.GLOBAL and any([self.account_id, self.server_id, self.application_id]):
            raise ValidationError({"scope": "Global knowledge entries must not be tied to tenant objects."})
        if self.scope == self.Scope.ACCOUNT and not self.account_id:
            raise ValidationError({"account": "Account scope requires an account."})
        if self.scope == self.Scope.SERVER and not self.server_id:
            raise ValidationError({"server": "Server scope requires a server."})
        if self.scope == self.Scope.APPLICATION and not self.application_id:
            raise ValidationError({"application": "Application scope requires an application."})
        if self.server_id:
            if not self.account_id:
                self.account = self.server.account
            elif self.server.account_id != self.account_id:
                raise ValidationError({"server": "Server must belong to the knowledge entry account."})
        if self.application_id:
            if not self.account_id:
                self.account = self.application.account
            if self.application.account_id != self.account_id:
                raise ValidationError({"application": "Application must belong to the knowledge entry account."})
            if self.server_id and self.application.server_id != self.server_id:
                raise ValidationError({"application": "Application must belong to the knowledge entry server."})

    def save(self, *args, **kwargs):
        self.title = redact_secrets(self.title)[:255]
        self.body_redacted = redact_secrets(self.body_redacted)
        self.category = redact_secrets(self.category)[:80]
        super().save(*args, **kwargs)


class KnowledgeSource(TimeStampedModel):
    entry = models.ForeignKey(KnowledgeEntry, on_delete=models.CASCADE, related_name="sources")
    source_type = models.CharField(max_length=80)
    source_id = models.CharField(max_length=120, blank=True)
    title_redacted = models.CharField(max_length=255, blank=True)
    summary_redacted = models.TextField(blank=True)

    class Meta:
        ordering = ["entry", "source_type", "created_at"]

    def __str__(self):
        return f"{self.source_type}:{self.source_id}"

    def save(self, *args, **kwargs):
        self.source_type = redact_secrets(self.source_type)[:80]
        self.source_id = redact_secrets(self.source_id)[:120]
        self.title_redacted = redact_secrets(self.title_redacted)[:255]
        self.summary_redacted = redact_secrets(self.summary_redacted)
        super().save(*args, **kwargs)


class Recommendation(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACCEPTED = "accepted", "Accepted"
        DISMISSED = "dismissed", "Dismissed"

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="recommendations")
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="recommendations", null=True, blank=True)
    finding = models.ForeignKey(Finding, on_delete=models.SET_NULL, related_name="recommendations", null=True, blank=True)
    server = models.ForeignKey(Server, on_delete=models.SET_NULL, related_name="recommendations", null=True, blank=True)
    application = models.ForeignKey(
        Application,
        on_delete=models.SET_NULL,
        related_name="recommendations",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    body_redacted = models.TextField(blank=True)
    priority = models.CharField(max_length=20, choices=Severity.choices, default=Severity.INFO)
    category = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_recommendations",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["account", "status", "priority"]),
            models.Index(fields=["report", "status"]),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.report_id and self.report.account_id != self.account_id:
            raise ValidationError({"report": "Report must belong to the recommendation account."})
        if self.finding_id and self.finding.account_id != self.account_id:
            raise ValidationError({"finding": "Finding must belong to the recommendation account."})
        if self.server_id and self.server.account_id != self.account_id:
            raise ValidationError({"server": "Server must belong to the recommendation account."})
        if self.application_id and self.application.account_id != self.account_id:
            raise ValidationError({"application": "Application must belong to the recommendation account."})

    def save(self, *args, **kwargs):
        self.title = redact_secrets(self.title)[:255]
        self.body_redacted = redact_secrets(self.body_redacted)
        self.category = redact_secrets(self.category)[:80]
        super().save(*args, **kwargs)
