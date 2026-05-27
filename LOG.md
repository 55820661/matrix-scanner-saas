# Log

Operational notes for repository work. Update this file before and after every requested implementation, repository-changing command, or multi-step operation.

## 2026-05-27 - Documentation and Scaffolding Commit Preparation

Intent:
- Add required task-tracking guidance to `AGENTS.md`.
- Create `LOG.md` and `docs/CURRENT-TASKS.md`.
- Commit and push the planning, skills, documentation, and scaffold structure created for Matrix Scanner SaaS.

Scope:
- Documentation and project scaffolding only.
- No Sprint 1 implementation code.
- No Django models, migrations, agent APIs, bootstrap, baseline, Telegram, or Diagnostic Agent implementation.

Result before commit:
- Added planning, decision, security, data model, API contract, environment, testing, and sprint-spec documentation.
- Added scaffold directories with `.gitkeep` files only.
- Added required task-tracking rule to `AGENTS.md`.
- Created `LOG.md` and `docs/CURRENT-TASKS.md`.
- Staged intended repository files for commit.
- No tests were run because this change is documentation and scaffolding only.

Result after commit and push:
- Created commit `34ce9bc` with message `docs: add planning docs and project scaffold`.
- Pushed `main` to `origin/main`.
- Follow-up task-tracking update recorded in this file and `docs/CURRENT-TASKS.md`.

## 2026-05-27 - Sprint 1 Start

Intent:
- Implement Sprint 1 only: Django SaaS core foundation, PostgreSQL-ready settings, requirements, Sprint 1 apps, Sprint 1 models, and Django Admin registrations.

Scope:
- Project `scanner_platform`.
- Apps: `accounts`, `servers`, `applications`, `plans`, `subscriptions`, `audit`, `core`.
- Models: Account, custom User, Server, Application, Plan, Subscription, AuditLog.
- No agent APIs, Scanner Runtime, Remote Bootstrap, Baseline Scan, Tool Registry, Policy Engine, Telegram, Diagnostic Agent, Celery, payment gateway, or remediation.

Pre-start:
- Read required planning and decision files.
- Updated `docs/CURRENT-TASKS.md` before implementation.

Result:
- Added Django project `scanner_platform`.
- Added PostgreSQL-ready settings with local `.env` loading and default PostgreSQL `DATABASE_URL`.
- Added `requirements.txt` with Django and psycopg.
- Added Sprint 1 apps and models only: Account, custom User, Server, Application, Plan, Subscription, AuditLog.
- Added Django Admin registrations with list displays, filters, and search fields.
- Added initial migrations for all Sprint 1 models.
- Added minimal Sprint 1 model tests.
- Updated README setup notes.

Verification:
- Installed requirements with network approval after the first sandboxed pip attempt could not reach package versions.
- `python manage.py check` passed with no issues.
- `python manage.py makemigrations --check --dry-run` reported no missing migrations. It emitted a PostgreSQL connection warning because no local PostgreSQL service is available at `localhost:5432`.
- `python manage.py test tests.unit --noinput` discovered 4 tests but failed before running them because Django could not create a PostgreSQL test database without a running local PostgreSQL service.
- Parsed 49 Python files successfully with an AST syntax check.
- Confirmed no out-of-scope modules such as agent APIs, bootstrap, baseline, Tool Registry, Policy Engine, Telegram, Diagnostic Agent, Celery, payment gateway, or remediation were implemented.

Remaining issue:
- Run the Django tests again once PostgreSQL is running and `DATABASE_URL` points to a reachable database.

## 2026-05-27 - Push Sprint 1 Commit

Intent:
- Push existing Sprint 1 commit `508a1e6` to `origin/main`.

Scope:
- Git push only.
- No code changes.

Result:
- Pushed `main` to `origin/main`.
- Remote advanced from `cb3fcd0` to `f8726de`.
- Sprint 1 implementation commit `508a1e6` is now on GitHub.

## 2026-05-27 - Local Development Environment Preparation

Intent:
- Prepare and verify local development/testing setup for the existing Sprint 1 Django codebase only.

Scope:
- Requirements review.
- Local setup documentation with Windows PowerShell commands.
- PostgreSQL dev database option via Docker Compose.
- `.env.example` review/update.
- Run or document requested setup/check/test commands.

Out of scope:
- Sprint 2 work, agent APIs, Scanner Runtime, Bootstrap, Baseline, Tool Registry, Policy Engine, Telegram, Diagnostic Agent, Celery implementation, payment gateway, product features, or remediation.

Result:
- Verified `requirements.txt` remains sufficient for the current Sprint 1 Django codebase: Django and psycopg.
- Added `docker-compose.dev.yml` with a PostgreSQL 16 development service.
- Added `docs/operations/LOCAL-DEVELOPMENT.md` with Windows PowerShell setup commands, Docker PostgreSQL setup, manual PostgreSQL alternative, and troubleshooting.
- Updated `.env.example` with local PostgreSQL variables and removed unused Celery/Redis variables from the current local setup.
- Updated README to point to the local development guide and include the PowerShell setup flow.

Verification:
- `docker --version` and `docker compose version` are installed.
- `docker compose -f docker-compose.dev.yml config` passed.
- `docker compose -f docker-compose.dev.yml up -d postgres` failed because Docker Desktop Linux engine is not running.
- `python -m venv .venv` failed during `ensurepip`; the partial `.venv` was removed.
- `.\.venv\Scripts\Activate.ps1` could not run because the venv was not created successfully.
- `python -m pip install -r requirements.txt` succeeded using the user/global Python environment; requirements were already satisfied.
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no missing migrations, with the expected PostgreSQL connection warning because no database was reachable.
- `python manage.py migrate --noinput`, `python manage.py createsuperuser --noinput --username admin --email admin@example.com`, and `python manage.py test --noinput` failed because PostgreSQL was unavailable.

Remaining setup:
- Start Docker Desktop or configure manual PostgreSQL, then rerun migrate, createsuperuser, and tests.

## 2026-05-27 - Local Development Documentation Adjustment

Intent:
- Clarify local development setup so manual Windows PostgreSQL is the primary path and Docker Compose is optional only.

Scope:
- Documentation and environment setup text only.
- No product code changes.
- No Sprint 2 work.
- No Celery/Redis additions.
- PostgreSQL remains required.

Result:
- Updated local development docs to make Windows PostgreSQL the primary/manual path.
- Kept Docker Compose as an optional PostgreSQL helper only.
- Updated README to state PostgreSQL is required and Docker is not mandatory.
- No product code changed.

Verification:
- Verified documentation contains manual Windows PostgreSQL setup steps: install PostgreSQL, create user/database, set `DATABASE_URL`, run migrations and tests.
- Verified Docker section is titled optional and says Docker Desktop must be running with the Linux engine.
- `git diff --check` passed.
- No commit made.

## 2026-05-27 - Sprint 1 Test Fixture Fix

Intent:
- Fix the failing Sprint 1 staff-user test by giving the test user a valid/unusable password before `full_clean()`.

Scope:
- Test fixture only unless a product-code change is strictly necessary.
- No Sprint 2 work.
- No agent, Scanner Runtime, Bootstrap, Baseline, Tool Registry, Policy Engine, Telegram, or Diagnostic Agent work.

Result:
- Updated only the Sprint 1 test fixture.
- The staff/superuser test now calls `set_unusable_password()` before `full_clean()`.
- No product behavior changed.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes detected.
- `python manage.py test --noinput` passed: 4 tests ran successfully.
