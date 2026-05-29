# Test Plan

Testing focuses on safety boundaries, tenant isolation, deterministic execution, and release readiness.

## Test Levels

Unit tests:

- model validation
- token hashing/expiry/revocation
- redaction helpers
- ToolPolicy checks
- deterministic service behavior
- safe report/Telegram summaries

Integration tests:

- Portal account scoping
- agent registration, heartbeat, polling, and result submission
- bootstrap state transitions with SSH mocked
- baseline orchestration through ToolPolicy
- diagnostics through ToolPolicy
- Telegram webhook and callback handling with mocked updates

Security regression tests:

- cross-account access denial
- staff/customer separation
- viewer POST denial
- raw token non-storage
- revoked/expired token denial
- Bootstrap credential cleanup
- ToolPolicy denial before ToolRun/AgentJob creation
- AgentJob terminal double-submit rejection
- no raw AgentJob/ToolRun output in Portal/Admin/Telegram/reports
- AuditLog metadata secret scanning
- `.env.example` required variable coverage

## Release Verification Commands

Run before every Sprint 12 completion report:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test --noinput
git diff --check
```

## Manual Smoke Coverage

- Admin login.
- Portal login.
- Create Account, owner User, and Server.
- Registration token raw value shown once.
- Mocked agent registration, heartbeat, job polling, and job result.
- Baseline/report/diagnostic happy path.
- Mocked Telegram webhook secret validation.
- Telegram private chat diagnostics require owner/operator.
- Telegram groups remain summaries/alerts only.

## Required Security Checks

Tenant isolation:

- Portal.
- Telegram.
- Diagnostics.
- Reports.
- Tools.
- Baseline.
- Bootstrap.

Permissions:

- owner.
- operator.
- viewer.
- staff/superuser.
- Matrix Admin-only flows.

Secret handling:

- registration tokens.
- agent tokens.
- bootstrap credentials.
- Telegram bot token.
- Telegram link tokens.
- SSH credentials.
- ToolRun/AgentJob outputs.
- `.env`.
- logs.
- AuditLog metadata.

Redaction before:

- database storage.
- Portal display.
- Admin display.
- Telegram messages.
- reports.
- findings.
- knowledge entries.
- audit logs.

## Fixtures

Use sanitized fixtures only:

- Apache logs.
- cPanel userdata.
- Laravel directory structures.
- Laravel logs.
- PHP-FPM config snippets.
- MySQL status output.
- Agent JSON outputs.

Never commit real customer logs, `.env` files, credentials, tokens, private keys, or API responses containing secrets.

## Deferred Test Areas

Do not add tests for unimplemented product workflows in Sprint 12:

- Celery/Redis workers.
- PDF/email/scheduled reports.
- payment gateway.
- customer Remote Bootstrap.
- live LLM execution.
- remediation/write/destructive tools.
- PostgreSQL RLS.
- multi-account membership.
- full self-install automation.
- advanced knowledge matching.
