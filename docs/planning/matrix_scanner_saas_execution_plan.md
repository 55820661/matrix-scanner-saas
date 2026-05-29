# Matrix Scanner SaaS Execution Plan

This document reflects the final implemented MVP sprint order through Sprint 12 planning. Older planning text that conflicts with this document is superseded.

## MVP Rule

```text
Read-only first.
No free shell commands.
No file edits.
No service restarts.
No remediation actions.
All execution goes through approved Tool Definitions and ToolPolicy.
```

## Stack

- SaaS platform: Django.
- Database: PostgreSQL.
- Admin: Django Admin.
- Portal: Django Templates.
- Telegram: webhook-based bot.
- Scanner Runtime: Python, installed as a systemd service.
- Agent communication: polling from customer server to SaaS.
- Celery/Redis: deferred future production components, not implemented in MVP Sprint 12.

## Sprint 1 - Django SaaS Core

Core SaaS foundation:

- `Account`
- custom `User`
- `Plan`
- `Subscription`
- `Server`
- `Application`
- `AuditLog`
- Django Admin

Out of scope: agent APIs, bootstrap, baseline, tools, Telegram, diagnostics, remediation.

## Sprint 2 - Agent Registration Foundation

Connect servers to the platform:

- `ScannerAgent`
- `AgentRegistrationToken`
- `AgentJob`
- `BaselineScan` skeleton
- one-time hashed registration tokens
- hashed raw-once agent tokens
- heartbeat, job polling, job result endpoint
- temporary `system_identity` allowlist fallback

Out of scope: Remote Bootstrap and full Baseline Scan.

## Sprint 3 - Remote Bootstrap MVP

Matrix Admin-only runtime install/start:

- `BootstrapSession`
- `BootstrapStep`
- `BootstrapCredential`
- `AgentInstallation`
- Paramiko SSH
- temporary encrypted credentials with TTL and cleanup
- fixed command templates only
- explicit package install confirmation
- deploy runtime by tarball/SFTP
- install path `/opt/matrix_scanner`
- service `matrix-scanner-agent.service`
- heartbeat verification only

Out of scope: Baseline Scan, Security Preflight, diagnostics, customer bootstrap.

## Sprint 4 - Tool Registry and Policy Engine MVP

Controlled execution foundation before Baseline:

- `ToolTemplate`
- `ToolDefinition`
- `ToolPolicy`
- `PlanTool`
- `ToolRun`
- registry-backed `system_identity`
- input validation
- path policy
- read-only risk enforcement
- output and timeout caps
- ToolPolicy-approved AgentJob creation only

Out of scope: full Baseline Scan, Diagnostic Agent, Telegram-guided execution, remediation.

## Sprint 5 - Baseline Scan Implementation

Practical read-only baseline using Tool Registry and ToolPolicy:

- `BaselineScanStep`
- `DiscoveredService`
- `DiscoveredDomain`
- `LogSource`
- `Finding`
- baseline tools:
  - `system_identity`
  - `services_status`
  - `panel_detector`
  - `cpanel_domain_scanner`
  - `application_discovery`
  - `laravel_discovery`
  - `log_sources_discovery`
  - `webroot_risk_checker`
- Application records created as `pending_review`
- Laravel `.env` allowlisted safe keys only

Out of scope: remediation, raw logs, raw `.env`, full Security Preflight.

## Sprint 6 - Admin and Portal MVP Screens

Usable Admin and customer Portal:

- Portal dashboard.
- server list/detail/add.
- registration token generation.
- application review actions.
- findings actions.
- baseline read-only visibility.
- subscription read-only.
- Telegram/diagnostics/reports placeholders where not yet implemented.

Remote Bootstrap remains Admin-only.

## Sprint 7 - Telegram Integration MVP

Telegram read-only communication:

- `TelegramChatLink`
- `TelegramLinkToken`
- `TelegramNotification`
- webhook secret validation
- private and group chat linking
- read-only commands
- safe notifications

Out of scope: diagnostics from Telegram, ToolRun/AgentJob creation from Telegram, remediation.

## Sprint 8 - Diagnostic Agent MVP

Portal-only deterministic diagnostics:

- `DiagnosticSession`
- `DiagnosticStep`
- `DiagnosticDecision`
- deterministic planner
- owner/operator starts sessions
- viewer read-only
- approval before each tool step
- uses `ToolDefinition -> ToolPolicy -> ToolRun -> AgentJob`
- concise redacted report on `DiagnosticSession`

Out of scope: live LLM, Telegram guided diagnostics, remediation.

## Sprint 9 - Telegram Guided Diagnostics

Private-chat guided diagnostics:

- `TelegramDiagnosticState`
- `/diagnose`, `/cancel`, `/approve`, `/session`, `/report`
- callback query support
- one active state per private chat
- owner/operator only
- viewer blocked
- groups remain alerts/summaries only
- approvals use existing Diagnostic service and ToolPolicy path

Out of scope: group diagnostics, live LLM, remediation.

## Sprint 10 - Admin Tool Definition Proposal Builder

Matrix Admin-only proposal builder inside `apps/tools`:

- `ToolBuildRequest`
- `ToolBuildProposal`
- `ToolBuildReview`
- `ToolTestResult`
- deterministic metadata-only proposal generation
- validation over allowlisted existing runtime handlers
- conversion only to draft/pending_review ToolDefinition
- inactive conservative ToolPolicy on conversion

Out of scope: live LLM, executable code generation, runtime handler generation, ToolRun/AgentJob creation, automatic enablement, automatic PlanTool attachment.

## Sprint 11 - Reports, Findings, and Knowledge Base Enhancement

Operational memory and safe reporting:

- `Report`
- `ReportSection`
- `FindingGroup`
- `KnowledgeEntry`
- `KnowledgeSource`
- `Recommendation`
- stored redacted report snapshots
- finding grouping/deduplication
- advisory-only recommendations
- Portal report/finding group pages
- safe Telegram report summaries

Deferred from earlier planning:

- IncidentReport model.
- AlertEvent model.
- KnowledgePattern model.
- PDF/email/scheduled reports.
- Celery/report workers.
- live LLM report generation.
- remediation workflows.

## Sprint 12 - Stabilization, Security Hardening, and Release Preparation

Final MVP stabilization:

- final test pass
- security hardening review
- tenant isolation review
- secret handling and redaction review
- permission review
- Admin/Portal/Telegram access review
- ToolPolicy enforcement review
- migration consistency review
- settings/env validation
- documentation cleanup
- deployment notes
- runbook
- release checklist
- manual smoke checklist

Sprint 12 must not implement:

- remediation/actions
- write tools
- live LLM execution
- Celery/Redis
- payment gateway
- PDF export
- email reports
- scheduled reports
- customer Remote Bootstrap
- new product workflows
- ToolPolicy bypass
- direct AgentJob creation outside existing approved flows

## Post-MVP Deferred Features

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
