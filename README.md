# Matrix Scanner SaaS

Matrix Scanner SaaS is a Django-based platform for read-only diagnostics of customer servers, initially focused on cPanel/WHM, Laravel, Apache/EasyApache, PHP, MySQL/MariaDB, and traditional `public_html` production environments.

The current repository state is planning and scaffolding. Implementation should follow:

- [PLANS.md](PLANS.md)
- [docs/DECISIONS.md](docs/DECISIONS.md)
- [docs/PROJECT-STRUCTURE.md](docs/PROJECT-STRUCTURE.md)
- [docs/SECURITY-MODEL.md](docs/SECURITY-MODEL.md)
- [docs/IMPLEMENTATION-CHECKLIST.md](docs/IMPLEMENTATION-CHECKLIST.md)

## MVP Rule

Read-only first. No free shell commands, no remediation, no file edits, no service restarts, and no secrets in storage, reports, AI prompts, or Telegram.

## Sprint 1 Local Setup

Detailed Windows PowerShell setup is documented in [docs/operations/LOCAL-DEVELOPMENT.md](docs/operations/LOCAL-DEVELOPMENT.md).

PostgreSQL is required. Provide it either with a local Windows PostgreSQL installation or, optionally, with Docker Compose. Docker is not mandatory.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py createsuperuser
python manage.py test
```

Configure `DATABASE_URL` in `.env` for PostgreSQL before running migrations against a real database.
