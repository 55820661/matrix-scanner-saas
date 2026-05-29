# Local Development

This guide prepares a Windows PowerShell development environment for the Matrix Scanner SaaS MVP.

## Requirements

- Python 3.13 or compatible Python 3.x supported by Django.
- PostgreSQL.
- Docker Desktop is optional only as a helper for PostgreSQL.

Do not switch the project to SQLite. Local tests intentionally run against PostgreSQL.

## Create `.env`

From the repository root:

```powershell
Copy-Item .env.example .env
```

Set or confirm:

```text
DATABASE_URL=postgres://matrix_scanner:matrix_scanner@localhost:5432/matrix_scanner
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000
BOOTSTRAP_CREDENTIAL_ENCRYPTION_KEY=change-me-to-a-long-random-bootstrap-key
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=change-me-to-a-random-webhook-secret
PUBLIC_BASE_URL=http://localhost:8000
```

Do not commit `.env`.

## Primary PostgreSQL Setup on Windows

Install PostgreSQL locally on Windows. If `psql` is not on your PATH, run it from the PostgreSQL `bin` directory, for example:

```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres
```

Inside `psql`:

```sql
CREATE USER matrix_scanner WITH PASSWORD 'matrix_scanner';
CREATE DATABASE matrix_scanner OWNER matrix_scanner;
ALTER ROLE matrix_scanner SET client_encoding TO 'utf8';
ALTER ROLE matrix_scanner SET default_transaction_isolation TO 'read committed';
ALTER ROLE matrix_scanner SET timezone TO 'UTC';
\q
```

## Optional PostgreSQL via Docker Desktop

Docker is not mandatory. Use this only if you prefer Docker for local PostgreSQL.

Docker Desktop must be running with the Linux engine.

```powershell
docker compose -f docker-compose.dev.yml up -d postgres
docker compose -f docker-compose.dev.yml ps
```

Stop the local PostgreSQL helper:

```powershell
docker compose -f docker-compose.dev.yml down
```

Delete local Docker database data only when intentional:

```powershell
docker compose -f docker-compose.dev.yml down -v
```

## Python Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation scripts:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Local Verification

Run from the repository root after PostgreSQL is available:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py createsuperuser
python manage.py test --noinput
git diff --check
```

Expected behavior:

- `check` passes without system check issues.
- `makemigrations --check --dry-run` reports no missing migrations.
- `migrate` applies all committed migrations to PostgreSQL.
- `createsuperuser` creates a Matrix Admin staff/superuser.
- `test --noinput` passes against PostgreSQL.
- `git diff --check` has no whitespace errors. Windows line-ending warnings are acceptable.

## Local Smoke Checks

- Admin login at `/admin/`.
- Portal login at `/portal/login/`.
- Create Account, owner User, and Server.
- Generate a registration token from Portal and confirm the raw token is shown once.
- Mock agent registration, heartbeat, job polling, and job result submission.
- Run or inspect baseline/report/diagnostic happy paths with test data.
- Mock Telegram webhook with the configured secret.

## MVP Boundaries

Local development must not introduce:

- Celery/Redis implementation.
- Remediation/actions.
- Write/destructive tools.
- Live LLM calls.
- PDF/email/scheduled reports.
- Payment gateway.
- Customer Remote Bootstrap.
