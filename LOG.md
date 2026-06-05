# Log

Operational notes for repository work. Update this file before and after every requested implementation, repository-changing command, or multi-step operation.

## 2026-06-05 - Sprint C2 Safe Context Builder MVP Start

Intent:
- Execute Sprint C2 from the approved corrected Matrix Scanner SaaS roadmap.

Scope:
- Add dedicated `apps/ai_context` safe context builder.
- Build versioned, redacted, summarized, capped JSON context.
- Include `available_tools` metadata respecting ToolPolicy and PlanTool.
- Add focused tests for scoping, redaction, raw output exclusion, caps, and tool policy filtering.

Out of scope:
- Live AI provider calls, chat UI/models, tool execution, direct AgentJob access, raw outputs/secrets, and Sprint C3 implementation.

Testing note:
- Per updated instruction, use focused Sprint tests by default.
- C2 touches redaction/permissions context, so full suite may be used as a security regression gate if needed and will be reported explicitly.

## 2026-06-05 - Sprint C1.5 Remote Bootstrap Runtime Completion Start

Intent:
- Execute Sprint C1.5 from the approved corrected Matrix Scanner SaaS roadmap.

Scope:
- Update Remote Bootstrap so the installed bundle is a real polling Runtime/Agent rather than registration/heartbeat only.
- Reuse existing bootstrap foundation and tests.
- Preserve Matrix Admin-only bootstrap, `/opt/matrix_scanner`, and `matrix-scanner-agent.service`.
- Ensure generated config includes `base_url`, `registration_token` or `agent_token`, `poll_interval_seconds`, and `runtime_mode`.

Out of scope:
- Portal/customer bootstrap, new raw shell/arbitrary commands, remediation/write/destructive actions, server/VM execution, and Sprint C2 implementation.

Result:
- Updated bootstrap archive generation to package the current `scanner_runtime` modules.
- Replaced the generated heartbeat-only `agent_service.py` with a polling runtime service using `scanner_runtime.prototype`.
- The generated runtime service now supports registration, heartbeat, polling, allowlisted AgentJob execution, and job result submission.
- Added `runtime_mode = polling_agent` to the generated bootstrap config.
- Preserved `/opt/matrix_scanner` and `matrix-scanner-agent.service`.
- Added focused tests for runtime archive contents, config shape, and systemd service target.
- Added Sprint C1.5 report to `docs/planning/تقارير التنفيذ.md`.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint3_bootstrap --noinput` passed: 13 tests.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 294 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Sprint C1.5 is complete.
- Proceed to `Sprint C2 - Safe Context Builder MVP` after the C1.5 commit if no untracked official files remain.
- No Portal/customer bootstrap, raw shell/arbitrary command expansion, remediation/write/destructive behavior, server/VM execution, or Sprint C2 implementation was performed.

## 2026-06-05 - Sprint C1 Current State and Documentation Alignment Start

Intent:
- Execute Sprint C1 from the approved corrected Matrix Scanner SaaS roadmap.

Scope:
- Align documentation around the approved planning references.
- Confirm `DECISION-REGISTER.md` is the official decision reference.
- Confirm `CORRECTED-EXECUTION-PLAN.md` is the top execution reference after `ROADMAP-CORRECTION.md`.
- Document that the first real implementation Sprint after C1 is `Sprint C1.5 - Remote Bootstrap Runtime Completion`.
- Run non-destructive validation commands.

Out of scope:
- Product code changes, model/service/runtime changes, migrations beyond dry-run checks, server execution, and Sprint C1.5 implementation.

Result:
- Added corrected-roadmap documentation links to `README.md`.
- Added a corrected roadmap authority section to `PLANS.md`.
- Added corrected roadmap references to `docs/DECISIONS.md`.
- Added Sprint C1 report to `docs/planning/تقارير التنفيذ.md`.
- Confirmed `docs/planning/DECISION-REGISTER.md` is the official decision reference.
- Confirmed `docs/planning/CORRECTED-EXECUTION-PLAN.md` is the top execution reference after `docs/planning/ROADMAP-CORRECTION.md`.
- Confirmed the first real implementation Sprint after documentation alignment is `Sprint C1.5 - Remote Bootstrap Runtime Completion`.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 292 tests, 4 skipped.
- Initial full test run also reached `OK` but the shell wrapper timed out after printing results; it was rerun with a longer timeout and exited successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Sprint C1 is complete.
- Proceed to `Sprint C1.5 - Remote Bootstrap Runtime Completion` only after owner approval.
- No product code, migration, runtime/service/model change, or server execution was performed.

## 2026-06-05 - Decision Register Approval Update

Intent:
- Mark the corrected execution decision register as approved.

Scope:
- Update `docs/planning/DECISION-REGISTER.md` status.
- Update documentation tracking only.

Result:
- Marked `docs/planning/DECISION-REGISTER.md` as `Approved`.
- Added `Approved by project owner on 2026-06-05.`
- Recorded that the decision register is the official decision reference.
- Recorded that `docs/planning/CORRECTED-EXECUTION-PLAN.md` is the top execution reference after `docs/planning/ROADMAP-CORRECTION.md`.
- Recorded that the first real implementation Sprint after documentation alignment is `Sprint C1.5 - Remote Bootstrap Runtime Completion`.

Verification:
- `git diff --check` passed with line-ending warnings only.
- No code, migrations, tests, runtime changes, or server execution were performed.

## 2026-06-05 - Roadmap Tool Runtime Correction Detail Start

Intent:
- Apply the attached detailed correction to `docs/planning/ROADMAP-CORRECTION.md`.

Scope:
- Strengthen the roadmap reference around command-template-first tools.
- Clarify Admin AI Chatbot's responsibilities for selecting/proposing tools.
- Clarify Runtime/Agent as a safe restricted command executor.
- Clarify Tool Registry to Runtime execution flow and new-tool approval flow.

Out of scope:
- Product code changes, migrations, command-template runtime implementation, ToolPolicy/PlanTool changes, AI implementation, Telegram implementation, commits, and pushes.

Result:
- Strengthened `docs/planning/ROADMAP-CORRECTION.md` with detailed command-template-first tool semantics.
- Added sections covering proposed tool shape, Admin AI Chatbot responsibilities, Runtime/Agent responsibilities, Tool Registry to Runtime relationship, new-tool proposal/validation flow, and tool type classification.
- Kept `runtime_handler` as an advanced later option and `command_template` / `script_template` as the current preferred model.

Verification:
- Confirmed the roadmap contains the expected command-template details, including `nginx_error_tail`, `ToolBuildRequest`, `ToolBuildProposal`, `command_template`, `script_template`, and `runtime_handler`.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No product code, migration, command-template runtime implementation, ToolPolicy/PlanTool change, AI implementation, Telegram implementation, commit, or push was made.

## 2026-06-04 - Tool Model Correction Start

Intent:
- Apply the attached correction about Matrix Scanner tool concepts to the roadmap/execution planning docs.

Scope:
- Clarify that the preferred current tool model is `command_template`, not one runtime handler per tool.
- Clarify Runtime/Agent as a safe restricted command executor for approved read-only command templates.
- Keep runtime handlers as an advanced later option.
- Update the corrected execution plan and roadmap reference wording accordingly.

Out of scope:
- Product code changes, migrations, runtime command-template implementation, ToolPolicy/PlanTool activation, AI implementation, Telegram implementation, commits, and pushes.

Result:
- Updated `docs/planning/ROADMAP-CORRECTION.md` to add an explicit correction for tool concepts and Runtime/Agent responsibilities.
- Updated `docs/planning/CORRECTED-EXECUTION-PLAN.md` so the execution roadmap is command-template-first instead of handler-first.
- Renamed the phase 5 concept from runtime capability/handler hardening to `Safe Command Execution Runtime`.
- Clarified that runtime handlers are advanced later options, while the current preferred model is approved read-only command/script templates in Tool Registry.

Verification:
- Confirmed both Markdown files read correctly as UTF-8.
- Confirmed both files include the Safe Command Execution Runtime concept.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No product code, migration, runtime command-template implementation, ToolPolicy/PlanTool activation, AI implementation, Telegram implementation, commit, or push was made.

## 2026-06-04 - Corrected Execution Plan Start

Intent:
- Study the roadmap correction reference and current project state, then create a detailed implementation plan Markdown file for the next phases.

Scope:
- Use `docs/planning/ROADMAP-CORRECTION.md` as the guiding reference.
- Reconcile the plan with the implemented SaaS, Agent, Tool Registry, Baseline, Reports, Telegram foundation, and Phase 2 discovery state.
- Create a new Markdown execution plan for upcoming phases.

Out of scope:
- Product code changes, migrations, runtime handlers, ToolPolicy/PlanTool activation, AI/Telegram implementation, commits, and pushes.

Result:
- Added `docs/planning/CORRECTED-EXECUTION-PLAN.md` as the detailed implementation plan based on the roadmap correction and current code state.
- The plan reconciles the existing SaaS, Agent, Runtime, Tool Registry, baseline profiles, Phase 2 ingestion, reports, diagnostics, Telegram foundation, and Tool Builder with the corrected one-AI architecture.
- The plan defines phases for current-state lock, architecture cleanup, Safe Context Builder, Admin Chat, Tool Orchestrator, runtime capabilities, Tool Builder in chat, first full tool cycle, reports from chat, internal pilot, Telegram interface, and Telegram pilot.

Verification:
- Read the generated Markdown as UTF-8 and confirmed Arabic content is intact.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No product code, migration, runtime handler, ToolPolicy/PlanTool activation, AI implementation, Telegram implementation, commit, or push was made.

## 2026-06-04 - Roadmap Correction Reference Start

Intent:
- Convert the Word document `docs/planning/خطة_تصحيح_المسار_Matrix_Scanner_SaaS.docx` into a Markdown reference plan for the next project phases.

Scope:
- Read the Word document carefully.
- Create a Markdown reference document under project planning docs.
- Keep the content focused on the corrected roadmap: one Admin AI Chatbot, safe context, tool orchestration, runtime hardening, tool creation flow, reports, internal pilot, and Telegram later.

Out of scope:
- Product code changes, migrations, runtime changes, ToolPolicy/PlanTool changes, AI implementation, Telegram implementation, commits, and pushes.

Result:
- Added `docs/planning/ROADMAP-CORRECTION.md` as a Markdown reference copy of the roadmap correction Word document.
- Preserved the corrected architecture: one Admin AI Chatbot with SaaS Backend, Tool Registry/Policy, Runtime/Agent, Reports Engine, and Telegram as supporting service layers.
- Captured phases 0 through 11 from current-state stabilization through Safe Context, Admin Chat, Tool Orchestrator, Runtime hardening, Tool Builder flow, reports, internal pilot, Telegram interface, and Telegram pilot.

Verification:
- Read the generated Markdown as UTF-8 and confirmed Arabic content is intact.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No product code, migrations, runtime handlers, ToolPolicy/PlanTool changes, AI implementation, Telegram implementation, commit, or push was made.

## 2026-06-04 - Phase 2 Sprint 2.11B Start

Intent:
- Implement only Phase 2 application ingestion and deduplication for `opt_apps_discovery` and `django_apps_discovery`.

Scope:
- Add nullable `Application.baseline_scan` attribution.
- Ingest safe application outputs from `opt_apps_discovery` and `django_apps_discovery`.
- Deduplicate by the existing `account + server + domain + path` application location.
- Apply safe framework priority so Django enriches generic Python/unknown application records.
- Update application summary counts to use scan attribution where available while preserving legacy compatibility.
- Add focused tests for deduplication, metadata safety, approved app preservation, and summary accuracy.

Out of scope:
- Report redesign, AI planner, external bot, ToolPolicy/PlanTool changes, runtime tool changes, findings generation, remediation/write actions, and service-to-application relationship modeling.

Result:
- Added nullable `Application.baseline_scan` attribution with migration `applications.0003_application_baseline_scan`.
- Added Phase 2 application ingestion for `opt_apps_discovery` and `django_apps_discovery`.
- Deduplicated Phase 2 applications by existing `account + server + domain + path` location.
- Added framework priority so Django enriches Python/unknown app records and unknown does not overwrite more specific frameworks.
- Preserved approved applications from aggressive name/framework/status overwrites while still enriching metadata and scan attribution.
- Updated application summary counting to prefer scan-scoped applications, with legacy cPanel fallback preserved.
- Added focused tests for app creation, deduplication, framework priority, malformed/unsafe inputs, secret redaction, approved app preservation, scan attribution, summary accuracy, and legacy behavior.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_baseline_ingestion --noinput` passed: 15 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint5_baseline --noinput` passed: 22 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 291 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No report redesign, AI planner, external bot, ToolPolicy/PlanTool change, runtime tool change, finding generation, remediation/write behavior, or service-to-application relationship model was added.
- No commit or push was made.

## 2026-06-04 - Phase 2 Sprint 2.11B Nested App Hotfix Start

Intent:
- Prevent `opt_apps_discovery` nested internal package candidates from being ingested as standalone Applications when a parent application is already detected.

Scope:
- Skip clearly internal depth-2 `opt_apps_discovery` candidates without systemd hints or strong standalone markers.
- Preserve top-level apps and nested apps with strong standalone indicators.
- Keep `django_apps_discovery` enrichment for real parent Django apps.

Out of scope:
- Migrations, report redesign, AI planner, external bot, ToolPolicy/PlanTool changes, runtime tool changes, findings generation, remediation/write actions, and service-to-application relationship modeling.

Result:
- Added nested internal candidate filtering for `opt_apps_discovery` application ingestion.
- Candidates nested under a detected parent app are skipped when they are depth 2+, lack a systemd/explicit app hint, and only contain weak markers such as `wsgi.py`, `asgi.py`, or `requirements.txt`.
- Top-level `/opt` applications continue to ingest.
- Nested applications with strong markers such as `package.json` or explicit systemd hints continue to ingest.
- `django_apps_discovery` still enriches the real parent Django application.
- Added regression coverage for parent apps, internal package skips, nested standalone app preservation, and Django parent enrichment.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_baseline_ingestion --noinput` passed: 16 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint5_baseline --noinput` passed: 22 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 292 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No migrations, report redesign, AI planner, external bot, ToolPolicy/PlanTool changes, runtime tool changes, findings generation, remediation/write behavior, or service-to-application relationship model was added.
- No commit or push was made.

## 2026-06-01 - Phase 2 Sprint 2.11A Start

Intent:
- Implement only Phase 2 services, domains, and log source ingestion plus scan-scoped summary counts for models that already support `baseline_scan`.

Scope:
- Ingest `systemd_services_discovery`, `gunicorn_uvicorn_services_discovery`, and `postgres_status_discovery` into `DiscoveredService`.
- Ingest `nginx_sites_discovery.domains[]` into `DiscoveredDomain`.
- Ingest `log_sources_discovery_v2.log_sources[]` into `LogSource`.
- Tolerate malformed output, skip unsafe values, redact/cap metadata, and preserve legacy ingestion.
- Make summary counts scan-scoped for `DiscoveredService`, `DiscoveredDomain`, `LogSource`, and `Finding`.
- Keep applications at 0 for Phase 2 in this sprint.

Out of scope:
- Application ingestion, `Application.baseline_scan` migration, report redesign, AI planner, external bot, ToolPolicy/PlanTool changes, runtime tools, findings generation from Phase 2, remediation/actions, and write behavior.

Result:
- Added safe Phase 2 service ingestion for `systemd_services_discovery`, `gunicorn_uvicorn_services_discovery`, and `postgres_status_discovery`.
- Added safe Phase 2 domain ingestion for `nginx_sites_discovery.domains[]`.
- Added safe Phase 2 log source ingestion for `log_sources_discovery_v2.log_sources[]`.
- Added metadata filtering/redaction/capping helpers and merge behavior for duplicate service/domain/log records.
- Updated `summarize_scan()` to count `DiscoveredService`, `DiscoveredDomain`, `LogSource`, and `Finding` by `baseline_scan`.
- Kept applications at `0` in baseline summary for this sprint and did not add application ingestion or migrations.
- Added focused Phase 2 baseline ingestion tests and updated the Sprint 5 Phase 2 expectation.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_baseline_ingestion --noinput` passed: 10 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 285 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Application ingestion and application scan attribution remain deferred to Sprint 2.11B.
- No Application migration, report redesign, AI planner, external bot, ToolPolicy/PlanTool change, runtime tool change, finding generation, remediation, or write behavior was added.
- No commit or push was made.

## 2026-06-04 - Phase 2 Sprint 2.11A Metadata Hotfix Start

Intent:
- Prevent `gunicorn_uvicorn_services_discovery` entries with missing, empty, or `unknown` `process_type` from overwriting generic systemd service metadata.

Scope:
- Filter Gunicorn/Uvicorn service ingestion to only `gunicorn`, `uvicorn`, or `daphne` process types.
- Add a regression test proving generic systemd service metadata is not overwritten by unknown Gunicorn/Uvicorn entries.

Out of scope:
- Application ingestion, migrations, reports, AI planner, external bot, ToolPolicy/PlanTool changes, runtime tools, findings generation, remediation/actions, and write behavior.

Result:
- Added a Phase 2 service ingestion guard so `gunicorn_uvicorn_services_discovery` only ingests/enriches services with `process_type` of `gunicorn`, `uvicorn`, or `daphne`.
- Unknown, missing, or empty `process_type` rows from that tool are skipped and cannot overwrite systemd metadata.
- Updated regression coverage so generic `cron.service` remains sourced from `systemd_services_discovery`, while real Gunicorn services still enrich existing service records without duplicates.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_baseline_ingestion --noinput` passed: 10 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_baseline_ingestion tests.unit.test_sprint5_baseline --noinput` passed: 32 tests.
- First full-suite run found one outdated Sprint 5 fixture expecting an untyped Gunicorn row to ingest; fixture was corrected to use `process_type="gunicorn"`.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 286 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No Application ingestion, migrations, report redesign, AI planner, external bot, ToolPolicy/PlanTool changes, runtime tool changes, findings generation, remediation, or write behavior was added.
- No commit or push was made.

## 2026-06-01 - Phase 2 Sprint 2.10 Start

Intent:
- Implement only the approved Sprint 2.10 safe Phase 2 pilot tool enablement command/helper.

Scope:
- Add a management command requiring `--plan-id` to enable Phase 2 read-only discovery tools for one selected pilot plan.
- Add dry-run support that reports intended ToolDefinition, ToolPolicy, and PlanTool changes without writes.
- Enable only the Phase 2 tools required by the `debian_nginx_opt` baseline profile.
- Keep `allow_customer_run=False` and create/update PlanTool only for the selected plan.
- Add focused tests for dry-run safety, plan scoping, policy shape, preflight success, and no ToolRun/AgentJob/report/ingestion side effects.

Out of scope:
- Migrations, Admin UI, customer Portal behavior, automatic scan creation, ToolRun/AgentJob creation inside the command, baseline ingestion, reports, AI planner, external bot, remediation/actions, global plan activation, and unrelated refactors.

Result:
- Added `apps/tools/phase2_enablement.py` with scoped Phase 2 pilot enablement logic.
- Added `enable_phase2_pilot_tools --plan-id <PLAN_ID> [--dry-run]`.
- Dry-run reports intended ToolDefinition, ToolPolicy, and PlanTool changes without writing.
- Actual run seeds missing Phase 2 contracts, enables only selected Phase 2 read-only discovery ToolDefinitions, activates admin/agent ToolPolicy with `allow_customer_run=False`, and creates/enables PlanTool rows only for the selected plan.
- The command does not create ToolRuns, AgentJobs, baseline scans, reports, or ingestion side effects.
- Added focused Sprint 2.10 tests for dry-run safety, plan-id requirements, invalid plan handling, selected-plan scoping, non-read-only skip behavior, policy shape, no ToolRun/AgentJob side effects, and Debian/Nginx baseline preflight readiness.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_pilot_enablement --noinput` passed: 11 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 275 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No migration, Admin UI, Portal behavior, ingestion, report, AI planner, external bot, remediation, or global activation changes were added.
- No commit or push was made.

## 2026-05-31 - Phase 2 Sprint 2.9 Start

Intent:
- Implement only the approved Sprint 2.9 baseline profile and runtime tool selection support.

Scope:
- Add stable baseline profile definitions for `legacy_cpanel`, `debian_nginx_opt`, and `minimal_linux`.
- Add `BaselineScan.profile_key` with default `legacy_cpanel`.
- Update baseline preflight and job creation to use the selected profile tool list.
- Preserve current/default cPanel baseline behavior exactly for `legacy_cpanel`.
- Add focused tests for profile selection, preflight scoping, and no Phase 2 ingestion side effects.

Out of scope:
- Phase 2 ingestion mapping, report changes, ToolPolicy/PlanTool activation, AI planner, external bot, remediation/actions, customer-facing behavior changes, and unrelated refactors.

Result:
- Added `apps/servers/baseline_profiles.py` with stable profile definitions for `legacy_cpanel`, `debian_nginx_opt`, and `minimal_linux`.
- Added `BaselineScan.profile_key` with default `legacy_cpanel` and a migration.
- Updated baseline preflight and ToolRun/AgentJob creation to use the selected scan profile tool list.
- Preserved the legacy cPanel baseline tool list as the default behavior.
- Exposed `profile_key` in BaselineScan Admin list display/filter only.
- Added focused tests for default profile behavior, profile-specific tool creation, selected-tool preflight scoping, failure-before-job-creation, and no Phase 2 ingestion side effects.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint5_baseline --noinput` passed: 21 tests.
- First full-suite run produced `OK` but hit the command timeout after test completion; reran with a longer timeout.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 264 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No Phase 2 result ingestion is implemented yet.
- Phase 2 ToolPolicy/PlanTool activation remains a separate Matrix Admin operation.
- No commit or push was made.

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

## 2026-05-29 - Phase 2 Sprint 2.2 Start

Intent:
- Implement only the approved Sprint 2.2 runtime safe execution helper and `systemd_services_discovery` handler.

Scope:
- Add a runtime helper for fixed argv-only read-only command execution using `subprocess.run(..., shell=False)`.
- Enforce timeouts, output size caps, safe stderr capture, and redaction.
- Add `systemd_services_discovery` using fixed `systemctl` read-only commands.
- Register only this handler in the runtime executor.
- Add focused tests for safety, parsing, runtime execution routing, param rejection, and unsupported tools.

Out of scope:
- Baseline orchestration, baseline profiles, baseline ingestion, `DiscoveredService` updates, ToolPolicy/PlanTool activation, enabling migrations, other Phase 2 handlers, AI planner, external bot, remediation/actions, shell execution, raw unit file reads, raw `ExecStart`, and raw `Environment=...`.

Result:
- Added `scanner_runtime/safe_exec.py` with fixed argv-list command execution, `subprocess.run(..., shell=False)`, timeout enforcement, output cap enforcement, and redacted stderr handling.
- Added `systemd_services_discovery` runtime parsing and collection using fixed read-only `systemctl` commands only.
- Added structured `services` and `summary` output with safe fields only.
- Registered only `systemd_services_discovery` in the runtime executor; runtime still creates no ToolRun or AgentJob.
- Added focused Sprint 2.2 tests for safe execution, parser behavior, enabled-state merge, runtime routing, param rejection, and unsupported tool rejection.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_systemd_discovery --noinput` passed: 12 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 171 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Baseline/profile/ingestion integration and ToolPolicy/PlanTool activation remain deferred.
- No commit or push was made.

## 2026-05-31 - Phase 2 Sprint 2.8 Hotfix Start

Intent:
- Tighten `log_sources_discovery_v2` `/opt` log discovery after server smoke testing showed noisy internal/heavy directories and missing app log candidates.

Scope:
- Skip hidden/heavy/internal directories under `/opt` during log source candidate discovery.
- Emit `/opt/*/logs` and `/opt/*/*/logs` candidates only when the logs path exists.
- Preserve fixed system log candidates even when missing.
- Preserve realpath escape protection for `/opt` log paths.
- Add focused regression tests.

Out of scope:
- Baseline/profile/ingestion changes, ToolPolicy/PlanTool activation, migrations, other runtime handlers, AI planner, external bot, log content reads, and findings generation.

Result:
- Updated `/opt` log source discovery to skip hidden/heavy/internal directories:
  `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `.cache`, `.config`, `.npm`, `.tox`, `tests`, `docs`, `static`, `staticfiles`, `templates`, `scripts`, `skills`, `dist`, `build`, `tmp`.
- Stopped emitting missing `/opt/*/logs` and `/opt/*/*/logs` candidates.
- Kept fixed system candidates emitted even when missing.
- Preserved `/opt` realpath escape validation for app log paths.
- Added regression tests for hidden/heavy/missing app log paths and fixed system missing paths.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_log_sources_discovery_v2 --noinput` passed: 18 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 257 tests (4 skipped).
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No commit or push was made.

## 2026-05-31 - Phase 2 Sprint 2.8 Start

Intent:
- Implement only the approved Sprint 2.8 runtime `log_sources_discovery_v2` collector.

Scope:
- Add `scanner_runtime/log_sources_discovery_v2.py` with pure filesystem metadata collection (no content reads, no shell commands).
- Allow only fixed candidates:
  - `/var/log/nginx`
  - `/var/log/postgresql`
  - `/var/log/syslog`
  - `/var/log/messages`
  - `/opt/*/logs`
  - `/opt/*/*/logs`
- Return only safe metadata fields and contract-compatible top-level keys: `log_sources`, `summary`.
- Reject non-empty params.
- Register only `log_sources_discovery_v2` in runtime executor.
- Add focused Sprint 2.8 tests.

Out of scope:
- Baseline/profile/ingestion changes, ToolPolicy/PlanTool activation, migrations, other runtime handlers, AI planner, external bot, `journalctl`, `systemctl`, service correlation, unit file reads, log parsing, and findings generation.

Result:
- Added `scanner_runtime/log_sources_discovery_v2.py` implementing `collect_log_sources_v2(params=None)` with pure filesystem metadata only.
- Added fixed allowlisted candidates only:
  - `/var/log/nginx`
  - `/var/log/postgresql`
  - `/var/log/syslog`
  - `/var/log/messages`
  - `/opt/*/logs`
  - `/opt/*/*/logs`
- Collected safe metadata fields only: `path`, `type`, `exists`, `is_dir`, `size_bytes`, `modified_at`, `metadata.source`.
- Added path canonicalization and allowlist enforcement for `/opt` patterns.
- Enforced params rejection, graceful `OSError/PermissionError` handling, redacted strings, and output cap.
- Registered only `log_sources_discovery_v2` in `scanner_runtime/prototype.py`.
- Added focused Sprint 2.8 tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_log_sources_discovery_v2 --noinput` passed: 12 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 251 tests (4 skipped).
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Baseline/profile/ingestion integration and ToolPolicy/PlanTool activation remain deferred.
- No commit or push was made.

## 2026-05-30 - Phase 2 Sprint 2.4 Start

Intent:
- Implement only the approved Sprint 2.4 runtime `opt_apps_discovery` collector for Debian/Nginx `/opt` servers.

Scope:
- Add `scanner_runtime/opt_discovery.py` as a pure file-reading runtime collector rooted at `/opt` only (max depth 2), with strict caps.
- Use presence-based framework detection for Django/Python, Node, and Laravel/PHP without reading source files.
- Optionally extract only a safe project name from size-capped `pyproject.toml`, `package.json`, and `composer.json`.
- Reject non-empty params.
- Register only `opt_apps_discovery` in the runtime executor.
- Add focused unit tests for traversal, symlink safety, framework detection, safe name extraction, and output safety.

Out of scope:
- Baseline orchestration, baseline profiles, baseline ingestion, any DB writes from runtime, ToolPolicy/PlanTool activation, migrations, other Phase 2 handlers, AI planner, external bot, remediation/actions, and shell command execution.

Result:
- Added `scanner_runtime/opt_discovery.py` as a pure file-reading runtime collector rooted at `/opt` only.
- Added max-depth-2 candidate discovery, strict caps, symlink realpath validation under `/opt`, heavy/hidden directory skipping, marker-based framework detection, safe project-name extraction, redaction, and JSON output cap enforcement.
- Returned `applications` and `summary` only, matching the Phase 2 ToolDefinition contract.
- Registered only `opt_apps_discovery` in the runtime executor; runtime still creates no ToolRun or AgentJob.
- Added focused Sprint 2.4 tests.
- Fixed candidate handling so directories without detection markers are not appended as applications, deduped by resolved realpath, and corrected the `pyproject.toml` name regex.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected; database connection timeout warning only.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_opt_apps_discovery --noinput` passed: 13 tests ran successfully with 2 symlink tests skipped in this Windows environment.
- `.\.venv\Scripts\python.exe manage.py test --noinput` was blocked by PostgreSQL connection timeout while creating the test database.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Re-run the full test suite once the local PostgreSQL test database connection is available.
- Baseline/profile/ingestion integration and ToolPolicy/PlanTool activation remain deferred.
- No commit or push was made.

## 2026-05-30 - Phase 2 Sprint 2.5 Start

Intent:
- Implement only the approved Sprint 2.5 runtime `django_apps_discovery` collector for safe Django application metadata under `/opt`.

Scope:
- Add `scanner_runtime/django_discovery.py` as a pure filesystem runtime collector rooted at `/opt` only (max depth 2), with strict caps.
- Detect Django application roots using `manage.py` or strong project-root markers plus Django indicators.
- Treat `wsgi.py`, `asgi.py`, `urls.py`, and `apps.py` as supporting markers only.
- Suppress nested Django package false positives when an ancestor is already selected as a Django root.
- Optionally read only size-capped `pyproject.toml` for a safe project name.
- Reject non-empty params.
- Register only `django_apps_discovery` in the runtime executor.
- Add focused unit tests for detection, nested package suppression, symlink safety, output safety, and unsupported tool behavior.

Out of scope:
- Baseline orchestration, baseline profiles, baseline ingestion, `Application` DB writes, ToolPolicy/PlanTool activation, migrations, other Phase 2 handlers, AI planner, external bot, remediation/actions, and shell command execution.

Result:
- Added `scanner_runtime/django_discovery.py` as a pure filesystem runtime collector rooted at `/opt` only.
- Added max-depth-2 candidate scanning, symlink realpath validation under `/opt`, heavy/hidden directory skipping, strict stat/output caps, and redacted JSON output.
- Added Django root detection using `manage.py` or strong project-root markers plus Django indicators.
- Treated `wsgi.py`, `asgi.py`, `urls.py`, and `apps.py` as supporting markers only.
- Suppressed nested Django package false positives when an ancestor is already selected as a Django root.
- Registered only `django_apps_discovery` in the runtime executor; runtime still creates no ToolRun or AgentJob.
- Added focused Sprint 2.5 tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_django_apps_discovery --noinput` passed: 15 tests ran successfully with 2 symlink tests skipped in this Windows environment.
- `.\.venv\Scripts\python.exe manage.py test --noinput` ran 200 tests before failing in `tests.unit.test_sprint8_diagnostics.Sprint8DiagnosticsTests.setUpClass` due to PostgreSQL connection timeout.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Re-run the full test suite once the local PostgreSQL test database connection is stable.
- Baseline/profile/ingestion integration and ToolPolicy/PlanTool activation remain deferred.
- No commit or push was made.

## 2026-05-31 - Phase 2 Sprint 2.6 Start

Intent:
- Implement only the approved Sprint 2.6 runtime `gunicorn_uvicorn_services_discovery` collector.

Scope:
- Add `scanner_runtime/gunicorn_uvicorn_discovery.py` using fixed `systemctl list-units` and capped `systemctl show` execution through `safe_exec.py`.
- Reject non-empty params.
- Detect `gunicorn`, `uvicorn`, and `daphne` from safe fields only (unit Id and redacted Description).
- Return only safe structured metadata and contract-compatible top-level keys: `services`, `applications`, and `summary`.
- Register only `gunicorn_uvicorn_services_discovery` in the runtime executor.
- Add focused unit tests for parsing, safety, redaction, and runtime routing behavior.

Out of scope:
- Baseline orchestration, baseline profiles, baseline ingestion, ToolPolicy/PlanTool activation, migrations, other runtime handlers, AI planner, external bot, Supervisor support, port correlation, unit file content parsing, `/proc/<pid>/cmdline`, and any write/restart actions.

Result:
- Added `scanner_runtime/gunicorn_uvicorn_discovery.py` with a safe two-step discovery flow:
  - fixed `systemctl list-units --type=service --all --no-pager --plain --no-legend`
  - fixed capped `systemctl show <unit names> --property=Id,Description,LoadState,ActiveState,SubState,UnitFileState,MainPID,FragmentPath,User,WorkingDirectory`
- Enforced unit cap before `systemctl show` and rejected non-empty params.
- Added safe parsing for `gunicorn`, `uvicorn`, and `daphne` from unit Id + redacted Description only.
- Excluded unsafe fields and sources (`ExecStart`, `Environment`, unit file contents, `/proc/<pid>/cmdline`).
- Returned only contract-compatible top-level keys: `services`, `applications`, `summary`.
- Registered only `gunicorn_uvicorn_services_discovery` in `scanner_runtime/prototype.py`.
- Added focused Sprint 2.6 tests.

Verification:
- `python manage.py check` failed locally because shell `python` is not using the project venv and cannot import Django.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` failed for the same shell `python` reason.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected and a database timeout warning.
- `python manage.py test tests.unit.test_phase2_gunicorn_uvicorn_services_discovery --noinput` failed for the same shell `python` reason.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_gunicorn_uvicorn_services_discovery --noinput` passed: 11 tests ran successfully.
- `python manage.py test --noinput` failed for the same shell `python` reason.
- `.\.venv\Scripts\python.exe manage.py test --noinput` ran 216 tests before failing in `tests.unit.test_sprint2_agent_foundation.Sprint2AgentFoundationTests.setUpClass` due to PostgreSQL connection timeout.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Re-run full suite after local PostgreSQL test connection is stable.
- Baseline/profile/ingestion integration and ToolPolicy/PlanTool activation remain deferred.
- No commit or push was made.

## 2026-05-31 - Phase 2 Sprint 2.7 Start

Intent:
- Implement only the approved Sprint 2.7 runtime `postgres_status_discovery` collector.

Scope:
- Add `scanner_runtime/postgres_discovery.py` with fixed-command discovery via `safe_exec.py`:
  - `systemctl list-units --type=service --all --no-pager --plain --no-legend`
  - capped `systemctl show <unit names> --property=Id,Description,LoadState,ActiveState,SubState,UnitFileState,MainPID,FragmentPath`
- Parse safe PostgreSQL service variants (`postgresql.service`, `postgresql@*.service`, obvious distro variants).
- Add optional fixed `pg_isready` probe (no host/user/db/password args), normalized to `ok|failed|not_available`.
- Reject non-empty params.
- Register only `postgres_status_discovery` in runtime executor.
- Add focused unit tests and run requested validation commands.

Out of scope:
- Baseline/profile/ingestion changes, ToolPolicy/PlanTool activation, migrations, other runtime handlers, AI planner, external bot, `psql`/SQL queries, `.pgpass`, connection strings, config file reads, and port inspection.

Result:
- Added `scanner_runtime/postgres_discovery.py` implementing `collect_postgres_status(params=None)`.
- Implemented safe fixed-command flow via `safe_exec.py`:
  - `systemctl list-units --type=service --all --no-pager --plain --no-legend`
  - capped `systemctl show <unit names> --property=Id,Description,LoadState,ActiveState,SubState,UnitFileState,MainPID,FragmentPath`
  - optional fixed `pg_isready` probe normalized to `ok|failed|not_available`.
- Added safe parsing for PostgreSQL units (`postgresql.service`, `postgresql@*.service`, obvious variants).
- Returned contract-compatible top-level keys only: `services`, `summary`.
- Added strict safety behavior: reject non-empty params, no raw diagnostics with secret-like key names, no `psql`, no config reads, no credentials, no connection strings.
- Registered only `postgres_status_discovery` in `scanner_runtime/prototype.py`.
- Added focused Sprint 2.7 tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_postgres_status_discovery --noinput` passed: 9 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 239 tests (4 skipped).
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Baseline/profile/ingestion integration and ToolPolicy/PlanTool activation remain deferred.
- No commit or push was made.

## 2026-05-30 - Phase 2 Sprint 2.3 Start

Intent:
- Implement only the approved Sprint 2.3 runtime `nginx_sites_discovery` collector.

Scope:
- Add a pure file-reading Nginx discovery runtime module.
- Read only `/etc/nginx/nginx.conf`, direct files under `/etc/nginx/sites-enabled/*`, and direct `*.conf` files under `/etc/nginx/conf.d/*.conf`.
- Handle safe symlinks from `sites-enabled` only when resolved targets remain under allowlisted Nginx roots.
- Parse safe server block metadata without storing raw config text.
- Register only `nginx_sites_discovery` in the runtime executor.
- Add focused tests for parsing, safety, symlink behavior, params rejection, and unsupported tool behavior.

Out of scope:
- Baseline orchestration, baseline profiles, baseline ingestion, `DiscoveredDomain`, `Application`, or `LogSource` writes, ToolPolicy/PlanTool activation, migrations, other Phase 2 handlers, AI planner, external bot, remediation/actions, and shell command execution.

Result:
- Added `scanner_runtime/nginx_discovery.py` as a pure file-reading runtime collector.
- Added code-defined Nginx config sources, safe source validation, safe symlink handling, per-file size cap, and total scanned bytes cap.
- Added Nginx `server` block parsing for safe `server_name`, `listen`, `root`, `access_log`, `error_log`, and `proxy_pass` metadata.
- Ignored cert/key/auth directives, rejected variable filesystem paths, dropped credentialed/variable proxy targets, and avoided returning raw config text.
- Registered only `nginx_sites_discovery` in the runtime executor; runtime still creates no ToolRun or AgentJob.
- Added focused Sprint 2.3 tests for parsing, safety, symlink behavior via read validation outcomes, include flagging, params rejection, and unsupported tool behavior.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_nginx_sites_discovery --noinput` passed: 12 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 185 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Baseline/profile/ingestion integration and ToolPolicy/PlanTool activation remain deferred.
- No commit or push was made.
## 2026-06-05 - Corrected Execution Plan Remote Bootstrap Update Start

Intent:
- Update only `docs/planning/CORRECTED-EXECUTION-PLAN.md` with the approved planning corrections.

Scope:
- Add Remote Bootstrap Runtime Completion as a standalone planning/implementation sprint.
- Clarify the current Remote Bootstrap foundation versus the remaining runtime bundle gap.
- Change the first full tool cycle away from `laravel_env_sanity` as the initial preferred tool.
- Clarify the dependency between C5 Tool Orchestrator and C6 Safe Command Execution Runtime.

Out of scope:
- Code, migrations, tests, runtime/service/model changes, and any server execution.

Result:
- Updated `docs/planning/CORRECTED-EXECUTION-PLAN.md` only.
- Added Sprint C1.5 / Phase 0.5: Remote Bootstrap Runtime Completion.
- Documented that the current Remote Bootstrap foundation exists, but the installed bundle is still `sprint3-bootstrap-runtime` with registration + heartbeat only.
- Clarified that C5 Tool Orchestrator can use existing safe execution paths only, and command/script template execution waits for C6.
- Changed C8 first preferred tool to `laravel_log_health` or `apache_5xx_summary`, with `laravel_env_sanity` deferred until safety controls are proven.

Verification:
- `git diff --check` passed with line-ending warnings only.
- No code, migrations, tests, runtime/service/model changes, or server execution were performed.
## 2026-06-05 - Decision Register Documentation Start

Intent:
- Create an official decision register for the corrected execution plan.

Scope:
- Add `docs/planning/DECISION-REGISTER.md`.
- Capture approved Sprint decisions, deferred decisions, and guardrails requiring explicit approval.
- Update tracking documentation only.

Out of scope:
- Code, migrations, tests, runtime/service/model changes, and server execution.

Result:
- Created `docs/planning/DECISION-REGISTER.md`.
- Captured the approved corrected execution decisions across C1 through C12.
- Captured deferred decisions and guardrails requiring explicit approval to change.

Verification:
- `git diff --check` passed with line-ending warnings only.
- No code, migrations, tests, runtime/service/model changes, or server execution were performed.

## 2026-06-05 - Sprint C2 Safe Context Builder MVP Start

Intent:
- Implement the approved `Sprint C2 - Safe Context Builder MVP`.

Scope:
- Add a dedicated `apps.ai_context` app.
- Add a deterministic safe context builder service that returns versioned, capped, redacted JSON.
- Include safe account, server, baseline, applications, services, domains, logs, findings, reports, knowledge, recommendations, recent ToolRun metadata, risk summary, and available tools metadata.
- Enforce tenant scope, role-aware tool availability, ToolPolicy/PlanTool checks, and no raw output exposure.
- Add focused unit tests.

Out of scope:
- Chat UI/models, live AI providers, tool execution, direct AgentJob creation, Telegram behavior, remediation/actions, and report redesign.

Result:
- Added `apps.ai_context` with `build_safe_context()`.
- Registered `apps.ai_context` in `INSTALLED_APPS`.
- Safe context output now includes `context_version`, metadata, capped summaries, recent ToolRun metadata without raw results, and policy-aware available tool metadata.
- Added redaction and tenant-scope safeguards before returning context.
- Added focused tests for account scoping, redaction, raw output exclusion, tool availability, caps, and safe summary fields.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_safe_context_builder --noinput` passed: 6 tests.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 300 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Testing note:
- Full suite was run for Sprint C2 because this sprint touches security-sensitive redaction, permissions, and tenant-scoped context behavior.

## 2026-06-05 - Sprint C3 Admin Chat Data Model and Read-only UI Start

Intent:
- Implement the approved `Sprint C3 - Admin Chat Data Model and Read-only UI`.

Scope:
- Add dedicated `apps.ai_chat` app.
- Add `AdminChatSession`, `AdminChatMessage`, and `AdminChatDecision` models.
- Add Portal read-only/basic chat screens for account-scoped owner/operator use.
- Store redacted messages and metadata only.
- Prevent tool execution, ToolRun creation, AgentJob creation, live AI calls, and Telegram behavior.
- Add focused tests for permissions, tenant scope, redaction, and no execution side effects.

Out of scope:
- Deterministic responder logic, live AI provider calls, tool orchestration, reports from chat, Telegram, remediation/actions, and any direct AgentJob creation.

Result:
- Added dedicated `apps.ai_chat` app.
- Added `AdminChatSession`, `AdminChatMessage`, and `AdminChatDecision` models with redacted fields and account/server/application scope validation.
- Added Django Admin registration for review of redacted chat records.
- Added Portal chat list/detail/start/message routes and templates.
- Owner/operator can start sessions and save user messages; viewer can view but cannot start or post.
- Chat MVP stores user messages only and creates no ToolRun or AgentJob.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_chat --noinput` passed: 7 tests.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected after the intended migration was created.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint6_portal --noinput` passed: 16 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 307 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Testing note:
- Full suite was run for Sprint C3 because this sprint changes Portal permissions, redaction-sensitive chat storage, and tenant-scoped access behavior.

## 2026-06-05 - Sprint C4 Deterministic Chat Responder Start

Intent:
- Implement the approved `Sprint C4 - Deterministic Chat Responder`.

Scope:
- Add deterministic context-only chat responses for status, summaries, findings, reports, and available tools.
- Store response decisions in `AdminChatDecision`.
- Store assistant replies as redacted `AdminChatMessage` records.
- Rebuild safe context when responding and store only capped/redacted decision output.

Out of scope:
- Live AI provider calls, tool execution, ToolRun/AgentJob creation, Telegram, report generation from chat, and remediation/actions.

Result:
- Added deterministic intent routing for status, findings, reports, available tools, and general summary questions.
- Added context-only assistant response generation using `build_safe_context()`.
- Added `AdminChatDecision` logging for deterministic answer decisions.
- Updated Portal chat message POST to save the user message and generate an assistant response.
- Kept C4 free of live AI, ToolRun creation, AgentJob creation, Telegram, and remediation behavior.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_chat --noinput` passed: 10 tests.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint6_portal --noinput` passed: 16 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 310 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Testing note:
- Full suite was run for Sprint C4 because this sprint changes Portal chat behavior, decision logging, redaction-sensitive response storage, and permission-protected message flow.

## 2026-06-05 - Sprint C5 Tool Orchestrator MVP Start

Intent:
- Implement the approved `Sprint C5 - Tool Orchestrator MVP`.

Scope:
- Add chat tool request model and service flow.
- Allow owner/operator to request and approve existing available read-only tools only.
- Route execution only through `create_tool_run_job()` so ToolDefinition, ToolPolicy, PlanTool, ToolRun, and AgentJob checks remain authoritative.
- Keep MVP params empty only to avoid arbitrary parameter submission in C5.
- Add focused tests for policy denial, plan denial, approval permissions, and no direct AgentJob creation.

Out of scope:
- Command/script template execution, live AI, arbitrary params, new tools, report generation, Telegram, remediation/actions, and direct AgentJob creation.

Result:
- Added `AdminChatToolRequest`.
- Added request and approval services for available chat tools.
- Approval calls existing `create_tool_run_job()` only, preserving ToolDefinition, ToolPolicy, PlanTool, ToolRun, and AgentJob enforcement.
- Added minimal Portal UI for requesting and approving tools from server-scoped chat sessions.
- Kept C5 parameterless for chat tool requests and did not add command/script template execution.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_chat --noinput` passed: 16 tests.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected after the intended migration was created.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint6_portal tests.unit.test_sprint4_tools_policy --noinput` passed: 31 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 316 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Testing note:
- Full suite was run for Sprint C5 because this sprint touches the ToolRun/AgentJob execution path and permission/policy enforcement.
- An initial regression command used a non-existent test module name; it was corrected to `tests.unit.test_sprint4_tools_policy` and rerun successfully.
