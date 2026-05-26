# Test Plan

Testing should focus first on safety boundaries, tenant isolation, and deterministic execution.

## Test Levels

Unit tests:
- Model validations.
- Status helpers.
- Token hashing/expiry/revocation.
- Policy checks.
- Redaction.
- Tool registry mappings.

Integration tests:
- Portal/API account scoping.
- Agent registration and heartbeat.
- Agent job polling and result submission.
- Bootstrap step transitions with SSH mocked.
- ToolRun creation through policy.
- Baseline orchestration.
- Telegram linking with mocked Telegram API.

Security regression tests:
- Cross-account access denial.
- Staff/customer separation.
- Viewer cannot start diagnostics.
- Archived accounts cannot log in.
- Archived servers cannot receive jobs.
- Raw tokens are not stored.
- Secrets do not appear in AuditLog metadata, ToolRun output, reports, Telegram messages, or AI prompt context.

## Sprint 1 Required Tests

- Account status values.
- Custom User has one Account.
- Customer roles are owner/operator/viewer.
- Matrix Admin is staff/superuser and not a customer role.
- Server status values.
- Application review status values.
- Subscription status values.
- AuditLog shape and safe metadata behavior.
- Soft-archive fields preserve rows.

## Fixtures

Use sanitized fixtures only:
- Apache logs.
- cPanel userdata.
- Laravel directory structures.
- Laravel logs.
- PHP-FPM config snippets.
- MySQL status output.
- Agent JSON outputs.

Never commit real customer logs, `.env` files, credentials, tokens, private keys, or API responses containing secrets.
