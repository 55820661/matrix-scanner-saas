# Matrix Scanner SaaS Testing Skill

## Purpose
Use this skill when adding tests for Matrix Scanner SaaS. It complements the general testing skill with project-specific requirements for Django apps, scanner runtime, agent APIs, tool policy, bootstrap, diagnostics, and Telegram.

## Testing Priorities
Focus first on safety boundaries and deterministic behavior:
- tenant isolation.
- user roles and object ownership.
- Matrix Admin separation from customer roles.
- soft-archive/status behavior instead of hard deletes.
- agent registration, token hashing, heartbeat, and job polling.
- tool authorization and policy checks.
- registry allowlist and ToolTemplate/ToolDefinition separation.
- secret redaction before storage and display.
- PostgreSQL-backed model constraints and service logic.
- scanner parsing.
- alert cooldown.
- Telegram command mapping.
- report formatting.

## Unit Tests
Required for:
- custom User, Account, Server, Application, Plan, Subscription, and AuditLog model behavior.
- token generation, hashing, expiry, revocation, and one-time registration.
- ToolTemplate registry mapping known template keys to handlers.
- policy engine denying unknown, disabled, unsafe, cross-account, or unauthorized tools.
- secret redaction for `.env`, logs, headers, tokens, private keys, and common password patterns.
- alert rules for threshold crossings.
- cooldown behavior.
- report formatter output shape.

## Scanner Tests
Use fixtures for:
- Apache domlogs and error logs.
- cPanel userdata.
- Laravel logs.
- PHP-FPM config snippets.
- MySQL status sample output.
- service status sample output.

Scanners should be tested without requiring real Nginx, MySQL, PHP-FPM, or Laravel.

## Integration Tests
Required for:
- Account/User/Server creation and role enforcement.
- Matrix Admin staff/superuser access separated from customer Portal roles.
- soft-archive behavior for tenant-owned records.
- agent registration, heartbeat, job fetch, and job result APIs.
- baseline launch and discovered app Pending Review flow.
- ToolRun creation only after policy approval.
- remote bootstrap session step transitions with mocked SSH/Paramiko.
- DiagnosticSession running tools through policy and AgentJob.
- Telegram linking and command handling with mocked Telegram API.
- audit logging for sensitive operations.

## Security Tests
Required for:
- cross-account access denial for Portal/API/Admin-adjacent service methods.
- unauthorized Telegram users and username-only identity rejection.
- Diagnostic Agent cannot execute directly or bypass policy.
- database ToolDefinition values cannot create new executable behavior.
- agent token mismatch, revoked token, expired registration token, and replay attempts.
- bootstrap credentials are encrypted, expire, and are deleted/destroyed after session.
- Sprint 3 bootstrap does not launch Baseline Scan or Security Preflight.
- output truncation.
- secret redaction.

## Test Data Rules
- Do not commit real logs containing secrets.
- Use sanitized fixtures.
- Include edge cases:
  - missing log files.
  - permission denied.
  - malformed log lines.
  - empty scan results.
  - service unavailable.
  - missing cPanel metadata.
  - symlink/path traversal attempts.
  - oversized tool output.

## Done Criteria
A feature is not complete until:
- happy path tests pass.
- denial/failure path tests pass.
- unsafe behavior is covered by at least one regression test.
- audit and redaction behavior are covered for security-sensitive changes.
