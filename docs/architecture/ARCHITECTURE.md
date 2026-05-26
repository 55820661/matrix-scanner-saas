# Architecture

Matrix Scanner SaaS is split into a central SaaS platform and a small scanner runtime installed on customer servers.

## SaaS Platform

Responsibilities:
- Accounts and users.
- Roles and permissions.
- Plans, subscriptions, and usage.
- Servers and applications.
- Agent registration and jobs.
- Tool Registry and Policy Engine.
- Remote Bootstrap.
- Baseline orchestration.
- Findings and reports.
- Diagnostic Agent orchestration.
- Telegram linking, alerts, and summaries.
- Audit logging.

## Scanner Runtime

Responsibilities:
- Register with SaaS once using a one-time token.
- Store agent token locally.
- Send heartbeat.
- Poll for jobs.
- Execute only supported approved local tools.
- Return structured JSON.
- Reject unknown tools defensively.

The runtime does not own tenancy, subscriptions, policy decisions, reports, or AI decisions.

## Data Flow

```text
Portal/Admin creates intent
SaaS validates account/role/policy
SaaS creates AgentJob
Scanner Runtime polls job
Runtime executes approved local handler
Runtime returns structured JSON
SaaS redacts, stores, audits, and updates reports/findings
```

## Execution Boundary

The Diagnostic Agent and Telegram never execute work directly. They can only request or select available tools through the SaaS policy layer.
