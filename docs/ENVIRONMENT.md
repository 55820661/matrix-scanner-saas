# Environment Setup

This document describes the intended local development environment. It is preparatory documentation; implementation will add exact commands as the Django project is created.

## Required Services

- Python 3.12 or newer, unless the implementation pins a different version.
- PostgreSQL.
- Redis.

## Environment Variables

Start from `.env.example` and create a local `.env` file. Never commit `.env`.

Important variables:
- `DJANGO_SETTINGS_MODULE`
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `TOKEN_HASH_SALT`
- `FIELD_ENCRYPTION_KEY`
- `PUBLIC_BASE_URL`
- `AGENT_REGISTRATION_TOKEN_TTL_MINUTES`

Integration variables are optional until their sprint:
- `TELEGRAM_BOT_TOKEN`
- `OPENAI_API_KEY`

## Local Development Rules

- Use PostgreSQL for development once Sprint 1 starts; do not build around SQLite assumptions.
- Keep secrets in `.env` or local secret storage only.
- Do not use real customer logs, `.env` files, SSH credentials, tokens, or private keys as fixtures.
- Keep Redis available before implementing Celery-dependent behavior.

## Expected Future Commands

These commands are placeholders until the Django project exists:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py test
python manage.py runserver
```

Celery commands will be added when background jobs are introduced.
