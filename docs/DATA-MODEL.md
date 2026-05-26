# Data Model

This is the implementation-facing data model guide. It should be updated as models are implemented.

## Sprint 1 Core Models

### Account

Purpose: tenant/customer container.

Fields:
- `id`
- `name`
- `type`: company or individual
- `status`: `active`, `suspended`, `archived`
- `created_at`
- `updated_at`

Rules:
- Archived accounts cannot log in or start jobs/diagnostics.
- Historical data remains available to Matrix Admin and for retained reports.

### User

Purpose: custom Django user.

Fields:
- `id`
- `account_id`
- `name`
- `email`
- `password`
- `role`: `owner`, `operator`, `viewer`
- `status`
- `telegram_id` later
- `created_at`
- `updated_at`

Rules:
- MVP user belongs to exactly one Account.
- Matrix Admin is Django staff/superuser, not a customer role.
- Multi-account membership is deferred.

### Server

Purpose: customer server record.

Fields:
- `id`
- `account_id`
- `name`
- `hostname`
- `public_ip`
- `status`: `pending`, `active`, `offline`, `archived`
- `agent_status`
- `last_seen_at`
- `created_at`
- `updated_at`

Rules:
- Archived servers cannot receive jobs or diagnostics.
- Reports/history remain accessible.

### Application

Purpose: discovered or reviewed application on a server.

Fields:
- `id`
- `account_id`
- `server_id`
- `name`
- `domain`
- `path`
- `framework`
- `review_status`: `pending_review`, `approved`, `ignored`, `archived`
- `status`
- `created_at`
- `updated_at`

Rules:
- Discovered apps enter `pending_review`.
- Archived apps are hidden from active workflows but history remains accessible.

### Plan

Purpose: dynamic SaaS plan definition.

Fields:
- `id`
- `name`
- `description`
- `price`
- `currency`
- `billing_cycle`
- `max_servers`
- `max_applications`
- `max_users`
- `max_diagnostic_sessions_per_month`
- `retention_days`
- `is_active`
- `created_at`
- `updated_at`

### Subscription

Purpose: Account-to-Plan relationship.

Fields:
- `id`
- `account_id`
- `plan_id`
- `status`: `trial`, `active`, `past_due`, `suspended`, `cancelled`, `expired`
- `start_date`
- `end_date`
- `current_period_start`
- `current_period_end`
- `trial_ends_at`
- `auto_renew`
- `cancelled_at`
- `created_at`
- `updated_at`

### AuditLog

Purpose: append-only operational record.

Fields:
- `id`
- `actor_user`
- `actor_type`: suggested values `user`, `admin`, `agent`, `system`
- `account`
- `action`
- `target_type`
- `target_id`
- `result`
- `ip_address`
- `user_agent`
- `metadata`
- `created_at`

Rules:
- `metadata` must never store secrets.
- Use a central audit helper/service.

## Later Models

### Agent and Jobs

- ScannerAgent
- AgentRegistrationToken
- AgentJob
- AgentInstallation

### Bootstrap

- BootstrapSession
- BootstrapStep
- BootstrapCredential

### Tools and Policy

- ToolTemplate
- ToolDefinition
- ToolPolicy
- PlanTool
- ToolRun

### Baseline and Findings

- BaselineScan
- DiscoveredService
- DiscoveredDomain
- LogSource
- Finding

### Diagnostics and Reports

- DiagnosticSession
- DiagnosticStep
- AgentNote
- IncidentReport
- ReportSection

### Telegram

- TelegramProfile
- TelegramLinkToken
- TelegramChat
- TelegramDiagnosticState
