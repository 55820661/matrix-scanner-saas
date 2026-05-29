# Matrix Scanner SaaS Plans

This file is the implementation-facing plan for Matrix Scanner SaaS. It summarizes the approved direction from `docs/planning/` and the locked pre-Sprint 1 decisions.

## Product Summary

Matrix Scanner SaaS is a Django-based SaaS platform for diagnosing and monitoring customer servers, initially focused on traditional cPanel/WHM, Laravel, Apache/EasyApache, PHP, MySQL/MariaDB, `public_html`, Apache logs, Laravel logs, and related production workflows.

The customer server runs a small Python Scanner Runtime as a systemd service. The runtime polls the SaaS platform for approved jobs, executes only registered and policy-approved tools, and returns structured JSON. The SaaS platform owns tenancy, users, roles, subscriptions, tool policy, audit, reports, Telegram integrations, and Diagnostic Agent orchestration.

## Core Constraints

- MVP diagnostics are read-only and suggest-only.
- No free shell tools from Portal, Telegram, AI, database rows, or config.
- No file edits, service restarts, package changes, permission changes, IP blocking, code patches, or remediation actions in diagnostic MVP.
- Matrix Admin is Django staff/superuser, not a customer role.
- Customer roles are `owner`, `operator`, and `viewer`.
- Every tenant-owned object must be scoped by `account_id` directly or through a required parent.
- PostgreSQL RLS is deferred; ORM scoping, object ownership checks, and tests are mandatory.
- MVP deletion uses status or soft-archive behavior, not hard deletes.
- Secrets are redacted before storage, display, AI prompts, and Telegram delivery.
- Laravel `.env` handling uses allowlisted safe keys only and never stores the full `.env`.

## Locked Pre-Sprint Decisions

1. For MVP, each user belongs to one Account directly via `account_id` on the custom User model. Multi-account membership is deferred.
2. Sprint 1 AuditLog fields: `actor_user`, `actor_type`, `account`, `action`, `target_type`, `target_id`, `result`, `ip_address`, `user_agent`, `metadata`, `created_at`.
3. `metadata` must never store secrets.
4. Account statuses: `active`, `suspended`, `archived`.
5. Server statuses: `pending`, `active`, `offline`, `archived`.
6. Application review statuses: `pending_review`, `approved`, `ignored`, `archived`.
7. Subscription statuses: `trial`, `active`, `past_due`, `suspended`, `cancelled`, `expired`.
8. Registration token TTL is 60 minutes by default.
9. Registration tokens and agent tokens are one-time/raw-once and stored hashed only.
10. Archived Account prevents user login and blocks new jobs/diagnostics.
11. Archived Server blocks agent jobs and diagnostics while preserving reports/history.
12. Archived Application is hidden from active workflows while preserving reports/history.
13. Usage counters may be cached/stored in MVP, but source tables remain the source of truth and recalculation must be possible later.
14. Staff users must not act as Portal customer users unless explicitly linked to an Account. Future impersonation must be audited and is not part of Sprint 1.

## Sprint Plan

### Sprint 1 - Django SaaS Core

Goal: create the clean SaaS foundation only.

Scope:
- Django project foundation.
- PostgreSQL settings.
- Custom User from day one.
- Account, User, Server skeleton, Application skeleton, Plan, Subscription, AuditLog.
- Customer roles: owner/operator/viewer.
- Django Admin for core models.
- Status/soft-archive fields.
- Basic model/admin tests for roles, ownership, statuses, and AuditLog shape.

Out of scope:
- Agent APIs.
- Remote Bootstrap.
- Baseline Scan.
- Tool Registry runtime execution.
- Telegram.
- Diagnostic Agent.
- Remediation.

### Sprint 2 - Agent Registration and Job Foundation

Goal: connect customer servers to the SaaS platform safely.

Scope:
- ScannerAgent.
- AgentRegistrationToken with 60-minute TTL, one-time use, revocation, hashed storage.
- Agent token generation, raw-once return, hashed storage.
- Agent heartbeat.
- AgentJob model and simple polling endpoints.
- First minimal safe `system_identity` job via hardcoded allowlist only if Tool Registry is not complete yet.
- Audit for registration, heartbeat state changes, and job result ingestion.

### Sprint 3 - Remote Bootstrap MVP

Goal: allow Matrix Admin to install/start the Scanner Runtime and verify heartbeat.

Scope:
- BootstrapSession, BootstrapStep, BootstrapCredential, AgentInstallation.
- Paramiko-based SSH workflow.
- BootstrapPolicy: fixed command templates only, typed parameters only, Matrix Admin only, explicit confirmation before package install, credential TTL, encrypted temporary credentials, full audit.
- Runtime deployment via tarball/SFTP, not git clone.
- Install path `/opt/matrix_scanner`.
- systemd service install/start.
- Heartbeat verification.
- Credential cleanup on success, failure, cancellation, or expiry.

Out of scope:
- Baseline Scan.
- Security Preflight.
- Customer self-service remote bootstrap.
- Diagnostics.

### Sprint 4 - Tool Registry and Policy Engine Foundation

Goal: establish the controlled execution model before full baseline.

Scope:
- ToolTemplate.
- ToolDefinition.
- ToolPolicy.
- PlanTool.
- ToolRun.
- Input schema validation.
- Path policy.
- Risk policy with read-only MVP enforcement.
- Runtime and output limits.
- Secret redaction before persistence/display/AI/Telegram.
- Policy-approved AgentJob creation only.

### Sprint 5 - Baseline Scan Implementation

Goal: implement practical baseline discovery for cPanel/Laravel servers.

Scope:
- BaselineScan orchestration in SaaS.
- Agent runs one approved tool per job and returns structured JSON.
- Tools: system_identity, services_status, panel_detector, cpanel_domain_scanner, application_discovery, laravel_discovery, log_sources_discovery, webroot_risk_checker.
- DiscoveredDomain, DiscoveredService, LogSource.
- Applications enter `pending_review`.
- Findings created and deduplicated where possible.

Out of scope:
- Security Preflight unless explicitly pulled into a later hardening sprint.
- Remediation.

### Sprint 6 - Admin and Portal MVP

Goal: make platform data usable for Matrix Admin and customers.

Scope:
- Customized Django Admin for operational management.
- Portal templates for Dashboard, Servers, Add Server, Server Detail, Applications Pending Review, Application Detail, Findings, Subscription/Usage.
- Customer manual install token generation.
- Application review actions: approve, rename, ignore, archive.
- Read-only subscription and usage view.

### Sprint 7 - Telegram Integration MVP

Goal: link Telegram and provide summaries/alerts.

Scope:
- TelegramProfile, TelegramLinkToken, TelegramChat.
- Portal-generated short-lived link code.
- Private commands: `/start`, `/link`, `/menu`, `/servers`, `/apps`, `/findings`, `/reports`, `/help`.
- Group alerts/summaries only.
- Alerts for agent offline/recovered, critical finding newly detected, baseline completed with critical findings, bootstrap failed.
- No tool execution from Telegram in this sprint.

### Sprint 8 - Diagnostic Agent MVP from Portal

Goal: create the first guided DiagnosticSession from Portal.

Scope:
- DiagnosticSession, DiagnosticStep, AgentNote, IncidentReport skeleton.
- Agent actions: `run_tool`, `ask_user`, `final_report`, `stop`.
- Max 10 tool runs per session.
- JSON-only agent output.
- Agent can only choose available policy-approved tools.
- Prompt context contains no secrets.
- Every agent decision is stored and audited.

### Sprint 9 - Telegram Guided Diagnostics

Goal: start and follow diagnostics from Telegram private chat.

Scope:
- TelegramDiagnosticState.
- Button/menu flow: select server, application, problem type, time window, confirm.
- Same DiagnosticSession backend as Portal.
- Short notes and final summary in Telegram.
- Full report in Portal.
- Viewer cannot start diagnostics.
- Groups remain alerts/summaries only.

### Sprint 10 - Admin Tool Builder Agent MVP

Goal: help Matrix Admin create ToolDefinitions safely.

Scope:
- Matrix Admin only.
- Creates ToolDefinition metadata only, not ToolTemplate code.
- JSON-only output.
- Saves as draft.
- Manual review/approval/enable lifecycle.
- Read-only tools only.
- No automatic test execution on customer servers.

### Sprint 11 - Reports, Findings, and Knowledge Base

Goal: improve operational memory and reporting.

Scope:
- Report and ReportSection stored redacted snapshots.
- FindingGroup deduplication by account, server, optional application, and normalized fingerprint.
- KnowledgeEntry and KnowledgeSource for safe operational context.
- Advisory Recommendation records only; no executable actions.
- Portal/Admin report, finding group, and knowledge visibility.
- Telegram short safe report summaries.

Deferred from Sprint 11:
- IncidentReport model.
- AlertEvent model; use TelegramNotification for notification history and suppression.
- KnowledgePattern model; use KnowledgeEntry and KnowledgeSource.
- PDF export.
- Email reports.
- Scheduled reports.
- Celery/report workers.
- Live LLM report generation.
- Remediation workflows.

### Sprint 12 - Stabilization, Security Hardening, and Pilot Readiness

Goal: harden the MVP for internal pilot.

Scope:
- Security review for agent auth, registration tokens, bootstrap credentials, tenant isolation, tool policy, redaction, Telegram linking, Admin/Portal permissions.
- Timeouts and output caps on every ToolRun.
- Documentation cleanup for the implemented sprint order and deferred features.
- Deployment notes for Gunicorn, Nginx, systemd, PostgreSQL, environment variables, logging, and backups.
- Release checklist and manual smoke checklist.
- Regression tests for security, redaction, tenant isolation, and permissions.
- Internal pilot on Matrix Clouds/WhatsApp SaaS infrastructure.

Out of scope:
- Celery/Redis implementation.
- Live LLM execution.
- Remediation/write/destructive tools.
- Payment gateway.
- PDF/email/scheduled reporting.
- Customer Remote Bootstrap.

## Post-MVP

- Self-install hardening.
- Limited customer pilot.
- Payment gateway.
- PDF/email reports.
- Celery/Redis workers.
- Live LLM execution.
- PostgreSQL RLS.
- Multi-account membership.
- Full self-install automation.
- Advanced knowledge matching.
- Low-risk actions study.
- Advanced/sensitive actions only after read-only MVP proves stable.
