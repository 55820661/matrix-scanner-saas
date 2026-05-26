# Matrix Scanner SaaS Telegram Skill

## Purpose
Use this skill when implementing Telegram linking, alerts, summaries, menus, guided diagnostics, command handling, or Telegram output formatting.

## MVP Transport
- Use webhook-based Telegram handling in production unless the execution plan explicitly changes.
- Keep Telegram code separate from scanners, tool handlers, policy checks, and Diagnostic Agent execution.
- Telegram is a SaaS interface, not a direct channel to the customer server.

## Authentication
- Link a Telegram user to a SaaS User through a short-lived Portal code.
- Use `telegram user_id` and chat identifiers.
- Do not rely on username.
- Unknown users are denied or ignored according to policy.
- Groups can receive alerts/summaries only in MVP unless explicitly changed later.
- Log denied attempts and important interactions with minimal safe metadata.
- Enforce SaaS roles: Viewer cannot start diagnostic sessions.

## Commands
Initial command set:
- `/start`
- `/link <code>`
- `/menu`
- `/servers`
- `/apps`
- `/findings`
- `/reports`
- `/help`

Guided diagnosis should use buttons/menus first. Natural language routing is deferred or limited.

## Output
- Keep Telegram messages concise.
- Split long reports if required by Telegram limits.
- Avoid raw logs unless the command explicitly asks for diagnostic detail.
- Sanitize secrets and environment values.
- Do not send long raw tool output to Telegram.
- Full reports should open in Portal; Telegram receives short summaries and notes.
- Use Arabic summaries when that matches the customer workflow.

## Failure Handling
- Telegram API failures should not crash diagnostics, scans, alerts, or web requests.
- Failed sends are logged.
- Alerts should use cooldown to avoid repeated noisy messages.
- Do not alert on old findings unless they are newly detected or recently active.

## Diagnostic Rules
- Telegram diagnostics start from private chat only.
- Use the same DiagnosticSession backend as Portal.
- Read-only tools can be auto-approved inside a confirmed session.
- Groups remain alerts/summaries only in MVP.
- Every diagnostic Telegram interaction should be audited.

## Testing Checklist
- Linking succeeds only with valid, unexpired codes.
- Unauthorized chat/user is denied.
- Commands show only account-owned servers, apps, findings, and reports.
- Viewer cannot start diagnostic sessions.
- Tool errors return a safe message.
- Long output is truncated or split.
- Group alerts never include secrets or long diagnostic output.
