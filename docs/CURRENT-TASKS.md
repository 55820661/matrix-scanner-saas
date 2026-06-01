# Current Tasks

Track active work before and after every requested implementation, repository-changing command, or multi-step operation.

## Active Task - Phase 2 Sprint 2.11A Ingestion

Task:
- Implement only Phase 2 services, domains, and log source ingestion plus scan-scoped summary counts.

Scope:
- Map Phase 2 service discovery outputs into `DiscoveredService`.
- Map `nginx_sites_discovery.domains[]` into `DiscoveredDomain`.
- Map `log_sources_discovery_v2.log_sources[]` into `LogSource`.
- Keep ingestion safe, redacted, tolerant of malformed output, and metadata-capped.
- Make `summarize_scan()` scan-scoped for models that already support `baseline_scan`.

Out of scope:
- Application ingestion.
- `Application.baseline_scan` migration.
- Report redesign.
- AI planner.
- External bot.
- ToolPolicy/PlanTool changes.
- Runtime tool changes.
- Findings generation from Phase 2.
- Remediation/write actions.

Immediate next steps:
- Update `apps/servers/baseline.py` ingestion mapping.
- Add focused `tests/unit/test_phase2_baseline_ingestion.py`.
- Run the requested verification commands.

Progress:
- Added Phase 2 services ingestion into `DiscoveredService`.
- Added Phase 2 Nginx domain ingestion into `DiscoveredDomain`.
- Added Phase 2 log source ingestion into `LogSource`.
- Added safe metadata selection, redaction, caps, and merge behavior.
- Updated scan summaries to count scan-scoped services, domains, log sources, and findings.
- Kept applications at `0` until the deferred application ingestion sprint.
- Added focused Phase 2 baseline ingestion tests and updated the Sprint 5 Phase 2 expectation.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_baseline_ingestion --noinput` passed: 10 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 285 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.11A implementation is complete within the approved scope.
- No Application ingestion/migration/report/AI/tool activation/runtime/remediation changes were added.
- No commit or push was made.

## Active Task - Phase 2 Sprint 2.10 Pilot Tool Enablement

Task:
- Implement only the Sprint 2.10 management command/helper for safe Phase 2 pilot tool enablement.

Scope:
- Add `enable_phase2_pilot_tools --plan-id <PLAN_ID>` with dry-run support.
- Enable only Phase 2 discovery tools required by `debian_nginx_opt`.
- Scope PlanTool creation/update to the selected plan only.
- Keep customer execution disabled for these tools.
- Add focused tests for safety, scoping, and baseline preflight readiness.

Out of scope:
- Migrations.
- Admin UI.
- Customer Portal behavior.
- Automatic scan creation.
- ToolRun/AgentJob creation inside the command.
- Baseline ingestion.
- Report changes.
- AI planner.
- External bot.
- Remediation/actions.
- Global activation for all plans.

Immediate next steps:
- Add the enablement helper and management command.
- Add focused unit tests.
- Run the requested verification commands.

Progress:
- Added the Phase 2 pilot enablement helper.
- Added the `enable_phase2_pilot_tools --plan-id <PLAN_ID> [--dry-run]` management command.
- Kept dry-run write-free.
- Scoped PlanTool creation/update to the selected plan only.
- Kept customer execution disabled for Phase 2 pilot tools.
- Added focused tests for command safety, policy/plan scoping, and Debian/Nginx baseline preflight readiness.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_pilot_enablement --noinput` passed: 11 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 275 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.10 implementation is complete within the approved scope.
- No migration/Admin UI/Portal/ingestion/report/AI/external bot/remediation/global activation changes were added.
- No commit or push was made.

## Active Task - Phase 2 Sprint 2.9 Baseline Profiles

Task:
- Implement only the Sprint 2.9 baseline profile and runtime tool selection layer.

Scope:
- Add profile definitions for `legacy_cpanel`, `debian_nginx_opt`, and `minimal_linux`.
- Add `BaselineScan.profile_key` with default `legacy_cpanel`.
- Use the selected profile to decide baseline preflight and ToolRun/AgentJob creation.
- Keep default behavior identical to the current cPanel-oriented baseline.
- Add focused regression tests for profile tool selection and preflight scoping.

Out of scope:
- Phase 2 ingestion mapping.
- Report changes.
- ToolPolicy or PlanTool activation.
- AI planner.
- External bot.
- Remediation/actions.
- Customer-facing behavior changes.

Immediate next steps:
- Add profile definitions and model field migration.
- Update baseline orchestration to use selected profile tools.
- Add focused tests.
- Run the requested verification commands.

Progress:
- Added baseline profile definitions for `legacy_cpanel`, `debian_nginx_opt`, and `minimal_linux`.
- Added `BaselineScan.profile_key` with default `legacy_cpanel`.
- Updated baseline preflight and enqueue logic to use the selected profile's tool list.
- Kept default cPanel baseline behavior unchanged.
- Added a small BaselineScan Admin visibility improvement for `profile_key`.
- Added focused profile selection and preflight regression tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint5_baseline --noinput` passed: 21 tests.
- First full-suite run produced `OK` but hit the command timeout after test completion; rerun passed cleanly.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 264 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.9 implementation is complete within the approved scope.
- No ingestion/report/ToolPolicy activation/AI planner/external bot changes were added.
- No commit or push was made.

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

## Active Task - Sprint 6 Admin and Portal MVP Screens

Task:
- Implement Sprint 6 only: Admin and Portal MVP Screens.

Scope:
- Create/use `apps/portal`.
- Add a minimal customer Portal using Django templates.
- Keep Portal views/templates separate from Django Admin.
- Add Portal-safe permissions, tenant-scoped views, templates, actions, and tests.
- Improve Django Admin usability where needed.

Out of scope:
- Telegram integration.
- Diagnostic Agent.
- Celery.
- Payments gateway.
- Remediation/actions.
- Admin Tool Builder Agent.
- Advanced reporting, PDF export, or email alerts.
- Customer Remote Bootstrap.
- React/Vue.
- User invitation/role management.
- Customer baseline start.

Immediate next steps:
- Add `apps.portal` structure, URLs, permissions, forms, views, and templates.
- Wire Portal URLs into the project.
- Add focused tests for authentication, tenant isolation, role permissions, token generation, safe display, and out-of-scope route absence.
- Run Django checks, migration dry-run, tests, and diff check.

Progress:
- Added `apps.portal` with Portal app config, permissions, forms, services, URLs, and views.
- Wired `/portal/` into project URLs and added `apps.portal` to installed apps.
- Added Portal login/logout/access-denied pages separate from Django Admin UI.
- Added Portal pages for dashboard, servers, add server, server detail, registration token generation, applications, pending applications, application detail/actions, findings, finding detail/actions, baseline scans, subscription/usage, and placeholders.
- Implemented tenant-scoped Portal querysets and role checks for owner/operator/viewer.
- Implemented owner-only registration token generation with raw token shown once and AuditLog without raw token metadata.
- Added read-only baseline/subscription visibility and placeholder pages for Telegram, diagnostics, and reports.
- Added safe display for application metadata, findings, baseline summaries, and server details without raw AgentJob or ToolRun output.
- Added minimal Admin branding for Matrix Scanner Admin.
- Added focused Sprint 6 tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 72 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 6 implementation is complete within the locked scope.
- No Telegram integration, Diagnostic Agent, Celery, payments gateway, remediation/actions, Admin Tool Builder Agent, advanced reporting, PDF export, email alerts, customer Remote Bootstrap, React/Vue, user invitation/role management, or customer baseline start were added.
- Changes are not committed, per instruction.

## Active Task - Sprint 7 Telegram Integration MVP

Task:
- Implement Sprint 7 only: Telegram Integration MVP.

Scope:
- Create/use `apps/telegram_integration`.
- Add Telegram chat linking with short-lived hashed link tokens.
- Add Telegram webhook foundation using secret validation.
- Add read-only Telegram commands and safe notification records.
- Add owner-only Portal surface for Telegram link token generation.
- Keep Telegram separate from Diagnostic Agent, ToolRun, AgentJob, and remediation/actions.

Out of scope:
- Diagnostic Agent.
- Telegram Guided Diagnostics.
- DiagnosticSession creation from Telegram.
- ToolRun or AgentJob creation from Telegram.
- Remediation/actions.
- Write tools.
- Payments.
- Celery.
- Polling infrastructure.
- Per-account bot tokens.
- Customer-created tools.
- Admin Tool Builder Agent.

Immediate next steps:
- Add Telegram models, services, webhook views, URLs, Admin registration, and migrations.
- Add Portal Telegram link-token page/action.
- Add safe command formatting and notification suppression.
- Add focused tests for token safety, linking, webhook security, command scoping, notification redaction/suppression, and out-of-scope side effects.
- Run Django checks, migration dry-run, tests, and diff check.

Progress:
- Added `apps.telegram_integration` with Telegram chat links, one-time link tokens, notification records, Admin registration, webhook URL/view, and migration.
- Added global Telegram environment settings for `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_SECRET`; bot token is not stored in the database.
- Added secret-validated webhook handling for allowlisted read-only commands.
- Added Telegram chat linking with hashed one-time codes, TTL/used/revoked enforcement, private/group scope checks, and account-scoped active links.
- Added safe read-only command summaries for servers, applications, findings, account status, and latest baseline.
- Added notification record creation with redacted payloads, dedupe suppression, and an explicit Bot API delivery helper.
- Added notification event hooks for baseline completion, high/critical findings, agent offline/recovered, and bootstrap completed/failed.
- Added Portal Telegram settings page with owner/operator private link-code generation and owner-only group link-code generation.
- Added AuditLog entries for link code generation and chat link/unlink events without raw codes or secrets.
- Added focused Sprint 7 tests for token safety, linking, command scoping, webhook secret validation, notification redaction/suppression, Portal permissions, and out-of-scope side effects.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint7_telegram --noinput` passed: 13 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 85 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 7 implementation is complete within the locked scope.
- No Diagnostic Agent, Telegram Guided Diagnostics, DiagnosticSession creation, ToolRun creation, AgentJob creation, remediation/actions, write tools, payments, Celery, polling infrastructure, per-account bot tokens, customer-created tools, or Admin Tool Builder Agent were added.
- Changes are not committed, per instruction.

## Active Task - Sprint 8 Diagnostic Agent MVP

Task:
- Implement Sprint 8 only: Diagnostic Agent MVP from Portal.

Scope:
- Create/use `apps/diagnostics`.
- Add DiagnosticSession, DiagnosticStep, and DiagnosticDecision models.
- Add deterministic diagnostic planning only, with no live LLM calls.
- Add Portal-only diagnostic session list/start/detail/approval flow.
- Require approval before each tool step creates a ToolRun.
- Execute diagnostic tools only through Tool Registry and ToolPolicy.
- Produce concise redacted diagnostic reports.

Out of scope:
- Telegram Guided Diagnostics.
- Telegram diagnostic commands, messages, or approvals.
- Live LLM execution.
- Remediation/actions.
- Write tools.
- Shell/free commands.
- Celery.
- Email alerts.
- PDF export.
- Advanced reporting.
- IncidentReport.
- Customer-created tools.
- Admin Tool Builder Agent.

Immediate next steps:
- Inspect existing Portal, ToolPolicy/ToolRun, baseline, and agent job flow.
- Add diagnostics app models, services, Admin registration, Portal URLs/views/templates, and migrations.
- Add focused tests for Portal permissions, tenant scoping, deterministic planning, approval gating, policy integration, redaction, and out-of-scope side effects.
- Run Django checks, migration dry-run, full test suite, and diff check.

Progress:
- Added `apps.diagnostics` with DiagnosticSession, DiagnosticStep, and DiagnosticDecision models, Admin registrations, services, Portal views, and initial migration.
- Wired diagnostics into the Portal under `/portal/diagnostics/`, including list, start, detail, and step approval routes.
- Added Portal templates for diagnostics list, start, and detail pages.
- Implemented deterministic planning over existing baseline tool keys only.
- Enforced approval before a diagnostic tool step creates a ToolRun.
- Integrated approved steps through the existing ToolPolicy path using `create_tool_run_job`; diagnostics do not create AgentJob directly.
- Added ToolRun result synchronization into DiagnosticStep summaries and concise final reports.
- Strengthened redaction for `APP_KEY` and API key style strings before diagnostic context/report display.
- Added focused Sprint 8 tests for login, staff blocking, role permissions, tenant scoping, application ownership, approval gating, ToolPolicy denial, max tool-run limits, ToolRun/AgentJob linking, result ingestion, redaction, no Telegram side effects, and safe Portal display.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint8_diagnostics --noinput` passed: 17 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 102 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 8 implementation is complete within the locked scope.
- No Telegram Guided Diagnostics, Telegram diagnostic commands/messages/approvals, live LLM execution, remediation/actions, write tools, shell/free commands, Celery, email alerts, PDF export, advanced reporting, IncidentReport, customer-created tools, or Admin Tool Builder Agent were added.
- Changes are not committed, per instruction.

## Active Task - Sprint 9 Telegram Guided Diagnostics

Task:
- Implement Sprint 9 only: Telegram Guided Diagnostics.

Scope:
- Add private-chat-only Telegram diagnostic flow.
- Add `TelegramDiagnosticState`.
- Add Telegram diagnostic commands: `/diagnose`, `/cancel`, `/approve`, `/session`, `/report`.
- Add `callback_query` handling and inline keyboard responses with text fallback.
- Connect Telegram flow to existing diagnostics services.
- Keep ToolPolicy / ToolRun / AgentJob flow unchanged and only reached through diagnostics services.
- Keep all Telegram diagnostic output concise and redacted.

Out of scope:
- Group diagnostics.
- Remediation/actions.
- Write tools.
- Free shell commands.
- Direct AgentJob creation from Telegram.
- ToolPolicy bypass.
- Live LLM execution.
- Raw outputs or secrets in Telegram.

Immediate next steps:
- Inspect current Telegram and diagnostics services/models/webhook handling.
- Add diagnostic source fields, Telegram diagnostic state model, services, callback support, and admin registration.
- Add focused tests for private chat flow, role checks, tenant scoping, callbacks, approval replay protection, cancellation, redaction, and out-of-scope side effects.
- Run Django checks, migration dry-run, full test suite, and diff check.

Progress:
- Added `TelegramDiagnosticState` for private-chat diagnostic flow state without storing active state on `TelegramChatLink`.
- Added `DiagnosticSession.source` and nullable `source_chat_link` to distinguish Portal and Telegram sessions.
- Added Telegram diagnostic commands: `/diagnose`, `/cancel`, `/approve`, `/session`, and `/report`.
- Kept Sprint 7 read-only commands unchanged.
- Added `callback_query` handling and inline keyboard response payloads with constrained callback keys.
- Implemented private-chat-only diagnostic server, application, problem type, description, confirmation, approval, status, report, and cancellation flow.
- Enforced owner/operator-only Telegram diagnostics and blocked viewer/group diagnostics.
- Enforced one active Telegram diagnostic state per private chat with 30-minute expiry.
- Routed session creation and approval through existing diagnostics services; Telegram never creates AgentJob directly and never bypasses ToolPolicy.
- Added concise redacted Telegram diagnostic report formatting.
- Added AuditLog events for important Telegram diagnostic interactions without raw prompts, raw callbacks, raw updates, or secrets.
- Added focused Sprint 9 tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint9_telegram_diagnostics --noinput` passed: 16 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 118 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 9 implementation is complete within the locked scope.
- No group diagnostics, remediation/actions, write tools, free shell commands, direct AgentJob creation from Telegram, ToolPolicy bypass, live LLM execution, or raw outputs/secrets in Telegram were added.
- Changes are not committed, per instruction.

## Active Task - Sprint 10 Tool Definition Proposal Builder

Task:
- Implement Sprint 10 only: Matrix Admin Tool Definition Proposal Builder MVP inside `apps/tools`.

Scope:
- Add ToolBuildRequest, ToolBuildProposal, ToolBuildReview, and ToolTestResult.
- Add deterministic proposal generation and validation only.
- Add Django Admin-only review actions.
- Allow conversion of approved proposals to draft/pending_review ToolDefinition records only.
- Keep Tool Registry and ToolPolicy as the source of truth.

Out of scope:
- New Django app.
- Live LLM/provider calls.
- Runtime handler/code generation.
- Shell/free-command generation.
- Remediation/actions, write tools, destructive tools, package installs, service restarts, or file edits.
- Customer Portal tool builder.
- Automatic enablement.
- Automatic PlanTool attachment.
- ToolRun or AgentJob creation.
- Execution on customer servers.

Immediate next steps:
- Inspect current tools models, services, admin, migrations, and tests.
- Add Sprint 10 models/services/Admin actions.
- Add focused safety and Admin access tests.
- Run Django checks, migration dry-run, full test suite, and diff check.

Progress:
- Added Sprint 10 Tool Definition Proposal Builder models inside `apps/tools`.
- Added deterministic proposal generation and validation services.
- Added Admin-only proposal generation, validation, approval, rejection, and conversion actions.
- Added conversion from approved proposal to draft ToolDefinition with inactive conservative ToolPolicy.
- Added mock validation ToolTestResult records only.
- Added Sprint 10 safety and Admin access tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint10_tool_builder --noinput` passed: 14 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 132 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 10 implementation is complete within the locked scope.
- No new app, live LLM, provider calls, runtime handler/code generation, shell/free commands, remediation/actions, write/destructive tools, automatic enablement, automatic PlanTool attachment, ToolRun creation, AgentJob creation, or customer server execution were added.
- Changes are not committed, per instruction.

## Active Task - Sprint 11 Reports, Findings, and Knowledge Base Enhancement

Task:
- Implement Sprint 11 only: reports, finding groups, advisory recommendations, and safe knowledge/context storage.

Scope:
- Add Report, ReportSection, FindingGroup, KnowledgeEntry, KnowledgeSource, and Recommendation.
- Add synchronous explicit report generation from safe/redacted sources only.
- Add Admin registrations/actions for reports, report sections, finding groups, knowledge, recommendations, baseline report generation, diagnostic report generation, and finding group rebuild.
- Add Portal reports/finding group visibility and owner/operator report refresh actions with viewer read-only.
- Add small safe Telegram report summary support.

Out of scope:
- PDF export, email reports, scheduled reports, Celery/report worker, live LLM report generation, public API endpoints, remediation/actions, write tools, service restarts, package installs, file edits, ToolPolicy bypass, direct AgentJob creation, raw logs, raw `.env`, raw ToolRun output, raw AgentJob output, credentials, tokens, passwords, or private keys.

Immediate next steps:
- Inspect current Portal/Admin/report-adjacent models and routes.
- Add Sprint 11 models, services, admin actions, Portal views/templates, Telegram summary update, and tests.
- Run Django checks, migration dry-run, full test suite, and diff check.

Progress:
- Added `apps.reports` with Report, ReportSection, FindingGroup, KnowledgeEntry, KnowledgeSource, and Recommendation.
- Added synchronous redacted report generation services for baseline, diagnostic, server health, and findings summaries.
- Added finding group rebuild/deduplication and advisory-only recommendation creation.
- Added Django Admin registrations and actions for reports, report generation, and finding group rebuilds.
- Added Portal report list/detail/generation views, finding group list/detail views, findings filters, server report/group summaries, and diagnostic report links.
- Added safe Telegram `/report` fallback to the latest stored redacted report summary.
- Added Sprint 11 tests for report safety, grouping, portal tenant isolation, Admin visibility, recommendations, knowledge redaction, Telegram summaries, and out-of-scope exclusions.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 142 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 11 implementation is complete within the locked scope.
- No PDF export, email reports, scheduled reports/Celery, live LLM report generation, public API endpoints, remediation/actions, write tools, ToolPolicy bypass, direct AgentJob creation, or raw sensitive output display/storage were added.
- Changes are not committed, per instruction.

## Active Task - Sprint 12 Stabilization, Security Hardening, and Release Preparation

Task:
- Implement Sprint 12 only: final MVP stabilization, security hardening, documentation cleanup, release readiness, and regression coverage.

Scope:
- Review and harden tenant isolation, permissions, secret handling, redaction, ToolPolicy enforcement, Admin/Portal/Telegram access, settings/env coverage, migrations, and operational documentation.
- Update README, local development, deployment notes, runbook, plans, execution plan, implementation checklist, and test plan.
- Add a release checklist document.
- Add or strengthen practical security/regression tests.

Out of scope:
- New product workflows, remediation/actions, write tools, live LLM execution, Celery/Redis implementation, payment gateway, PDF export, email reports, scheduled reports, customer Remote Bootstrap, ToolPolicy bypass, and direct AgentJob creation outside existing approved flows.

Immediate next steps:
- Inspect settings, environment variables, routes, services, and existing tests for Sprint 12 hardening gaps.
- Apply narrow documentation and test/security fixes only.
- Run Django checks, migration dry-run, migrate, full test suite, and diff check.

Progress:
- Updated MVP documentation to reflect the actual implemented sprint order, Sprint 4/5 ordering, Sprint 11 actual scope, and deferred features.
- Added `docs/operations/RELEASE-CHECKLIST.md` with local verification, environment, migration, Admin, Portal, Telegram, security, tenant isolation, deployment, and deferred-feature checks.
- Updated `.env.example` with CSRF and proxy/secure cookie settings needed for production readiness review.
- Added production-aware settings for `CSRF_TRUSTED_ORIGINS`, optional proxy SSL header, and secure session/CSRF cookies.
- Hardened AuditLog metadata by redacting secret-like values before validation/storage while still rejecting secret-like metadata keys.
- Hid raw `AgentJob.result` from Django Admin detail display.
- Added Sprint 12 regression tests for env coverage, AuditLog redaction, Portal staff/viewer denial, Telegram token/callback denial, bootstrap credential cleanup, revoked agent token denial, AgentJob double-submit rejection, ToolPolicy denial before ToolRun/AgentJob, and raw AgentJob result display prevention.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint12_stabilization --noinput` passed: 11 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py migrate` passed.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 153 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 12 implementation is complete within the locked stabilization scope.
- No new product workflows, remediation/actions, write tools, live LLM execution, Celery/Redis, payment gateway, PDF/email/scheduled reporting, customer Remote Bootstrap, ToolPolicy bypass, or direct AgentJob creation outside existing approved flows were added.
- Changes are not committed, per instruction.

## Active Task - Phase 2 Sprint 2.1 Runtime Discovery Tool Contracts

Task:
- Prepare only the first Phase 2 implementation step: Runtime Discovery Tool Contracts and seeding structure for Debian/Nginx `/opt` discovery tools.

Scope:
- Pull local `main` to the deployed source-of-truth commit `762abd4`.
- Re-inspect current baseline, tools, diagnostics, and runtime code after the deployment fix.
- Add safe Tool Registry contract/seeding structure for planned Phase 2 runtime discovery tools.
- Keep the contracts non-executing until runtime handlers and baseline integration are implemented in later steps.

Out of scope:
- Runtime handler implementation.
- Baseline orchestration changes.
- UI redesign.
- External bot work.
- Live LLM work.
- Remediation/actions, write tools, free shell commands, or unsafe execution paths.

Immediate next steps:
- Add Phase 2 discovery tool specs and idempotent seeding helper.
- Add focused tests for contract safety, disabled-by-default behavior, and no ToolRun/AgentJob side effects.
- Run Django checks, migration dry-run, tests, and diff check.

Progress:
- Added Phase 2 discovery tool contract specs for Debian/Nginx `/opt` discovery tools.
- Added idempotent seeding helper that creates ToolTemplate, ToolDefinition, and inactive ToolPolicy records.
- Kept Phase 2 tools out of the current baseline and diagnostic tool sets until handlers and orchestration are implemented later.
- Added a data migration that seeds the contracts as approved/read-only but non-executable by default.
- Added focused tests for safe seeding, idempotency, baseline/diagnostic separation, and no ToolRun/AgentJob side effects.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_tool_contracts --noinput` passed: 4 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 157 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Phase 2 Sprint 2.1 contract/seeding preparation is complete.
- Runtime handlers, baseline integration, UI changes, external bot work, live LLM work, and remediation/write behavior remain out of scope and were not implemented.
- No commit or push was made.

## Active Task - Phase 2 Sprint 2.2 systemd Services Discovery

Task:
- Implement only the Sprint 2.2 runtime safe execution helper and `systemd_services_discovery` runtime handler.

Scope:
- Add `scanner_runtime/safe_exec.py`.
- Use fixed code-defined argv lists with `subprocess.run(..., shell=False)`.
- Enforce runtime command timeout and output caps.
- Capture and redact stderr safely.
- Add `systemd_services_discovery` runtime collector using fixed read-only `systemctl` commands.
- Register only this handler in the runtime executor.
- Add focused unit tests for safe execution, parsing, handler routing, param rejection, and unsupported tools.

Out of scope:
- Baseline orchestration changes.
- Baseline profiles.
- `ingest_tool_result()` changes.
- `DiscoveredService` ingestion.
- ToolPolicy or PlanTool activation.
- Migrations to enable tools.
- Other Phase 2 runtime handlers.
- AI planner, external bot, remediation/actions, shell commands, raw unit files, raw `ExecStart`, or raw `Environment=...`.

Immediate next steps:
- Add safe execution helper.
- Add systemd collector/parser.
- Register the runtime handler in `scanner_runtime/prototype.py`.
- Add tests and run requested checks.

Progress:
- Added `scanner_runtime/safe_exec.py` with fixed argv-only command execution, `shell=False`, timeout handling, output cap enforcement, and redacted stderr.
- Added `systemd_services_discovery` parser and collector using fixed read-only `systemctl` commands.
- Registered only `systemd_services_discovery` in the runtime executor path.
- Added focused tests for safe execution, timeout/output caps, parser behavior, enabled-state merge, runtime execution routing, param rejection, and unsupported tool rejection.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_systemd_discovery --noinput` passed: 12 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 171 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 2.2 implementation is complete within the approved runtime-only scope.
- No baseline orchestration, baseline profile, ingestion, ToolPolicy/PlanTool activation, enabling migration, AI planner, external bot, or remediation/write behavior was added.
- No commit or push was made.

## Active Task - Phase 2 Sprint 2.3 Nginx Sites Discovery

Task:
- Implement only the Sprint 2.3 runtime `nginx_sites_discovery` collector.

Scope:
- Add `scanner_runtime/nginx_discovery.py`.
- Read only allowlisted Nginx config sources.
- Parse Nginx `server` blocks with safe brace counting.
- Extract safe `server_name`, `listen`, `root`, `access_log`, `error_log`, and `proxy_pass` metadata.
- Reject non-empty params.
- Register only `nginx_sites_discovery` in the runtime executor.
- Add focused tests for parser behavior, path safety, symlink safety, include flagging, param rejection, and output safety.

Out of scope:
- Baseline orchestration changes.
- Baseline profile changes.
- `ingest_tool_result()` changes.
- `DiscoveredDomain`, `Application`, or `LogSource` writes.
- ToolPolicy or PlanTool activation.
- Migrations.
- Other Phase 2 runtime handlers.
- AI planner, external bot, remediation/actions, or shell command execution.

Immediate next steps:
- Add the Nginx discovery runtime module.
- Wire the handler into `scanner_runtime/prototype.py`.
- Add focused Sprint 2.3 tests.
- Run requested checks.

Progress:
- Added `scanner_runtime/nginx_discovery.py` as a pure file-reading runtime collector.
- Added allowlisted Nginx config candidate handling, safe symlink resolution checks, file size caps, and total scan cap.
- Added parser support for `server` blocks, `server_name`, `listen`, `root`, `access_log`, `error_log`, `proxy_pass`, comments, multiple domains, default servers, wildcard names, and include flagging without following includes.
- Added output safety rules for blocked paths, variable paths, credentialed/variable proxy targets, cert/key/auth directives, and raw config exclusion.
- Registered only `nginx_sites_discovery` in `scanner_runtime/prototype.py`.
- Added focused Sprint 2.3 tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_nginx_sites_discovery --noinput` passed: 12 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 185 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 2.3 implementation is complete within the approved runtime-only scope.
- No baseline orchestration, baseline profile, ingestion, ToolPolicy/PlanTool activation, migrations, AI planner, external bot, or remediation/write behavior was added.
- No commit or push was made.

## Active Task - Phase 2 Sprint 2.4 /opt Applications Discovery

Task:
- Implement only the Sprint 2.4 runtime `opt_apps_discovery` collector.

Scope:
- Add `scanner_runtime/opt_discovery.py` as a pure file-reading runtime collector for `/opt`.
- Candidate directories: `/opt/*` and `/opt/*/*` only (max depth 2), with strict caps.
- Presence-based framework detection (Django/Python, Node, Laravel/PHP) using marker files only.
- Optional safe project name extraction from size-capped:
  - `pyproject.toml`
  - `package.json`
  - `composer.json`
  Extract only project `name`; ignore all other fields.
- Reject non-empty params.
- Register only `opt_apps_discovery` in `scanner_runtime/prototype.py`.
- Add focused tests for traversal caps, symlink safety, framework detection, safe name extraction, and output safety.

Out of scope:
- Baseline orchestration changes.
- Baseline profile changes.
- `ingest_tool_result()` changes.
- Any DB writes from runtime (no `Application`, `LogSource`, or `DiscoveredDomain` writes).
- ToolPolicy or PlanTool activation.
- Migrations.
- Other Phase 2 runtime handlers.
- AI planner, external bot, remediation/actions, or shell execution.

Progress:
- Added `scanner_runtime/opt_discovery.py` with `/opt`-rooted discovery, max-depth-2 candidate scanning, strict caps, symlink validation under `/opt`, and heavy/hidden directory skipping.
- Added marker-based framework detection for Django/Python, Node, and Laravel/PHP.
- Added safe project-name extraction from size-capped `pyproject.toml`, `package.json`, and `composer.json`.
- Returned `applications` and `summary` only, with redacted strings and no raw file contents.
- Registered only `opt_apps_discovery` in `scanner_runtime/prototype.py`.
- Added focused Sprint 2.4 tests.
- Fixed empty-marker parent directories being counted as applications and deduped applications by resolved realpath.
- Corrected the `pyproject.toml` name regex to use proper whitespace matching.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected; database connection timeout warning only.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_opt_apps_discovery --noinput` passed: 13 tests ran successfully with 2 symlink tests skipped in this Windows environment.
- `.\.venv\Scripts\python.exe manage.py test --noinput` was blocked by PostgreSQL connection timeout while creating the test database.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.4 implementation is complete except for a full-suite re-run after local PostgreSQL test database connectivity is restored.
- No baseline orchestration, baseline profile, ingestion, ToolPolicy/PlanTool activation, migrations, other Phase 2 handlers, AI planner, external bot, or remediation/write behavior was added.
- No commit or push was made.

## Active Task - Phase 2 Sprint 2.5 Django Apps Discovery

Task:
- Implement only the Sprint 2.5 runtime `django_apps_discovery` collector.

Scope:
- Add `scanner_runtime/django_discovery.py` as a pure filesystem runtime collector for `/opt`.
- Candidate directories: `/opt/*` and `/opt/*/*` only (max depth 2), with strict caps.
- Detect Django roots using:
  - `manage.py`; or
  - strong project-root markers (`pyproject.toml`, `requirements.txt`, `Pipfile`, `poetry.lock`, `uv.lock`) plus Django indicators.
- Treat `wsgi.py`, `asgi.py`, `urls.py`, and `apps.py` as supporting markers only.
- Avoid nested false positives when a child package sits under an already selected Django root.
- Return only `applications` and `summary` with safe redacted metadata.
- Reject non-empty params.
- Register only `django_apps_discovery` in `scanner_runtime/prototype.py`.
- Add focused tests.

Out of scope:
- Baseline orchestration changes.
- Baseline profile changes.
- `ingest_tool_result()` changes.
- `Application` database writes.
- ToolPolicy or PlanTool activation.
- Migrations.
- Other Phase 2 runtime handlers.
- AI planner, external bot, remediation/actions, or shell execution.

Progress:
- Added `scanner_runtime/django_discovery.py` with `/opt`-rooted discovery, max-depth-2 candidate scanning, strict caps, symlink validation under `/opt`, and heavy/hidden directory skipping.
- Added Django root detection using `manage.py` or strong project-root markers plus Django indicators.
- Treated `wsgi.py`, `asgi.py`, `urls.py`, and `apps.py` as supporting markers only.
- Added nested candidate suppression so child Django packages are not emitted as standalone apps when an ancestor is already selected as a Django root.
- Returned `applications` and `summary` only, with redacted safe fields.
- Registered only `django_apps_discovery` in `scanner_runtime/prototype.py`.
- Added focused Sprint 2.5 tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_django_apps_discovery --noinput` passed: 15 tests ran successfully with 2 symlink tests skipped in this Windows environment.
- `.\.venv\Scripts\python.exe manage.py test --noinput` ran 200 tests before failing in `tests.unit.test_sprint8_diagnostics.Sprint8DiagnosticsTests.setUpClass` due to PostgreSQL connection timeout.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.5 implementation is complete except for a full-suite re-run after local PostgreSQL test database connectivity is stable.
- No baseline orchestration, baseline profile, ingestion, ToolPolicy/PlanTool activation, migrations, other Phase 2 handlers, AI planner, external bot, or remediation/write behavior was added.
- No commit or push was made.

## Active Task - Phase 2 Sprint 2.6 Gunicorn/Uvicorn Services Discovery

Task:
- Implement only the Sprint 2.6 runtime `gunicorn_uvicorn_services_discovery` collector.

Scope:
- Add `scanner_runtime/gunicorn_uvicorn_discovery.py`.
- Discovery flow:
  - Run fixed `systemctl list-units --type=service --all --no-pager --plain --no-legend`.
  - Parse safe unit names.
  - Run fixed `systemctl show <capped units> --property=Id,Description,LoadState,ActiveState,SubState,UnitFileState,MainPID,FragmentPath,User,WorkingDirectory`.
- Use `safe_exec.py` only with fixed argv and `shell=False`.
- Reject non-empty params.
- Detect `gunicorn`, `uvicorn`, `daphne` from safe fields only (Id and redacted Description).
- Return only safe contract-compatible keys: `services`, `applications`, `summary`.
- Register only `gunicorn_uvicorn_services_discovery` in `scanner_runtime/prototype.py`.
- Add focused tests for parsing and safety constraints.

Out of scope:
- Baseline orchestration/profile/ingestion changes.
- ToolPolicy or PlanTool activation.
- Migrations.
- Other runtime handlers.
- Supervisor support.
- Port correlation.
- Unit file content reads.
- `/proc/<pid>/cmdline`.
- AI planner or external bot.

Progress:
- Added `scanner_runtime/gunicorn_uvicorn_discovery.py` with fixed two-step discovery:
  - `systemctl list-units --type=service --all --no-pager --plain --no-legend`
  - capped `systemctl show <unit names> --property=Id,Description,LoadState,ActiveState,SubState,UnitFileState,MainPID,FragmentPath,User,WorkingDirectory`
- Added safe unit-name extraction and show-unit cap enforcement.
- Added service typing (`gunicorn`, `uvicorn`, `daphne`, `unknown`) from safe fields only.
- Added safe metadata shaping with `/opt`-only working directory handling, safe fragment path allowlist, and related app path inference.
- Returned only top-level keys required by the seeded contract: `services`, `applications`, `summary`.
- Registered only `gunicorn_uvicorn_services_discovery` in `scanner_runtime/prototype.py`.
- Added focused Sprint 2.6 tests.

Verification:
- `python manage.py check` failed locally because shell `python` is not bound to the project venv.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` failed for the same shell `python` reason.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected and a database timeout warning.
- `python manage.py test tests.unit.test_phase2_gunicorn_uvicorn_services_discovery --noinput` failed for the same shell `python` reason.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_gunicorn_uvicorn_services_discovery --noinput` passed: 11 tests.
- `python manage.py test --noinput` failed for the same shell `python` reason.
- `.\.venv\Scripts\python.exe manage.py test --noinput` ran 216 tests before failing in `tests.unit.test_sprint2_agent_foundation.Sprint2AgentFoundationTests.setUpClass` due to PostgreSQL connection timeout.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.6 implementation is complete except for a clean full-suite run after PostgreSQL test connectivity is stable.
- No baseline/profile/ingestion changes, ToolPolicy/PlanTool activation, migrations, other handlers, AI planner, or external bot changes were added.
- No commit or push was made.

## Active Task - Phase 2 Sprint 2.7 PostgreSQL Status Discovery

Task:
- Implement only the Sprint 2.7 runtime `postgres_status_discovery` collector.

Scope:
- Add `scanner_runtime/postgres_discovery.py`.
- Use fixed commands via `safe_exec.py`:
  - `systemctl list-units --type=service --all --no-pager --plain --no-legend`
  - capped `systemctl show <unit names> --property=Id,Description,LoadState,ActiveState,SubState,UnitFileState,MainPID,FragmentPath`
- Add optional fixed `pg_isready` probe without connection arguments.
- Normalize `pg_isready` health result to `ok|failed|not_available`.
- Reject non-empty params.
- Return contract-compatible top-level keys: `services`, `summary`.
- Register only `postgres_status_discovery` in `scanner_runtime/prototype.py`.
- Add focused Sprint 2.7 tests.

Out of scope:
- Baseline/profile/ingestion changes.
- ToolPolicy or PlanTool activation.
- Migrations.
- Other runtime handlers.
- `psql`, SQL queries, DB contents, `.pgpass`, credentials, connection strings.
- PostgreSQL config reads (`postgresql.conf`, `pg_hba.conf`).
- Port inspection.
- AI planner or external bot.

Progress:
- Added `scanner_runtime/postgres_discovery.py` with fixed-command safe collection flow.
- Added PostgreSQL unit discovery from:
  - `systemctl list-units --type=service --all --no-pager --plain --no-legend`
  - capped `systemctl show <unit names> --property=Id,Description,LoadState,ActiveState,SubState,UnitFileState,MainPID,FragmentPath`
- Added optional fixed `pg_isready` probe normalized to `ok|failed|not_available`.
- Enforced contract-compatible output keys: `services`, `summary`.
- Registered only `postgres_status_discovery` in `scanner_runtime/prototype.py`.
- Added focused Sprint 2.7 tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_postgres_status_discovery --noinput` passed: 9 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 239 tests (4 skipped).
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.7 implementation is complete within approved runtime-only scope.
- No baseline/profile/ingestion changes, ToolPolicy/PlanTool activation, migrations, other handlers, AI planner, or external bot changes were added.
- No commit or push was made.

## Active Task - Phase 2 Sprint 2.8 Log Sources Discovery V2

Task:
- Implement only the Sprint 2.8 runtime `log_sources_discovery_v2` collector.

Scope:
- Add `scanner_runtime/log_sources_discovery_v2.py` using pure filesystem metadata only.
- Fixed allowlisted candidates only:
  - `/var/log/nginx`
  - `/var/log/postgresql`
  - `/var/log/syslog`
  - `/var/log/messages`
  - `/opt/*/logs`
  - `/opt/*/*/logs`
- Collect safe fields only: `path`, `type`, `exists`, `is_dir`, `size_bytes`, `modified_at`, `metadata.source`.
- Canonicalize paths and reject outside-allowlist paths.
- Reject non-empty params.
- Register only `log_sources_discovery_v2` in `scanner_runtime/prototype.py`.
- Add focused Sprint 2.8 tests.

Out of scope:
- Baseline/profile/ingestion changes.
- ToolPolicy or PlanTool activation.
- Migrations.
- Other runtime handlers.
- `journalctl`, `systemctl`, unit-file reads, service correlation.
- Any log content reads/parsing/tail/grep.
- Findings generation.
- AI planner or external bot.

Progress:
- Added `scanner_runtime/log_sources_discovery_v2.py` with metadata-only log source discovery.
- Added fixed allowlisted candidates for:
  - `/var/log/nginx`
  - `/var/log/postgresql`
  - `/var/log/syslog`
  - `/var/log/messages`
  - `/opt/*/logs`
  - `/opt/*/*/logs`
- Added safe metadata output fields only: `path`, `type`, `exists`, `is_dir`, `size_bytes`, `modified_at`, `metadata.source`.
- Added canonicalization and allowlist validation to reject unsafe/outside paths.
- Registered only `log_sources_discovery_v2` in `scanner_runtime/prototype.py`.
- Added focused Sprint 2.8 unit tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_log_sources_discovery_v2 --noinput` passed: 12 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 251 tests (4 skipped).
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.8 implementation is complete within approved runtime-only scope.
- No baseline/profile/ingestion changes, ToolPolicy/PlanTool activation, migrations, other handlers, AI planner, or external bot changes were added.
- No commit or push was made.

## Active Task - Phase 2 Sprint 2.8 Log Sources Discovery V2 Hotfix

Task:
- Tighten `/opt` log source discovery after server smoke testing showed noisy internal/heavy directories and missing `/opt/.../logs` candidates.

Scope:
- Skip hidden/heavy/internal directories under `/opt`:
  `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `.cache`, `.config`, `.npm`, `.tox`, `tests`, `docs`, `static`, `staticfiles`, `templates`, `scripts`, `skills`, `dist`, `build`, `tmp`.
- Do not emit `/opt/*/logs` or `/opt/*/*/logs` if the logs path does not exist.
- Keep fixed system candidates even when missing.
- Preserve `/opt` realpath escape protection.
- Add regression tests for hidden/heavy/missing app log paths.

Out of scope:
- Baseline/profile/ingestion changes.
- ToolPolicy or PlanTool activation.
- Migrations.
- Other runtime handlers.
- AI planner or external bot.
- Log content reads/parsing or findings generation.

Progress:
- Updated `/opt` log source discovery to skip hidden/heavy/internal directories.
- Stopped emitting missing `/opt` app log candidates while preserving missing fixed system candidates.
- Preserved `/opt` realpath escape protection for app log paths.
- Added regression tests for `.git/logs`, `node_modules/logs`, missing `/opt/app/logs`, existing safe `/opt/app/logs`, and missing fixed system candidates.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_log_sources_discovery_v2 --noinput` passed: 18 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 257 tests (4 skipped).
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.8 hotfix is complete within approved runtime-only scope.
- No baseline/profile/ingestion changes, ToolPolicy/PlanTool activation, migrations, other handlers, AI planner, external bot, log parsing, or findings generation were added.
- No commit or push was made.
