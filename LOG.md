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

## 2026-05-27 - Sprint 2 Start

Intent:
- Implement Sprint 2 agent registration and job foundation within the locked scope.

Scope:
- Add `ScannerAgent`, `AgentRegistrationToken`, `AgentJob`, and `BaselineScan` skeleton.
- Add agent registration, heartbeat, one-job polling, and result submission endpoints.
- Add bearer token authentication for agents.
- Add temporary `system_identity` allowlist only.
- Add minimal scanner runtime prototype for register, heartbeat, poll one job, execute `system_identity`, and submit result.

Out of scope:
- Systemd, install flow, Remote Bootstrap, full Baseline Scan, Finding, full Tool Registry, full Policy Engine, Telegram, Diagnostic Agent, Celery, and remediation/actions.

Result:
- Added Sprint 2 agent foundation models and admin registrations.
- Added hashed registration and agent token helpers.
- Added agent registration, heartbeat, one-job polling, and job result APIs.
- Added atomic job claiming with `claimed_at`, `claim_expires_at`, and 5 minute default expiry.
- Added result submission guards for terminal jobs, unclaimed jobs, expired claims, output size, and agent ownership.
- Added temporary hardcoded allowlist with `system_identity` only.
- Added `BaselineScan` as a model skeleton only.
- Added a minimal scanner runtime prototype limited to register, heartbeat, poll one job, execute `system_identity`, and submit result.
- Added Sprint 2 unit/integration tests for the new agent foundation, including claim expiry and output size checks.

Verification:
- `python manage.py makemigrations servers` created `apps/servers/migrations/0002_agentregistrationtoken_baselinescan_scanneragent_and_more.py`.
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes detected.
- `python manage.py test --noinput` passed: 16 tests ran successfully.
- `python manage.py migrate` applied the Sprint 2 migration successfully.

Remaining:
- No known Sprint 2 implementation issues.
- Changes are not committed yet.

## 2026-05-27 - Sprint 3 Start

Intent:
- Implement Sprint 3 Remote Bootstrap MVP within the locked scope.

Scope:
- Admin-only Remote Bootstrap using Paramiko.
- Add `apps/bootstrap` with BootstrapSession, BootstrapStep, BootstrapCredential, and AgentInstallation.
- Use fixed command templates, typed parameters, package allowlists, encrypted temporary credentials, 30 minute TTL, and credential cleanup.
- Install/start Scanner Runtime under `/opt/matrix_scanner` using JSON config and `matrix-scanner-agent.service`.
- Verify heartbeat only.

Out of scope:
- Full Baseline Scan, Security Preflight, diagnostic tools, full Tool Registry, full Policy Engine, Telegram, Diagnostic Agent, Celery, remediation/actions, customer Portal bootstrap, self-install flow, install script, and free shell execution.

Result:
- Added `apps/bootstrap` with BootstrapSession, BootstrapStep, BootstrapCredential, and AgentInstallation.
- Added Matrix Admin-only Admin registrations, non-stored credential entry on session creation, and a synchronous Admin action for running selected bootstrap sessions.
- Added Paramiko SSH adapter.
- Added BootstrapPolicy fixed command templates and package manager allowlist handling.
- Added encrypted temporary credentials using `BOOTSTRAP_CREDENTIAL_ENCRYPTION_KEY`.
- Added 30 minute credential TTL and cleanup behavior that clears encrypted payloads and sets `destroyed_at`.
- Added generated runtime upload payload, JSON config handling, and systemd unit for `matrix-scanner-agent.service`.
- Added heartbeat verification step using Sprint 2 ScannerAgent state.
- Added secret redaction for stored command output and failure text.
- Added Sprint 3 tests for Admin-only access, credential encryption/expiry/cleanup, policy rejection, package confirmation, step statuses, mocked SSH success/failure, out-of-scope record absence, and audit metadata safety.

Verification:
- Installed new dependencies from `requirements.txt`: `paramiko` and `cryptography`.
- `python manage.py makemigrations bootstrap` created `apps/bootstrap/migrations/0001_initial.py`.
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes detected.
- `python manage.py test --noinput` passed: 27 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No known Sprint 3 implementation issues.
- Changes are not committed yet, per instruction.

## 2026-05-28 - Sprint 4 Start

Intent:
- Implement Sprint 4 Tool Registry and Policy Engine MVP within the locked scope.

Scope:
- Add `apps/tools` with ToolTemplate, ToolDefinition, ToolPolicy, PlanTool, and ToolRun.
- Register `system_identity` as the first registry-backed read-only tool.
- Enforce ToolPolicy and PlanTool for new tool/job creation.
- Create ToolRun after policy approval and before AgentJob.
- Update AgentJob result ingestion to update linked ToolRun with redacted results.

Out of scope:
- Full Baseline Scan, Baseline orchestration, Security Preflight, Diagnostic Agent, Telegram, Celery, remediation/actions, customer-created tools, Admin Tool Builder Agent, new diagnostic tools beyond `system_identity`, and external JSON Schema dependencies.

Result:
- Added `apps/tools` with ToolTemplate, ToolDefinition, ToolPolicy, PlanTool, and ToolRun.
- Added Admin registrations for all Sprint 4 models.
- Added idempotent `system_identity` registry setup and safe data migration.
- Added ToolPolicy/PlanTool deny-by-default service.
- Added internal parameter validation and path policy checks.
- Added ToolRun creation after policy approval and before AgentJob creation.
- Updated AgentJob result ingestion to update linked ToolRun with redacted output.
- Kept Sprint 2 hardcoded allowlist as a temporary fallback.
- Kept Sprint 3 BootstrapPolicy separate and unaffected.
- Added structured JSON redaction helper.
- Added Sprint 4 tests covering registry, policy denials, PlanTool enforcement, params/path policy, ToolRun updates, Sprint 2 polling, and BootstrapPolicy separation.

Verification:
- `python manage.py makemigrations tools` created `apps/tools/migrations/0001_initial.py`.
- Added `apps/tools/migrations/0002_seed_system_identity.py`.
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes detected.
- `python manage.py test --noinput` passed: 42 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No known Sprint 4 implementation issues.
- Changes are not committed yet, per instruction.

## 2026-05-28 - Sprint 5 Start

Intent:
- Implement Sprint 5 Baseline Scan Implementation within the locked scope.

Scope:
- Add baseline orchestration that uses ToolDefinition, ToolPolicy, ToolRun, and AgentJob.
- Add BaselineScanStep, DiscoveredService, DiscoveredDomain, LogSource, and simple MVP Finding.
- Seed the required baseline tools as read-only registry-backed tools.
- Add only the required read-only runtime handlers for baseline tools.
- Add Admin-only baseline workflow/action and focused tests.

Out of scope:
- Diagnostic Agent, Telegram, Celery, remediation/actions, Portal UI, full Security Preflight, raw log ingestion, raw `.env` storage, free shell commands, customer-created tools, and Admin Tool Builder Agent.

Pre-start:
- Read the required agent, log, current task, decision, plan, security, structure, checklist, and test plan documents.
- Updated `docs/CURRENT-TASKS.md` before implementation.

Result:
- Expanded `BaselineScan` with request/user, current step, summary, and error fields.
- Added `BaselineScanStep`, `DiscoveredService`, `DiscoveredDomain`, `LogSource`, and simple MVP `Finding`.
- Added Application metadata and unique discovered-location constraint.
- Added step-based baseline orchestration services that fail fast before creating jobs if required tools are not allowed by the active plan.
- Added ingestion for completed ToolRuns into services, domains, applications, Laravel safe env metadata, log source metadata, and finding evidence summaries.
- Added idempotent baseline tool setup and a data migration for the required read-only tools.
- Added read-only scanner runtime handlers for the required baseline tools.
- Added Matrix Admin-only baseline actions in Django Admin.
- Adjusted AgentJob result size enforcement to use each job's stored output cap.
- Updated agent polling responses to return the linked ToolRun timeout where available.
- Added Sprint 5 tests covering baseline seeding, policy failure, ToolRun/AgentJob creation, result ingestion, deduplication, Laravel env allowlist, blocked path handling, findings redaction, status transitions, tenant isolation, and out-of-scope side effects.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 56 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No known Sprint 5 implementation issues.
- Changes are not committed, per instruction.

## 2026-05-28 - Sprint 6 Start

Intent:
- Implement Sprint 6 Admin and Portal MVP Screens within the locked scope.

Scope:
- Create/use `apps/portal`.
- Add customer Portal templates, views, permissions, role checks, and tenant-scoped querysets.
- Add Portal pages for dashboard, servers, add server, server detail, registration token generation, applications, findings, baseline visibility, subscription/usage, and placeholders.
- Improve Django Admin usability where useful without changing product behavior outside Sprint 6.
- Add focused tests for Portal access, tenant isolation, role behavior, token safety, action audits, and safe display.

Out of scope:
- Telegram integration, Diagnostic Agent, Celery, payments gateway, remediation/actions, Admin Tool Builder Agent, advanced reporting, PDF/email output, customer Remote Bootstrap, React/Vue, user invitation/role management, and customer baseline start.

Pre-start:
- Read the required agent, log, current task, decision, plan, interface, security, structure, checklist, and test plan documents.
- Updated `docs/CURRENT-TASKS.md` before implementation.

## 2026-05-28 - Sprint 11 Start

Intent:
- Implement Sprint 11 Reports, Findings, and Knowledge Base Enhancement within the locked scope.

Scope:
- Add Report, ReportSection, FindingGroup, KnowledgeEntry, KnowledgeSource, and Recommendation.
- Add synchronous explicit report generation from safe/redacted sources.
- Add Admin registrations/actions for report generation and finding group rebuild.
- Improve Portal report and finding group visibility with account scoping and role permissions.
- Add small safe Telegram report summary support.

Out of scope:
- PDF export, email reports, scheduled reports, Celery/report workers, live LLM report generation, public API endpoints, remediation/actions, write tools, service restarts, package installs, file edits, ToolPolicy bypass, direct AgentJob creation, raw logs, raw `.env`, raw ToolRun output, raw AgentJob output, credentials, tokens, passwords, or private keys.

Pre-start:
- Read required agent, log, current task, decision, plan, interface, security, structure, checklist, and test-plan documents.
- Updated `docs/CURRENT-TASKS.md` before implementation.

Result:
- Added ToolBuildRequest, ToolBuildProposal, ToolBuildReview, and ToolTestResult models inside `apps/tools`.
- Added deterministic builder services for proposal generation, validation, review, and conversion.
- Added mock/sandbox validation only; no customer server execution path was added.
- Added Django Admin registrations and actions for generating, validating, approving, rejecting, and converting proposals.
- Conversion creates a ToolDefinition only as draft or pending_review and creates an inactive conservative ToolPolicy.
- Kept PlanTool attachment manual only and did not add automatic enablement.
- Redacted proposal text, review notes, validation output, and test result data before storage.
- Added AuditLog entries for request submission, proposal generation, validation, approval/rejection, and conversion without raw prompts/logs/secrets.
- Added focused Sprint 10 tests covering Admin-only access, safe storage, validation denials, safe conversion, no automatic enablement/PlanTool, no ToolRun/AgentJob, no customer server execution, and ToolPolicy source-of-truth behavior.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint10_tool_builder --noinput` passed: 14 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 132 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No known Sprint 10 implementation issues.
- Changes are not committed, per instruction.

Result:
- Added `TelegramDiagnosticState` to manage private-chat Telegram guided diagnostic flow state separately from `TelegramChatLink`.
- Added `DiagnosticSession.source` and nullable `source_chat_link` for Portal vs Telegram attribution.
- Added Telegram guided diagnostic commands: `/diagnose`, `/cancel`, `/approve`, `/session`, and `/report`.
- Added `callback_query` handling to the Telegram webhook and inline keyboard response payloads with constrained callback keys.
- Implemented private-chat-only server selection, application selection, problem type selection, bounded/redacted description capture, confirmation, approval, status, report, and cancellation flow.
- Enforced owner/operator-only diagnostic actions and blocked viewer and group/supergroup diagnostics.
- Enforced one active Telegram diagnostic state per private chat and 30-minute state expiry.
- Connected Telegram session creation and approval to existing diagnostics services and ToolPolicy-backed ToolRun/AgentJob creation.
- Added replay controls so repeated approvals are rejected once a step is no longer awaiting approval.
- Added concise redacted Telegram final report output and avoided raw ToolRun, AgentJob, logs, `.env`, stdout/stderr, credentials, tokens, and passwords.
- Added AuditLog entries for important Telegram diagnostic interactions without raw prompts, raw callback payloads, raw Telegram updates, or secrets.
- Added Sprint 9 tests covering unlinked/group/viewer denial, owner/operator flow, account-scoped server/application selection, cross-account callback rejection, one active state, cancellation, expiry, approval, replay prevention, webhook callbacks, Sprint 7 command compatibility, group summary behavior, and final report redaction.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint9_telegram_diagnostics --noinput` passed: 16 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 118 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No known Sprint 9 implementation issues.
- Changes are not committed, per instruction.

Result:
- Added `apps.diagnostics` with DiagnosticSession, DiagnosticStep, and DiagnosticDecision models plus Admin registrations and initial migration.
- Added deterministic diagnostic services that plan one approved read-only baseline tool step at a time.
- Added user approval gating before any diagnostic ToolRun is created.
- Integrated approved diagnostic steps through the existing ToolPolicy service via `create_tool_run_job`; diagnostics do not create AgentJob directly.
- Added ToolRun status/result synchronization into DiagnosticStep summaries and final DiagnosticSession reports.
- Added Portal diagnostics list, start, detail, and step approval views/templates under `/portal/diagnostics/`.
- Enforced Portal tenant scoping and owner/operator action permissions; viewers remain read-only.
- Strengthened shared redaction for `APP_KEY` and API key style strings before diagnostic context/report display.
- Added Sprint 8 tests covering Portal access, staff blocking, owner/operator/viewer permissions, tenant and application ownership, deterministic planning, approval gating, ToolPolicy denial, max tool-run limits, ToolRun/AgentJob linkage through ToolRun, result ingestion, final report redaction, no Telegram side effects, and safe Portal display.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint8_diagnostics --noinput` passed: 17 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 102 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No known Sprint 8 implementation issues.
- Changes are not committed, per instruction.

## 2026-05-28 - Sprint 9 Start

Intent:
- Implement Sprint 9 Telegram Guided Diagnostics within the locked scope.

Scope:
- Add private-chat-only Telegram diagnostic state and guided command/callback flow.
- Add Telegram diagnostic commands: `/diagnose`, `/cancel`, `/approve`, `/session`, and `/report`.
- Add callback_query handling and inline keyboard responses.
- Connect Telegram diagnostics to existing diagnostics services and ToolPolicy-backed approval workflow.
- Add minimal DiagnosticSession source fields for Portal vs Telegram attribution.
- Keep Telegram output concise and redacted.

Out of scope:
- Group diagnostics, remediation/actions, write tools, free shell commands, direct AgentJob creation from Telegram, ToolPolicy bypass, live LLM execution, and raw outputs/secrets in Telegram.

Pre-start:
- Read the required agent, log, current task, decision, plan, interface, security, structure, checklist, and test plan documents.
- Updated `docs/CURRENT-TASKS.md` before implementation.

## 2026-05-28 - Sprint 10 Start

Intent:
- Implement Sprint 10 Tool Definition Proposal Builder MVP inside `apps/tools`.

Scope:
- Add Matrix Admin-only ToolBuildRequest, ToolBuildProposal, ToolBuildReview, and ToolTestResult.
- Add deterministic proposal generation and validation.
- Add Admin review actions and conversion to draft/pending_review ToolDefinition only.
- Add mock/sandbox validation only.
- Keep Tool Registry and ToolPolicy as the source of truth.

Out of scope:
- New Django app, live LLM/provider calls, executable/runtime handler generation, shell/free command generation, remediation/actions, write/destructive tools, customer Portal tool builder, automatic enablement, automatic PlanTool attachment, ToolRun or AgentJob creation, and customer server execution.

Pre-start:
- Read the required agent, log, current task, decision, plan, interface, security, structure, checklist, and test plan documents.
- Updated `docs/CURRENT-TASKS.md` before implementation.

Result:
- Added `apps.telegram_integration` with `TelegramChatLink`, `TelegramLinkToken`, and `TelegramNotification` models, Admin registrations, and initial migration.
- Added Telegram webhook foundation at `/telegram/webhook/<secret>/` with path/header secret validation.
- Added global Telegram settings loaded from environment: `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_SECRET`; no bot token is stored in the database.
- Implemented hashed, one-time Telegram link tokens with TTL, used/revoked checks, private/group scope validation, and raw code shown once through Portal.
- Implemented read-only allowlisted Telegram commands: `/start`, `/link`, `/unlink`, `/help`, `/menu`, `/servers`, `/apps`, `/findings`, `/status`, and `/baseline`.
- Implemented account-scoped Telegram command summaries that avoid raw ToolRun output, AgentJob results, logs, `.env`, bootstrap credentials, SSH credentials, and secrets.
- Added safe notification records for Sprint 7 notification types with redacted payloads, dedupe suppression, and an explicit Bot API delivery helper.
- Added notification event hooks for baseline completion, high/critical findings, agent offline/recovered, and bootstrap completed/failed.
- Added Portal Telegram settings page and route, with owner/operator private link-code generation and owner-only group link-code generation.
- Added AuditLog entries for Telegram link-code generation and chat link/unlink events without raw codes or sensitive metadata.
- Added Sprint 7 tests covering token hashing/use/expiry/revocation, linking, Portal permissions, webhook secret enforcement, tenant scoping, read-only command behavior, notification redaction/suppression, event notification creation, and no DiagnosticSession/ToolRun/AgentJob creation from Telegram commands.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint7_telegram --noinput` passed: 13 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 85 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No known Sprint 7 implementation issues.
- Changes are not committed, per instruction.

## 2026-05-28 - Sprint 8 Start

Intent:
- Implement Sprint 8 Diagnostic Agent MVP within the locked scope.

Scope:
- Create/use `apps/diagnostics`.
- Add DiagnosticSession, DiagnosticStep, and DiagnosticDecision models.
- Add deterministic planning with read-only baseline tools only.
- Add Portal-only diagnostic session start/detail/approval flow.
- Require user approval before each diagnostic tool step creates a ToolRun.
- Use Tool Registry and ToolPolicy for every diagnostic ToolRun.
- Store concise redacted final reports on DiagnosticSession.

Out of scope:
- Telegram Guided Diagnostics, Telegram diagnostic commands/messages/approvals, live LLM execution, remediation/actions, write tools, shell/free commands, Celery, email alerts, PDF export, advanced reporting, IncidentReport, customer-created tools, and Admin Tool Builder Agent.

Pre-start:
- Read the required agent, log, current task, decision, plan, interface, security, structure, checklist, and test plan documents.
- Updated `docs/CURRENT-TASKS.md` before implementation.

Result:
- Added `apps.portal` with app config, permissions, forms, services, views, and URLs.
- Added Portal templates for dashboard, servers, add server, server detail, registration token generation, applications, findings, baseline scans, subscription/usage, login/logout/access-denied, and placeholders.
- Wired `/portal/` into the project and registered `apps.portal`.
- Implemented Portal access rules requiring authentication, account linkage, active account, and owner/operator/viewer role.
- Implemented tenant-scoped querysets and account ownership checks for every Portal object lookup.
- Implemented owner-only server creation and owner-only registration token generation.
- Ensured registration token raw value is shown once, stored hashed only, and audited without raw token metadata.
- Implemented application approve/ignore/archive actions and finding acknowledge/ignore actions with AuditLog entries.
- Added read-only baseline scan and subscription/usage views.
- Kept baseline start and remote bootstrap Admin-only by not exposing Portal routes for those actions.
- Added safe display rules for application metadata, finding evidence, baseline summaries, and server details without raw AgentJob or ToolRun output.
- Added minimal Django Admin branding for Matrix Scanner Admin.
- Added Sprint 6 tests covering login, staff blocking, tenant isolation, role permissions, token generation safety, action auditing, subscription read-only behavior, bootstrap route absence, and secret/output display safety.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 72 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No known Sprint 6 implementation issues.
- Changes are not committed, per instruction.

## 2026-05-28 - Sprint 7 Start

Intent:
- Implement Sprint 7 Telegram Integration MVP within the locked scope.

Scope:
- Create/use `apps/telegram_integration`.
- Add Telegram webhook foundation with secret validation.
- Add short-lived one-time Telegram link tokens stored hashed only.
- Add private and group chat linking rules.
- Add read-only Telegram command handling and safe summaries.
- Add safe notification records with dedupe/suppression.
- Add owner-only Portal surface for Telegram link token generation.

Out of scope:
- Diagnostic Agent, Telegram Guided Diagnostics, DiagnosticSession creation from Telegram, ToolRun or AgentJob creation from Telegram, remediation/actions, write tools, payments, Celery, polling infrastructure, per-account bot tokens, customer-created tools, and Admin Tool Builder Agent.

Pre-start:
- Read the required agent, log, current task, decision, plan, interface, security, structure, checklist, and test plan documents.
- Updated `docs/CURRENT-TASKS.md` before implementation.

## 2026-05-28 - Sprint 11 Completed

Result:
- Added `apps.reports` and registered it in Django settings.
- Added Report, ReportSection, FindingGroup, KnowledgeEntry, KnowledgeSource, and Recommendation with migration.
- Added report generation services using redacted snapshots only from approved safe sources.
- Added finding group rebuild/deduplication and advisory-only recommendations with no execution path.
- Added Report, ReportSection, FindingGroup, KnowledgeEntry, KnowledgeSource, and Recommendation Admin screens.
- Added Admin actions for baseline report generation, diagnostic report generation, and finding group rebuilds.
- Added Portal report list/detail/generation pages, finding group list/detail pages, findings filters, server latest report/group summary, and diagnostic report links.
- Updated Telegram `/report` to return a short latest safe report summary when no active diagnostic session report is present.
- Added Sprint 11 tests for safe report content, grouping, Portal scoping, Admin visibility, advisory recommendations, knowledge redaction, Telegram report summary, and out-of-scope exclusions.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 142 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No known Sprint 11 implementation issues.
- Changes are not committed, per instruction.

## 2026-05-28 - Sprint 12 Start

Intent:
- Implement Sprint 12 stabilization, security hardening, and release preparation within the locked scope.

Scope:
- Final verification, tenant isolation review, permission review, secret/redaction review, ToolPolicy enforcement review, Admin/Portal/Telegram access review, settings/env validation, migration consistency checks, documentation cleanup, release checklist, manual smoke checklist, and focused regression tests.

Out of scope:
- New product workflows, remediation/actions, write tools, live LLM execution, Celery/Redis implementation, payment gateway, PDF export, email reports, scheduled reports, customer Remote Bootstrap, ToolPolicy bypass, and direct AgentJob creation outside existing approved flows.

Pre-start:
- Read the required agent, log, current task, decision, plan, interface, security, structure, checklist, test plan, README, local development, deployment notes, and runbook documents.
- Updated `docs/CURRENT-TASKS.md` before implementation.

Result:
- Updated README, local development, deployment notes, runbook, PLANS, execution plan, implementation checklist, test plan, and decisions docs for MVP release readiness.
- Added `docs/operations/RELEASE-CHECKLIST.md`.
- Documented Celery/Redis, PDF/email/scheduled reports, payment gateway, customer Remote Bootstrap, live LLM, remediation/write/destructive tools, PostgreSQL RLS, multi-account membership, full self-install automation, and advanced knowledge matching as deferred.
- Added `.env.example` entries for CSRF trusted origins, proxy SSL header, and secure session/CSRF cookies.
- Added settings support for CSRF trusted origins, optional proxy SSL header, and secure cookies.
- Hardened AuditLog metadata value redaction before validation/storage.
- Hid raw `AgentJob.result` from Django Admin detail display.
- Added Sprint 12 security regression tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint12_stabilization --noinput` passed: 11 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py migrate` passed.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 153 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No known Sprint 12 implementation issues.
- Changes are not committed, per instruction.

## 2026-05-29 - Phase 2 Sprint 2.1 Start

Intent:
- Prepare only Phase 2 Sprint 2.1: runtime discovery tool contracts and seeding structure for Debian/Nginx `/opt`-based servers.

Scope:
- Update local `main` to deployed source-of-truth commit `762abd4`.
- Re-inspect current baseline, tool registry, diagnostics, and runtime code.
- Add non-executing Tool Registry contracts and idempotent seeding helper for the new Phase 2 discovery tools.
- Add focused tests for safe contract defaults and absence of ToolRun/AgentJob side effects.

Out of scope:
- Runtime handler implementation, baseline orchestration changes, UI redesign, external bot work, live LLM work, remediation/actions, write tools, free shell commands, and unsafe execution paths.

Pre-start:
- Fast-forwarded local `main` to `762abd4 fix: auto-ingest baseline after agent job result`.
- Confirmed working tree was clean before task-tracking updates.
- Re-inspected current code paths before implementation.

Result:
- Added Phase 2 discovery tool contracts for Debian/Nginx `/opt` runtime discovery:
  `systemd_services_discovery`, `nginx_sites_discovery`, `opt_apps_discovery`, `django_apps_discovery`,
  `gunicorn_uvicorn_services_discovery`, `postgres_status_discovery`, and `log_sources_discovery_v2`.
- Added an idempotent seeding helper that creates ToolTemplate, ToolDefinition, and inactive ToolPolicy records.
- Added a safe data migration to seed the contracts as approved/read-only but non-executable by default.
- Kept the new contracts out of current `BASELINE_TOOL_KEYS` and diagnostic allowed tools to avoid requesting runtime handlers that are not implemented yet.
- Added focused Phase 2 contract tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_tool_contracts --noinput` passed: 4 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 157 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Implement runtime handlers in later Phase 2 steps before enabling these tools or adding them to baseline/diagnostics.
- No commit or push was made.
