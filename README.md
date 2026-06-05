# Matrix Scanner SaaS

Matrix Scanner SaaS is a Django-based platform for read-only diagnostics of customer servers. The MVP targets cPanel/WHM, Laravel, Apache/EasyApache, PHP, MySQL/MariaDB, `public_html`, application discovery, safe findings, reports, Telegram summaries, and guided diagnostics.

The customer server runs a small Python Scanner Runtime as a systemd service. The runtime polls the SaaS platform for approved jobs, executes only registered and policy-approved read-only tools, and returns structured JSON.

## MVP Safety Rule

Read-only advisory diagnostics only.

The MVP does not provide automatic remediation, write tools, file edits, service restarts, package changes, permission changes, PDF export, email reports, scheduled reports, payment gateway, live LLM execution, or customer Remote Bootstrap.

Do not enter real secrets into prompts, descriptions, reports, knowledge entries, support notes, or test fixtures. Secrets must not appear in database storage, Admin, Portal, Telegram, reports, findings, knowledge entries, logs, or audit metadata.

Telegram group summaries can expose operational metadata. Group linking is owner-only.

## Implemented MVP Areas

- Django SaaS core: accounts, users, plans, subscriptions, servers, applications, audit.
- Agent registration, heartbeat, polling, job result submission.
- Matrix Admin Remote Bootstrap for installing and starting Scanner Runtime only.
- Tool Registry and ToolPolicy MVP.
- Baseline scan implementation using registered read-only tools.
- Customer Portal using Django templates.
- Telegram linking, read-only summaries, safe notifications, and private-chat guided diagnostics.
- Deterministic Diagnostic Agent from Portal and Telegram.
- Matrix Admin Tool Definition Proposal Builder for metadata-only read-only tool proposals.
- Reports, finding groups, advisory recommendations, and safe knowledge storage.

## Deferred

- Celery/Redis workers.
- PDF/email/scheduled reports.
- Payment gateway.
- Customer Remote Bootstrap.
- Live LLM execution.
- Remediation/write/destructive tools.
- PostgreSQL RLS.
- Multi-account membership.
- Full self-install automation.
- Advanced knowledge matching.

## Documentation

- [docs/planning/ROADMAP-CORRECTION.md](docs/planning/ROADMAP-CORRECTION.md) - approved corrected roadmap reference.
- [docs/planning/CORRECTED-EXECUTION-PLAN.md](docs/planning/CORRECTED-EXECUTION-PLAN.md) - top execution reference after the roadmap correction.
- [docs/planning/DECISION-REGISTER.md](docs/planning/DECISION-REGISTER.md) - official decision reference for corrected-plan sprints.
- [PLANS.md](PLANS.md)
- [docs/DECISIONS.md](docs/DECISIONS.md)
- [docs/SECURITY-MODEL.md](docs/SECURITY-MODEL.md)
- [docs/TEST-PLAN.md](docs/TEST-PLAN.md)
- [docs/operations/LOCAL-DEVELOPMENT.md](docs/operations/LOCAL-DEVELOPMENT.md)
- [docs/operations/DEPLOYMENT-NOTES.md](docs/operations/DEPLOYMENT-NOTES.md)
- [docs/operations/RUNBOOK.md](docs/operations/RUNBOOK.md)
- [docs/operations/RELEASE-CHECKLIST.md](docs/operations/RELEASE-CHECKLIST.md)

## Local Setup

PostgreSQL is required. Use a local Windows PostgreSQL installation as the primary path, or optional Docker Compose for PostgreSQL only.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py createsuperuser
python manage.py test --noinput
```

Configure `DATABASE_URL`, `DJANGO_SECRET_KEY`, `BOOTSTRAP_CREDENTIAL_ENCRYPTION_KEY`, `TELEGRAM_WEBHOOK_SECRET`, and production host/HTTPS settings in `.env`. Never commit `.env`.
