# Decision Register - Matrix Scanner SaaS Corrected Execution Plan

## Document Status

Status: Approved

Approved by project owner on 2026-06-05.

Created: 2026-06-05

## References

- `docs/planning/ROADMAP-CORRECTION.md`
- `docs/planning/CORRECTED-EXECUTION-PLAN.md`
- Sprint decision review accepted by project owner before implementation.

## Critical Decisions Summary

| ID | Area | Decision | Status | Applies To |
|---|---|---|---|---|
| DR-001 | Plan Authority | `CORRECTED-EXECUTION-PLAN.md` is the top execution reference after `ROADMAP-CORRECTION.md`. | Approved | All sprints |
| DR-002 | AI Architecture | There is one AI only: `Admin AI Chatbot`; no separate Diagnostic AI, Report AI, or Tool Builder AI. | Approved | All sprints |
| DR-003 | Remote Bootstrap | Remote Bootstrap remains Matrix Admin-only; no Portal/customer bootstrap now. | Approved | C1.5 |
| DR-004 | Bootstrap Runtime | Sprint C1.5 updates existing bootstrap to install the real Runtime/Agent instead of the heartbeat demo bundle. | Approved | C1.5 |
| DR-005 | Bootstrap Install Defaults | Runtime path is `/opt/matrix_scanner`; systemd service is `matrix-scanner-agent.service`. | Approved | C1.5 |
| DR-006 | Safe Context | Safe Context is a versioned, capped, redacted JSON built by a dedicated `apps/ai_context` app. | Approved | C2 |
| DR-007 | Admin Chat | Admin Chat uses a dedicated `apps/ai_chat` app with `AdminChatSession`, `AdminChatMessage`, and `AdminChatDecision`. | Approved | C3 |
| DR-008 | Live AI | No live AI provider before Safe Context, Chat MVP, and redaction/permission tests. | Approved | C4+ |
| DR-009 | Tool Execution Path | All tool execution must pass through `ToolDefinition -> ToolPolicy -> PlanTool -> ToolRun -> AgentJob`. | Approved | C5+ |
| DR-010 | C5/C6 Boundary | C5 can run only existing safe tools; `command_template` execution starts only after C6. | Approved | C5/C6 |
| DR-011 | Command Runtime | C6 starts with `command_template`, `argv-only` by default; `script_template` is deferred. | Approved | C6 |
| DR-012 | Tool Builder | Tool Builder from Chat creates proposals only; no automatic enablement; Matrix Admin review is mandatory. | Approved | C7 |
| DR-013 | First Tool Cycle | First full tool cycle must not be `laravel_env_sanity`; use `apache_5xx_summary` if Apache is available or `laravel_log_health` otherwise. | Approved | C8 |
| DR-014 | Reports | Reports from Chat use draft/review flow; PDF is deferred; raw ToolRun/AgentJob output is forbidden. | Approved | C9 |
| DR-015 | Pilot | Internal pilot starts with 1-2 internal users, staged servers, redacted review logs, and clear stop criteria. | Approved | C10/C12 |
| DR-016 | Telegram | Telegram is an interface to the same chat/orchestrator; private commands only; no direct AgentJob. | Approved | C11/C12 |

## Sprint C1 - Current State and Documentation Alignment

### Decision: Plan Authority

Status: Approved

Reason:
- The project needs one corrected execution reference to prevent returning to the earlier multi-AI architecture.

Impact:
- Every later Sprint must be checked against `CORRECTED-EXECUTION-PLAN.md`.
- `ROADMAP-CORRECTION.md` remains the higher-level correction reference.

Implementation Notes:
- Documentation alignment is allowed.
- No code changes are implied by this decision.
- Any contradiction in older planning files should be resolved in favor of `ROADMAP-CORRECTION.md` and `CORRECTED-EXECUTION-PLAN.md`.

### Decision: Single AI Architecture

Status: Approved

Reason:
- The corrected product architecture is based on one AI: `Admin AI Chatbot`.

Impact:
- No separate Diagnostic AI, Report AI, Tool Builder AI, or Telegram AI should be created.
- Diagnostics, reports, tool builder, and Telegram remain workflows/interfaces around the same AI/chat layer.

Implementation Notes:
- Existing deterministic diagnostic/report/tool-builder foundations can be reused as service/workflow layers.

## Sprint C1.5 - Remote Bootstrap Runtime Completion

### Decision: Matrix Admin-only Bootstrap

Status: Approved

Reason:
- Remote Bootstrap handles SSH credentials, systemd, package installation, and runtime installation.

Impact:
- Customer Portal must not expose bootstrap creation or execution in this phase.
- Any customer self-bootstrap is deferred.

Implementation Notes:
- Use the existing Admin-only bootstrap models, services, admin action, credentials, and tests.

### Decision: Complete Existing Bootstrap, Do Not Rebuild It

Status: Approved

Reason:
- The existing foundation already includes `BootstrapSession`, `BootstrapStep`, `BootstrapCredential`, `AgentInstallation`, Paramiko SSH, encrypted temporary credentials, TTL, cleanup, fixed command templates, config upload, systemd install/start, heartbeat verification, Admin action, and mocked tests.

Impact:
- Sprint C1.5 should update the installed runtime bundle or install flow, not replace the bootstrap architecture.

Implementation Notes:
- The current `sprint3-bootstrap-runtime` registration/heartbeat demo bundle is not enough.
- The target is the real Runtime/Agent capable of registration or token use, heartbeat, polling, AgentJob execution, and job result submission.

### Decision: Bootstrap Install Defaults

Status: Approved

Reason:
- Stable defaults reduce operational confusion and avoid unnecessary migration of existing assumptions.

Impact:
- Runtime path remains `/opt/matrix_scanner`.
- systemd service remains `matrix-scanner-agent.service`.

Implementation Notes:
- Changes to these defaults require explicit approval.

### Decision: Runtime Config Shape

Status: Approved

Reason:
- The installed runtime needs a clear, inspectable, compatible JSON configuration.

Impact:
- Config must include at least:
  - `base_url`
  - `registration_token` or `agent_token`
  - `poll_interval_seconds`
  - `runtime_mode`

Implementation Notes:
- Config must not expose secrets in logs, admin output, reports, Telegram, or audit metadata.

### Decision: Real Smoke Test Required

Status: Approved

Reason:
- Mocked SSH tests are necessary but insufficient for systemd/bootstrap validation.

Impact:
- A real smoke test on a VM or internal server is mandatory before any customer server.

Implementation Notes:
- Smoke should verify config creation, systemd service, heartbeat, polling, approved AgentJob execution, result submission, and credential cleanup.

## Sprint C2 - Safe Context Builder MVP

### Decision: Dedicated App

Status: Approved

Reason:
- Safe Context is a cross-cutting layer used by chat, tools, reports, and Telegram.

Impact:
- Create a dedicated app with the working name `apps/ai_context`.

Implementation Notes:
- The app should build context only; it must not call AI providers or run tools.

### Decision: Safe Context JSON Contract

Status: Approved

Reason:
- AI/chat must consume a predictable, safe, capped structure.

Impact:
- Context must be JSON, stable, versioned, redacted, summarized, and capped.

Implementation Notes:
- Forbidden data:
  - raw logs
  - raw `.env`
  - credentials
  - tokens
  - private keys
  - raw AgentJob result
  - raw ToolRun output
  - bootstrap stdout/stderr

### Decision: Available Tools in Context

Status: Approved

Reason:
- The Tool Orchestrator depends on a safe list of tools available to the current account/server/role.

Impact:
- `available_tools` is included from the beginning as short metadata only.
- It must respect ToolPolicy and PlanTool.

Implementation Notes:
- Do not include command text, scripts, secrets, raw outputs, or unsafe parameters.

### Decision: Preview

Status: Approved with optional implementation

Reason:
- A preview is useful for debugging but can expand scope and expose sensitive context.

Impact:
- Admin-only preview may be included in C2 if it remains small and redacted.
- Portal preview can be deferred.

Implementation Notes:
- Preview must never display raw data.

## Sprint C3 - Admin Chat Data Model and Read-only UI

### Decision: Dedicated App

Status: Approved

Reason:
- Chat is a central product layer, not just diagnostics.

Impact:
- Use working app name `apps/ai_chat`.

Implementation Notes:
- Chat must remain account-scoped and redacted.

### Decision: Initial UI Scope

Status: Approved

Reason:
- First version should support internal customer-facing operation without broad Admin UX work.

Impact:
- Chat starts inside Portal for owner/operator.
- Viewer is read-only for viewing only and cannot actively run chat flows.

Implementation Notes:
- Matrix Admin oversight can be added via Django Admin or later Admin screens.

### Decision: Chat Models

Status: Approved

Reason:
- Separate models provide auditability and make later Telegram mapping easier.

Impact:
- Add:
  - `AdminChatSession`
  - `AdminChatMessage`
  - `AdminChatDecision`

Implementation Notes:
- All stored text/metadata must be redacted.

### Decision: Hybrid Context

Status: Approved

Reason:
- Pure live context loses auditability; full snapshots can become large and stale.

Impact:
- Store a short context snapshot when responding.
- Rebuild context when requested or needed.

Implementation Notes:
- Snapshot must be capped and redacted.

## Sprint C4 - Deterministic Chat Responder

### Decision: Deterministic First

Status: Approved

Reason:
- Live AI before Safe Context, Chat MVP, and tests creates unnecessary security risk.

Impact:
- C4 uses deterministic responses only.

Implementation Notes:
- No live AI provider calls in C4.

### Decision: Context-only Answers

Status: Approved

Reason:
- Direct raw model access can bypass Safe Context controls.

Impact:
- Chat answers must come from Safe Context only.

Implementation Notes:
- Supported first questions should focus on status, summaries, findings, reports, and available tools.

### Decision: Decision Logging

Status: Approved

Reason:
- Response decisions need traceability before tool execution and live AI are introduced.

Impact:
- Store decision output in `AdminChatDecision`.

Implementation Notes:
- Store safe summaries, not hidden raw context.

## Sprint C5 - Tool Orchestrator MVP

### Decision: Existing Safe Tools Only

Status: Approved

Reason:
- C5 happens before general command-template execution.

Impact:
- C5 may only run currently existing tools that already have a safe execution path and are enabled through ToolPolicy/PlanTool.
- C5 must not run `command_template` or `script_template`.

Implementation Notes:
- Examples may include current approved runtime-handler tools.

### Decision: Required Execution Path

Status: Approved

Reason:
- Direct AgentJob creation bypasses Tool Registry and ToolPolicy.

Impact:
- All execution must pass through:
  `ToolDefinition -> ToolPolicy -> PlanTool -> ToolRun -> AgentJob`

Implementation Notes:
- No direct AgentJob from chat.
- ToolPolicy and PlanTool denial must happen before ToolRun/AgentJob creation.

### Decision: Tool Request and Approval

Status: Approved

Reason:
- Chat-initiated execution needs explicit user intent, approval, and audit.

Impact:
- Add `AdminChatToolRequest` is recommended.
- Every MVP chat tool run requires approval.
- owner/operator can approve.
- viewer cannot approve.

Implementation Notes:
- The UI can show pending results rather than blocking synchronously.

## Sprint C6 - Safe Command Execution Runtime

### Decision: Command Template First

Status: Approved

Reason:
- `script_template` is more complex and riskier.

Impact:
- Start with `command_template` only.
- Defer `script_template`.

Implementation Notes:
- Runtime handlers remain supported as advanced/current mode and must not be removed.

### Decision: argv-only Default

Status: Approved

Reason:
- Shell strings are the highest-risk command injection path.

Impact:
- `argv-only` is the default.
- Shell execution, if ever allowed, must be an explicit, narrow, reviewed exception.

Implementation Notes:
- Command execution must include:
  - allowed binaries
  - typed parameters
  - blocked tokens
  - timeout
  - max output
  - redaction
  - exit_code
  - execution_time
  - truncated flag

### Decision: Execution Type

Status: Approved as implementation preference

Reason:
- Tool Registry needs to distinguish command templates, script templates, and runtime handlers.

Impact:
- Prefer adding `execution_type` to ToolDefinition/ToolTemplate during C6.

Implementation Notes:
- Exact migration shape is decided in C6 design.

## Sprint C7 - Tool Builder from Chat

### Decision: Proposal-only First

Status: Approved

Reason:
- Automatic tool creation or enablement from chat is unsafe.

Impact:
- Tool Builder from Chat creates proposals only at first.
- It does not activate tools automatically.

Implementation Notes:
- Matrix Admin review is always required.

### Decision: Proposal Type

Status: Approved

Reason:
- The corrected architecture prefers safe command templates over new runtime handlers.

Impact:
- `command_template` proposal is the default.
- Runtime handler proposal is allowed only as advanced metadata-only planning and is not executable automatically.

Implementation Notes:
- Final FK from ToolBuildRequest to ChatSession is deferred to C7 design, but recommended for audit.

## Sprint C8 - First Laravel/Apache Tool Cycle

### Decision: Do Not Start with `.env`

Status: Approved

Reason:
- `laravel_env_sanity` touches `.env` and is too sensitive as the first proof of the cycle.

Impact:
- `laravel_env_sanity` is deferred.

Implementation Notes:
- It can be revisited only after redaction, output caps, approval flow, safe summary, and no raw data display are proven.

### Decision: First Tool Choice

Status: Approved

Reason:
- The first full cycle should prove the command-template path with lower sensitivity.

Impact:
- Use `apache_5xx_summary` if Apache is available.
- Otherwise use `laravel_log_health`.

Implementation Notes:
- First experiment should run on an internal VM if possible, then Innvii or a real Laravel/Apache server after smoke success.
- Outputs must be counters/summaries only.
- Raw logs are forbidden.
- Use `command_template` only; no `script_template`.

## Sprint C9 - Reports from Chat

### Decision: Draft Review Flow

Status: Approved

Reason:
- Chat-generated reports need human review before becoming final user-visible reports.

Impact:
- Prefer adding `AdminChatReportDraft`.
- MVP reports require approval before conversion to final `Report`.

Implementation Notes:
- Report types:
  - `technical/internal`
  - `customer_summary`

### Decision: No Raw Output and No PDF

Status: Approved

Reason:
- Reports are high-visibility and can leak operational data.

Impact:
- Raw ToolRun and AgentJob output is forbidden inside reports.
- PDF export is deferred.

Implementation Notes:
- Use only safe summaries and redacted sections.

## Sprint C10 - Internal Pilot

### Decision: Staged Pilot

Status: Approved

Reason:
- The system needs real usage validation without broad exposure.

Impact:
- Start gradually.
- Begin with Matrix/Siyaq or an internal VM, then Laravel/Apache.
- Use only 1-2 internal users at first.

Implementation Notes:
- Record chat responses redacted for review.

### Decision: Success Criteria

Status: Approved

Reason:
- Telegram should not start without measurable pilot success.

Impact:
- Success requires:
  - no raw leaks
  - useful answers
  - policy enforced
  - stable runtime

Implementation Notes:
- Failure to meet these blocks C11.

## Sprint C11 - Telegram Interface to Same Chat

### Decision: Telegram Scope

Status: Approved

Reason:
- Telegram expands exposure and must reuse the same safe backend.

Impact:
- Telegram private chat only for commands.
- Groups are summaries only.
- Telegram uses the same `AdminChatSession` or a lightweight mapping to it.
- No independent Telegram AI/backend.

Implementation Notes:
- No direct AgentJob from Telegram.

### Decision: Initial Commands

Status: Approved

Reason:
- Minimal commands reduce scope and risk.

Impact:
- Start with:
  - `/start`
  - `/help`
  - `/servers`
  - `/select_server`
  - `/status`
  - `/report`
  - `/cancel`

Implementation Notes:
- `/diagnose` can be deferred if it expands scope.

### Decision: Telegram Approvals

Status: Deferred

Reason:
- Approvals from Telegram are security-sensitive and need separate Sprint design.

Impact:
- MVP may restrict approvals heavily or require returning to Portal approval.

Implementation Notes:
- Must be decided before C11 implementation.

## Sprint C12 - Telegram Pilot

### Decision: Narrow Pilot

Status: Approved

Reason:
- Telegram pilot should validate safety with minimum blast radius.

Impact:
- 1-2 internal users only.
- One server only.
- Very narrow tool allowlist.

Implementation Notes:
- Stop immediately on:
  - secret leak
  - raw output leak
  - policy bypass
  - runtime instability

## Deferred Decisions

| Decision | Deferred Until | Notes |
|---|---|---|
| Final chat retention policy | C3 or post-MVP hardening | MVP can use archive/status and later retention configuration. |
| Live AI provider timing | After C4/C5 safety validation | No live provider before Safe Context, Chat MVP, redaction, and permission tests. |
| Final FK between ToolBuildRequest and ChatSession | C7 | Recommended for audit, but exact model shape deferred. |
| Telegram approval details | C11 | Must be designed before implementation. |
| Pilot expansion after C12 | After Telegram Pilot review | Requires go/no-go checklist. |
| PDF export | Post-C9 | Deferred; not part of MVP chat reports. |
| Customer self-bootstrap | Future | Explicitly not allowed in C1.5. |
| Remediation/write tools | Future explicit approval only | Not part of corrected execution path. |
| `script_template` support | After command_template is safe and proven | Start with `command_template` only. |

## Decisions Requiring Explicit Approval to Change

- The project has one AI only: `Admin AI Chatbot`.
- No separate Diagnostic AI, Report AI, Tool Builder AI, or Telegram AI.
- No remediation/write/destructive tools in the current roadmap.
- No raw logs, raw `.env`, credentials, tokens, private keys, raw AgentJob result, or raw ToolRun output in context, chat, reports, Telegram, audit metadata, or stored summaries.
- Remote Bootstrap remains Matrix Admin-only until explicitly approved otherwise.
- No Portal/customer bootstrap in Sprint C1.5.
- No direct AgentJob creation from chat or Telegram.
- All tool execution must pass through `ToolDefinition -> ToolPolicy -> PlanTool -> ToolRun -> AgentJob`.
- C5 must not execute `command_template` or `script_template`.
- C6 starts with `command_template`; `script_template` is deferred.
- `laravel_env_sanity` is not the first full tool cycle.
- Telegram must reuse the same chat/orchestrator architecture and must not become an independent backend.
