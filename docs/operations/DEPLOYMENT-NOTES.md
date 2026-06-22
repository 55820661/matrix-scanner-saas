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
ADMIN_LIVE_AI_ENABLED=false
OPENAI_API_KEY
OPENAI_MODEL
OPENAI_CHATKIT_DOMAIN_KEY
OPENAI_TIMEOUT_SECONDS=30
OPENAI_MAX_INPUT_TOKENS=12000
OPENAI_MAX_OUTPUT_TOKENS=1000
ADMIN_LIVE_AI_RATE_LIMIT_PER_HOUR=30
```

Never commit `.env`, Telegram bot tokens, SSH credentials, API keys, database passwords, private keys, raw registration tokens, or raw agent tokens.

## Live Admin ChatKit Deployment

Live Admin AI is disabled by default and is restricted to staff-only Admin Internal Chat. It uses ChatKit Custom Server Integration; the browser calls the same-origin Django endpoint and never receives the OpenAI API key.

Register the production origin in the OpenAI domain allowlist and set its public ChatKit domain key in `OPENAI_CHATKIT_DOMAIN_KEY`. The Admin JavaScript lives under the `ai_chat` app static directory and is collected by Django automatically; do not copy it into `STATIC_ROOT` manually. Run `python manage.py collectstatic --noinput` during deployment.

Serve Django through ASGI for production SSE:

```text
uvicorn scanner_platform.asgi:application --host 127.0.0.1 --port 8000 --proxy-headers
```

WSGI can technically stream but ties up a worker for the lifetime of each response and is not the recommended Live AI deployment. Review and update the production systemd unit manually; this repository does not change a running server unit.

Apply proxy settings only to the Live AI path:

```nginx
location ~ ^/admin/internal-chat/[0-9]+/live/$ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 45s;
    proxy_send_timeout 45s;
    gzip off;
}
```

Preserve the existing forwarding headers and HTTPS configuration when merging this location into production Nginx. The proxy timeouts must remain longer than `OPENAI_TIMEOUT_SECONDS`.

If Content Security Policy is enabled at Nginx or another proxy, keep it narrow:

```text
script-src 'self' https://cdn.platform.openai.com
connect-src 'self'
```

The frontend must not connect directly to `api.openai.com`. The custom initialization script is served from local static files. Test the final CSP against Django Admin before rollout because existing Admin styles may have separate style policy requirements.

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
