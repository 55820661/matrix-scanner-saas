# Locked Decisions

These decisions are constraints for implementation. Do not change them casually during a sprint.

## Corrected Roadmap References

- `docs/planning/ROADMAP-CORRECTION.md` is the corrected product and architecture roadmap reference.
- `docs/planning/CORRECTED-EXECUTION-PLAN.md` is the top execution reference after the roadmap correction.
- `docs/planning/DECISION-REGISTER.md` is the official approved decision reference for corrected-plan Sprints.
- The corrected roadmap has one AI only: `Admin AI Chatbot`; diagnostics, reports, Tool Builder, and Telegram are workflows/interfaces around the same chat/orchestrator.
- The first real implementation Sprint after documentation alignment is `Sprint C1.5 - Remote Bootstrap Runtime Completion`.

## SaaS and Tenancy

- The SaaS platform is built with Django, Django REST Framework, PostgreSQL, Django Admin, and Django templates for the MVP Portal.
- Celery and Redis are deferred future production components and are not implemented in the MVP Sprint 12 release.
- Each MVP user belongs to one Account directly through `account_id` on the custom User model.
- Multi-account membership is deferred.
- Tenant-owned records must be scoped by Account directly or through a required parent.
- PostgreSQL RLS is deferred; ORM scoping, object ownership checks, and tests are required.

## Roles

- Matrix Admin is Django staff/superuser.
- Matrix Admin is not a customer role.
- Customer roles are `owner`, `operator`, and `viewer`.
- A staff user must not act as a Portal customer user unless explicitly linked to an Account.
- Future impersonation must be audited and is not part of Sprint 1.

## Statuses

Account:
- `active`
- `suspended`
- `archived`

Server:
- `pending`
- `active`
- `offline`
- `archived`

Application review:
- `pending_review`
- `approved`
- `ignored`
- `archived`

Subscription:
- `trial`
- `active`
- `past_due`
- `suspended`
- `cancelled`
- `expired`

## AuditLog

Sprint 1 AuditLog fields:

```text
actor_user
actor_type
account
action
target_type
target_id
result
ip_address
user_agent
metadata
created_at
```

Rules:
- `metadata` must never store secrets.
- Use a central audit helper/service instead of scattered ad hoc writes.
- Suggested `actor_type` values: `user`, `admin`, `agent`, `system`.

## Tokens

- Registration token TTL defaults to 60 minutes.
- Registration tokens are one-time use.
- Registration tokens and agent tokens are stored hashed only.
- Raw tokens are shown or returned once.
- Tokens can be revoked manually later from Admin/Portal.

## Soft Archive

- MVP deletion uses status/soft-archive, not hard delete.
- Archived Account prevents user login and blocks new jobs/diagnostics.
- Archived Server blocks agent jobs and diagnostics, but preserves reports/history.
- Archived Application is hidden from active workflows, but reports/history remain accessible.

## Usage Counters

- Usage counters may be cached/stored for performance.
- Source tables remain the source of truth.
- Design must allow recalculation later via an admin command.

## Sprint Boundaries

- Sprint 1 is core SaaS models and Django Admin only.
- No agent APIs, bootstrap, baseline, Telegram, Diagnostic Agent, or remediation in Sprint 1.
- Remote Bootstrap is separate from Baseline.
- Tool/Policy foundation comes before full Baseline implementation.
- Sprint 3 Remote Bootstrap installs/starts Scanner Runtime and verifies heartbeat only.
- Security Preflight is deferred.
