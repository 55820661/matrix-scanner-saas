# Contributing

This repository should be developed sprint by sprint according to `PLANS.md` and the locked decisions in `docs/DECISIONS.md`.

## Working Rules

- Keep changes scoped to the current sprint.
- Do not start later-sprint functionality without an explicit request.
- Add or update tests for behavior changes.
- Update docs when a decision, model, endpoint, or workflow changes.
- Never commit secrets, real customer logs, raw tokens, private keys, or full `.env` files.

## Sprint Boundaries

Sprint 1 is only:
- accounts
- users
- roles
- plans
- subscriptions
- servers skeleton
- applications skeleton
- audit
- Django Admin

Sprint 1 is not:
- agent APIs
- bootstrap
- baseline scans
- Telegram
- Diagnostic Agent
- remediation

## Branch and Commit Guidance

Suggested branch names:
- `feat/sprint-1-saas-core`
- `feat/agent-registration`
- `feat/bootstrap-mvp`
- `docs/update-plans`

Suggested commit prefixes:
- `feat:`
- `fix:`
- `docs:`
- `test:`
- `refactor:`
- `chore:`

## Review Checklist

- Tenant isolation is enforced in backend code.
- Staff/superuser behavior is separate from customer Portal roles.
- Secrets are not stored or displayed.
- Audit logs do not contain secrets.
- Status/soft-archive behavior is respected.
- Tests cover happy path and denial/failure path.
