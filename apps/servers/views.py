import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import AgentJob
logger = logging.getLogger(__name__)

from .services import (
    AgentAuthError,
    AgentJobError,
    AgentRegistrationError,
    authenticate_agent_token,
    claim_next_job,
    record_heartbeat,
    register_agent,
    submit_job_result,
)


def parse_json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return None


def bearer_token_from_request(request):
    header = request.headers.get("Authorization", "")
    prefix = "Bearer "
    if not header.startswith(prefix):
        return ""
    return header[len(prefix) :].strip()


def authenticate_request_agent(request):
    return authenticate_agent_token(bearer_token_from_request(request))


@csrf_exempt
@require_POST
def register(request):
    payload = parse_json_body(request)
    if payload is None:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    raw_token = payload.get("registration_token", "")
    if not raw_token:
        return JsonResponse({"error": "registration_token is required."}, status=400)

    try:
        agent, raw_agent_token = register_agent(
            raw_token,
            hostname=payload.get("hostname", ""),
            agent_version=payload.get("agent_version", ""),
        )
    except AgentRegistrationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse(
        {
            "agent_id": str(agent.id),
            "server_id": str(agent.server_id),
            "agent_token": raw_agent_token,
            "poll_interval_seconds": 30,
        },
        status=201,
    )


@csrf_exempt
@require_POST
def heartbeat(request):
    payload = parse_json_body(request)
    if payload is None:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    try:
        agent = authenticate_request_agent(request)
    except AgentAuthError as exc:
        return JsonResponse({"error": str(exc)}, status=401)

    record_heartbeat(agent, agent_version=payload.get("agent_version", ""))
    return JsonResponse({"ok": True, "poll_interval_seconds": 30})


@csrf_exempt
@require_GET
def next_job(request):
    try:
        agent = authenticate_request_agent(request)
    except AgentAuthError as exc:
        return JsonResponse({"error": str(exc)}, status=401)

    job = claim_next_job(agent)
    if job is None:
        return JsonResponse({"job": None})

    timeout_seconds = 30
    try:
        timeout_seconds = job.tool_run.timeout_seconds
    except Exception:
        pass

    return JsonResponse(
        {
            "job": {
                "job_id": str(job.id),
                "tool_key": job.tool_key,
                "params": job.params,
                "timeout_seconds": timeout_seconds,
                "max_output_bytes": job.max_output_bytes,
                "claim_expires_at": job.claim_expires_at.isoformat() if job.claim_expires_at else None,
            }
        }
    )


@csrf_exempt
@require_POST
def job_result(request, job_id):
    payload = parse_json_body(request)
    if payload is None:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    try:
        agent = authenticate_request_agent(request)
        job = submit_job_result(
            agent,
            job_id,
            status=payload.get("status", AgentJob.Status.SUCCEEDED),
            output=payload.get("output", {}),
            error=payload.get("error") or "",
        )
    except AgentAuthError as exc:
        return JsonResponse({"error": str(exc)}, status=401)
    except AgentJobError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    try:
        from .baseline import ingest_completed_tool_runs

        tool_run = getattr(job, "tool_run", None)
        baseline_step = getattr(tool_run, "baseline_step", None) if tool_run else None
        if baseline_step:
            ingest_completed_tool_runs(baseline_step.baseline_scan)
    except Exception:
        logger.exception("Failed to ingest baseline scan after agent job result.")

    return JsonResponse({"ok": True, "job_id": str(job.id), "status": job.status})
