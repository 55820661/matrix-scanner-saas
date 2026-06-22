# Matrix Scanner SaaS

Matrix Scanner SaaS is a Django-based platform for read-only diagnostics of customer servers. The MVP targets cPanel/WHM, Laravel, Apache/EasyApache, PHP, MySQL/MariaDB, `public_html`, application discovery, safe findings, reports, Telegram summaries, and guided diagnostics.

The customer server runs a small Python Scanner Runtime as a systemd service. The runtime polls the SaaS platform for approved jobs, executes only registered and policy-approved read-only tools, and returns structured JSON.

## Current State

The project is at an advanced MVP stage before broader pilot expansion. The corrected C1-C9 path is complete, and the first Matrix/Siyaq internal pilot was completed manually.

The current implementation includes the Safe Context Builder, staff-only Admin Internal Chat, Portal Customer Chat, policy-backed Tool Orchestrator, argv-only safe `command_template` runtime, Admin-only Tool Builder proposals, and self-service customer-safe Portal reports. Chat-generated reports use redaction and readable summaries rather than raw logs or raw ToolRun/AgentJob output. The Runtime/Agent and Matrix Admin Remote Bootstrap foundation support the approved polling and job execution path.

C10.5 and C10.5-B completed the Admin/Portal responsibility split and internal chat UX. The Laravel/Apache/Innvii pilot is deferred. Live AI and the C11 Telegram interface have not started; the next proposed sprint is C10.6 Live Admin AI Chatbot MVP inside Admin Internal Chat only.

Before Live AI, Safe Context now enforces a structured hard byte cap and provides a second-redacted, allowlisted AI-ready payload. Raw logs, environment data, ToolRun/AgentJob outputs, credentials, and execution behavior are excluded from that payload.

Staff-only Admin Internal Chat now includes a disabled-by-default ChatKit Custom Server mode with same-origin streaming, safe persistence, rate limiting, and deterministic fallback. Enabling it requires explicit server-side OpenAI and ASGI/Nginx configuration; Portal and Telegram remain deterministic and unchanged.

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
- Safe Context Builder and deterministic chat responses.
- Separate staff-only Admin Internal Chat and Portal Customer Chat.
- Policy-backed chat tool requests and safe `command_template` execution.
- Admin-only Tool Builder proposal flow and self-service safe Portal reports.

## Deferred

- Celery/Redis workers.
- PDF/email/scheduled reports.
- Payment gateway.
- Customer Remote Bootstrap.
- Live LLM execution; C10.6 is proposed but not implemented.
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
