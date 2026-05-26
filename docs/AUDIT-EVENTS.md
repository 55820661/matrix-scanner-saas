# Audit Events

Audit event names should be stable strings. Add to this file as new areas are implemented.

## Naming Convention

Use:

```text
domain.action
```

Examples:
- `account.created`
- `server.archived`
- `agent.registered`

## Sprint 1 Events

Accounts:
- `account.created`
- `account.updated`
- `account.suspended`
- `account.archived`
- `account.reactivated`

Users:
- `user.created`
- `user.updated`
- `user.role_changed`
- `user.disabled`
- `user.login_denied`

Plans:
- `plan.created`
- `plan.updated`
- `plan.disabled`

Subscriptions:
- `subscription.created`
- `subscription.updated`
- `subscription.status_changed`

Servers:
- `server.created`
- `server.updated`
- `server.archived`

Applications:
- `application.created`
- `application.updated`
- `application.review_status_changed`
- `application.archived`

Audit:
- `audit.created`

## Later Events

Agent:
- `agent.registration_token_created`
- `agent.registration_token_revoked`
- `agent.registered`
- `agent.heartbeat_received`
- `agent.revoked`

Jobs:
- `agent_job.created`
- `agent_job.started`
- `agent_job.succeeded`
- `agent_job.failed`
- `agent_job.rejected_by_policy`

Bootstrap:
- `bootstrap.started`
- `bootstrap.step_started`
- `bootstrap.step_succeeded`
- `bootstrap.step_failed`
- `bootstrap.completed`
- `bootstrap.failed`
- `bootstrap.cancelled`
- `bootstrap.credentials_destroyed`

Policy:
- `policy.approved`
- `policy.rejected`

Tools:
- `tool_definition.created`
- `tool_definition.approved`
- `tool_definition.enabled`
- `tool_definition.disabled`
- `tool_run.created`
- `tool_run.completed`

Telegram:
- `telegram.link_token_created`
- `telegram.user_linked`
- `telegram.chat_linked`
- `telegram.alert_sent`
- `telegram.message_denied`

Diagnostics:
- `diagnostic_session.started`
- `diagnostic_step.created`
- `diagnostic_session.completed`
- `diagnostic_session.stopped`
