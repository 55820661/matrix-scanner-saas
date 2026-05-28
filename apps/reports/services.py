from collections import defaultdict

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.core.redaction import redact_json, redact_secrets
from apps.diagnostics.models import DiagnosticSession
from apps.servers.models import BaselineScan, BaselineScanStep, Finding, Server

from .models import FindingGroup, KnowledgeEntry, Recommendation, Report, ReportSection, Severity


SEVERITY_ORDER = {
    Severity.CRITICAL: 5,
    Severity.HIGH: 4,
    Severity.MEDIUM: 3,
    Severity.LOW: 2,
    Severity.INFO: 1,
}
ADVISORY_FORBIDDEN_WORDS = (
    "run ",
    "execute ",
    "restart ",
    "install ",
    "delete ",
    "remove ",
    "chmod ",
    "chown ",
    "edit ",
    "write ",
    "apply ",
    "fix button",
    "command",
)


def safe_text(value, limit=8000):
    return redact_secrets(value or "")[:limit]


def safe_json(value):
    return redact_json(value or {})


def normalize_fingerprint(value):
    return safe_text(value or "unknown", limit=255).strip().lower()


def normalize_severity(value):
    normalized = str(value or "").lower()
    return normalized if normalized in Severity.values else Severity.INFO


def severity_max(values):
    severities = [normalize_severity(value) for value in values]
    return max(severities or [Severity.INFO], key=lambda item: SEVERITY_ORDER.get(item, 0))


def audit_report_action(*, user=None, account=None, action, target=None, result=AuditLog.Result.SUCCESS, metadata=None):
    AuditLog.objects.create(
        actor_user=user,
        actor_type=AuditLog.ActorType.ADMIN if user and user.is_staff else AuditLog.ActorType.USER if user else AuditLog.ActorType.SYSTEM,
        account=account,
        action=action,
        target_type=target.__class__.__name__ if target else "",
        target_id=str(target.id) if target else "",
        result=result,
        metadata=metadata or {},
    )


def report_section(report, *, section_type, title, body="", data=None, order=0):
    return ReportSection.objects.create(
        report=report,
        section_type=section_type,
        title=safe_text(title, 255),
        body_redacted=safe_text(body),
        data_redacted=safe_json(data or {}),
        order=order,
    )


def recommendation_text_for_finding(finding):
    title = f"Review {finding.title}"
    body = (
        "Advisory only: review the evidence summary and confirm the risk in your normal operational workflow. "
        "Do not perform automated changes from this report."
    )
    return safe_text(title, 255), safe_text(body)


def create_recommendation(*, report, finding=None, server=None, application=None, created_by=None, title="", body="", priority=Severity.INFO, category="general"):
    if finding and not title:
        title, body = recommendation_text_for_finding(finding)
        priority = normalize_severity(finding.severity)
        category = "finding_review"
    combined = f"{title} {body}".lower()
    if any(word in combined for word in ADVISORY_FORBIDDEN_WORDS):
        body = "Advisory only: review this issue manually. Automated actions are not available in the MVP."
    return Recommendation.objects.create(
        account=report.account,
        report=report,
        finding=finding,
        server=server or report.server,
        application=application or (finding.application if finding else report.application),
        title=safe_text(title, 255),
        body_redacted=safe_text(body),
        priority=normalize_severity(priority),
        category=safe_text(category, 80),
        created_by=created_by,
    )


def rebuild_finding_groups(*, account=None, server=None):
    findings = Finding.objects.select_related("account", "server", "application").order_by("created_at")
    if account:
        findings = findings.filter(account=account)
    if server:
        findings = findings.filter(server=server)

    buckets = defaultdict(list)
    for finding in findings:
        key = (
            finding.account_id,
            finding.server_id,
            finding.application_id or 0,
            normalize_fingerprint(finding.fingerprint),
        )
        buckets[key].append(finding)

    groups = []
    with transaction.atomic():
        for (_account_id, _server_id, application_key, fingerprint), group_findings in buckets.items():
            latest = max(group_findings, key=lambda item: item.created_at)
            first = min(group_findings, key=lambda item: item.created_at)
            status = Finding.Status.OPEN if any(item.status == Finding.Status.OPEN for item in group_findings) else latest.status
            severity = severity_max(item.severity for item in group_findings)
            existing = FindingGroup.objects.filter(
                account=latest.account,
                server=latest.server,
                normalized_fingerprint=fingerprint,
                application_id=None if application_key == 0 else application_key,
            ).first()
            defaults = {
                "application": latest.application,
                "latest_finding": latest,
                "fingerprint": safe_text(latest.fingerprint, 255),
                "title": safe_text(latest.title, 255),
                "severity": severity,
                "status": status,
                "first_seen_at": first.created_at,
                "last_seen_at": latest.created_at,
                "occurrence_count": len(group_findings),
                "summary_redacted": safe_text(latest.evidence_summary or latest.description),
            }
            if existing:
                for field, value in defaults.items():
                    setattr(existing, field, value)
                existing.save()
                group = existing
            else:
                group = FindingGroup.objects.create(
                    account=latest.account,
                    server=latest.server,
                    normalized_fingerprint=fingerprint,
                    **defaults,
                )
            groups.append(group)
    return groups


def safe_finding_rows(findings):
    return [
        {
            "title": safe_text(finding.title, 255),
            "severity": normalize_severity(finding.severity),
            "status": finding.status,
            "server": safe_text(finding.server.name, 255),
            "application": safe_text(finding.application.name, 255) if finding.application else "",
            "evidence_summary": safe_text(finding.evidence_summary, 1000),
        }
        for finding in findings
    ]


def safe_tool_step_rows(steps):
    rows = []
    for step in steps:
        tool_name = ""
        if getattr(step, "tool_run", None) and step.tool_run and step.tool_run.tool_definition_id:
            tool_name = step.tool_run.tool_definition.name
        rows.append(
            {
                "step_key": safe_text(getattr(step, "step_key", "") or getattr(step, "tool_key", ""), 120),
                "tool_name": safe_text(tool_name, 160),
                "status": step.status,
                "started_at": str(getattr(step, "started_at", "") or ""),
                "finished_at": str(getattr(step, "finished_at", "") or ""),
                "summary": safe_text(getattr(step, "summary", "") or getattr(step, "result_summary_redacted", ""), 1000),
                "error": safe_text(getattr(step, "error_message", ""), 1000),
            }
        )
    return rows


def create_baseline_report(scan, *, user=None):
    scan = BaselineScan.objects.select_related("account", "server").get(id=scan.id)
    findings = Finding.objects.select_related("server", "application").filter(account=scan.account, baseline_scan=scan)
    steps = scan.steps.select_related("tool_run", "tool_run__tool_definition").order_by("created_at")
    summary = safe_json(scan.summary)
    title = f"Baseline report for {scan.server.name}"
    report = Report.objects.create(
        account=scan.account,
        server=scan.server,
        baseline_scan=scan,
        generated_by=user,
        report_type=Report.ReportType.BASELINE,
        title=safe_text(title, 255),
        summary_redacted=safe_text(
            f"Baseline {scan.status}. Services: {summary.get('services', 0)}; domains: {summary.get('domains', 0)}; "
            f"applications: {summary.get('applications', 0)}; findings: {summary.get('findings', findings.count())}."
        ),
        source_snapshot_redacted={
            "baseline_scan_id": str(scan.id),
            "status": scan.status,
            "summary": summary,
        },
        generated_at=timezone.now(),
    )
    report_section(report, section_type=ReportSection.SectionType.SUMMARY, title="Summary", body=report.summary_redacted, data=summary, order=10)
    report_section(
        report,
        section_type=ReportSection.SectionType.TOOLS_EXECUTED,
        title="Tools executed",
        body="Read-only baseline tool step summary.",
        data={"steps": safe_tool_step_rows(steps)},
        order=20,
    )
    report_section(
        report,
        section_type=ReportSection.SectionType.FINDINGS,
        title="Findings",
        body=f"{findings.count()} finding(s) recorded in this baseline.",
        data={"findings": safe_finding_rows(findings[:25])},
        order=30,
    )
    for finding in findings.filter(status=Finding.Status.OPEN).order_by("-created_at")[:5]:
        create_recommendation(report=report, finding=finding, created_by=user)
    audit_report_action(user=user, account=scan.account, action="reports.baseline.generated", target=report, metadata={"scan_id": str(scan.id)})
    return report


def create_diagnostic_report(session, *, user=None):
    session = DiagnosticSession.objects.select_related("account", "server", "application").get(id=session.id)
    steps = session.steps.select_related("tool_run", "tool_run__tool_definition").order_by("created_at")
    report = Report.objects.create(
        account=session.account,
        server=session.server,
        application=session.application,
        diagnostic_session=session,
        generated_by=user,
        report_type=Report.ReportType.DIAGNOSTIC,
        title=safe_text(f"Diagnostic report for {session.server.name}", 255),
        summary_redacted=safe_text(session.summary_redacted or session.final_report_redacted or f"Diagnostic session {session.status}."),
        source_snapshot_redacted={
            "diagnostic_session_id": str(session.id),
            "status": session.status,
            "problem_type": session.problem_type,
            "tool_run_count": session.tool_run_count,
        },
        generated_at=timezone.now(),
    )
    report_section(
        report,
        section_type=ReportSection.SectionType.SUMMARY,
        title="Diagnostic summary",
        body=safe_text(session.final_report_redacted or session.summary_redacted),
        data={"status": session.status, "problem_type": session.problem_type},
        order=10,
    )
    report_section(
        report,
        section_type=ReportSection.SectionType.TOOLS_EXECUTED,
        title="Tool step summaries",
        body="Read-only diagnostic tool status and summaries.",
        data={"steps": safe_tool_step_rows(steps)},
        order=20,
    )
    findings = Finding.objects.select_related("server", "application").filter(account=session.account, server=session.server).order_by("-created_at")
    report_section(
        report,
        section_type=ReportSection.SectionType.FINDINGS,
        title="Related findings",
        body="Latest related findings for the diagnostic scope.",
        data={"findings": safe_finding_rows(findings[:10])},
        order=30,
    )
    for finding in findings.filter(status=Finding.Status.OPEN)[:5]:
        create_recommendation(report=report, finding=finding, created_by=user)
    audit_report_action(user=user, account=session.account, action="reports.diagnostic.generated", target=report, metadata={"session_id": str(session.id)})
    return report


def create_server_health_summary(server, *, user=None):
    findings = Finding.objects.select_related("server", "application").filter(account=server.account, server=server)
    open_findings = findings.filter(status=Finding.Status.OPEN)
    latest_baseline = BaselineScan.objects.filter(account=server.account, server=server).order_by("-created_at").first()
    report = Report.objects.create(
        account=server.account,
        server=server,
        baseline_scan=latest_baseline,
        generated_by=user,
        report_type=Report.ReportType.SERVER_HEALTH,
        title=safe_text(f"Server health summary for {server.name}", 255),
        summary_redacted=safe_text(
            f"Server {server.status}; agent {server.agent_status or 'unknown'}; open findings {open_findings.count()}."
        ),
        source_snapshot_redacted={
            "server_id": str(server.id),
            "server_status": server.status,
            "agent_status": server.agent_status,
            "open_findings": open_findings.count(),
        },
        generated_at=timezone.now(),
    )
    report_section(report, section_type=ReportSection.SectionType.SUMMARY, title="Server summary", body=report.summary_redacted, order=10)
    report_section(
        report,
        section_type=ReportSection.SectionType.FINDINGS,
        title="Open findings",
        body=f"{open_findings.count()} open finding(s).",
        data={"findings": safe_finding_rows(open_findings.order_by("-created_at")[:25])},
        order=20,
    )
    audit_report_action(user=user, account=server.account, action="reports.server_health.generated", target=report, metadata={"server_id": str(server.id)})
    return report


def create_findings_summary(account, *, user=None, server=None):
    groups = rebuild_finding_groups(account=account, server=server)
    group_qs = FindingGroup.objects.select_related("server", "application").filter(account=account)
    if server:
        group_qs = group_qs.filter(server=server)
    grouped_counts = group_qs.values("severity", "status").annotate(count=Count("id"))
    report = Report.objects.create(
        account=account,
        server=server,
        generated_by=user,
        report_type=Report.ReportType.FINDINGS,
        title=safe_text(f"Findings summary for {server.name}" if server else f"Findings summary for {account.name}", 255),
        summary_redacted=safe_text(f"{group_qs.count()} grouped finding(s)."),
        source_snapshot_redacted={"group_count": group_qs.count(), "counts": list(grouped_counts)},
        generated_at=timezone.now(),
    )
    report_section(
        report,
        section_type=ReportSection.SectionType.FINDINGS,
        title="Finding groups",
        body=report.summary_redacted,
        data={
            "groups": [
                {
                    "title": safe_text(group.title, 255),
                    "severity": group.severity,
                    "status": group.status,
                    "server": safe_text(group.server.name, 255),
                    "application": safe_text(group.application.name, 255) if group.application else "",
                    "occurrence_count": group.occurrence_count,
                    "summary": safe_text(group.summary_redacted, 1000),
                }
                for group in group_qs.order_by("-last_seen_at")[:50]
            ]
        },
        order=10,
    )
    audit_report_action(user=user, account=account, action="reports.findings.generated", target=report, metadata={"server_id": str(server.id) if server else "", "rebuilt_groups": len(groups)})
    return report


def visible_knowledge_for_account(account):
    return KnowledgeEntry.objects.filter(
        account=account,
        status=KnowledgeEntry.Status.APPROVED,
        visibility=KnowledgeEntry.Visibility.CUSTOMER_VISIBLE,
    )


def telegram_latest_report_summary(chat_link):
    qs = Report.objects.filter(account=chat_link.account).select_related("server").order_by("-generated_at", "-created_at")
    if chat_link.server_id:
        qs = qs.filter(server_id=chat_link.server_id)
    report = qs.first()
    if not report:
        return "No reports are available for this account yet."
    return safe_text(
        f"Latest report: {report.title}\n"
        f"- Type: {report.report_type}\n"
        f"- Generated: {report.generated_at or report.created_at}\n"
        f"- Summary: {report.summary_redacted[:500]}",
        1000,
    )
