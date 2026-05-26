# API Contracts

This document captures API intent before implementation. Exact serializers and response shapes should be updated as endpoints are built.

## Principles

- All tenant-owned API access must enforce account ownership.
- Agent endpoints authenticate with agent token, not customer user sessions.
- Raw tokens are returned once and stored hashed only.
- Responses must never include secrets.
- Errors should be structured and safe.

## Agent Registration

```http
POST /api/agent/register/
```

Purpose: exchange a one-time registration token for a persistent agent token.

Request:
```json
{
  "registration_token": "raw-token-shown-once",
  "hostname": "server.example.com",
  "agent_version": "0.1.0"
}
```

Response:
```json
{
  "agent_id": "uuid",
  "server_id": "uuid",
  "agent_token": "raw-agent-token-shown-once",
  "poll_interval_seconds": 30
}
```

Rules:
- Registration token TTL defaults to 60 minutes.
- Registration token is one-time use.
- Registration and agent tokens are stored hashed only.

## Heartbeat

```http
POST /api/agent/heartbeat/
```

Purpose: update agent liveness and runtime metadata.

Request:
```json
{
  "agent_id": "uuid",
  "status": "online",
  "agent_version": "0.1.0"
}
```

Response:
```json
{
  "ok": true,
  "poll_interval_seconds": 30
}
```

## Next Job

```http
GET /api/agent/jobs/next/
```

Purpose: return the next pending job for the authenticated agent.

Response when job exists:
```json
{
  "job_id": "uuid",
  "tool_key": "system_identity",
  "params": {},
  "timeout_seconds": 30,
  "max_output_bytes": 65536
}
```

Response when no job exists:
```json
{
  "job": null
}
```

Rules:
- Do not return jobs for archived accounts or archived servers.
- Do not return jobs to inactive or revoked agents.

## Job Result

```http
POST /api/agent/jobs/{job_id}/result/
```

Purpose: submit structured job output.

Request:
```json
{
  "status": "succeeded",
  "started_at": "2026-05-27T00:00:00Z",
  "finished_at": "2026-05-27T00:00:05Z",
  "output": {},
  "error": null
}
```

Rules:
- Output is redacted before persistence.
- Oversized output is truncated safely.
- Job must belong to the authenticated agent.

## Portal API

Portal endpoints should be documented as they are introduced. All must be scoped to the current user's Account.
