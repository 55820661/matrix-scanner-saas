# Release Checklist

Use this checklist before the internal MVP pilot.

## Local Verification

- [ ] `python manage.py check`
- [ ] `python manage.py makemigrations --check --dry-run`
- [ ] `python manage.py migrate`
- [ ] `python manage.py test --noinput`
- [ ] `git diff --check`
- [ ] Working tree contains only approved release changes.

## Environment Variables

- [ ] `DATABASE_URL`
- [ ] `DJANGO_SECRET_KEY`
- [ ] `DJANGO_DEBUG=false`
- [ ] `DJANGO_ALLOWED_HOSTS`
- [ ] `CSRF_TRUSTED_ORIGINS`
- [ ] `DJANGO_SECURE_PROXY_SSL_HEADER=true` when behind a trusted HTTPS proxy.
- [ ] `DJANGO_SESSION_COOKIE_SECURE=true`
- [ ] `DJANGO_CSRF_COOKIE_SECURE=true`
- [ ] `BOOTSTRAP_CREDENTIAL_ENCRYPTION_KEY`
- [ ] `TELEGRAM_BOT_TOKEN`
- [ ] `TELEGRAM_WEBHOOK_SECRET`
- [ ] `PUBLIC_BASE_URL`
- [ ] `TOKEN_HASH_SALT`
- [ ] `FIELD_ENCRYPTION_KEY`

## Database and Migrations

- [ ] All migrations are committed.
- [ ] Migration order is correct.
- [ ] Fresh PostgreSQL migrate succeeds.
- [ ] No migration squashing in Sprint 12.
- [ ] PostgreSQL backup and restore procedure is documented.

## Admin Smoke Checks

- [ ] Matrix Admin can log in.
- [ ] Account/User/Server can be created.
- [ ] Remote Bootstrap pages are Admin-only.
- [ ] Tool Builder pages are Admin-only.
- [ ] Tool registry approval/enabling remains Admin-only.
- [ ] KnowledgeEntry editing remains Admin-only.
- [ ] `AgentJob.result` raw output is not displayed.
- [ ] AuditLog metadata contains no secrets.

## Portal Smoke Checks

- [ ] Customer owner can log in.
- [ ] Staff user without account is blocked from Portal.
- [ ] Viewer cannot POST application/finding/diagnostic/report actions.
- [ ] Owner can add server.
- [ ] Registration token raw value is shown once only.
- [ ] Portal does not expose Remote Bootstrap.
- [ ] Portal does not expose Tool Builder.
- [ ] Portal does not display raw logs, raw `.env`, credentials, raw ToolRun output, or raw AgentJob output.
- [ ] Cross-account URL IDs are denied or return 404.

## Agent API Smoke Checks

- [ ] Mock registration token can register an agent once.
- [ ] Reused, revoked, or expired registration token is rejected.
- [ ] Agent heartbeat requires valid active agent token.
- [ ] Inactive/revoked agent token is rejected.
- [ ] Agent job poll returns only jobs for that agent/account/server.
- [ ] Terminal AgentJob rejects repeated result submission.

## Baseline, ToolPolicy, and Diagnostics

- [ ] Baseline required tools are enabled in the active plan.
- [ ] ToolPolicy denial happens before ToolRun/AgentJob creation.
- [ ] Baseline creates only read-only ToolRuns/AgentJobs through ToolPolicy.
- [ ] Diagnostic approval creates ToolRun/AgentJob only through Diagnostic service and ToolPolicy.
- [ ] Final diagnostic report is redacted.

## Telegram Webhook Mock Checks

- [ ] Webhook secret path/header validation accepts valid secret.
- [ ] Invalid webhook secret is rejected.
- [ ] Unlinked chat receives linking/help only.
- [ ] Revoked/expired Telegram link token is rejected.
- [ ] Private chat diagnostics require owner/operator.
- [ ] Viewer cannot start or approve diagnostics.
- [ ] Groups receive summaries/alerts only and cannot diagnose.
- [ ] Telegram responses are concise and secret-free.

## Security and Redaction

- [ ] Registration tokens stored hashed only.
- [ ] Agent tokens stored hashed only.
- [ ] Telegram link tokens stored hashed only.
- [ ] Telegram bot token stored only in environment.
- [ ] Bootstrap credentials are encrypted temporarily and cleaned up.
- [ ] SSH credentials are not logged or displayed.
- [ ] ToolRun/AgentJob outputs are redacted before display/report/Telegram.
- [ ] Laravel `.env` handling is allowlist-only.
- [ ] Reports, findings, knowledge entries, and recommendations contain no raw secrets.

## Deployment Warnings

- [ ] HTTPS is configured.
- [ ] Secure cookies are enabled in production.
- [ ] Nginx/proxy forwarding is trusted before enabling proxy SSL header.
- [ ] Logs and backups are protected.
- [ ] Customer approval is obtained before runtime/bootstrap installation.
- [ ] MVP is read-only advisory diagnostics and not a professional security audit replacement.
- [ ] Telegram group summaries may expose operational metadata; group linking is owner-only.

## Deferred Features

- [ ] Celery/Redis workers are deferred.
- [ ] PDF/email/scheduled reports are deferred.
- [ ] Payment gateway is deferred.
- [ ] Customer Remote Bootstrap is deferred.
- [ ] Live LLM execution is deferred.
- [ ] Remediation/write/destructive tools are deferred.
- [ ] PostgreSQL RLS is deferred.
- [ ] Multi-account membership is deferred.
- [ ] Full self-install automation is deferred.
- [ ] Advanced knowledge matching is deferred.
