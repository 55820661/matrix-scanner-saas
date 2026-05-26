# Matrix Scanner SaaS Project Skills

This folder contains project-specific skills for building Matrix Scanner SaaS: a Django-based SaaS platform with a small Python scanner runtime installed on customer servers.

Use these guides before implementing or reviewing related parts of the project:

- [architecture.md](architecture.md): SaaS/platform/runtime boundaries, component responsibilities, and MVP constraints.
- [security.md](security.md): agent authentication, tenant isolation, bootstrap credentials, secret redaction, and read-only execution rules.
- [tool-design.md](tool-design.md): how to define safe ToolTemplates, ToolDefinitions, policy checks, and handlers.
- [diagnostics.md](diagnostics.md): scanner behavior for Linux, cPanel, Apache, PHP, MySQL, and Laravel.
- [telegram.md](telegram.md): Telegram linking, alerts, summaries, auth, and guided diagnostic rules.
- [testing.md](testing.md): project-specific testing strategy and required coverage.

## Skill Rules
- Keep MVP behavior read-only and suggest-only.
- Do not add free-form shell execution from Telegram, AI, database fields, config, or user input.
- Treat the Diagnostic Agent as a planner only; it may choose an approved tool, never execute work directly.
- Store raw secrets only in approved secret storage or environment variables; never in logs, reports, Telegram, AI prompts, or committed files.
- Prefer small, deterministic handlers with typed parameters, bounded runtime, bounded output, and explicit audit logging.
- Enforce account/tenant ownership before reading or changing any tenant-owned object.
- Matrix Admin is Django staff/superuser, not a customer role.
- Use status or soft-archive behavior for MVP deletion.
- Sprint 3 Remote Bootstrap installs/starts the Scanner Runtime and verifies heartbeat only; Baseline Scan and Security Preflight are separate later work.
- Tool Registry and Policy Engine foundation must exist before full Baseline Scan implementation.

## Related Planning Docs
- [../../docs/planning/matrix_scanner_saas_mvp_plan.md](../../docs/planning/matrix_scanner_saas_mvp_plan.md)
- [../../docs/planning/matrix_scanner_saas_execution_plan.md](../../docs/planning/matrix_scanner_saas_execution_plan.md)
- [../../docs/planning/matrix_scanner_saas_interfaces_plan.md](../../docs/planning/matrix_scanner_saas_interfaces_plan.md)
- [../../docs/planning/matrix_scanner_phase_2_5_remote_bootstrap.md](../../docs/planning/matrix_scanner_phase_2_5_remote_bootstrap.md)
