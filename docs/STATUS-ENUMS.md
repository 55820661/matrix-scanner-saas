# Status Enums

This document defines initial status values and expected behavior.

## Account Status

### `active`
Normal account behavior.

### `suspended`
Account is blocked operationally but not archived. Use for billing or admin holds.

### `archived`
Historical state. Prevents user login and blocks new jobs/diagnostics. Data remains for reports/history.

## Server Status

### `pending`
Created but not fully active or registered.

### `active`
Available for normal workflows.

### `offline`
Agent is not currently reachable or heartbeat is stale.

### `archived`
Hidden from active workflows. Blocks agent jobs and diagnostics. Reports/history remain accessible.

## Application Review Status

### `pending_review`
Discovered but not approved by customer/owner.

### `approved`
Active application for workflows and diagnostics.

### `ignored`
Known but intentionally excluded from active workflows.

### `archived`
Historical application. Hidden from active workflows. Reports/history remain accessible.

## Subscription Status

### `trial`
Trial period.

### `active`
Normal paid or manually active subscription.

### `past_due`
Payment or renewal issue.

### `suspended`
Operationally blocked subscription.

### `cancelled`
Cancelled subscription.

### `expired`
Subscription period ended.
