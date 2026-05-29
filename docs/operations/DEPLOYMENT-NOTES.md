# Deployment Notes

These notes cover MVP pilot deployment preparation. They are not an automated deployment script.

## MVP Deployment Shape

Required:

- Django web application.
- PostgreSQL.
- Gunicorn or equivalent WSGI/ASGI serving process.
- Nginx or equivalent HTTPS reverse proxy.
- systemd service for the Django web process.
- Telegram webhook handled by Django.
- HTTPS for Portal, Admin, Telegram webhook, and Scanner Runtime API calls.

Deferred:

- Celery workers.
- Redis.
- Celery beat or scheduled report workers.
- PDF/email report delivery.
- Payment gateway.
- Live LLM providers.
- Remediation/write/destructive automation.

## Required Environment Variables

Set production values outside the repository:

```text
DATABASE_URL
DJANGO_SECRET_KEY
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS
DJANGO_SECURE_PROXY_SSL_HEADER=true
DJANGO_SESSION_COOKIE_SECURE=true
DJANGO_CSRF_COOKIE_SECURE=true
BOOTSTRAP_CREDENTIAL_ENCRYPTION_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
PUBLIC_BASE_URL
TOKEN_HASH_SALT
FIELD_ENCRYPTION_KEY
```

Never commit `.env`, Telegram bot tokens, SSH credentials, API keys, database passwords, private keys, raw registration tokens, or raw agent tokens.

## HTTPS and Proxy Notes

- Terminate TLS at Nginx or the hosting proxy.
- Set `DJANGO_ALLOWED_HOSTS` to production hostnames.
- Set `CSRF_TRUSTED_ORIGINS` to HTTPS origins, for example `https://scanner.example.com`.
- Enable secure cookies with `DJANGO_SESSION_COOKIE_SECURE=true` and `DJANGO_CSRF_COOKIE_SECURE=true`.
- Enable `DJANGO_SECURE_PROXY_SSL_HEADER=true` only when the proxy reliably sets `X-Forwarded-Proto`.

## Database and Migrations

Before release:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test --noinput
```

Do not squash migrations in Sprint 12. Review that all migrations are committed, ordered, and apply cleanly to a fresh PostgreSQL database.

## Logging

Configure production logs for:

- Django web requests.
- Agent API access and errors.
- Bootstrap workflow errors.
- Telegram webhook errors.
- Security/audit events.

Logs must not contain raw `.env`, raw ToolRun output, raw AgentJob output, SSH credentials, Bootstrap credentials, registration tokens, agent tokens, passwords, private keys, or Telegram bot tokens.

## Backups

Before pilot:

- Enable PostgreSQL backups.
- Test restore procedure on a non-production database.
- Protect backup storage with access controls and encryption.
- Keep `.env` and encryption keys backed up separately and securely.

## Operational Warnings

- Remote Bootstrap is Matrix Admin only and requires customer approval before runtime installation.
- The MVP is read-only advisory diagnostics and is not a replacement for a professional security audit.
- Telegram group summaries may expose operational metadata; group linking remains owner-only.
- Reports are redacted snapshots and must not be treated as raw forensic logs.
- Customer Remote Bootstrap, remediation, live LLM, scheduled jobs, PDF/email reports, and payment gateway are deferred.
