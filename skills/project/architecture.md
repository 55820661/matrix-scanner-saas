# Matrix Scanner SaaS Architecture Skill

## Purpose
Use this skill when designing or changing Matrix Scanner SaaS components, package layout, data flow, app boundaries, agent runtime behavior, or sprint phase boundaries.

## Core Principles
- The platform is a Django SaaS with PostgreSQL, DRF, Celery/Redis, Django Admin, and a portal built with Django templates in MVP.
- The customer server runs only the Python Scanner Runtime as a systemd service.
- Agent communication is outbound polling from the customer server to the SaaS platform.
- The MVP is read-only for diagnostics: no file edits, service restarts, package changes, remediations, or free shell tools.
- Remote Bootstrap is an admin-only provisioning workflow and must stay separate from customer diagnostic tools.
- Sprint 3 Remote Bootstrap installs/starts the Scanner Runtime and verifies heartbeat only. Baseline Scan belongs to the following sprint, and Security Preflight is deferred.
- Tool Registry and Policy Engine foundation comes before full Baseline Scan implementation.
- Every diagnostic action must pass tenant authorization, tool policy, parameter validation, output limits, redaction, and audit logging.
- Missing services, missing logs, and permission failures should become structured findings or partial results, not crashes.

## Sprint 1 Boundaries
- Build the Django SaaS foundation only.
- Include Account, custom User, customer roles, Server/Application skeletons, Plan, Subscription, and AuditLog.
- Matrix Admin is represented by Django staff/superuser, not by a customer role.
- Customer roles are `owner`, `operator`, and `viewer`.
- Tenant-owned models should carry `account_id` directly or through a required parent.
- Use status or soft-archive patterns in MVP instead of hard deletes.
- Do not add agent APIs, bootstrap execution, baseline orchestration, Telegram flows, Diagnostic Agent, or remediation behavior in Sprint 1.

## Component Boundaries
- `accounts`: Account, custom User, roles, membership, and tenant ownership.
- `servers`: Server records, ScannerAgent, registration tokens, heartbeat state, and installations.
- `applications`: discovered domains/apps, application review status, log sources, and app metadata.
- `plans` and `subscriptions`: dynamic limits, features, tool availability, and usage visibility.
- `audit`: append-only record of sensitive actions, policy decisions, and operational events.
- `tools`: ToolTemplate, ToolDefinition, ToolPolicy, PlanTool, and ToolRun.
- `agent jobs`: platform-created jobs consumed by scanner runtime polling.
- `bootstrap`: Matrix Admin remote install sessions, steps, temporary encrypted credentials, and installation records.
- `diagnostics`: DiagnosticSession, DiagnosticStep, AgentNote, IncidentReport, and session orchestration.
- `telegram`: account linking, chat/group records, menus, summaries, alerts, and guided diagnostics.
- `matrix_scanner`: Python runtime package installed on customer servers; it executes approved local tools only.

## Required Checks Before Design Changes
- Does the change preserve read-only behavior?
- Is the tenant/account boundary enforced at the model, service, API, and UI level?
- Is the handler reachable only through a ToolDefinition backed by a known ToolTemplate?
- Is the action logged in AuditLog and ToolRun or BootstrapStep where applicable?
- Are all outputs bounded, redacted, and safe for Admin, Portal, Telegram, and AI prompts?
- Does the agent job remain idempotent and safe to retry?
- Does it work when a dependency is missing, unavailable, or permission-restricted?
- Does it avoid storing secrets in database fields that are not explicitly encrypted and short-lived?
- Does the change respect the current sprint boundary?
- If deleting or disabling data, does it use status/soft-archive behavior rather than hard delete?

## Common Pitfalls
- Letting AI, Telegram, Admin forms, or database rows construct free-form commands.
- Mixing bootstrap tools with customer diagnostic tools.
- Relying on UI filtering for tenant isolation instead of backend enforcement.
- Storing raw `.env`, SSH credentials, agent tokens, or provider keys in reports or logs.
- Coupling scanner code to Portal or Telegram formatting.
- Adding remediation behavior before the read-only MVP is stable.
