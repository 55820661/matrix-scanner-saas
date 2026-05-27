# Local Development

This guide prepares a Windows PowerShell development environment for the current Sprint 1 Django codebase.

## Scope

This setup is for the existing Django SaaS core only. It does not start Sprint 2 and does not implement agent APIs, Scanner Runtime, Bootstrap, Baseline, Tool Registry, Policy Engine, Telegram, Diagnostic Agent, Celery, Redis, payments, or remediation features.

## Requirements

- Python 3.13 or compatible Python 3.x supported by the installed Django version.
- PostgreSQL.
- Docker Desktop with Docker Compose is optional only, as a helper for PostgreSQL.

Python packages are listed in `requirements.txt`:

```text
Django
psycopg[binary]
```

## Create `.env`

From the repository root:

```powershell
Copy-Item .env.example .env
```

The default `.env.example` values match the recommended local PostgreSQL database:

```text
DATABASE_URL=postgres://matrix_scanner:matrix_scanner@localhost:5432/matrix_scanner
POSTGRES_DB=matrix_scanner
POSTGRES_USER=matrix_scanner
POSTGRES_PASSWORD=matrix_scanner
POSTGRES_PORT=5432
```

Do not commit `.env`.

## Primary PostgreSQL Setup on Windows

Install PostgreSQL locally on Windows from the official PostgreSQL installer or your preferred package manager.

After installation, open PowerShell and create the development database and user. If `psql` is not on your PATH, run it from the PostgreSQL `bin` directory, for example `C:\Program Files\PostgreSQL\16\bin\psql.exe`.

```powershell
psql -U postgres
```

Inside the `psql` prompt:

```sql
CREATE USER matrix_scanner WITH PASSWORD 'matrix_scanner';
CREATE DATABASE matrix_scanner OWNER matrix_scanner;
ALTER ROLE matrix_scanner SET client_encoding TO 'utf8';
ALTER ROLE matrix_scanner SET default_transaction_isolation TO 'read committed';
ALTER ROLE matrix_scanner SET timezone TO 'UTC';
\q
```

Confirm `.env` contains:

```text
DATABASE_URL=postgres://matrix_scanner:matrix_scanner@localhost:5432/matrix_scanner
```

Then run migrations and tests from the repository root:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py test
```

## Optional PostgreSQL via Docker Desktop

Docker is not mandatory. Use this helper only if you prefer Docker for the local PostgreSQL service.

Start Docker Desktop first and wait until the Linux engine is running.

Start PostgreSQL:

```powershell
docker compose -f docker-compose.dev.yml up -d postgres
```

Check status:

```powershell
docker compose -f docker-compose.dev.yml ps
```

The Docker service uses the same default values:

```text
database: matrix_scanner
user: matrix_scanner
password: matrix_scanner
host: localhost
port: 5432
```

Stop PostgreSQL:

```powershell
docker compose -f docker-compose.dev.yml down
```

Remove the local database volume only when you intentionally want to delete local data:

```powershell
docker compose -f docker-compose.dev.yml down -v
```

## Python Environment

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation scripts, run PowerShell as the current user and allow local scripts:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Install requirements:

```powershell
python -m pip install -r requirements.txt
```

## Django Verification Commands

Run these from the repository root after PostgreSQL is available:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py createsuperuser
python manage.py test
```

Expected behavior:
- `check` should pass without system check issues.
- `makemigrations --check --dry-run` should report no missing migrations.
- `migrate` requires a reachable PostgreSQL database.
- `createsuperuser` creates the Matrix Admin user as Django staff/superuser.
- `test` requires PostgreSQL because the project intentionally does not switch to SQLite for local tests.

## Troubleshooting

If tests fail with a PostgreSQL connection timeout, verify the local Windows PostgreSQL service is running and that `.env` has the correct `DATABASE_URL`.

To inspect Windows services from PowerShell:

```powershell
Get-Service *postgres*
```

If port `5432` is already in use, change `POSTGRES_PORT` in `.env` and update `DATABASE_URL` to match.

If using optional Docker and `docker compose` reports that `dockerDesktopLinuxEngine` cannot be found, Docker Desktop is installed but not running. Open Docker Desktop, wait for it to finish starting, then rerun:

```powershell
docker compose -f docker-compose.dev.yml up -d postgres
```

If `python -m venv .venv` fails during `ensurepip`, repair or reinstall Python with pip support enabled, then recreate the virtual environment:

```powershell
Remove-Item -Recurse -Force .venv
python -m venv .venv
```
