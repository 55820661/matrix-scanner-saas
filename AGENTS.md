# Matrix Scanner SaaS Agents Guide

## Purpose
This file describes how automation agents, helpers, or bots should behave when operating in this Matrix Scanner SaaS repository.

## Role
Agents assist contributors by performing safe, explicit tasks such as gathering context, creating or updating non-sensitive documentation, adapting project guidance files, implementing explicitly requested code changes, and running non-destructive checks.

## Allowed Without Extra Approval
- Read and summarize repository files.
- Create or update documentation, templates, or helper files when requested.
- Run linting, static analysis, or non-destructive tests when requested.

## Require Explicit Approval
Do not proceed without approval for actions that change behaviour, infrastructure, dependencies, or that modify production code in ways that affect runtime or data.

Examples requiring approval:
- Installing or removing dependencies
- Changing runtime configuration or environment settings
- Creating, deleting, or renaming source files that affect application behavior
- Running destructive operations or migrations against production data
- Changing agent authentication, tenant isolation, bootstrap execution, secret handling, or tool execution policy
- Adding remediation behavior such as file edits, service restarts, package installs, or permission changes outside the approved bootstrap workflow

## Project Guardrails
- Sprint 1 is SaaS foundation only: accounts, users, roles, plans, subscriptions, server/application skeletons, audit, and Django Admin.
- Do not start agent APIs, remote bootstrap, baseline scans, diagnostics, Telegram execution, or remediation work unless explicitly requested for the relevant sprint.
- Matrix Admin is Django staff/superuser, not a customer role.
- Customer roles are `owner`, `operator`, and `viewer`.
- Tenant-owned models must be scoped by `account_id` and protected by backend ownership checks.
- MVP deletion uses status or soft-archive patterns, not hard deletes.
- Raw registration tokens, agent tokens, SSH credentials, API keys, and `.env` secrets must never be stored in plain text.
- Secret redaction must happen before storage, display, AI prompts, and Telegram.

## Decision Rules
- When a decision is needed, present up to three options with brief trade-offs.
- If the intent is unclear, stop and ask rather than guessing.

## Working Style
- Be minimal and reversible: prefer smaller, reviewable edits.
- Keep changes documented and scoped to the user's request.
- Avoid unasked-for refactors or style-only mass edits.

## Required Task Tracking
- Before executing any requested implementation, repository-changing command, or multi-step operation, update the necessary helper files.
- `LOG.md` is required. If it does not exist, create it before proceeding.
- `docs/CURRENT-TASKS.md` is required. If it does not exist, create it before proceeding.
- Update `docs/CURRENT-TASKS.md` before work starts with the active task, scope, and immediate next steps.
- Update `LOG.md` before work starts with a short entry describing intent and scope.
- After work completes, update both files again with what changed, verification performed, and any remaining risks or next steps.
- Keep these updates concise and factual. Do not store secrets, raw tokens, credentials, customer logs, or private data in either file.

## Useful Local References
- Skills and guides: [skills/general](skills/general)
- Project-specific skills: [skills/project](skills/project)
- Planning docs: [docs/planning](docs/planning)

## Priority
Follow the user's explicit instructions first; when unsure, ask.
