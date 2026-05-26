# Security Model

Matrix Scanner SaaS handles customer infrastructure data and eventually deploys a runtime to customer servers. Security decisions must be explicit and enforced in backend code, not just UI.

## Security Principles

- Read-only diagnostic MVP.
- No free shell execution from users, AI, Telegram, database fields, or config.
- Least privilege for Scanner Runtime where practical.
- Tenant isolation by Account on every backend path.
- Secrets are redacted before persistence and before any external presentation.
- Every sensitive action is audited.

## Tenant Isolation

Required:
- `account_id` on tenant-owned models directly or through required parents.
- Portal/API querysets scoped to the current Account.
- Object ownership checks before accessing server, application, job, finding, tool run, or report records.
- Cross-account denial tests.

Deferred:
- PostgreSQL RLS.
- Multi-account membership.
- Customer impersonation.

## Secrets

Never store plain:
- Raw registration tokens.
- Raw agent tokens.
- SSH passwords.
- Private keys.
- API keys.
- Telegram bot tokens.
- OpenAI/provider keys.
- Database passwords.
- Full Laravel `.env` files.

Redact before:
- Database storage.
- Admin display.
- Portal display.
- Telegram delivery.
- AI prompt construction.
- Report/finding creation.
- Logs.

Laravel `.env` handling:
- Use allowlisted safe keys only.
- Never store full `.env`.
- Pattern redaction is a backup, not the primary control.

## Agent Authentication

- One-time registration tokens.
- 60-minute default TTL.
- Hashed token storage.
- Raw token returned once.
- Agent tokens bound to one ScannerAgent, Server, and Account.
- Revocation support.
- Heartbeat and job endpoints reject inactive, revoked, expired, or mismatched agents.
- HTTPS required for SaaS-agent communication.

## Tool Execution

Required policy checks:
- User permission.
- Account ownership.
- Tool enabled and approved.
- Tool available in plan.
- Risk level allowed for MVP.
- Parameter schema validation.
- Canonical path validation.
- Runtime and output limits.
- Redaction before persistence/display.

Forbidden in diagnostic MVP:
- Raw command parameters.
- Shell/script parameters.
- File edits.
- Service restarts.
- Package installs.
- Permission changes.
- IP blocking.
- Git/composer actions.
- `.env` edits.

## Remote Bootstrap

Sprint 3 scope:
- Matrix Admin only.
- Install/start Scanner Runtime.
- Verify heartbeat.
- No Baseline Scan.
- No Security Preflight.

BootstrapPolicy:
- Fixed command templates only.
- Typed parameters only.
- Explicit confirmation before package install.
- Temporary encrypted credentials with TTL.
- Cleanup on success, failure, cancellation, or expiry.
- Full audit for every step.

## Telegram

- Link through short-lived Portal code.
- Use Telegram `user_id` and chat identifiers, never username.
- Groups receive alerts/summaries only in MVP.
- Private chat can later start guided diagnostics.
- Viewer cannot start diagnostic sessions.
- Telegram output must be short and secret-free.
