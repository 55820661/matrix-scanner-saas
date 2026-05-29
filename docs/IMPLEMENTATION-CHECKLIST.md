# Implementation Checklist

This checklist reflects the actual MVP sprint order through Sprint 12.

## Global Guardrails

- [ ] MVP diagnostics remain read-only and advisory.
- [ ] No free shell execution from Portal, Telegram, AI, DB rows, or config.
- [ ] No remediation/actions, write tools, service restarts, package installs, file edits, or permission changes outside approved Matrix Admin Remote Bootstrap.
- [ ] Tenant-owned data is scoped by `account_id` directly or through a required parent.
- [ ] Raw registration tokens, agent tokens, Telegram link tokens, SSH credentials, private keys, and `.env` secrets are never stored.
- [ ] Redaction happens before storage, Portal, Admin, Telegram, reports, findings, knowledge entries, and audit metadata.

## Sprint 1 - SaaS Core

- [x] Django project `scanner_platform`.
- [x] PostgreSQL-ready settings.
- [x] Custom User from day one.
- [x] Account, User, Plan, Subscription, Server, Application, AuditLog.
- [x] owner/operator/viewer roles.
- [x] Matrix Admin as staff/superuser.
- [x] Django Admin registrations.
- [x] Sprint 1 tests.

## Sprint 2 - Agent Registration Foundation

- [x] ScannerAgent.
- [x] AgentRegistrationToken.
- [x] AgentJob.
- [x] hashed one-time registration token storage.
- [x] hashed raw-once agent token storage.
- [x] register, heartbeat, poll, result endpoints.
- [x] terminal result replay rejection.
- [x] token expiry/revocation/mismatch tests.

## Sprint 3 - Remote Bootstrap MVP

- [x] BootstrapSession.
- [x] BootstrapStep.
- [x] BootstrapCredential.
- [x] AgentInstallation.
- [x] BootstrapPolicy fixed command templates.
- [x] temporary encrypted credentials with TTL and cleanup.
- [x] package install confirmation.
- [x] runtime tarball/SFTP deployment.
- [x] systemd service install/start.
- [x] heartbeat verification.
- [x] Matrix Admin only.

## Sprint 4 - Tool Registry and Policy Engine MVP

- [x] ToolTemplate.
- [x] ToolDefinition.
- [x] ToolPolicy.
- [x] PlanTool.
- [x] ToolRun.
- [x] registry-backed `system_identity`.
- [x] input schema validation.
- [x] path canonicalization and blocked-before-allowed policy.
- [x] timeout/output caps.
- [x] ToolPolicy-approved AgentJob creation only.

## Sprint 5 - Baseline Scan Implementation

- [x] BaselineScanStep.
- [x] DiscoveredService.
- [x] DiscoveredDomain.
- [x] LogSource.
- [x] Finding.
- [x] baseline orchestration through ToolPolicy.
- [x] required baseline tools seeded.
- [x] application discovery creates `pending_review`.
- [x] Laravel `.env` allowlisted safe keys only.
- [x] raw logs and full `.env` excluded.

## Sprint 6 - Admin and Portal MVP Screens

- [x] Portal app.
- [x] Portal auth and account scoping.
- [x] dashboard, servers, applications, findings, baseline, subscription.
- [x] owner-only registration token generation.
- [x] application and finding actions with AuditLog.
- [x] Remote Bootstrap remains Admin-only.

## Sprint 7 - Telegram Integration MVP

- [x] TelegramChatLink.
- [x] TelegramLinkToken.
- [x] TelegramNotification.
- [x] webhook secret validation.
- [x] private/group linking.
- [x] read-only commands.
- [x] safe notifications and suppression.
- [x] no ToolRun/AgentJob/DiagnosticSession creation from Telegram.

## Sprint 8 - Diagnostic Agent MVP

- [x] DiagnosticSession.
- [x] DiagnosticStep.
- [x] DiagnosticDecision.
- [x] deterministic planner.
- [x] Portal-only start.
- [x] approval before every tool step.
- [x] uses ToolPolicy path only.
- [x] redacted final reports.
- [x] no live LLM.

## Sprint 9 - Telegram Guided Diagnostics

- [x] TelegramDiagnosticState.
- [x] private-chat-only diagnostics.
- [x] owner/operator only.
- [x] viewer and groups blocked.
- [x] callback query handling.
- [x] approval through Diagnostic service.
- [x] no direct AgentJob creation.

## Sprint 10 - Tool Definition Proposal Builder

- [x] Implemented inside `apps/tools`.
- [x] ToolBuildRequest.
- [x] ToolBuildProposal.
- [x] ToolBuildReview.
- [x] ToolTestResult.
- [x] deterministic metadata-only proposals.
- [x] read-only risk only.
- [x] draft/pending_review conversion only.
- [x] no runtime handler or executable code generation.

## Sprint 11 - Reports, Findings, and Knowledge Base

- [x] Report.
- [x] ReportSection.
- [x] FindingGroup.
- [x] KnowledgeEntry.
- [x] KnowledgeSource.
- [x] Recommendation.
- [x] redacted stored report snapshots.
- [x] advisory-only recommendations.
- [x] Portal/Admin report and finding group visibility.
- [x] safe Telegram report summaries.

Deferred:

- [ ] IncidentReport model.
- [ ] AlertEvent model.
- [ ] KnowledgePattern model.
- [ ] PDF/email/scheduled reports.
- [ ] Celery/report workers.
- [ ] live LLM report generation.
- [ ] remediation workflows.

## Sprint 12 - Stabilization and Release Preparation

- [ ] Final full test pass.
- [ ] `makemigrations --check --dry-run` clean.
- [ ] Fresh `migrate` verified.
- [ ] `.env.example` required variables reviewed.
- [ ] Admin raw-output display reviewed.
- [ ] Portal tenant isolation reviewed.
- [ ] Telegram authorization and redaction reviewed.
- [ ] ToolPolicy enforcement reviewed.
- [ ] Bootstrap credential cleanup reviewed.
- [ ] AuditLog metadata secret handling reviewed.
- [ ] README, local development, deployment notes, runbook, test plan, and release checklist updated.

Must remain deferred:

- [ ] Celery/Redis workers.
- [ ] payment gateway.
- [ ] PDF/email/scheduled reports.
- [ ] customer Remote Bootstrap.
- [ ] live LLM.
- [ ] remediation/write/destructive tools.
- [ ] PostgreSQL RLS.
- [ ] multi-account membership.
- [ ] full self-install automation.
- [ ] advanced knowledge matching.
