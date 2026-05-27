import json
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import Account
from apps.audit.models import AuditLog
from apps.core.tokens import hash_token

from .models import AgentJob, AgentRegistrationToken, ScannerAgent, Server
from .tool_allowlist import is_allowed_tool


DEFAULT_CLAIM_EXPIRY = timedelta(minutes=5)


class AgentAuthError(Exception):
    pass


class AgentRegistrationError(Exception):
    pass


class AgentJobError(Exception):
    pass


def audit_agent_event(agent, action, result=AuditLog.Result.INFO, metadata=None, target_type="", target_id=""):
    AuditLog.objects.create(
        actor_type=AuditLog.ActorType.AGENT,
        account=agent.account if agent else None,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else "",
        result=result,
        metadata=metadata or {},
    )


def authenticate_agent_token(raw_token):
    if not raw_token:
        raise AgentAuthError("Missing agent token.")

    token_hash = hash_token(raw_token)
    try:
        agent = ScannerAgent.objects.select_related("account", "server").get(token_hash=token_hash)
    except ScannerAgent.DoesNotExist as exc:
        raise AgentAuthError("Invalid agent token.") from exc

    if not agent.is_active_for_api:
        raise AgentAuthError("Agent is not active.")
    return agent


@transaction.atomic
def register_agent(raw_registration_token, *, hostname="", agent_version=""):
    token_hash = hash_token(raw_registration_token)
    try:
        registration_token = (
            AgentRegistrationToken.objects.select_for_update()
            .select_related("account", "server")
            .get(token_hash=token_hash)
        )
    except AgentRegistrationToken.DoesNotExist as exc:
        raise AgentRegistrationError("Invalid registration token.") from exc

    if not registration_token.is_usable:
        raise AgentRegistrationError("Registration token is expired, used, or revoked.")

    server = registration_token.server
    account = registration_token.account
    if account.status != Account.Status.ACTIVE or server.status == Server.Status.ARCHIVED:
        raise AgentRegistrationError("Server is not eligible for agent registration.")

    try:
        agent = ScannerAgent.objects.select_for_update().get(server=server)
    except ScannerAgent.DoesNotExist:
        agent = ScannerAgent(server=server)
    agent.account = account
    agent.agent_version = agent_version[:50]
    agent.status = ScannerAgent.Status.ACTIVE
    agent.registered_at = timezone.now()
    agent.last_seen_at = timezone.now()
    agent.revoked_at = None
    raw_agent_token = agent.issue_token()
    agent.save()

    if hostname and not server.hostname:
        server.hostname = hostname[:255]
    server.status = Server.Status.ACTIVE
    server.agent_status = ScannerAgent.Status.ACTIVE
    server.last_seen_at = agent.last_seen_at
    server.save(update_fields=["hostname", "status", "agent_status", "last_seen_at", "updated_at"])

    registration_token.mark_used()
    audit_agent_event(
        agent,
        "agent.registered",
        result=AuditLog.Result.SUCCESS,
        metadata={"agent_version": agent.agent_version},
        target_type="ScannerAgent",
        target_id=agent.id,
    )
    return agent, raw_agent_token


def record_heartbeat(agent, *, agent_version=""):
    now = timezone.now()
    fields = ["last_seen_at", "updated_at"]
    agent.last_seen_at = now
    if agent.status == ScannerAgent.Status.OFFLINE:
        agent.status = ScannerAgent.Status.ACTIVE
        fields.append("status")
    if agent_version:
        agent.agent_version = agent_version[:50]
        fields.append("agent_version")
    agent.save(update_fields=fields)

    agent.server.agent_status = agent.status
    agent.server.last_seen_at = now
    agent.server.save(update_fields=["agent_status", "last_seen_at", "updated_at"])

    audit_agent_event(
        agent,
        "agent.heartbeat_received",
        result=AuditLog.Result.SUCCESS,
        metadata={"agent_version": agent.agent_version},
        target_type="ScannerAgent",
        target_id=agent.id,
    )


@transaction.atomic
def claim_next_job(agent):
    now = timezone.now()
    job = (
        AgentJob.objects.select_for_update(skip_locked=True)
        .filter(
            account=agent.account,
            server=agent.server,
            agent=agent,
        )
        .filter(Q(status=AgentJob.Status.PENDING) | Q(status=AgentJob.Status.CLAIMED, claim_expires_at__lt=now))
        .order_by("created_at")
        .first()
    )
    if job is None:
        return None

    if not is_allowed_tool(job.tool_key):
        job.status = AgentJob.Status.REJECTED
        job.finished_at = now
        job.error_message = "Tool is not allowlisted for Sprint 2."
        job.save(update_fields=["status", "finished_at", "error_message", "updated_at"])
        audit_agent_event(
            agent,
            "agent_job.rejected_by_policy",
            result=AuditLog.Result.DENIED,
            metadata={"tool_key": job.tool_key},
            target_type="AgentJob",
            target_id=job.id,
        )
        return None

    job.status = AgentJob.Status.CLAIMED
    job.claimed_at = now
    job.claim_expires_at = now + DEFAULT_CLAIM_EXPIRY
    job.save(update_fields=["status", "claimed_at", "claim_expires_at", "updated_at"])
    audit_agent_event(
        agent,
        "agent_job.claimed",
        result=AuditLog.Result.SUCCESS,
        metadata={"tool_key": job.tool_key},
        target_type="AgentJob",
        target_id=job.id,
    )
    return job


def serialized_size(value):
    return len(json.dumps(value, separators=(",", ":"), default=str).encode("utf-8"))


def submit_job_result(agent, job_id, *, status, output=None, error=""):
    expired_claim = False
    with transaction.atomic():
        try:
            job = (
                AgentJob.objects.select_for_update()
                .select_related("account", "server", "agent")
                .get(id=job_id, account=agent.account, server=agent.server, agent=agent)
            )
        except AgentJob.DoesNotExist as exc:
            raise AgentJobError("Job does not exist for this agent.") from exc

        if job.is_terminal:
            raise AgentJobError("Job is already in a terminal status.")

        if job.status not in {AgentJob.Status.CLAIMED, AgentJob.Status.RUNNING}:
            raise AgentJobError("Job must be claimed before result submission.")

        now = timezone.now()
        if job.claim_expires_at and job.claim_expires_at <= now:
            job.status = AgentJob.Status.TIMEOUT
            job.finished_at = now
            job.error_message = "Job claim expired before result submission."
            job.save(update_fields=["status", "finished_at", "error_message", "updated_at"])
            from apps.tools.services import update_tool_run_from_job

            update_tool_run_from_job(job)
            audit_agent_event(
                agent,
                "agent_job.claim_expired",
                result=AuditLog.Result.FAILURE,
                metadata={"tool_key": job.tool_key},
                target_type="AgentJob",
                target_id=job.id,
            )
            expired_claim = True

        if not expired_claim:
            if status not in {
                AgentJob.Status.SUCCEEDED,
                AgentJob.Status.FAILED,
                AgentJob.Status.REJECTED,
                AgentJob.Status.TIMEOUT,
            }:
                raise AgentJobError("Invalid terminal result status.")

            output = output or {}
            if serialized_size(output) > job.max_output_bytes:
                raise AgentJobError("Job result output exceeds the allowed size.")

            job.status = status
            job.result = output
            job.error_message = error[:4000]
            job.finished_at = now
            job.save(update_fields=["status", "result", "error_message", "finished_at", "updated_at"])
            from apps.tools.services import update_tool_run_from_job

            update_tool_run_from_job(job)
            audit_agent_event(
                agent,
                "agent_job.result_received",
                result=AuditLog.Result.SUCCESS if status == AgentJob.Status.SUCCEEDED else AuditLog.Result.FAILURE,
                metadata={"tool_key": job.tool_key, "job_status": status},
                target_type="AgentJob",
                target_id=job.id,
            )

    if expired_claim:
        raise AgentJobError("Job claim has expired.")
    return job
