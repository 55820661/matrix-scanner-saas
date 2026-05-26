# Matrix Scanner SaaS Security Skill

## Purpose
Use this skill when implementing tenant isolation, agent authentication, remote bootstrap, tool execution, Diagnostic Agent routing, Telegram auth, config handling, logging, or future approved-fix behavior.

## Security Model
- Diagnostic MVP is read-only and suggest-only.
- Customer users cannot execute free-form commands, edit files, restart services, install packages, change permissions, block IPs, or run remediation.
- The Scanner Runtime should run with the least privilege that still permits the planned read-only checks.
- Remote Bootstrap is Matrix Admin only and is not a customer-facing diagnostic capability.
- Matrix Admin is Django staff/superuser, not a customer role.
- Customer roles are only `owner`, `operator`, and `viewer`.
- Telegram identity must use `user_id` and chat identifiers, never username.
- Unauthorized API, Portal, Admin, agent, or Telegram actions are denied and audited with minimal safe metadata.

## Tenant Isolation
- Every tenant-owned model must be scoped by `account_id` directly or through a parent object.
- Never trust `server_id`, `application_id`, `job_id`, or `tool_run_id` without confirming account ownership.
- Portal and API queries must filter by the current account on the backend.
- Matrix Admin views must be clearly separated from customer Portal behavior.
- PostgreSQL RLS is deferred; ORM-level scoping, object ownership checks, and regression tests are mandatory in MVP.
- Cross-account access attempts should be denied and audited.

## Agent Authentication
- Agent registration uses a one-time, short-lived registration token.
- Raw registration and agent tokens are shown only once and stored only as hashes.
- Agent tokens are bound to exactly one ScannerAgent, Server, and Account.
- Support revocation and rotation.
- Heartbeat and job endpoints must reject inactive, revoked, or mismatched agents.
- Use HTTPS only for SaaS-agent communication.

## Remote Bootstrap
- Sprint 3 bootstrap installs and starts the Scanner Runtime and verifies heartbeat only.
- Baseline Scan runs in the following sprint, and Security Preflight is deferred.
- Prefer temporary SSH keys over passwords.
- If a password or private key is accepted, store it only encrypted with a short TTL.
- Delete bootstrap credentials after success, failure, cancellation, or expiry.
- Bootstrap tools may write install files and systemd units, but only through fixed tool templates with typed parameters.
- Sprint 3 must include a minimal BootstrapPolicy: fixed command templates only, typed parameters only, Matrix Admin only, explicit confirmation before package install, credential TTL, and full audit.
- Require explicit Matrix Admin confirmation before package installation or privileged system changes.
- Never log raw SSH credentials, private keys, registration tokens, or config secrets.

## Tool Execution Rules
- No free-form shell commands from Portal, Telegram, Diagnostic Agent, AI, config, or database fields.
- No dynamic handler imports from database values.
- ToolTemplate code is the executable boundary.
- ToolDefinition database rows can configure typed parameters and metadata, but cannot introduce new executable behavior.
- Every tool has:
  - risk level: `read_only`, future `low_risk_action`, `sensitive_action`, or `forbidden`.
  - max runtime.
  - max output size.
  - allowed roles.
  - input schema.
  - output schema.
  - ToolRun and AuditLog records.
- Path parameters must be canonicalized and limited to baseline-discovered or explicitly allowed paths.

## Secrets
- Store platform secrets only in environment variables or approved secret storage.
- Store bootstrap credentials only encrypted and temporarily.
- Do not store Telegram bot tokens, API keys, database passwords, OpenAI keys, raw agent tokens, SSH passwords, or private keys in plain database fields.
- Do not include secrets in Admin, Portal, Telegram, AI prompts, reports, findings, alerts, tool output, or command logs.
- Redact before storage and before display.
- Redact before AI prompts and Telegram delivery.
- Prefer allowlists for `.env` parsing; pattern-based redaction is a backup, not the primary defense.
- Laravel `.env` handling must use allowlisted safe keys only and must never store the full `.env`.

## Future Approved-fix Requirements
Approved-fix mode is out of MVP. When added later, it requires:
- explicit confirmation flow.
- short-lived confirmation codes.
- strict service/action allowlist.
- minimal sudoers rules if OS privileges are needed.
- full audit trail.
- no destructive file operations by default.

## Review Checklist
- Can an unauthorized user trigger any handler?
- Can the Diagnostic Agent bypass policy or create an AgentJob directly?
- Can DB content cause new executable behavior?
- Can one account access another account's server, app, job, finding, or report?
- Are agent tokens hashed, revocable, and bound to the correct server?
- Are bootstrap credentials encrypted, time-limited, and destroyed?
- Are errors and outputs sanitized?
- Are permission failures reported safely?
