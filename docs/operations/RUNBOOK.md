# Runbook

This runbook lists MVP operational procedures for internal pilot readiness.

## Create Matrix Admin

```powershell
python manage.py createsuperuser
```

Matrix Admin users are Django staff/superuser accounts. They are not customer roles. Staff users without `account_id` must not access the customer Portal.

## Create Customer Account and Owner

Use Django Admin:

1. Create `Account` with status `active`.
2. Create `User` linked to that Account with role `owner`.
3. Create Plan and Subscription if the account needs ToolPolicy-enabled scans or diagnostics.

## Create Server and Registration Token

Portal owner flow:

1. Login to Portal.
2. Add Server.
3. Open Server Detail.
4. Generate registration token.
5. Confirm raw token is shown once only.

Raw registration tokens are never stored. Only hashes are stored.

## Agent Registration Smoke

Mock or run Scanner Runtime registration against:

```text
POST /api/agent/register/
POST /api/agent/heartbeat/
GET  /api/agent/jobs/next/
POST /api/agent/jobs/{job_id}/result/
```

Agent tokens are raw-once and stored hashed only. Revoked, inactive, or mismatched agents must be rejected.

## Remote Bootstrap Review

Remote Bootstrap is Matrix Admin only.

Before running:

- Confirm customer approval for runtime installation.
- Confirm target host and SSH user.
- Confirm package installation checkbox.
- Confirm `BOOTSTRAP_CREDENTIAL_ENCRYPTION_KEY` is configured.

After running:

- Verify session status.
- Verify heartbeat.
- Verify credentials were cleaned: encrypted payload cleared and `destroyed_at` set.
- Review BootstrapStep errors without exposing stdout/stderr secrets.

## Baseline Scan Smoke

From Admin:

1. Start baseline for a test server.
2. Confirm required baseline tools are enabled in the active plan.
3. Confirm ToolRun and AgentJob were created through ToolPolicy.
4. Submit mocked read-only tool results.
5. Confirm Applications, DiscoveredDomain, DiscoveredService, LogSource, and Finding records are created safely.

Do not store raw logs or full `.env` files.

## Diagnostic Smoke

Portal:

1. Owner/operator starts a diagnostic session.
2. Viewer cannot start or approve.
3. Approve the next read-only step.
4. Confirm ToolRun/AgentJob is created only through Diagnostic service and ToolPolicy.
5. Confirm final report is redacted.

Telegram:

1. Link private chat with one-time code.
2. Start `/diagnose`.
3. Select server/application/problem.
4. Approve next step.
5. Check `/report` summary.

Groups must not start diagnostics or approve steps.

## Report and Finding Review

- Generate baseline, diagnostic, server health, and findings summary reports.
- Confirm reports contain redacted snapshots only.
- Confirm `AgentJob.result` and raw `ToolRun` outputs are not displayed.
- Rebuild FindingGroups when needed.
- Recommendations are advisory only and do not create ToolRun or AgentJob.

## Telegram Webhook Smoke

Mock a webhook request with:

- Correct path secret or `X-Telegram-Bot-Api-Secret-Token`.
- Invalid secret rejection.
- Linked private chat read-only commands.
- Linked group status/help only.

Telegram messages must not expose raw logs, raw `.env`, ToolRun output, AgentJob result, SSH credentials, Bootstrap credentials, tokens, passwords, or private keys.

## Secret Leak Review

Check:

- Admin detail pages.
- Portal pages.
- Telegram command responses.
- Report sections.
- Findings and knowledge entries.
- AuditLog metadata.
- Application metadata.
- Bootstrap steps.

No raw secrets should be stored or displayed.

## Incident Response Basics

If a secret leak is suspected:

1. Stop sharing affected report/message/log.
2. Rotate the affected credential or token.
3. Revoke registration/link/agent tokens if relevant.
4. Archive or restrict affected account/server if needed.
5. Record an AuditLog-safe operational note without storing the secret.

## Deferred Operations

These are not part of the MVP runbook:

- Celery/Redis workers.
- Scheduled report workers.
- PDF/email report delivery.
- Payment gateway.
- Customer Remote Bootstrap.
- Live LLM execution.
- Remediation/write/destructive actions.
