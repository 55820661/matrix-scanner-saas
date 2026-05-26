# Implementation Checklist

Use this checklist to keep implementation aligned with the approved plan.

## Before Sprint 1

- [ ] Confirm Django project name: `scanner_platform`.
- [ ] Confirm custom User model before first migration.
- [ ] Confirm PostgreSQL database configuration.
- [ ] Confirm Account direct FK on User.
- [ ] Confirm Matrix Admin is staff/superuser only.
- [ ] Confirm status enum values.
- [ ] Confirm AuditLog fields.

## Sprint 1 - SaaS Core

- [ ] Create Django project.
- [ ] Create apps: accounts, servers, applications, plans, subscriptions, audit, core.
- [ ] Implement custom User with `account_id`.
- [ ] Implement Account.
- [ ] Implement customer roles: owner/operator/viewer.
- [ ] Implement Plan.
- [ ] Implement Subscription.
- [ ] Implement Server skeleton.
- [ ] Implement Application skeleton.
- [ ] Implement AuditLog.
- [ ] Implement status/soft-archive fields.
- [ ] Register models in Django Admin.
- [ ] Add model tests.
- [ ] Add admin smoke tests where useful.
- [ ] Verify no agent API/bootstrap/baseline/Telegram code entered Sprint 1.

## Sprint 2 - Agent Registration and Jobs

- [ ] Add ScannerAgent.
- [ ] Add AgentRegistrationToken.
- [ ] Add AgentJob.
- [ ] Add hashed registration token storage.
- [ ] Add one-time registration flow.
- [ ] Add 60-minute token TTL.
- [ ] Add heartbeat endpoint.
- [ ] Add job polling endpoints.
- [ ] Add job result endpoint.
- [ ] Add revocation support.
- [ ] Add audit events.
- [ ] Add tests for token expiry, revocation, replay, mismatch, and hashing.

## Sprint 3 - Remote Bootstrap

- [ ] Add BootstrapSession.
- [ ] Add BootstrapStep.
- [ ] Add BootstrapCredential.
- [ ] Add AgentInstallation.
- [ ] Add BootstrapPolicy.
- [ ] Add encrypted temporary credential storage.
- [ ] Add credential TTL and cleanup.
- [ ] Add fixed command templates.
- [ ] Add typed parameter validation.
- [ ] Add explicit confirmation before package install.
- [ ] Deploy runtime tarball/SFTP.
- [ ] Write config.
- [ ] Create systemd service.
- [ ] Start service.
- [ ] Verify heartbeat.
- [ ] Audit every step.
- [ ] Confirm no Baseline Scan or Security Preflight runs in Sprint 3.

## Sprint 4 - Tool Registry and Policy

- [ ] Add ToolTemplate.
- [ ] Add ToolDefinition.
- [ ] Add ToolPolicy.
- [ ] Add PlanTool.
- [ ] Add ToolRun.
- [ ] Add policy service.
- [ ] Add input schema validation.
- [ ] Add path canonicalization and allow rules.
- [ ] Add runtime/output limits.
- [ ] Add redaction service.
- [ ] Ensure AgentJob is created only after policy approval.
- [ ] Add denial and cross-account tests.

## Sprint 5 - Baseline Scan

- [ ] Add BaselineScan.
- [ ] Add DiscoveredService.
- [ ] Add DiscoveredDomain.
- [ ] Add LogSource.
- [ ] Implement baseline orchestration in SaaS.
- [ ] Register baseline tools.
- [ ] Discover cPanel domains.
- [ ] Discover Laravel/WordPress/Unknown applications.
- [ ] Store safe Laravel env keys only.
- [ ] Create findings.
- [ ] Put apps into `pending_review`.

## Later Sprints

- [ ] Portal MVP.
- [ ] Telegram linking and alerts.
- [ ] Diagnostic Agent from Portal.
- [ ] Telegram guided diagnostics.
- [ ] Admin Tool Builder Agent.
- [ ] Reports/findings/knowledge base.
- [ ] Stabilization and internal pilot.
