# Security Checklist

Use this checklist before merging security-sensitive work.

## Tenant Isolation

- [ ] Tenant-owned records are scoped by Account.
- [ ] Portal/API querysets filter by current Account.
- [ ] Object ownership is checked before access.
- [ ] Cross-account tests exist.
- [ ] Staff/Admin behavior is separate from customer Portal behavior.

## Secrets

- [ ] No raw token is stored.
- [ ] No SSH credential is stored unencrypted.
- [ ] No full `.env` file is stored.
- [ ] AuditLog metadata contains no secrets.
- [ ] Tool output is redacted before persistence.
- [ ] Reports and findings contain no secrets.
- [ ] Telegram output contains no secrets.
- [ ] AI prompt context contains no secrets.

## Agent Authentication

- [ ] Registration tokens expire.
- [ ] Registration tokens are one-time use.
- [ ] Registration tokens are revocable.
- [ ] Agent tokens are hashed.
- [ ] Agent tokens are bound to one agent/server/account.
- [ ] Revoked/inactive agents cannot poll jobs.

## Tool Policy

- [ ] No free-form shell path exists.
- [ ] ToolDefinition cannot create executable behavior.
- [ ] ToolTemplate is the executable boundary.
- [ ] Params are typed and schema-validated.
- [ ] Paths are canonicalized.
- [ ] Output size is bounded.
- [ ] Runtime is bounded.

## Bootstrap

- [ ] Matrix Admin only.
- [ ] Fixed command templates only.
- [ ] Typed params only.
- [ ] Explicit confirmation before package install.
- [ ] Temporary credentials have TTL.
- [ ] Credentials are destroyed after session.
- [ ] Every step is audited.
- [ ] Sprint 3 does not run Baseline or Security Preflight.

## Soft Archive

- [ ] Archived Account blocks login and new jobs/diagnostics.
- [ ] Archived Server blocks jobs/diagnostics.
- [ ] Archived Application is hidden from active workflows.
- [ ] History and reports remain accessible according to retention rules.
