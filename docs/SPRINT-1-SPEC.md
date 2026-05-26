# Sprint 1 Specification

Sprint 1 creates the SaaS foundation only.

## Goal

Create a Django project with core tenant, user, subscription, server/application skeleton, and audit models available in Django Admin.

## In Scope

- Django project `scanner_platform`.
- PostgreSQL configuration.
- Apps:
  - `accounts`
  - `servers`
  - `applications`
  - `plans`
  - `subscriptions`
  - `audit`
  - `core`
- Custom User from day one.
- Account direct FK on User.
- Customer roles: `owner`, `operator`, `viewer`.
- Matrix Admin through Django staff/superuser.
- Status and soft-archive fields.
- AuditLog shape from `docs/DECISIONS.md`.
- Django Admin registration.
- Basic tests.

## Out of Scope

- Agent APIs.
- Scanner Runtime code.
- Remote Bootstrap.
- Baseline Scan.
- Tool Registry execution.
- Telegram.
- Diagnostic Agent.
- Remediation.
- Payment gateway.

## Acceptance Criteria

- Django project starts.
- PostgreSQL is configured.
- Custom User model is active before first migration.
- Account/User/Server/Application/Plan/Subscription/AuditLog models exist.
- Django Admin can manage core records.
- Customer roles are constrained to owner/operator/viewer.
- Matrix Admin is staff/superuser, not a customer role.
- Soft-archive/status fields exist.
- AuditLog has the approved fields.
- Tests cover model creation, statuses, role constraints, and AuditLog metadata safety.
