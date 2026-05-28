from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.applications.models import Application
from apps.audit.models import AuditLog
from apps.core.redaction import redact_json, redact_secrets
from apps.servers.models import Finding
from apps.tools.models import ToolRun
from apps.tools.services import ToolPolicyDenied, create_tool_run_job
from apps.tools.setup import BASELINE_TOOL_KEYS

from .models import DiagnosticDecision, DiagnosticSession, DiagnosticStep


DIAGNOSTIC_ROLES = {User.CustomerRole.OWNER, User.CustomerRole.OPERATOR}
ALLOWED_DIAGNOSTIC_TOOLS = tuple(BASELINE_TOOL_KEYS)
PROBLEM_TOOL_PLAN = {
    DiagnosticSession.ProblemType.SLOWNESS: ("system_identity", "services_status"),
    DiagnosticSession.ProblemType.HTTP_500: ("system_identity", "panel_detector", "log_sources_discovery"),
    DiagnosticSession.ProblemType.SECURITY_SCAN: ("system_identity", "webroot_risk_checker"),
    DiagnosticSession.ProblemType.LARAVEL_PRODUCTION_AUDIT: ("system_identity", "laravel_discovery", "webroot_risk_checker"),
    DiagnosticSession.ProblemType.CUSTOM: ("system_identity",),
}


class DiagnosticError(ValueError):
    pass


def user_can_start_or_approve(user):
    return user.role in DIAGNOSTIC_ROLES


def audit_diagnostic_action(*, user, action, session, result=AuditLog.Result.SUCCESS, metadata=None):
    AuditLog.objects.create(
        actor_user=user,
        actor_type=AuditLog.ActorType.USER,
        account=session.account,
        action=action,
        target_type="DiagnosticSession",
        target_id=str(session.id),
        result=result,
        metadata=metadata or {},
    )


def diagnostic_context(session):
    findings = Finding.objects.filter(account=session.account, server=session.server).order_by("-created_at")[:10]
    context = {
        "problem_type": session.problem_type,
        "server": {
            "id": str(session.server_id),
            "name": session.server.name,
            "status": session.server.status,
            "agent_status": session.server.agent_status,
        },
        "application": {
            "id": str(session.application_id or ""),
            "name": session.application.name if session.application else "",
            "framework": session.application.framework if session.application else "",
            "review_status": session.application.review_status if session.application else "",
        },
        "findings": [
            {
                "title": finding.title,
                "severity": finding.severity,
                "status": finding.status,
                "evidence_summary": finding.evidence_summary,
            }
            for finding in findings
        ],
        "available_tool_keys": list(ALLOWED_DIAGNOSTIC_TOOLS),
    }
    return redact_json(context)


def create_decision(*, session, step=None, decision_type, output=None, reasoning="", created_by_type=DiagnosticDecision.CreatedByType.DETERMINISTIC):
    return DiagnosticDecision.objects.create(
        session=session,
        step=step,
        decision_type=decision_type,
        input_context_redacted=diagnostic_context(session),
        output_json_redacted=redact_json(output or {}),
        reasoning_summary=redact_secrets(reasoning),
        created_by_type=created_by_type,
    )


def start_diagnostic_session(*, user, server, application=None, problem_type=DiagnosticSession.ProblemType.CUSTOM, user_prompt=""):
    if not user_can_start_or_approve(user):
        raise PermissionDenied("Only owners and operators can start diagnostic sessions.")
    if server.account_id != user.account_id:
        raise PermissionDenied("Server does not belong to this account.")
    if application:
        if application.account_id != user.account_id or application.server_id != server.id:
            raise ValidationError("Application must belong to the selected account and server.")

    with transaction.atomic():
        session = DiagnosticSession.objects.create(
            account=user.account,
            server=server,
            application=application,
            requested_by=user,
            status=DiagnosticSession.Status.RUNNING,
            problem_type=problem_type,
            user_prompt_redacted=redact_secrets(user_prompt)[:4000],
            summary_redacted=redact_secrets(f"Diagnostic session for {problem_type} on {server.name}")[:1000],
            max_tool_runs=10,
            started_at=timezone.now(),
        )
        plan_next_step(session)
        audit_diagnostic_action(user=user, action="portal.diagnostic.started", session=session, metadata={"server_id": str(server.id)})
    return session


def planned_tool_keys(session):
    return PROBLEM_TOOL_PLAN.get(session.problem_type, PROBLEM_TOOL_PLAN[DiagnosticSession.ProblemType.CUSTOM])


def plan_next_step(session):
    if session.status in {DiagnosticSession.Status.SUCCEEDED, DiagnosticSession.Status.FAILED, DiagnosticSession.Status.CANCELLED}:
        return None
    if session.steps.filter(status__in=[DiagnosticStep.Status.AWAITING_APPROVAL, DiagnosticStep.Status.QUEUED, DiagnosticStep.Status.RUNNING]).exists():
        return session.steps.filter(
            status__in=[DiagnosticStep.Status.AWAITING_APPROVAL, DiagnosticStep.Status.QUEUED, DiagnosticStep.Status.RUNNING]
        ).order_by("created_at").first()
    if session.tool_run_count >= session.max_tool_runs:
        return finalize_session(session, reason="Maximum diagnostic tool-run limit reached.")

    used_tools = set(session.steps.exclude(tool_key="").values_list("tool_key", flat=True))
    next_tool = next((tool_key for tool_key in planned_tool_keys(session) if tool_key in ALLOWED_DIAGNOSTIC_TOOLS and tool_key not in used_tools), None)
    if not next_tool:
        return finalize_session(session, reason="No more deterministic diagnostic steps are required.")

    step = DiagnosticStep.objects.create(
        session=session,
        status=DiagnosticStep.Status.AWAITING_APPROVAL,
        step_type=DiagnosticStep.StepType.RUN_TOOL,
        tool_key=next_tool,
        params_redacted={},
        requires_approval=True,
    )
    session.status = DiagnosticSession.Status.WAITING_FOR_APPROVAL
    session.save(update_fields=["status", "updated_at"])
    create_decision(
        session=session,
        step=step,
        decision_type=DiagnosticDecision.DecisionType.PLAN_STEP,
        output={"step_type": step.step_type, "tool_key": next_tool, "requires_approval": True},
        reasoning="Deterministic planner selected the next allowed read-only baseline tool.",
    )
    return step


def approve_diagnostic_step(*, user, session, step):
    if not user_can_start_or_approve(user):
        raise PermissionDenied("Only owners and operators can approve diagnostic steps.")
    if session.account_id != user.account_id or step.session_id != session.id:
        raise PermissionDenied("Diagnostic step does not belong to this account.")
    next_step = (
        session.steps.filter(status=DiagnosticStep.Status.AWAITING_APPROVAL, requires_approval=True)
        .order_by("created_at")
        .first()
    )
    if not next_step or next_step.id != step.id:
        raise DiagnosticError("Only the next awaiting diagnostic step can be approved.")
    if session.tool_run_count >= session.max_tool_runs:
        session.status = DiagnosticSession.Status.FAILED
        session.error_message = "Maximum diagnostic tool-run limit reached."
        session.finished_at = timezone.now()
        session.save(update_fields=["status", "error_message", "finished_at", "updated_at"])
        step.status = DiagnosticStep.Status.FAILED
        step.result_summary_redacted = "Maximum diagnostic tool-run limit reached."
        step.save(update_fields=["status", "result_summary_redacted", "updated_at"])
        return step
    if step.tool_key not in ALLOWED_DIAGNOSTIC_TOOLS:
        raise DiagnosticError("Diagnostic tool is not allowed in Sprint 8.")

    try:
        tool_run, _job = create_tool_run_job(
            account=session.account,
            server=session.server,
            tool_key=step.tool_key,
            params={},
            requested_by=user,
            requested_by_type=ToolRun.RequestedByType.USER,
        )
    except ToolPolicyDenied as exc:
        step.status = DiagnosticStep.Status.FAILED
        step.result_summary_redacted = redact_secrets(str(exc))[:1000]
        step.approved_by = user
        step.approved_at = timezone.now()
        step.save(update_fields=["status", "result_summary_redacted", "approved_by", "approved_at", "updated_at"])
        session.status = DiagnosticSession.Status.FAILED
        session.error_message = redact_secrets(str(exc))[:1000]
        session.finished_at = timezone.now()
        session.save(update_fields=["status", "error_message", "finished_at", "updated_at"])
        create_decision(
            session=session,
            step=step,
            decision_type=DiagnosticDecision.DecisionType.APPROVE_STEP,
            output={"approved": False, "reason": str(exc)},
            reasoning="ToolPolicy rejected the approved diagnostic step.",
        )
        audit_diagnostic_action(
            user=user,
            action="portal.diagnostic.step_denied",
            session=session,
            result=AuditLog.Result.DENIED,
            metadata={"step_id": str(step.id), "tool_key": step.tool_key},
        )
        return step

    step.tool_run = tool_run
    step.status = DiagnosticStep.Status.QUEUED
    step.approved_by = user
    step.approved_at = timezone.now()
    step.save(update_fields=["tool_run", "status", "approved_by", "approved_at", "updated_at"])
    session.status = DiagnosticSession.Status.RUNNING
    session.tool_run_count += 1
    session.save(update_fields=["status", "tool_run_count", "updated_at"])
    create_decision(
        session=session,
        step=step,
        decision_type=DiagnosticDecision.DecisionType.APPROVE_STEP,
        output={"approved": True, "tool_run_id": str(tool_run.id), "tool_key": step.tool_key},
        reasoning="User approval released the diagnostic step through ToolPolicy.",
        created_by_type=DiagnosticDecision.CreatedByType.SYSTEM,
    )
    audit_diagnostic_action(
        user=user,
        action="portal.diagnostic.step_approved",
        session=session,
        metadata={"step_id": str(step.id), "tool_key": step.tool_key, "run_id": str(tool_run.id)},
    )
    return step


def summarize_tool_result(tool_run):
    if tool_run.status == ToolRun.Status.SUCCEEDED:
        result = redact_json(tool_run.result_redacted or {})
        sensitive_key_parts = {"password", "secret", "token", "api_key", "apikey", "app_key", "private_key", "authorization", "bearer", "credential"}
        keys = ""
        if isinstance(result, dict):
            safe_keys = [
                str(key)
                for key in result.keys()
                if not any(part in str(key).lower() for part in sensitive_key_parts)
            ]
            keys = ", ".join(sorted(safe_keys)[:8])
        return redact_secrets(f"{tool_run.tool_definition.key} completed. Safe result keys: {keys or 'none'}.")
    if tool_run.error_message:
        return redact_secrets(tool_run.error_message)[:1000]
    return redact_secrets(f"{tool_run.tool_definition.key} ended with status {tool_run.status}.")


def sync_completed_tool_runs(session):
    changed = []
    terminal_status_map = {
        ToolRun.Status.SUCCEEDED: DiagnosticStep.Status.SUCCEEDED,
        ToolRun.Status.FAILED: DiagnosticStep.Status.FAILED,
        ToolRun.Status.REJECTED: DiagnosticStep.Status.FAILED,
        ToolRun.Status.TIMEOUT: DiagnosticStep.Status.FAILED,
        ToolRun.Status.CANCELLED: DiagnosticStep.Status.CANCELLED,
    }
    active_status_map = {
        ToolRun.Status.QUEUED: DiagnosticStep.Status.QUEUED,
        ToolRun.Status.RUNNING: DiagnosticStep.Status.RUNNING,
        ToolRun.Status.PENDING: DiagnosticStep.Status.QUEUED,
    }
    for step in session.steps.select_related("tool_run", "tool_run__tool_definition").filter(tool_run__isnull=False):
        tool_run = step.tool_run
        next_status = terminal_status_map.get(tool_run.status) or active_status_map.get(tool_run.status)
        if not next_status or step.status == next_status:
            continue
        step.status = next_status
        if next_status in terminal_status_map.values():
            step.result_summary_redacted = summarize_tool_result(tool_run)
        step.save(update_fields=["status", "result_summary_redacted", "updated_at"])
        create_decision(
            session=session,
            step=step,
            decision_type=DiagnosticDecision.DecisionType.INGEST_RESULT,
            output={"tool_key": step.tool_key, "tool_run_status": tool_run.status, "step_status": next_status},
            reasoning="Diagnostic service summarized a completed ToolRun without storing raw output.",
            created_by_type=DiagnosticDecision.CreatedByType.SYSTEM,
        )
        changed.append(step)
    if changed and all(step.status == DiagnosticStep.Status.SUCCEEDED for step in session.steps.all()):
        finalize_session(session, reason="Deterministic diagnostic steps completed.")
    elif changed and any(step.status == DiagnosticStep.Status.FAILED for step in session.steps.all()):
        session.status = DiagnosticSession.Status.FAILED
        session.error_message = "A diagnostic tool step failed."
        session.finished_at = timezone.now()
        session.save(update_fields=["status", "error_message", "finished_at", "updated_at"])
    return changed


def finalize_session(session, *, reason):
    findings = Finding.objects.filter(account=session.account, server=session.server)
    open_findings = findings.filter(status=Finding.Status.OPEN).count()
    critical_findings = findings.filter(status=Finding.Status.OPEN, severity__iexact="critical").count()
    tool_summaries = [
        redact_secrets(step.result_summary_redacted)
        for step in session.steps.order_by("created_at")
        if step.result_summary_redacted
    ]
    report = (
        f"Diagnostic report for {redact_secrets(session.server.name)}\n"
        f"Problem type: {session.problem_type}\n"
        f"Tool runs: {session.tool_run_count}/{session.max_tool_runs}\n"
        f"Open findings: {open_findings}; critical findings: {critical_findings}\n"
        f"Summary: {redact_secrets(reason)}"
    )
    if tool_summaries:
        report = f"{report}\nTool summaries:\n- " + "\n- ".join(tool_summaries[:10])
    session.final_report_redacted = redact_secrets(report)[:8000]
    session.status = DiagnosticSession.Status.SUCCEEDED
    session.finished_at = timezone.now()
    session.save(update_fields=["final_report_redacted", "status", "finished_at", "updated_at"])
    step = DiagnosticStep.objects.create(
        session=session,
        status=DiagnosticStep.Status.SUCCEEDED,
        step_type=DiagnosticStep.StepType.FINAL_REPORT,
        requires_approval=False,
        result_summary_redacted=session.final_report_redacted,
    )
    create_decision(
        session=session,
        step=step,
        decision_type=DiagnosticDecision.DecisionType.FINAL_REPORT,
        output={"status": session.status, "tool_run_count": session.tool_run_count},
        reasoning="Deterministic planner produced the final redacted diagnostic report.",
        created_by_type=DiagnosticDecision.CreatedByType.SYSTEM,
    )
    return step
