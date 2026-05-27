# Current Tasks

Track active work before and after every requested implementation, repository-changing command, or multi-step operation.

## Active Task

Task:
- Sprint 1 Django SaaS Core implementation.

Scope:
- Set up Django project `scanner_platform`.
- Add PostgreSQL-ready settings, `requirements.txt`, and minimal setup notes.
- Create Sprint 1 apps: `accounts`, `servers`, `applications`, `plans`, `subscriptions`, `audit`, `core`.
- Implement Sprint 1 models only: Account, custom User, Server, Application, Plan, Subscription, AuditLog.
- Configure Django Admin for Sprint 1 models.
- Keep Matrix Admin as Django staff/superuser and customer roles as owner/operator/viewer.

Out of scope:
- Agent APIs.
- Remote Bootstrap.
- Baseline Scan.
- Scanner Runtime.
- Tool Registry.
- Policy Engine.
- Telegram.
- Diagnostic Agent.
- Celery.
- Payment gateway.
- Remediation/action features.

Immediate next steps:
- Inspect current scaffold and Python/Django availability.
- Create Django project/app files within Sprint 1 scope.
- Run Django checks and migration creation if dependencies are available.

Progress:
- Read AGENTS.md, PLANS.md, docs/CURRENT-TASKS.md, docs/DECISIONS.md, and execution plan as instructed.
- Added Django project `scanner_platform`.
- Added required Sprint 1 apps and models.
- Added Django Admin registrations.
- Added initial migrations.
- Added minimal Sprint 1 model tests.
- Updated README setup notes.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no missing migrations, with a PostgreSQL connection warning because local PostgreSQL is not running.
- `python manage.py test tests.unit --noinput` discovered 4 tests but failed before execution because no local PostgreSQL service was reachable to create a test database.
- AST syntax parsing succeeded for 49 Python files.
- No out-of-scope Sprint 2+ modules were implemented.

Completion:
- Sprint 1 implementation is complete pending commit.
- Remaining issue: rerun tests with PostgreSQL available.

## Active Task - Push Sprint 1 Commit

Task:
- Push Sprint 1 commit `508a1e6` to `origin/main`.

Scope:
- Push existing local commit only.
- Update `LOG.md` and `docs/CURRENT-TASKS.md` before and after the push.

Out of scope:
- Any code changes.
- Any new Sprint 1 implementation.

Immediate next steps:
- Push `main` to `origin/main`.

Completion:
- Pushed `main` to `origin/main`.
- Included Sprint 1 commit `508a1e6` and tracking commit `f8726de`.
- Remaining work: rerun tests when PostgreSQL is available.

## Active Task - Local Development Environment

Task:
- Prepare and verify the local development/testing environment for the current Sprint 1 Django codebase.

Scope:
- Verify `requirements.txt`.
- Add local development documentation with Windows PowerShell commands.
- Add PostgreSQL development database option via Docker Compose.
- Ensure `.env.example` covers required local variables.
- Run or document the requested setup/check/test commands.

Out of scope:
- Sprint 2.
- Agent APIs.
- Scanner Runtime.
- Remote Bootstrap.
- Baseline Scan.
- Tool Registry.
- Policy Engine.
- Telegram.
- Diagnostic Agent.
- Celery/Redis implementation.
- Business features or remediation actions.

Immediate next steps:
- Inspect current requirements and environment files.
- Add `docker-compose.dev.yml` and `docs/operations/LOCAL-DEVELOPMENT.md`.
- Run available local verification commands and record results.

Progress:
- Verified current requirements are sufficient for Sprint 1 local Django execution.
- Added Docker Compose PostgreSQL development service.
- Added Windows PowerShell local development guide.
- Updated `.env.example` for local PostgreSQL variables.
- Updated README setup notes.

Verification:
- Docker CLI and Docker Compose are installed.
- `docker compose -f docker-compose.dev.yml config` passed.
- Docker PostgreSQL startup failed because Docker Desktop Linux engine is not running.
- `python -m venv .venv` failed during `ensurepip`; partial `.venv` was removed.
- Activation command could not run because the venv was not created.
- `python -m pip install -r requirements.txt` succeeded in the user/global Python environment.
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no missing migrations, with expected PostgreSQL connection warning.
- `migrate`, `createsuperuser`, and `test` failed because PostgreSQL was unavailable.

Completion:
- Local setup documentation and Docker PostgreSQL option are in place.
- Remaining setup: start Docker Desktop or configure manual PostgreSQL, then rerun database-dependent commands.

## Active Task - Local Development Documentation Adjustment

Task:
- Adjust local development setup documentation so Docker is optional only and manual Windows PostgreSQL setup is the primary path.

Scope:
- Update `docs/operations/LOCAL-DEVELOPMENT.md`.
- Update `README.md` if needed.
- Update `.env.example` only if wording/variables need clarification.
- Update `LOG.md` and `docs/CURRENT-TASKS.md`.

Out of scope:
- Product code changes.
- Sprint 2.
- Agent APIs.
- Scanner Runtime.
- Bootstrap.
- Baseline.
- Celery/Redis.
- Removing PostgreSQL requirement.
- Commit.

Immediate next steps:
- Revise local development docs.
- Confirm Docker is documented as optional only.
- Confirm manual PostgreSQL setup is documented clearly.

Progress:
- Updated `docs/operations/LOCAL-DEVELOPMENT.md` so primary setup is local Windows PostgreSQL.
- Kept `docker-compose.dev.yml` as an optional PostgreSQL helper only.
- Updated `README.md` to state PostgreSQL is required and Docker is not mandatory.
- Left product code unchanged.

Verification:
- Confirmed docs include `Primary PostgreSQL Setup on Windows`.
- Confirmed docs include `Optional PostgreSQL via Docker Desktop`.
- Confirmed README says PostgreSQL can be local Windows PostgreSQL or optional Docker Compose.
- `git diff --check` passed.

Completion:
- Documentation adjustment complete.
- No commit was made, per instruction.

## Active Task - Fix Sprint 1 Staff User Test Fixture

Task:
- Fix only the failing Sprint 1 test `test_staff_user_without_account_has_no_customer_role`.

Scope:
- Update the test fixture to set a valid or unusable password before calling `full_clean()`.
- Run `python manage.py check`.
- Run `python manage.py makemigrations --check --dry-run`.
- Run `python manage.py test --noinput`.

Out of scope:
- Product behavior changes unless strictly necessary.
- Sprint 2.
- Agent APIs.
- Scanner Runtime.
- Bootstrap.
- Baseline.
- Tools/Policy.
- Telegram.

Immediate next steps:
- Update the test fixture only.
- Run the requested verification commands.

Progress:
- Updated only `tests/unit/test_sprint1_models.py`.
- Added `set_unusable_password()` to the staff/superuser fixture before `full_clean()`.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes detected.
- `python manage.py test --noinput` passed: 4 tests ran successfully.

Completion:
- Sprint 1 test fixture fix complete.

## Active Task - Sprint 2 Agent Registration and Job Foundation

Task:
- Implement Sprint 2 only: server agent registration, heartbeat, job polling/result endpoints, `system_identity` allowlist, `BaselineScan` skeleton, and a minimal scanner runtime prototype.

Scope:
- `ScannerAgent` as `OneToOne(Server)`.
- `AgentRegistrationToken`.
- `AgentJob` with direct `account`, `server`, and `agent`.
- `BaselineScan` model skeleton only.
- Bearer token agent authentication.
- One-time registration token with hashed storage.
- Hashed agent token storage, raw returned once.
- Atomic single-job claiming with `claimed_at` and `claim_expires_at`.
- 5 minute default claim expiry.
- Reject result submissions after terminal status.
- Temporary hardcoded allowlist containing only `system_identity`.
- 64KB structured output cap.
- Minimal runtime prototype only for register, heartbeat, poll one job, execute `system_identity`, submit result.

Out of scope:
- Systemd service.
- Install flow.
- Remote Bootstrap.
- Full Baseline Scan.
- Finding.
- Full Tool Registry.
- Full Policy Engine.
- Telegram.
- Diagnostic Agent.
- Celery.
- Remediation/actions.

Immediate next steps:
- Add Sprint 2 models and migrations.
- Add agent auth/services/views/URLs.
- Add minimal `system_identity` handler and scanner runtime prototype.
- Add focused tests for token, auth, job claiming/result behavior, allowlist, and endpoint basics.

Progress:
- Added Sprint 2 models: `ScannerAgent`, `AgentRegistrationToken`, `AgentJob`, and `BaselineScan`.
- Added hashed token helpers for registration and agent bearer tokens.
- Added agent registration, heartbeat, single-job polling, and job result endpoints under `/api/agent/`.
- Added temporary Sprint 2 allowlist containing only `system_identity`.
- Added minimal scanner runtime prototype for register, heartbeat, poll one job, execute `system_identity`, and submit result.
- Added Django Admin coverage for Sprint 2 server/agent/job/baseline models.
- Added Sprint 2 focused tests for registration tokens, bearer auth, one-job claiming, allowlist rejection, result submission, claim requirement/expiry, output size limits, cross-agent ownership, `system_identity` output, and audit token safety.

Verification:
- `python manage.py makemigrations servers` created the Sprint 2 migration.
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes detected.
- `python manage.py test --noinput` passed: 16 tests ran successfully.
- `python manage.py migrate` applied `servers.0002_agentregistrationtoken_baselinescan_scanneragent_and_more` successfully.

Completion:
- Sprint 2 implementation is complete within the locked scope.
- No Remote Bootstrap, full Baseline Scan, Finding, full Tool Registry, full Policy Engine, Telegram, Diagnostic Agent, Celery, systemd/install flow, or remediation/actions were added.

## Active Task - Sprint 3 Remote Bootstrap MVP

Task:
- Implement Sprint 3 only: Admin-only Remote Bootstrap MVP to install/start Scanner Runtime and verify heartbeat.

Scope:
- Create/use `apps/bootstrap`.
- Add `BootstrapSession`, `BootstrapStep`, `BootstrapCredential`, and `AgentInstallation`.
- Add Django Admin registrations.
- Add Admin-only synchronous bootstrap workflow with strict timeouts.
- Use Paramiko for SSH.
- Use fixed command templates, typed parameters, package allowlists, and no raw shell input.
- Encrypt temporary credentials with `BOOTSTRAP_CREDENTIAL_ENCRYPTION_KEY`.
- Use 30 minute credential TTL and cleanup on success, failure, cancellation, or expiry.
- Deploy runtime files via SFTP/tarball-style generated upload, not git clone.
- Install path `/opt/matrix_scanner`.
- Runtime config format JSON.
- systemd service `matrix-scanner-agent.service`.
- Verify agent heartbeat within 60 seconds using the Sprint 2 agent foundation.

Out of scope:
- Full Baseline Scan.
- Security Preflight.
- Diagnostic tools.
- Full Tool Registry.
- Full Policy Engine.
- Telegram.
- Diagnostic Agent.
- Celery.
- Remediation/actions.
- Customer Portal bootstrap.
- Self-install flow or install script.
- Free shell execution.

Immediate next steps:
- Add Bootstrap app models/admin/services/policy and migrations.
- Add Admin workflow hooks.
- Add focused mocked SSH/bootstrap tests.
- Run Django checks, migrations dry-run, tests, and diff check.

Progress:
- Added `apps/bootstrap`.
- Added Sprint 3 models: `BootstrapSession`, `BootstrapStep`, `BootstrapCredential`, and `AgentInstallation`.
- Added Matrix Admin-only Django Admin registrations, non-stored credential entry on session creation, and an Admin action to run selected bootstrap sessions.
- Added encrypted temporary bootstrap credential storage using `BOOTSTRAP_CREDENTIAL_ENCRYPTION_KEY`.
- Added credential TTL/cleanup helpers.
- Added fixed command template policy and package-manager allowlist handling.
- Added Paramiko SSH adapter.
- Added synchronous bootstrap workflow for SSH probe, privilege/systemd/package-manager checks, confirmed package install, runtime upload, JSON config install, systemd service install/start, and heartbeat verification.
- Added generated runtime service payload and systemd unit for `matrix-scanner-agent.service`.
- Added secret redaction helper for stored stdout/stderr/error text.
- Added Sprint 3 tests with mocked SSH paths and security regression checks.

Verification:
- Installed new local dependencies from `requirements.txt`: `paramiko` and `cryptography`.
- `python manage.py makemigrations bootstrap` created `apps/bootstrap/migrations/0001_initial.py`.
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes detected.
- `python manage.py test --noinput` passed: 27 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 3 implementation is complete within the locked scope.
- No full Baseline Scan, Security Preflight, diagnostic tools, full Tool Registry, full Policy Engine, Telegram, Diagnostic Agent, Celery, remediation/actions, customer Portal bootstrap, self-install flow, install script, or free shell execution were added.
- Changes are not committed, per instruction.

## Active Task - Sprint 4 Tool Registry and Policy Engine MVP

Task:
- Implement Sprint 4 only: Tool Registry and Policy Engine MVP.

Scope:
- Create/use `apps/tools`.
- Add `ToolTemplate`, `ToolDefinition`, `ToolPolicy`, `PlanTool`, and `ToolRun`.
- Register Sprint 4 models in Django Admin.
- Convert `system_identity` into the first registry-backed tool.
- Enforce PlanTool and deny-by-default policy checks.
- Create `ToolRun` after policy approval and before `AgentJob`.
- Update Agent result ingestion to update linked `ToolRun`.
- Keep Sprint 2 agent job flow working and keep Sprint 3 BootstrapPolicy separate/unaffected.

Out of scope:
- Full Baseline Scan.
- Baseline orchestration.
- Security Preflight.
- Diagnostic Agent.
- Telegram.
- Celery.
- Remediation/actions.
- Customer-created tools.
- Admin Tool Builder Agent.
- New diagnostic tools beyond `system_identity`.
- External JSON Schema dependency.

Immediate next steps:
- Inspect existing Plan/Subscription/AgentJob code paths.
- Add tools app models, admin, setup helper, policy service, and migrations.
- Add focused Sprint 4 tests.
- Run Django checks, migration dry-run, tests, and diff check.

Progress:
- Added `apps/tools`.
- Added Sprint 4 models: `ToolTemplate`, `ToolDefinition`, `ToolPolicy`, `PlanTool`, and `ToolRun`.
- Added Django Admin registrations for all Sprint 4 models.
- Added idempotent `system_identity` setup helper and safe data migration.
- Added PlanTool enforcement and deny-by-default policy service.
- Added internal params validator for required fields, allowed fields, primitive types, unknown param rejection, and path canonicalization.
- Added blocked-path-before-allowed-path policy checks.
- Added ToolRun creation after policy approval and before AgentJob creation.
- Added AgentJob result ingestion update for linked ToolRun with redacted results.
- Kept Sprint 2 hardcoded allowlist as temporary fallback while registry-backed tools are available.
- Kept Sprint 3 BootstrapPolicy separate and unaffected.
- Added structured JSON redaction helper.
- Added focused Sprint 4 tests.

Verification:
- `python manage.py makemigrations tools` created `apps/tools/migrations/0001_initial.py`.
- Added `apps/tools/migrations/0002_seed_system_identity.py` to seed `system_identity` idempotently.
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes detected.
- `python manage.py test --noinput` passed: 42 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 4 implementation is complete within the locked scope.
- No full Baseline Scan, Baseline orchestration, Security Preflight, Diagnostic Agent, Telegram, Celery, remediation/actions, customer-created tools, Admin Tool Builder Agent, new diagnostic tools beyond `system_identity`, or external JSON Schema dependency were added.
- Changes are not committed, per instruction.

## Active Task - Sprint 5 Baseline Scan Implementation

Task:
- Implement Sprint 5 only: Baseline Scan Implementation using the Sprint 4 Tool Registry and Policy Engine.

Scope:
- Add baseline scan orchestration service functions.
- Add `BaselineScanStep`, discovery models, and simple MVP `Finding`.
- Seed required baseline tools as registry-backed read-only tools.
- Add required read-only scanner runtime handlers only.
- Add Admin-only baseline workflow/action.
- Keep orchestration step-based and resumable through service functions.

Out of scope:
- Diagnostic Agent.
- Telegram.
- Celery.
- Remediation/actions.
- Portal UI.
- Full Security Preflight.
- Raw log ingestion.
- Raw `.env` storage.
- Free shell commands.
- Customer-created tools.
- Admin Tool Builder Agent.

Immediate next steps:
- Inspect current Sprint 2-4 models, tool policy service, runtime prototype, and admin registrations.
- Implement Sprint 5 models, orchestration, tool seeding, runtime handlers, and focused tests.
- Run Django checks, migration dry-run, tests, and diff check.

Progress:
- Expanded `BaselineScan` and added `BaselineScanStep`.
- Added discovery models: `DiscoveredService`, `DiscoveredDomain`, `LogSource`.
- Added simple MVP `Finding`.
- Added Application metadata and a uniqueness constraint for discovered application locations.
- Added baseline orchestration service functions: `start_baseline_scan`, `enqueue_next_baseline_tools`, and `ingest_completed_tool_runs`.
- Seeded required baseline tools as registry-backed read-only tools.
- Added read-only runtime handlers for required baseline tools.
- Added Admin-only baseline actions from Server and BaselineScan admin.
- Updated agent job polling to return the ToolRun timeout when a job is tied to a ToolRun.
- Added focused Sprint 5 tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 56 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 5 implementation is complete within the locked scope.
- No Diagnostic Agent, Telegram, Celery, remediation/actions, Portal UI, full Security Preflight, raw log ingestion, raw `.env` storage, free shell commands, customer-created tools, or Admin Tool Builder Agent were added.
- Changes are not committed, per instruction.
