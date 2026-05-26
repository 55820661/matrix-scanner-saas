# Project Structure

This repository is organized as a Django SaaS platform with a future Python Scanner Runtime package. The directories are intentionally scaffolded before implementation so each sprint has a clear destination.

## Top-Level Layout

```text
.
├── apps/
│   ├── accounts/
│   ├── applications/
│   ├── audit/
│   ├── bootstrap/
│   ├── core/
│   ├── diagnostics/
│   ├── plans/
│   ├── servers/
│   ├── subscriptions/
│   ├── telegram_integration/
│   └── tools/
├── config/
├── docs/
│   ├── architecture/
│   ├── operations/
│   ├── planning/
│   └── security/
├── scanner_platform/
├── scanner_runtime/
├── scripts/
├── skills/
├── templates/
│   ├── admin/
│   └── portal/
└── tests/
```

## Django Apps

- `apps/accounts`: Account, custom User, roles, account status, login eligibility.
- `apps/servers`: Server, ScannerAgent, registration tokens, heartbeat state, agent installations.
- `apps/applications`: Application skeleton, discovered domains/apps, review status, log sources.
- `apps/plans`: Plan, plan features, limits, tool availability metadata.
- `apps/subscriptions`: Subscription state, billing period fields, usage visibility.
- `apps/audit`: AuditLog and audit helpers.
- `apps/tools`: ToolTemplate, ToolDefinition, ToolPolicy, PlanTool, ToolRun, redaction and policy services.
- `apps/bootstrap`: Matrix Admin remote bootstrap sessions, steps, credentials, and installation records.
- `apps/diagnostics`: DiagnosticSession, DiagnosticStep, AgentNote, IncidentReport.
- `apps/telegram_integration`: Telegram profiles, link tokens, chats, alert routing, diagnostic state.
- `apps/core`: shared constants, base models, status helpers, tenancy helpers.

## Platform Package

- `scanner_platform/`: Django project settings, URLs, WSGI/ASGI, Celery app, and environment-specific settings modules.
- `config/`: non-secret local examples and deployment configuration templates.
- `templates/`: Django template roots for Admin overrides and Portal screens.

## Runtime Package

- `scanner_runtime/`: future Python package deployed to customer servers.
- The runtime must remain separate from SaaS app code.
- It should execute only platform-approved jobs and return structured JSON.

## Tests

- `tests/unit`: fast unit tests for models, services, policy, redaction, and helpers.
- `tests/integration`: Django integration tests for APIs, permissions, registration, bootstrap state, and workflows.
- `tests/fixtures`: sanitized sample logs, cPanel userdata, Laravel layouts, and scanner outputs.

## Documentation

- `PLANS.md`: implementation-facing sprint plan.
- `docs/DECISIONS.md`: locked decisions and rationale.
- `docs/IMPLEMENTATION-CHECKLIST.md`: sprint-by-sprint execution checklist.
- `docs/SECURITY-MODEL.md`: security constraints and expected enforcement.
- `docs/TEST-PLAN.md`: testing strategy and acceptance coverage.
- `docs/planning/`: original planning source documents.
