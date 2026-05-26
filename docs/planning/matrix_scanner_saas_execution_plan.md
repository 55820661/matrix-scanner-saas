# Matrix Scanner SaaS — Execution Plan

## Overview

This document is the approved execution plan for **Matrix Scanner SaaS**.

The platform will be built as a Django-based SaaS hosted centrally on Matrix Clouds / WhatsApp SaaS infrastructure. The scanner itself will be a small Python runtime installed on each customer server.

Initial target environments:

- cPanel / WHM
- Laravel applications
- Apache / EasyApache
- PHP / MySQL
- `public_html` structures
- Apache domlogs
- Laravel logs
- Telegram-based operations and alerts

Core rule for MVP:

```text
Read-only first.
No free shell commands.
No file edits.
No service restarts.
No remediation actions.
All execution goes through approved Tool Definitions and Policy Engine.
```

---

# Approved Technical Stack

```text
SaaS Platform: Django
API: Django REST Framework
Database: PostgreSQL
Background Jobs: Celery + Redis
Admin: Django Admin customized
Portal: Django Templates in MVP
Telegram: Webhook-based bot
Scanner Runtime: Python
Server Runtime Mode: systemd service
Agent Communication: Polling from customer server to SaaS
Initial Deployment: Matrix Clouds / WhatsApp SaaS server
```

---

# Sprint 1 — Django SaaS Core

## Goal

Create the Django SaaS foundation.

## Approved decisions

```text
Project name: scanner_platform
Database: PostgreSQL
Custom User from day one
Roles: owner / operator / viewer
Initial interface: Django Admin
Portal UI deferred to Sprint 6
Payments deferred, but Plans and Subscriptions included now
AuditLog included from day one
```

## Django apps

```text
accounts
servers
applications
plans
subscriptions
audit
core
```

## Core models

```text
Account
User
Server
Application
Plan
Subscription
AuditLog
```

## Expected output

```text
Django project works.
PostgreSQL connected.
Custom User ready.
Accounts, roles, servers, applications, plans, subscriptions ready.
AuditLog ready.
Django Admin usable.
```

---

# Sprint 2 — Server Agent Registration & Baseline Foundation

## Goal

Connect customer servers to the SaaS platform.

## Approved decisions

```text
Each Server has one ScannerAgent in MVP.
Agent uses one-time registration token.
After registration, Agent uses separate agent_token.
Raw tokens are never stored; only hashes are stored.
First tool: system_identity.
Runtime starts as simple Python CLI, then systemd.
Default polling interval: 30 seconds.
AgentJob introduced in Sprint 2.
BaselineScan and Finding skeleton introduced in Sprint 2.
Remote Bootstrap deferred to Sprint 3.
```

## New models

```text
ScannerAgent
AgentRegistrationToken
AgentJob
BaselineScan
Finding skeleton
```

## Agent API endpoints

```http
POST /api/agent/register/
POST /api/agent/heartbeat/
GET  /api/agent/jobs/next/
POST /api/agent/jobs/{job_id}/result/
```

## Expected output

```text
Server can be created.
Registration token can be generated.
Scanner Runtime can register.
Agent sends heartbeat.
Agent polls jobs.
Agent runs system_identity.
Structured result is stored.
```

---

# Sprint 3 — Remote Bootstrap MVP

## Goal

Allow Matrix Admin to install Scanner Runtime remotely on customer servers.

## Approved decisions

```text
Remote Bootstrap is Matrix Admin only.
SSH library: paramiko.
Default install path: /opt/matrix_scanner.
Runtime deployment: tarball/SFTP, not git clone.
systemd service required.
Heartbeat wait after start: 60 seconds.
Credentials are temporary, encrypted, and deleted after session.
Full Security Preflight deferred.
Self Install deferred but designed for.
Sprint 3 installs and starts agent only; no diagnostics.
```

## New models

```text
BootstrapSession
BootstrapStep
BootstrapCredential
AgentInstallation
```

## Bootstrap tools

```text
ssh_connectivity_check
remote_os_probe
privilege_check
python_runtime_detector
package_manager_detector
bootstrap_directory_prepare
scanner_code_deploy
scanner_config_write
scanner_venv_create
scanner_dependencies_install
systemd_service_install
systemd_service_start
agent_heartbeat_verify
bootstrap_cleanup
```

## Install structure

```text
/opt/matrix_scanner
/opt/matrix_scanner/.venv
/opt/matrix_scanner/config.yaml
/opt/matrix_scanner/logs
/opt/matrix_scanner/data
```

## Expected output

```text
Matrix Admin can start Bootstrap Session.
System connects over SSH.
Runtime is deployed to /opt/matrix_scanner.
systemd service is installed and started.
Heartbeat is verified.
Credentials are cleaned up.
All steps are audited.
```

---

# Sprint 4 — Baseline Scan Implementation

## Goal

Implement first practical Baseline Scan.

## Approved decisions

```text
Baseline orchestration happens in SaaS Platform, not Agent.
Agent runs one tool per job and returns structured JSON.
Sprint 4 focuses on cPanel + Laravel.
WordPress is only classified initially.
All discovered apps enter Pending Review.
Laravel env reader only exposes safe keys.
Findings are stored only; alerts deferred.
webroot_risk_checker included.
Full Git metadata deferred.
Full Security Preflight deferred, but webroot risks included.
```

## Baseline tools

```text
system_identity
services_status
panel_detector
cpanel_domain_scanner
application_discovery
laravel_discovery
log_sources_discovery
webroot_risk_checker
```

## New/expanded models

```text
DiscoveredService
DiscoveredDomain
Application
LogSource
Finding
```

## Expected output

```text
BaselineScan can be launched.
Server metadata is updated.
Services are discovered.
cPanel domains are discovered.
Applications are discovered.
Laravel safe env data is read.
Log sources are stored.
Initial findings are created.
Applications appear as Pending Review.
```

---

# Sprint 5 — Tool Registry & Policy Engine MVP

## Goal

Move tools into a controlled registry and enforce policies.

## Approved decisions

```text
Tool Registry starts in Sprint 5.
All Core Tools are registered in database.
No tool runs except via ToolDefinition.
ToolTemplate represents code executor.
ToolDefinition represents available tool.
PlanTool controls tools per plan.
Policy Engine blocks any non-read-only tool in MVP.
Secret Redaction is mandatory.
ToolRun records every execution.
Admin Tool Builder Agent deferred.
```

## New models

```text
ToolTemplate
ToolDefinition
ToolPolicy
PlanTool
ToolRun
```

## Policy checks

```text
User permission
Tool enabled
Tool available in plan
Risk level = read_only in MVP
Params match schema
Paths are baseline-discovered or allowed
Runtime and output limits set
```

## Secret redaction examples

```text
APP_KEY
DB_PASSWORD
MAIL_PASSWORD
API_KEY
SECRET
TOKEN
PRIVATE KEY
Authorization
Bearer
password=
```

## Expected output

```text
Tools are managed through registry.
Plan controls allowed tools.
ToolRun is logged.
Policy rejects unsafe requests.
Secrets are redacted.
AgentJob is only created after policy approval.
```

---

# Sprint 6 — Admin & Portal MVP Screens

## Goal

Build practical Admin and Portal screens.

## Approved decisions

```text
Admin uses customized Django Admin.
Portal uses Django Templates.
No React/Vue in MVP.
Remote Bootstrap remains Admin-only.
Customer can generate manual install token from Portal.
Discovered apps are reviewed in Portal.
Findings appear with acknowledge/ignore.
Subscription & Usage are read-only for customer.
Telegram Settings page added as initial UI.
Dashboard is simple and functional, not final design.
```

## Admin screens

```text
Admin Dashboard
Accounts
Users
Servers
Server Detail
Applications
Plans
Subscriptions
Tool Registry
Bootstrap Sessions
Baseline Scans
Findings
Audit Logs
```

## Portal screens

```text
Dashboard
My Servers
Add Server
Server Detail
Applications Pending Review
Application Detail
Findings
Diagnostic Sessions placeholder
Reports placeholder
Telegram Settings placeholder
Subscription & Usage
```

## Expected output

```text
Matrix Admin can manage platform basics.
Customers can see servers/apps/findings.
Customers can approve/rename discovered apps.
Usage and subscription are visible.
System is ready for Telegram and Diagnostic Agent.
```

---

# Sprint 7 — Telegram Integration MVP

## Goal

Connect Telegram for linking, menus, summaries, and alerts.

## Approved decisions

```text
Telegram bot uses Webhook in production.
Linking uses temporary code from Portal.
Private chat supports menu and summaries.
Groups are alerts-only in MVP.
No tool execution from Telegram in Sprint 7.
No Diagnostic Agent from Telegram in Sprint 7.
Alerts only for recent events.
No long outputs or secrets in Telegram.
Important Telegram interactions are audited.
Permissions rely fully on SaaS roles.
```

## New models

```text
TelegramProfile
TelegramLinkToken
TelegramChat
```

## Commands

```text
/start
/link <code>
/menu
/servers
/apps
/findings
/reports
/help
```

## Alerts

```text
Agent offline
Agent recovered
Critical finding newly detected
Baseline completed with critical findings
Bootstrap failed
```

## Expected output

```text
Users can link Telegram.
Owners can link groups for alerts.
Bot displays server/app/finding/report summaries.
Critical alerts are sent.
Tenant isolation and roles are respected.
```

---

# Sprint 8 — Diagnostic Agent MVP

## Goal

Add the first working Diagnostic Agent from Portal.

## Approved decisions

```text
Diagnostic Agent starts from Portal only.
Telegram diagnosis deferred to Sprint 9.
Agent output must be JSON only.
Agent can only choose available_tools.
Max 10 tool runs per session.
Read-only tools auto-approved inside session.
AI provider configured from env in Sprint 8.
Prompt context contains no secrets.
Every agent decision is stored.
Every completed session creates IncidentReport.
```

## New models

```text
DiagnosticSession
DiagnosticStep
AgentNote
IncidentReport skeleton
```

## Supported agent actions

```text
run_tool
ask_user
final_report
stop
```

Forbidden:

```text
run_shell
edit_file
restart_service
change_env
block_ip
```

## MVP session types

```text
slowness
http_500
security_scan
laravel_production_audit
custom
```

## Expected output

```text
Diagnostic session starts from Portal.
Agent reads baseline and available tools.
Agent selects read-only tools.
Tool runs execute through policy and AgentJob.
Agent notes appear in Portal.
Final report appears in Portal.
IncidentReport is generated.
```

---

# Sprint 9 — Telegram Guided Diagnostics

## Goal

Start and follow diagnostic sessions from Telegram private chat.

## Approved decisions

```text
Telegram diagnostics start from private chat only.
Groups remain alerts/summaries only.
Start flow uses buttons/menus, not free-form initially.
Natural free-form support deferred or limited.
Telegram uses same DiagnosticSession backend.
Read-only tools auto-approved inside session.
Viewer cannot start diagnostic sessions.
Telegram report is very short.
Full report opens in Portal.
All diagnostic Telegram interactions are audited.
```

## New model

```text
TelegramDiagnosticState
```

## Flow

```text
Start Diagnosis
Select Server
Select Application
Select Problem Type
Select Time Window
Confirm
Run session
Show notes
Show final report
```

## Buttons

```text
Stop
Show Details
Final Report
```

## Expected output

```text
User can start diagnostic from private Telegram chat.
Agent notes are summarized in Telegram.
Session can be stopped.
Final summary appears in Telegram.
Full report is available in Portal.
Roles and plan limits are respected.
```

---

# Sprint 10 — Admin Tool Builder Agent MVP

## Goal

Add internal Admin Tool Builder Agent for dynamic tool definitions.

## Approved decisions

```text
Admin Tool Builder Agent enters Sprint 10.
Available to Matrix Admin only.
Creates ToolDefinition only, not ToolTemplate.
Agent output is JSON only.
New tools save as Draft first.
Tool appears to Diagnostic Agent only after approved + enabled.
No shell or free code.
Sprint 10 supports read-only tools only.
No automatic tool test on server in Sprint 10.
All Tool Builder activity is audited.
```

## Tool lifecycle

```text
draft
pending_review
approved
enabled
disabled
deprecated
rejected
```

## Expected output

```text
Matrix Admin writes description of a tool.
Tool Builder suggests ToolDefinition JSON.
System validates it.
Tool is saved as Draft.
Matrix Admin reviews and approves/enables it.
Only approved + enabled tools appear to Diagnostic Agent.
```

---

# Sprint 11 — Reports, Findings & Knowledge Base Enhancement

## Goal

Improve reports and findings into operational memory.

## Approved decisions

```text
Use general Finding instead of BaselineFinding only.
Every Finding has fingerprint to avoid duplicates.
Alert only for new or recently active findings.
IncidentReport consists of ReportSections.
Developer Report starts in Sprint 11.
KnowledgePattern table starts simple and internal.
PDF export deferred.
Email alerts deferred.
Portal shows Reports and Findings clearly.
Admin sees AlertEvents and KnowledgePatterns.
```

## New/expanded models

```text
IncidentReport
ReportSection
Finding
AlertEvent
KnowledgePattern
```

## Finding statuses

```text
open
acknowledged
resolved
ignored
```

## Report sections

```text
summary
evidence
timeline
tools_executed
findings
recommendations
developer_notes
```

## Expected output

```text
Reports become structured.
Findings are deduplicated by fingerprint.
Historical findings do not spam alerts.
AlertEvent tracks sent/suppressed alerts.
KnowledgePattern stores reusable operational patterns.
Developer Report can be generated for technical issues.
```

---

# Sprint 12 — MVP Stabilization, Security Hardening & Release Preparation

## Goal

Stabilize MVP for internal pilot.

## Approved decisions

```text
Sprint 12 adds no major features.
First pilot is internal only.
No external customer before Matrix Clouds and WhatsApp SaaS tests.
Secrets must never appear in Admin/Portal/Telegram/AI.
Invalid AI JSON fails safely.
Every ToolRun has timeout and max output.
Every Bootstrap credential has TTL and is deleted after session.
Deployment is on Matrix Clouds / WhatsApp SaaS server.
Basic documentation is Markdown inside project.
After Sprint 12: Pilot Feedback and improvements.
```

## Security review areas

```text
Agent authentication
Registration tokens
Bootstrap credentials
Tenant isolation
Tool policy checks
Secret redaction
Telegram linking
Admin permissions
Portal permissions
```

## Deployment readiness

```text
Django settings
PostgreSQL
Redis
Celery
Gunicorn
Nginx
systemd services
environment variables
logging
backup plan
```

## Expected services

```text
scanner-platform-web.service
scanner-platform-celery.service
scanner-platform-celerybeat.service later
Telegram webhook handled by Django
```

## Acceptance criteria

```text
Account/User/Server can be created.
Scanner Runtime can be installed manually or via Remote Bootstrap.
Agent registers and sends heartbeat.
Baseline discovers cPanel/Laravel/apps/log sources.
Findings appear in Admin/Portal.
Tool Registry and Policy Engine work.
Portal diagnostic session works and produces report.
Telegram shows summaries, alerts, and short reports.
No secrets appear in outputs or prompts.
AuditLog records core operations.
```

---

# Final Sprint Order

```text
Sprint 1  — Django SaaS Core
Sprint 2  — Server Agent Registration & Baseline Foundation
Sprint 3  — Remote Bootstrap MVP
Sprint 4  — Baseline Scan Implementation
Sprint 5  — Tool Registry & Policy Engine MVP
Sprint 6  — Admin & Portal MVP Screens
Sprint 7  — Telegram Integration MVP
Sprint 8  — Diagnostic Agent MVP
Sprint 9  — Telegram Guided Diagnostics
Sprint 10 — Admin Tool Builder Agent MVP
Sprint 11 — Reports, Findings & Knowledge Base Enhancement
Sprint 12 — MVP Stabilization, Security Hardening & Release Preparation
```

---

# After Sprint 12

```text
Internal pilot on Matrix Clouds server
Internal pilot on WhatsApp SaaS server
Pilot feedback
First limited customer pilot
Low-risk actions study
Self-install full support
Payment gateway
PDF/Email reports
Advanced actions later
```
