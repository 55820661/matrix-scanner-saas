import argparse
import json
import socket
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .baseline_tools import BASELINE_TOOL_KEYS, SYSTEMD_SERVICES_DISCOVERY_TOOL_KEY, collect_systemd_services, execute_baseline_tool
from .nginx_discovery import NGINX_SITES_DISCOVERY_TOOL_KEY, NginxDiscoveryError, collect_nginx_sites
from .safe_exec import SafeExecError
from .system_identity import SYSTEM_IDENTITY_TOOL_KEY, SystemIdentityError, collect_system_identity


AGENT_VERSION = "sprint2-prototype"


class RuntimeApiError(Exception):
    pass


def _api_url(base_url, path):
    return f"{base_url.rstrip('/')}{path}"


def _request_json(method, base_url, path, payload=None, agent_token=""):
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if agent_token:
        headers["Authorization"] = f"Bearer {agent_token}"

    request = Request(_api_url(base_url, path), data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise RuntimeApiError(f"API request failed with HTTP {exc.code}: {message}") from exc
    except URLError as exc:
        raise RuntimeApiError(f"API request failed: {exc}") from exc


def register(base_url, registration_token, hostname=None):
    return _request_json(
        "POST",
        base_url,
        "/api/agent/register/",
        {
            "registration_token": registration_token,
            "hostname": hostname or socket.gethostname(),
            "agent_version": AGENT_VERSION,
        },
    )


def heartbeat(base_url, agent_token):
    return _request_json(
        "POST",
        base_url,
        "/api/agent/heartbeat/",
        {"agent_version": AGENT_VERSION},
        agent_token=agent_token,
    )


def poll_one_job(base_url, agent_token):
    return _request_json("GET", base_url, "/api/agent/jobs/next/", agent_token=agent_token)


def execute_job(job):
    tool_key = job.get("tool_key")
    if tool_key == SYSTEM_IDENTITY_TOOL_KEY:
        try:
            return {"status": "succeeded", "output": collect_system_identity(job.get("params") or {}), "error": ""}
        except SystemIdentityError as exc:
            return {"status": "rejected", "output": {}, "error": str(exc)}

    if tool_key in BASELINE_TOOL_KEYS:
        try:
            return {"status": "succeeded", "output": execute_baseline_tool(tool_key, job.get("params") or {}), "error": ""}
        except (OSError, ValueError) as exc:
            return {"status": "failed", "output": {}, "error": str(exc)}
    if tool_key == SYSTEMD_SERVICES_DISCOVERY_TOOL_KEY:
        try:
            return {"status": "succeeded", "output": collect_systemd_services(job.get("params") or {}), "error": ""}
        except ValueError as exc:
            return {"status": "rejected", "output": {}, "error": str(exc)}
        except (OSError, SafeExecError) as exc:
            return {"status": "failed", "output": {}, "error": str(exc)}
    if tool_key == NGINX_SITES_DISCOVERY_TOOL_KEY:
        try:
            return {"status": "succeeded", "output": collect_nginx_sites(job.get("params") or {}), "error": ""}
        except ValueError as exc:
            return {"status": "rejected", "output": {}, "error": str(exc)}
        except (OSError, NginxDiscoveryError) as exc:
            return {"status": "failed", "output": {}, "error": str(exc)}

    else:
        return {"status": "rejected", "output": {}, "error": "Tool is not allowlisted by this runtime."}


def submit_result(base_url, agent_token, job_id, result):
    return _request_json(
        "POST",
        base_url,
        f"/api/agent/jobs/{job_id}/result/",
        {
            "status": result["status"],
            "output": result.get("output", {}),
            "error": result.get("error", ""),
        },
        agent_token=agent_token,
    )


def poll_execute_submit_once(base_url, agent_token):
    payload = poll_one_job(base_url, agent_token)
    job = payload.get("job")
    if not job:
        return {"job": None}
    result = execute_job(job)
    return submit_result(base_url, agent_token, job["job_id"], result)


def main():
    parser = argparse.ArgumentParser(description="Sprint 2 scanner runtime prototype.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    register_parser = subparsers.add_parser("register")
    register_parser.add_argument("--base-url", required=True)
    register_parser.add_argument("--registration-token", required=True)

    heartbeat_parser = subparsers.add_parser("heartbeat")
    heartbeat_parser.add_argument("--base-url", required=True)
    heartbeat_parser.add_argument("--agent-token", required=True)

    once_parser = subparsers.add_parser("once")
    once_parser.add_argument("--base-url", required=True)
    once_parser.add_argument("--agent-token", required=True)

    args = parser.parse_args()
    if args.command == "register":
        print(json.dumps(register(args.base_url, args.registration_token), indent=2))
    elif args.command == "heartbeat":
        print(json.dumps(heartbeat(args.base_url, args.agent_token), indent=2))
    elif args.command == "once":
        print(json.dumps(poll_execute_submit_once(args.base_url, args.agent_token), indent=2))


if __name__ == "__main__":
    main()
