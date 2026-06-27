# Current Tasks

Track active work before and after every requested implementation, repository-changing command, or multi-step operation.

## Current Task: None

No implementation task is currently active.

## Archived Task: C10.11 Diagnostic Result Quality & Evidence Layer

Result:
- Added a centralized diagnostic summary helper for Arabic tool labels, status labels, skip-reason normalization, durations, completion level, and conservative next-step wording.
- Switched diagnostic bundle final summaries to that structured helper and attached safe evidence counts in final-message metadata.
- Passed ToolRun timing fields through bundle progress/finalization so durations can appear when available.
- Added focused regressions for structured summary sections, timeout wording, evidence counts, and no raw Python/JSON leakage.
- Kept the stream-managed diagnostic bundle lifecycle unchanged and made no Portal, Telegram, customer-facing AI, policy, or migration changes.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_ai_tool_request_flow --keepdb --noinput` passed: 38 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 15 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_live_ai_history_hydration --keepdb --noinput` passed: 9 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_live_ai_failure_finalization --keepdb --noinput` passed: 5 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c8_first_tool_cycle --keepdb --noinput` passed: 7 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_chat --keepdb --noinput` passed: 20 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.11 implementation and verification are complete within the approved scope.

## Archived Task: C10.10-H5 Use ChatKit Native Updates for Diagnostic Bundles

Result:
- Switched diagnostic bundle completion to native `chatkit.fetchUpdates()` as the primary ChatKit sync path.
- Left fallback UI only as a last-resort path when `fetchUpdates()` is unavailable or fails.
- Preserved final bundle message visibility through the existing ChatKit store/history mapping and stable `chatkit_item_id`.
- Removed remount/reload as the normal bundle-completion path.
- No migrations or changes to Portal, Telegram, customer-facing AI, or safety boundaries were made.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 15 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_ai_tool_request_flow --keepdb --noinput` passed: 35 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_live_ai_history_hydration --keepdb --noinput` passed: 9 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.10-H5 is complete within the approved scope.

## Archived Task: C10.10-H4 Reliable Final Bundle Delivery

Result:
- Added an explicit staff-only bundle execution status endpoint keyed by session and `bundle_execution_id`.
- Switched Live Admin AI bundle polling to the explicit bundle endpoint and stopped relying on ChatKit remount/history refresh for final delivery.
- Added a fallback assistant-style final summary card inside the Live Admin AI panel so the user sees the completed bundle result automatically without manual refresh.
- Added a bounded fallback notice when automatic final delivery still cannot complete inside the polling window.
- Preserved idempotent bundle messages, safe metadata-only responses, and no Portal/Telegram/customer-facing changes.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 15 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_ai_tool_request_flow --keepdb --noinput` passed: 35 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_live_ai_history_hydration --keepdb --noinput` passed: 9 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.10-H4 is complete within the approved scope.

## Archived Task: C10.10-H3 Auto-Refresh Running Diagnostic Bundles

Result:
- Replaced the diagnostic-bundle page reload path with bounded frontend polling that remounts ChatKit and reloads thread history after the same bundle completes.
- Added a visible running indicator inside the Live Admin AI panel while bundle execution is still in progress.
- Extended the staff-only bundle status endpoint with safe running/result identifiers needed for completion detection.
- Preserved existing bundle idempotency rules: no duplicate running/result messages and no individual tool messages inside the bundle transcript.
- No migrations or changes to Portal, Telegram, customer-facing AI, raw-output exposure, or tool safety scope were made.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 14 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_ai_tool_request_flow --keepdb --noinput` passed: 34 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_live_ai_history_hydration --keepdb --noinput` passed: 9 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.10-H3 is complete within the approved scope.

## Archived Task: C10.10-H2 Progressive Bundle UX and Non-Blocking Execution

Result:
- Diagnostic bundles now queue validated read-only ToolRuns and finish the ChatKit stream after one visible running message.
- Added stable `bundle_execution_id`, running/result ChatKit IDs, and retry-safe bundle lookup.
- ToolRun completion now finalizes one combined summary only after every expected bundle run reaches a terminal state.
- Added a staff-only bundle status endpoint and bounded frontend polling that reloads history once the final result exists.
- Preserved per-tool message suppression and reduced visible-message delete logging from warning to info.
- No migrations, Portal, Telegram, customer-facing AI, write/remediation/shell behavior, raw outputs, or secrets were added.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `test_admin_ai_tool_request_flow` passed: 34 tests.
- `test_live_admin_chat` passed: 13 tests.
- `test_live_ai_history_hydration` passed: 9 tests.
- `test_admin_live_ai_governance` passed: 8 tests.
- `test_admin_ai_agent_behavior` passed: 8 tests.
- `test_live_ai_failure_finalization` passed: 5 tests.
- `test_sprint_c8_first_tool_cycle` passed: 7 tests.
- `test_admin_chat` passed: 20 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.10-H2 is complete within the approved scope.

## Archived Task: C10.10-H1 Make ChatKit Delete Thread Item Idempotent

Scope:
- Make `AdminChatKitStore.delete_thread_item` safe for ChatKit internal lifecycle cleanup.
- Hard-delete only empty suppressed placeholders when requested by ChatKit.
- Treat missing items and visible-message delete attempts as no-op without breaking streams.

Out of scope:
- User-facing message deletion, Portal/Telegram/customer-facing behavior, migrations, tools/actions/remediation changes.

Result:
- Replaced the ChatKit item delete `PermissionDenied` with idempotent store handling.
- Missing items now return safely.
- Empty suppressed/internal handled placeholders are hard-deleted.
- Visible user messages, tool summaries, and bundle summaries are preserved with an internal warning only.
- Added focused coverage for missing deletes, placeholder cleanup, visible user preservation, visible tool summary preservation, and history hydration.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_live_ai_history_hydration --keepdb --noinput` passed: 9 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_ai_tool_request_flow --keepdb --noinput` passed: 34 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_live_ai_failure_finalization --keepdb --noinput` passed: 5 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c8_first_tool_cycle --keepdb --noinput` passed: 7 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_chat --keepdb --noinput` passed: 20 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.10-H1 is complete.

## Archived Task: C10.10 Multi-Tool Diagnostic Bundles

Scope:
- Add a code-only diagnostic bundle registry for Admin Live AI.
- Resolve broad server/web-stack execution intent to approved read-only tool bundles.
- Execute available bundle tools through existing allowlist, policy, plan, and selected-server validation.
- Show one bundle start message and one combined Arabic result summary.

Out of scope:
- Migrations, new tool definitions, write/remediation tools, shell execution, uploads, Portal AI, Telegram AI, and customer-facing AI.

Result:
- Added `apps.ai_chat.diagnostic_bundles` with server health and web stack bundle definitions.
- Added broad intent resolution for server-health requests while preserving specific single-tool requests.
- Executed bundle tools through existing validation, ToolPolicy, PlanTool, selected-server scope, and read-only allowlist.
- Added one bundle start message and one combined Arabic result message with bundle metadata and stable ChatKit IDs.
- Suppressed per-tool chat start/result messages for bundle runs while preserving ToolRun/AdminChatToolRequest records.
- Updated Live AI instructions and request analysis for diagnostic bundles.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_admin_ai_tool_request_flow --keepdb --noinput` passed: 34 tests.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_live_ai_failure_finalization --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_live_ai_history_hydration --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_sprint_c8_first_tool_cycle --keepdb --noinput` passed: 7 tests.
- `python manage.py test tests.unit.test_admin_chat --keepdb --noinput` passed: 20 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.10 is complete.

## Archived Task: C10.9-H7 Idempotent Tool Result Chat Messages

Scope:
- Make Live AI tool start/result chat messages idempotent across follow-up and sync paths.
- Prevent duplicates by `chatkit_item_id` and by `tool_run_id + tool_request_id + source`.
- Extend cleanup for duplicate detailed tool result summaries while preserving the best message.

Out of scope:
- Migrations, Portal/Telegram/customer-facing changes, write/remediation tools, shell execution, uploads, and policy expansion.

Result:
- Made tool result follow-up creation idempotent by stable `chatkit_item_id` and by `tool_request_id/tool_run_id/source`.
- Added start-message dedupe for `tool_orchestrator` messages per tool request.
- Kept repeated sync calls from creating duplicate detailed summaries.
- Extended cleanup to detect duplicate detailed result summaries and keep the best message by state/status, `chatkit_item_id`, and recency.
- Added tests for repeated sync, no duplicate ChatKit IDs, one start message, and detailed duplicate cleanup.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_admin_ai_tool_request_flow --keepdb --noinput` passed: 30 tests.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_live_ai_failure_finalization --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_live_ai_history_hydration --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_sprint_c8_first_tool_cycle --keepdb --noinput` passed: 7 tests.
- `python manage.py test tests.unit.test_admin_chat --keepdb --noinput` passed: 20 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.9-H7 is complete.

## Archived Task: C10.9-H6 Remove Duplicate Generic Tool Success Messages

Scope:
- Stop saving generic `<tool_key> completed successfully.` chat messages when a real Arabic tool result summary exists.
- Ensure only the detailed Arabic tool result is visible and hydrated in ChatKit history.
- Add safe cleanup support for legacy duplicate generic tool result messages.

Out of scope:
- Migrations, Portal/Telegram/customer-facing changes, write/remediation tools, shell execution, uploads, and policy expansion.

Result:
- Changed tool-result sync to use the chat-safe result summary path and skip creating another `tool_result_summary` when one already exists for the same `tool_run_id`.
- Assigned stable `chatkit_item_id` to sync-created or pre-existing result messages when needed.
- Preserved the Apache-specific 5xx summarizer used by C8.
- Extended `cleanup_live_ai_legacy_test_data` to dry-run/apply removal of old duplicate generic success messages only when a later detailed result exists for the same run.
- Added tests for duplicate prevention, history hydration, cleanup dry-run/apply, and preserving non-matching messages.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_admin_ai_tool_request_flow --keepdb --noinput` passed: 29 tests.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_live_ai_failure_finalization --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_live_ai_history_hydration --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_sprint_c8_first_tool_cycle --keepdb --noinput` passed: 7 tests.
- `python manage.py test tests.unit.test_admin_chat --keepdb --noinput` passed: 20 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.9-H6 is complete.

## Archived Task: C10.9-H5 Clean Direct Execution Chat Output

Scope:
- Hide confusing AI suggestion/approval wording only after explicit user execution intent actually creates a ToolRun/AgentJob.
- Keep backend start/result messages as the visible direct-execution output.
- Remove duplicate Arabic section headings from tool result summaries.
- Preserve advisory suggestions for non-execution questions.

Out of scope:
- Tool policy expansion, write/remediation tools, shell execution, uploads, Portal AI, Telegram AI, customer-facing changes, and migrations.

Result:
- Buffered Live AI text for deterministic direct-execution intent until tool orchestration confirms whether execution started.
- When ToolRun/AgentJob starts, stored the AI suggestion text as a hidden placeholder and displayed only backend start/result messages.
- Kept advisory suggestion text visible when the user asks what to check.
- Skipped hidden direct-execution placeholders during ChatKit history hydration.
- Avoided duplicate `الخلاصة:` / `التفسير:` headings when result summaries are already complete chat bodies.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_admin_ai_tool_request_flow --keepdb --noinput` passed: 27 tests.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_live_ai_failure_finalization --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_live_ai_history_hydration --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_sprint_c8_first_tool_cycle --keepdb --noinput` passed: 7 tests.
- `python manage.py test tests.unit.test_admin_chat --keepdb --noinput` passed: 20 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.9-H5 is complete.

## Archived Task: C10.9-H4 Direct Execution Intent and Real Tool Result Summaries

Scope:
- Detect explicit admin execution intent for approved read-only diagnostic checks.
- Add a deterministic fallback resolver from the user's latest message when the AI omits a proposal block.
- Improve safe Arabic summaries from `ToolRun.result_redacted`, especially `log_sources_discovery_v2`.
- Preserve existing allowlist, policy, plan, selected-server scope, and no write/remediation behavior.

Out of scope:
- Write/destructive tools, shell execution, remediation, uploads, Portal AI, Telegram AI, customer-facing AI, migrations, and policy expansion.

Result:
- Added direct execution-intent detection for explicit Arabic/English run/check/start/continue wording.
- Added deterministic mapping from user intent/scope to approved read-only tool proposals when the model omits a proposal block.
- Updated Live AI instructions and request analysis so explicit execution does not ask for extra approval.
- Added Arabic chat summaries for real `log_sources_discovery_v2` redacted results with counts, existing/missing paths, permission state, and metadata-only explanation.
- Added safe generic result-summary fallback without raw JSON, raw logs, or secrets.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_admin_ai_tool_request_flow --keepdb --noinput` passed: 27 tests.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_live_ai_failure_finalization --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_live_ai_history_hydration --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_sprint_c8_first_tool_cycle --keepdb --noinput` passed: 7 tests after rerun sequentially following a parallel database deadlock.
- `python manage.py test tests.unit.test_admin_chat --keepdb --noinput` passed: 20 tests after rerun sequentially following a parallel database deadlock.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.9-H4 is complete.

## Archived Task: C10.9-H3 Adaptive Tool Follow-up and Arabic Result Summary

Scope:
- Extend Live AI tool follow-up wait timing with a final grace refresh before timeout.
- Avoid timeout messages for ToolRuns that succeed within the practical wait window.
- Make backend start/final/failure/timeout/not-started messages Arabic and user-friendly.
- Improve safe result summaries beyond generic `completed successfully`.
- Keep multi-tool execution, combined summaries, and no raw JSON/secrets/log dumps.

Out of scope:
- Write/destructive/remediation tools, arbitrary commands, uploads, Portal AI, Telegram AI, customer-facing AI, migrations, and production-history cleanup.

Result:
- Extended single-tool follow-up wait to 45 seconds and added adaptive multi-tool waits up to 120 seconds.
- Added final grace wait and refresh before timeout to reduce timeout-then-success contradictions.
- Reworked backend tool execution messages into Arabic for start, success, failure, timeout, and not-started outcomes.
- Improved safe result summaries from redacted structured ToolRun output.
- Verified free-text tool names without proposal blocks do not execute tools.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_admin_ai_tool_request_flow --keepdb --noinput` passed: 21 tests.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_live_ai_failure_finalization --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_live_ai_history_hydration --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_sprint_c8_first_tool_cycle --keepdb --noinput` passed: 7 tests.
- `python manage.py test tests.unit.test_admin_chat --keepdb --noinput` passed: 20 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.9-H3 is complete.

## Archived Task: C10.9-H2 Tool Execution Completion Loop

Scope:
- Make Live AI-triggered read-only tool execution produce visible ChatKit start and final follow-up messages in the same lifecycle.
- Ensure each ToolRun triggered by Live AI has a final chat result message: summary, failed, timeout, or not-started.
- Support multiple safe proposal blocks with a combined result explanation.
- Remove stale Admin Live AI header copy that says read-only tools require explicit approval.

Out of scope:
- Write/destructive/remediation tools, arbitrary commands, uploads, Portal AI, Telegram AI, customer-facing AI, migrations, and tool policy expansion.

Result:
- Live AI-triggered tool start and final follow-up messages now stream back through ChatKit in the same response lifecycle.
- Final result messages are saved with explicit metadata sources: `tool_result_summary`, `tool_result_failed`, `tool_result_timeout`, or `tool_result_not_started`.
- Tool start/final messages receive stable `chatkit_item_id` metadata for immediate display and history hydration.
- Multiple proposal blocks produce per-tool results plus a combined final explanation.
- The Admin Live AI header no longer mentions explicit approval and now reflects automatic approved read-only execution.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_admin_ai_tool_request_flow --keepdb --noinput` passed: 17 tests.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_live_ai_failure_finalization --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_live_ai_history_hydration --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_sprint_c8_first_tool_cycle --keepdb --noinput` passed: 7 tests.
- `python manage.py test tests.unit.test_admin_chat --keepdb --noinput` passed: 20 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.9-H2 is complete.

## Archived Task: C10.9-H1 Auto-Execute Approved Read-Only Tools with Result Follow-up

Scope:
- Auto-execute valid Live AI read-only tool proposals through the existing ToolRun/AgentJob path.
- Poll briefly for completion and add a safe chat follow-up with result summary, failure reason, timeout/current status, or not-started explanation.
- Keep validation restricted to allowlisted, enabled, read-only tools permitted by ToolPolicy and PlanTool for the selected server.

Out of scope:
- Write/destructive/remediation tools, arbitrary shell, uploads, Portal AI, Telegram AI, customer-facing AI, and Portal/customer deterministic behavior changes.

Result:
- Valid Live AI proposals now create `AdminChatToolRequest` and immediately queue ToolRun/AgentJob through the existing policy-backed path.
- Added bounded backend follow-up polling with safe chat messages for succeeded, failed, timeout/current-status, and not-started outcomes.
- Added start messages only after actual ToolRun/AgentJob records are created.
- Updated Live AI instructions to avoid unsupported wait/completion claims.
- Preserved no raw proposal JSON, no unsafe raw output, no polling audit rows, and no Portal/Telegram/customer behavior changes.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_admin_ai_tool_request_flow --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_live_ai_failure_finalization --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_live_ai_history_hydration --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_sprint_c8_first_tool_cycle --keepdb --noinput` passed: 7 tests.
- `python manage.py test tests.unit.test_admin_chat --keepdb --noinput` passed: 20 tests when rerun alone after a parallel-test database deadlock.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.9-H1 is complete.

## Archived Task: C10.9-A AI Read-Only Tool Request Flow

Scope:
- Add a safe Admin Live AI proposal flow for read-only tool requests inside Admin Internal Chat.
- Require explicit staff approval before ToolRun/AgentJob creation through the existing policy-backed path.
- Validate proposals with a code allowlist plus existing ToolDefinition/ToolPolicy/plan/server checks.
- Add dry-run/apply cleanup for stale legacy pending Live AI audit rows.

Out of scope:
- Direct AI tool execution, auto-approved tools, write/destructive/remediation tools, arbitrary shell, uploads, Portal AI, Telegram AI, customer-facing AI, prompt management, and subscription/payment changes.

Result:
- Parsed hidden `<TOOL_REQUEST_PROPOSAL>` blocks from Live AI output and stripped them from streaming display and saved transcripts.
- Validated proposals against an explicit read-only allowlist plus current ToolDefinition, ToolPolicy, PlanTool, server-status, and server-scoped chat checks.
- Created `AdminChatToolRequest` only for valid proposals, with no ToolRun/AgentJob before approval.
- Added staff-only approve/reject flow in Admin Internal Chat; approval uses the existing `create_tool_run_job()` path and rejection creates no execution objects.
- Added `cleanup_live_ai_legacy_test_data` management command with dry-run default and explicit `--apply` for stale pending audit rows.
- Preserved Live AI generation audit scope: history/init/refresh/approval/rejection do not create `AdminLiveAIRequestLog`.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_live_ai_failure_finalization --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_live_ai_history_hydration --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_admin_ai_tool_request_flow --keepdb --noinput` passed: 11 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.9-A is complete.

## Archived Task: C10.8-H4 ChatKit History Hydration and Audit Scope

Scope:
- Hydrate Live Admin AI history from stored `AdminChatMessage` rows after refresh.
- Use stable ChatKit item IDs from `metadata_redacted.chatkit_item_id` or deterministic `admin_msg_<id>` fallback.
- Prevent `AdminLiveAIRequestLog` creation for ChatKit history/init/load requests.
- Add focused tests while preserving prompt behavior, Safe Context, no-tools/actions, Portal, and Telegram boundaries.

Out of scope:
- New models, migrations, prompt changes, diagnostic behavior changes, Safe Context builder changes, tools/function calling, ToolRun/AgentJob creation, command execution, remediation, Portal AI, Telegram AI, and customer deterministic chat changes.

Result:
- Hydration continues to read from `AdminChatMessage` through `AdminChatKitStore.load_thread_items`.
- Stored messages with `metadata_redacted.chatkit_item_id` keep that stable id; messages without one use deterministic `admin_msg_<id>`.
- `AdminLiveAIRequestLog` is now created only for generation request types, not `items.list` or `threads.get_by_id` history/init requests.
- Fixed non-streaming ChatKit byte responses so history/init requests return cleanly without audit rows.
- Added H4 tests for stored history hydration, item role/text/id mapping, no history audit, one generation audit, no pending refresh audit, no ToolRun/AgentJob, and Portal boundary.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_live_ai_failure_finalization --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_live_ai_history_hydration --keepdb --noinput` passed: 5 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.8-H4 is complete.

## Archived Task: C10.8-H3 Live AI UI Cleanup and Message Persistence

Scope:
- Remove the custom status/error strip from the Live Admin AI UI.
- Ensure Live AI user and assistant messages persist in the existing Admin Internal Chat session history.
- Enable ChatKit history loading from the existing store so refresh does not lose the transcript.
- Add focused tests while preserving audit, prompt behavior, no-tools/actions, Portal, and Telegram boundaries.

Out of scope:
- Prompt behavior changes, diagnostic intent changes, Safe Context builder changes, migrations unless unavoidable, tools/function calling, ToolRun/AgentJob creation, command execution, remediation, Portal AI, Telegram AI, and customer chat changes.

Result:
- Removed custom Live Admin AI status/error DOM and JavaScript display logic.
- Enabled ChatKit history with `history: { enabled: true }`.
- Verified Live AI user and assistant messages persist in `AdminChatMessage` and hydrate through `AdminChatKitStore.load_thread_items`.
- Verified transcripts do not store raw Safe Context or secret-like input.
- Preserved audit, H1 failure finalization, no ToolRun/AgentJob, Portal/customer deterministic chat, and C10.8-A behavior.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_live_ai_failure_finalization --keepdb --noinput` passed: 5 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.8-H3 is complete.

## Archived Task: C10.8-H2 Remove Visible Deterministic Fallback from Live Admin AI UI

Scope:
- Remove the visible deterministic fallback button and fallback panel from the Live Admin AI UI.
- Replace Live Admin AI UI/error copy that mentions deterministic fallback with generic safe messages.
- Keep backend deterministic behavior available for disabled/non-Live paths and Portal/customer chat unchanged.
- Add focused regressions while preserving C10.8-A behavior and C10.8-H1 audit finalization.

Out of scope:
- Prompt behavior changes, diagnostic reasoning changes, Safe Context/provider input changes, migrations, tools/function calling, ToolRun/AgentJob creation, command execution, remediation, Portal AI, Telegram AI, and customer deterministic chat changes.

Result:
- Removed the visible Live Admin AI `Deterministic fallback` button.
- Stopped rendering the deterministic fallback panel under ChatKit when Live Admin AI is available.
- Replaced Live AI UI/error copy with generic retry/refresh wording that does not mention fallback.
- Kept deterministic chat available for non-Live/disabled states and left Portal/customer deterministic chat untouched.
- Did not change prompt behavior, diagnostic reasoning, Safe Context/provider input, migrations, tools/actions, ToolRun/AgentJob, remediation, Portal AI, or Telegram AI.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_live_ai_failure_finalization --keepdb --noinput` passed: 5 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.8-H2 is complete.

## Archived Task: C10.8-H1 Live AI Failure State & Audit Finalization

Scope:
- Ensure Live Admin AI audit records are finalized as succeeded or failed, including exceptions raised during streaming iteration.
- Add safe failure logging without prompts, raw context, raw messages, responses, env, or secrets.
- Clear stale Live AI UI failure messages when a new request starts or a same-origin Live AI response succeeds.
- Add focused tests while preserving C10.8-A prompt behavior and execution boundaries.

Out of scope:
- Prompt behavior changes, migrations, new buttons, quick actions, tools/function calling, ToolRun/AgentJob creation, command execution, remediation, Portal/customer deterministic chat changes, and Telegram AI.

Result:
- Wrapped Live Admin AI streaming iteration so generator exceptions finalize `AdminLiveAIRequestLog` as failed instead of leaving pending rows.
- Added safe failure breadcrumbs with session/audit/status/error/model/latency only.
- Cleared stale Live AI UI error text before retry and after successful same-origin responses.
- Added focused hotfix tests for pre-stream and in-stream failures, success after failure, frontend reset logic, and Portal/tool boundaries.
- No migrations, prompt behavior changes, UI buttons, quick actions, ToolRun/AgentJob, command execution, remediation, Portal AI, or Telegram AI changes were made.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_live_ai_failure_finalization --keepdb --noinput` passed: 5 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.8-H1 is complete.

## Archived Task: C10.8-A Admin AI Agent Behavior & Contextual Diagnostic Reasoning

Scope:
- Improve the hardcoded Live Admin AI instructions for internal operational advisory behavior.
- Detect diagnostic intent from the redacted conversation and pass safe request-analysis metadata to the provider input.
- Keep ordinary requests concise and diagnostic requests structured but flexible.
- Add focused tests while preserving audit, feature flag, no-tools/actions, no Portal AI, and no Telegram AI boundaries.

Out of scope:
- Prompt profile database module, migrations, Admin prompt editing UI, Diagnostic Brief button, quick actions, tools/function calling, ToolRun/AgentJob creation, command execution, remediation, uploads, Portal/customer AI changes, and Telegram AI.

Result:
- Confirmed the current prompt is hardcoded in `apps/ai_chat/live_ai.py` as `LIVE_AI_INSTRUCTIONS`, with no settings-based prompt or prompt profile layer.
- Strengthened internal operational advisory, Safe Context-only, diagnostic reasoning, limitations, and read-only suggested-check instructions.
- Added diagnostic intent detection and safe request-analysis metadata without schema changes.
- Added focused behavior tests and kept UI, Portal, Telegram, tools/actions, ToolRun/AgentJob, command execution, and remediation unchanged.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.8-A is complete.

## Archived Task: C10.7-A Admin Live AI Governance Layer

Scope:
- Add safe per-request audit logging for Live Admin AI, including scoped IDs, status, latency, sizes, model, classified error, and fallback usage.
- Add readonly Django Admin list/filter/search visibility for Live AI audit records.
- Display non-secret Live AI enabled/model/rate-limit/safe-context-cap status in Admin Internal Chat.
- Add focused governance tests while preserving Admin-only, feature flag, Safe Context, no-tools/actions, Portal, and Telegram boundaries.

Out of scope:
- New AI capabilities, tools/function calling, command execution, remediation, uploads, Portal AI/customer deterministic changes, Telegram AI, raw prompt logging, and secret exposure.

Result:
- Added `AdminLiveAIRequestLog` and one migration for per-request Live AI governance audit.
- Logged successful and failed Live AI requests with classified errors, fallback usage, sizes, latency, user/session/account/server/application scope, and model.
- Added readonly Django Admin visibility and non-secret Admin Internal Chat status display.
- Redacted request payloads before ChatKit server processing to prevent raw secret-like user input from being echoed in SSE responses.
- Preserved Portal, Telegram, deterministic customer chat, tools/actions, uploads, and remediation boundaries.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no additional changes.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.7-A is complete.

## Archived Task: C10.6-H1 Fix ChatKit frontend initialization API mismatch

Scope:
- Verify the current official ChatKit Custom Server browser initialization contract.
- Correct the embedded Admin ChatKit options without changing the live backend unless required.
- Move the JavaScript asset into an app-owned static source so `collectstatic` discovers it automatically.
- Add focused initialization/static-discovery regressions while preserving staff-only, feature-flag, Safe Context, and no-tools boundaries.

Out of scope:
- Portal, Telegram, Hosted Agent Builder, tools/actions, backend provider behavior, migrations, and live infrastructure changes.

Result:
- Replaced invalid top-level `apiURL` and `fetch` with `api: { url, domainKey, fetch }` and replaced `header: false` with `header: { enabled: false }`.
- Added required `OPENAI_CHATKIT_DOMAIN_KEY` configuration and fail-closed rendering when it is missing.
- Moved the JavaScript source into `apps/ai_chat/static/admin_chat/` so Django app static discovery collects it without manual copying.
- Kept the existing Custom Server endpoint, Safe Context/provider logic, staff-only restriction, feature flag, and no-tools boundary unchanged.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `findstatic` resolved the asset from the `ai_chat` app static directory.
- `collectstatic --dry-run --noinput -v 2` included the asset and completed with 128 files.
- `git diff --check` passed.

Completion status:
- C10.6-H1 is complete.

## Archived Task: C10.6 Live Admin ChatKit with Custom Server MVP

Scope:
- Add feature-flagged, staff-only embedded ChatKit to Admin Internal Chat.
- Implement a Django Custom Server endpoint with safe-context-only live response streaming.
- Preserve current deterministic chat as the disabled/provider-failure/CDN fallback.
- Add server-side OpenAI configuration, rate limiting, safe persistence, audit metadata, and deployment documentation.

Out of scope:
- Portal or Telegram Live AI, tools/function calling/actions, ToolRequest/ToolRun/AgentJob creation, uploads, remediation, AI report generation, Agent Builder, Codex CLI runtime, and migrations.

Result:
- Added a disabled-by-default embedded ChatKit panel and staff-only Custom Server SSE endpoint.
- Added fresh capped/redacted Safe Context input, server-only provider configuration, rate limiting, timeout/failure/disconnect handling, safe completed-message persistence, and audit metadata.
- Kept deterministic chat available as fallback and left Portal, Telegram, tools, actions, uploads, remediation, and reports unchanged.
- Added ASGI/Uvicorn, Nginx buffering, CSP, and smoke-test documentation without changing live infrastructure.

Verification:
- `python manage.py check` passed with no issues.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- 42 Safe Context, Admin Chat, C10.5 split, and Live ChatKit tests reached `OK` with an in-memory SQLite override; the shell wrapper timed out after printing completion while closing the temporary database.
- `pip check` passed with no broken requirements.
- PostgreSQL-backed rerun remains pending because the local service is stopped and cannot be started with current permissions.

Completion status:
- C10.6 implementation is complete.

## Archived Task: C10.6-Pre Safe Context Hard Cap and Live AI Readiness

Scope:
- Enforce a deterministic structured hard byte cap on Safe Context.
- Add a second-redaction, allowlisted AI-ready context preparation layer.
- Add canary-secret, size-cap, JSON-integrity, priority, and no-execution tests.
- Make the cap configurable through `AI_SAFE_CONTEXT_MAX_BYTES` with a safe default.

Out of scope:
- ChatKit, Live AI, OpenAI calls, ASGI/SSE, Telegram, Portal changes, tools, AgentJobs, remediation, uploads, and migrations.

Result:
- Added deterministic structured hard-cap enforcement with original/final/max size metadata.
- Added `prepare_safe_context_for_ai()` with second redaction, an explicit allowlist, prompt-injection guidance, and no execution behavior.
- Added environment-backed configuration, canary-secret coverage, critical-finding priority, JSON-integrity checks, and no-execution assertions.
- Updated readiness documentation without adding ChatKit, Live AI, OpenAI calls, migrations, or execution paths.

Verification:
- `python manage.py test tests.unit.test_ai_context --noinput` passed: 5 tests.
- PostgreSQL-backed `tests.unit.test_safe_context_builder` could not start because the local PostgreSQL service is stopped and unavailable to the current process.
- The same Safe Context module passed 8 tests with an in-memory SQLite test override.
- Related chat/report/tool-summary regressions reached `OK`: 49 tests passed with the SQLite override; the shell wrapper timed out after printing completion.
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.6-Pre implementation is complete pending commit.
- Live AI and ChatKit remain unimplemented.

## Archived Task: C10.5-C Current State Reconciliation

Scope:
- Reconcile project documentation with the implemented and manually verified current state.
- Record C1-C9, C10-A, C10.5, and C10.5-B accurately.
- Keep C10-B deferred and Telegram unstarted.
- Make no application code, migration, runtime, permission, or execution-path changes.

Result:
- Corrected the execution status and current-state summary.
- Updated README, work log, and execution report.
- Archived all historical `Active Task` headings.
- No application code, migrations, runtime, permissions, execution paths, Portal/Admin Chat logic, Live AI, Telegram, or server state were changed.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed with no issues.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.5-C documentation reconciliation is complete pending its independent commit.

## Next Proposed Sprint: C10.6 Live Admin AI Chatbot MVP

- Proposed before Telegram unless a later approved decision changes the order.
- Live AI would start in staff-only Admin Internal Chat, not Portal or Telegram.
- Telegram is not the immediate next task and has not started.

## Archived Task History

All task entries below are completed or historical records. Their headings are retained as archived task history.

## Archived Task - Sprint C2 Safe Context Builder MVP

Task:
- Execute Sprint C2 from the approved corrected Matrix Scanner SaaS roadmap.

Scope:
- Add a dedicated `apps/ai_context` app/service that builds safe, versioned, capped JSON context.
- Include safe summaries for account, server, latest baseline, applications, services, domains, log sources, findings, reports, knowledge, recommendations, recent ToolRuns, available tools, and risk summary where available.
- Enforce account scoping and role-aware visibility.
- Include `available_tools` metadata respecting ToolPolicy and PlanTool.
- Add tests for account scoping, redaction, raw output exclusion, output caps, and available tool policy filtering.

Out of scope:
- Live AI provider calls.
- Chat models/UI.
- Tool execution.
- Direct AgentJob access.
- Raw logs, raw `.env`, credentials, tokens, raw AgentJob result, or raw ToolRun output.
- Moving to Sprint C3.

Immediate next steps:
- Inspect relevant models and tool policy services.
- Implement context builder and tests.
- Run Sprint C2 validation.

## Archived Task - Sprint C1.5 Remote Bootstrap Runtime Completion

Task:
- Execute Sprint C1.5 from the approved corrected Matrix Scanner SaaS roadmap.

Scope:
- Update Remote Bootstrap so the installed bundle is a real polling Runtime/Agent, not registration/heartbeat only.
- Reuse existing bootstrap models, services, admin, credentials, TTL, cleanup, fixed command templates, and tests.
- Preserve Matrix Admin-only bootstrap.
- Preserve install path `/opt/matrix_scanner` and service name `matrix-scanner-agent.service`.
- Ensure generated config contains `base_url`, `registration_token` or `agent_token`, `poll_interval_seconds`, and `runtime_mode`.
- Add/update tests for runtime config, systemd service target, polling/job execution support in the bundle, credential cleanup, and raw command rejection.

Out of scope:
- Portal/customer bootstrap.
- New raw shell or arbitrary commands.
- Tool philosophy changes.
- Remediation/write/destructive actions.
- Server or VM execution.
- Moving to Sprint C2.

Immediate next steps:
- Inspect current bootstrap bundle and runtime executor.
- Patch only bootstrap runtime bundle/install flow as needed.
- Update focused bootstrap tests.
- Run Sprint C1.5 validation.

Progress:
- Updated bootstrap runtime archive generation to package the current `scanner_runtime` modules.
- Replaced the heartbeat-only generated `agent_service.py` behavior with a polling runtime service that registers, heartbeats, polls, executes allowlisted jobs through `scanner_runtime.prototype`, and submits results.
- Added `runtime_mode = polling_agent` to the generated bootstrap config.
- Preserved `/opt/matrix_scanner` and `matrix-scanner-agent.service`.
- Added focused tests for runtime archive contents, polling runtime service behavior markers, generated config shape, and systemd service target.
- Added Sprint C1.5 report to `docs/planning/تقارير التنفيذ.md`.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint3_bootstrap --noinput` passed: 13 tests.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 294 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint C1.5 implementation is complete within the approved scope.
- No Portal/customer bootstrap, raw shell/arbitrary command expansion, remediation/write/destructive behavior, server/VM execution, or Sprint C2 work was added.

## Archived Task - Sprint C1 Current State and Documentation Alignment

Task:
- Execute Sprint C1 from the approved corrected Matrix Scanner SaaS roadmap.

Scope:
- Align documentation around the approved correction references:
  - `docs/planning/ROADMAP-CORRECTION.md`
  - `docs/planning/CORRECTED-EXECUTION-PLAN.md`
  - `docs/planning/DECISION-REGISTER.md`
- Confirm the decision register is the official decision reference.
- Confirm `CORRECTED-EXECUTION-PLAN.md` is the top execution reference after `ROADMAP-CORRECTION.md`.
- Document that the first real implementation Sprint after documentation alignment is `Sprint C1.5 - Remote Bootstrap Runtime Completion`.
- Run non-destructive validation commands.

Out of scope:
- Product code changes.
- Model/service/runtime changes.
- Migrations beyond dry-run checks.
- Tests that require new product behavior.
- Server execution.
- Moving to Sprint C1.5.

Immediate next steps:
- Inspect current planning/README docs for stale roadmap references.
- Patch only documentation that needs alignment.
- Run requested C1 verification commands.

Progress:
- Added corrected-roadmap documentation links to `README.md`.
- Added a corrected roadmap authority section to `PLANS.md`.
- Added corrected roadmap references to `docs/DECISIONS.md`.
- Added Sprint C1 report to `docs/planning/تقارير التنفيذ.md`.
- Confirmed `docs/planning/DECISION-REGISTER.md` is the official decision reference.
- Confirmed `docs/planning/CORRECTED-EXECUTION-PLAN.md` is the top execution reference after `docs/planning/ROADMAP-CORRECTION.md`.
- Confirmed the first real implementation Sprint after documentation alignment is `Sprint C1.5 - Remote Bootstrap Runtime Completion`.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 292 tests, 4 skipped.
- Initial full test run also reached `OK` but the shell wrapper timed out after printing results; it was rerun with a longer timeout and exited successfully.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint C1 documentation alignment is complete.
- No product code, model/service/runtime changes, migrations, or server execution were performed.
- Do not move to Sprint C1.5 until the owner approves proceeding.

## Archived Task - Decision Register Approval Update

Task:
- Mark `docs/planning/DECISION-REGISTER.md` as approved and record the owner approval.

Scope:
- Update decision register status only.
- Update documentation tracking.

Out of scope:
- Code changes.
- Migrations.
- Tests.
- Runtime changes.
- Server execution.

Progress:
- Marked `docs/planning/DECISION-REGISTER.md` as `Approved`.
- Added owner approval line dated 2026-06-05.
- Recorded that `DECISION-REGISTER.md` is the official decision reference.
- Recorded that `CORRECTED-EXECUTION-PLAN.md` is the top execution reference after `ROADMAP-CORRECTION.md`.
- Recorded that the first real implementation Sprint after documentation alignment is `Sprint C1.5 - Remote Bootstrap Runtime Completion`.

Verification:
- `git diff --check` passed with line-ending warnings only.
- No code, migrations, tests, runtime changes, or server execution were performed.

## Archived Task - Roadmap Tool Runtime Correction Detail

Task:
- Strengthen `docs/planning/ROADMAP-CORRECTION.md` with the attached command-template-first tool/runtime correction.

Scope:
- Keep the correction in the roadmap reference file.
- Clarify Admin AI Chatbot, Tool Registry, Runtime/Agent, and new-tool workflow responsibilities.

Out of scope:
- Product code changes.
- Migrations.
- Runtime command-template execution implementation.
- ToolPolicy/PlanTool changes.
- AI or Telegram implementation.
- Commit or push.

Immediate next steps:
- Patch `ROADMAP-CORRECTION.md`.
- Verify UTF-8 readability and diff formatting.

Progress:
- Added detailed tool shape guidance to the roadmap reference.
- Added Admin AI Chatbot tool responsibilities.
- Added Runtime/Agent command executor responsibilities.
- Added Tool Registry to Runtime execution flow.
- Added new command-template proposal, validation, and approval flow.
- Added tool type classification: `command_template`, `script_template`, and `runtime_handler`.

Verification:
- Confirmed expected command-template markers exist in `ROADMAP-CORRECTION.md`.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Roadmap tool/runtime correction detail is complete.
- No product code, migrations, runtime command-template implementation, ToolPolicy/PlanTool changes, AI/Telegram implementation, commit, or push was added.

## Archived Task - Tool Model Correction

Task:
- Apply the attached correction that Matrix Scanner tools should primarily be approved read-only command templates, not necessarily runtime handlers.

Scope:
- Update the planning documents created for the corrected roadmap.
- Clarify Tool Registry, Runtime/Agent, Tool Builder, and phase 5 terminology.
- Preserve all security constraints.

Out of scope:
- Product code changes.
- Migrations.
- Runtime command-template execution implementation.
- ToolPolicy/PlanTool activation.
- AI or Telegram implementation.
- Commit or push.

Immediate next steps:
- Patch the relevant Markdown plan sections.
- Verify UTF-8 readability and diff formatting.

Progress:
- Updated the roadmap correction reference to state that tools are primarily approved read-only command/script templates in Tool Registry.
- Updated the execution plan to use `Safe Command Execution Runtime` and command-template-first Tool Builder flow.
- Clarified that runtime handlers remain available later for advanced collectors/parsers only.

Verification:
- Confirmed both updated Markdown files read correctly as UTF-8.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Tool model correction is complete in the planning documents.
- No product code, migrations, runtime command-template implementation, ToolPolicy/PlanTool activation, AI/Telegram implementation, commit, or push was added.

## Archived Task - Corrected Execution Plan

Task:
- Create a detailed implementation plan Markdown file based on the roadmap correction and current project state.

Scope:
- Study the corrected one-AI architecture.
- Reconcile it with current implemented components and deferred work.
- Produce a practical phased execution plan for the next project stages.

Out of scope:
- Product code changes.
- Migrations.
- Runtime handlers.
- ToolPolicy/PlanTool activation.
- AI or Telegram implementation.
- Commit or push.

Immediate next steps:
- Inspect current planning and implementation state.
- Create the new execution plan document.
- Run formatting/diff checks.

Progress:
- Reviewed the corrected roadmap reference and current implementation files for baseline profiles, tool setup, runtime executor, diagnostics, reports, Telegram, and Tool Registry.
- Created `docs/planning/CORRECTED-EXECUTION-PLAN.md`.
- Defined practical phases and sprint candidates from Safe Context Builder through Telegram Pilot.

Verification:
- Confirmed the Markdown file reads correctly as UTF-8.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Corrected execution plan document is complete.
- No product code, migrations, runtime handlers, ToolPolicy/PlanTool activation, AI/Telegram implementation, commit, or push was added.

## Archived Task - Roadmap Correction Markdown Reference

Task:
- Convert `docs/planning/خطة_تصحيح_المسار_Matrix_Scanner_SaaS.docx` into a Markdown reference document for future project phases.

Scope:
- Preserve the corrected roadmap and terminology from the Word document.
- Make the Markdown usable as the reference plan for the next phases.
- Keep the plan centered on one Admin AI Chatbot and supporting service layers.

Out of scope:
- Product code changes.
- Migrations.
- Runtime handlers.
- ToolPolicy/PlanTool activation.
- AI/Telegram implementation.
- Commit or push.

Immediate next steps:
- Create the Markdown reference file in `docs/planning`.
- Run formatting/diff checks.
- Update tracking with the result.

Progress:
- Created `docs/planning/ROADMAP-CORRECTION.md`.
- Converted the roadmap correction content into Markdown sections, phase tables, phase details, fixed security constraints, practical priority order, and terminology definitions.

Verification:
- Confirmed the Markdown file reads correctly as UTF-8.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Roadmap correction Markdown reference is complete.
- No product code, migrations, runtime handlers, ToolPolicy/PlanTool activation, AI/Telegram implementation, commit, or push was added.

## Archived Task - Phase 2 Sprint 2.11B Application Ingestion

Task:
- Implement only Phase 2 application ingestion and deduplication for `opt_apps_discovery` and `django_apps_discovery`.

Scope:
- Add nullable `Application.baseline_scan`.
- Map safe Phase 2 application outputs into `Application`.
- Deduplicate by existing application location constraint.
- Apply framework priority and safe metadata merging.
- Keep approved applications from being overwritten aggressively.
- Update application summary counts using scan attribution where available.

Out of scope:
- Report redesign.
- AI planner.
- External bot.
- ToolPolicy/PlanTool changes.
- Runtime tool changes.
- Findings generation.
- Remediation/write actions.
- Service-to-application relationship modeling.

Immediate next steps:
- Add application scan attribution and migration.
- Update baseline application ingestion mapping.
- Add focused ingestion tests.
- Run requested verification commands.

Progress:
- Added nullable `Application.baseline_scan` attribution.
- Added migration `applications.0003_application_baseline_scan`.
- Added Phase 2 ingestion for `opt_apps_discovery` and `django_apps_discovery`.
- Added application deduplication/enrichment using the existing application location constraint.
- Added framework priority and approved-application preservation.
- Updated application summary counts to prefer scan-scoped applications with legacy fallback.
- Added focused tests for Phase 2 app ingestion, safety, deduplication, summary counts, and legacy behavior.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_baseline_ingestion --noinput` passed: 15 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint5_baseline --noinput` passed: 22 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 291 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.11B implementation is complete within the approved scope.
- No report/AI/external bot/ToolPolicy/runtime/finding/remediation changes were added.
- No commit or push was made.

## Archived Task - Phase 2 Sprint 2.11B Nested App Hotfix

Task:
- Filter clearly internal nested `opt_apps_discovery` package candidates during Phase 2 application ingestion.

Scope:
- Skip nested depth-2 opt candidates under an already detected parent app when they only have weak markers and no systemd hint.
- Keep top-level apps.
- Keep nested standalone apps with strong markers or explicit hints.
- Preserve Django enrichment of the real parent app.

Out of scope:
- Migrations.
- Report redesign.
- AI planner.
- External bot.
- ToolPolicy/PlanTool changes.
- Runtime tool changes.
- Findings generation.
- Remediation/write actions.
- Service-to-application relationship modeling.

Immediate next steps:
- Patch Phase 2 application ingestion filter.
- Add focused regression tests.
- Run requested verification commands.

Progress:
- Added nested internal candidate filtering for `opt_apps_discovery`.
- Skips depth-2 nested package candidates under an already detected parent app when they lack systemd/explicit app hints and strong standalone markers.
- Preserves top-level apps and nested standalone apps with strong markers or systemd hints.
- Preserves `django_apps_discovery` enrichment for the real parent Django app.
- Added focused regression coverage.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_baseline_ingestion --noinput` passed: 16 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint5_baseline --noinput` passed: 22 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 292 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.11B nested app hotfix is complete within the approved scope.
- No migration/report/AI/external bot/ToolPolicy/runtime/finding/remediation changes were added.
- No commit or push was made.

## Archived Task - Phase 2 Sprint 2.11A Ingestion

Task:
- Implement only Phase 2 services, domains, and log source ingestion plus scan-scoped summary counts.

Scope:
- Map Phase 2 service discovery outputs into `DiscoveredService`.
- Map `nginx_sites_discovery.domains[]` into `DiscoveredDomain`.
- Map `log_sources_discovery_v2.log_sources[]` into `LogSource`.
- Keep ingestion safe, redacted, tolerant of malformed output, and metadata-capped.
- Make `summarize_scan()` scan-scoped for models that already support `baseline_scan`.

Out of scope:
- Application ingestion.
- `Application.baseline_scan` migration.
- Report redesign.
- AI planner.
- External bot.
- ToolPolicy/PlanTool changes.
- Runtime tool changes.
- Findings generation from Phase 2.
- Remediation/write actions.

Immediate next steps:
- Update `apps/servers/baseline.py` ingestion mapping.
- Add focused `tests/unit/test_phase2_baseline_ingestion.py`.
- Run the requested verification commands.

Progress:
- Added Phase 2 services ingestion into `DiscoveredService`.
- Added Phase 2 Nginx domain ingestion into `DiscoveredDomain`.
- Added Phase 2 log source ingestion into `LogSource`.
- Added safe metadata selection, redaction, caps, and merge behavior.
- Updated scan summaries to count scan-scoped services, domains, log sources, and findings.
- Kept applications at `0` until the deferred application ingestion sprint.
- Added focused Phase 2 baseline ingestion tests and updated the Sprint 5 Phase 2 expectation.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_baseline_ingestion --noinput` passed: 10 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 285 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.11A implementation is complete within the approved scope.
- No Application ingestion/migration/report/AI/tool activation/runtime/remediation changes were added.
- No commit or push was made.

## Archived Task - Phase 2 Sprint 2.11A Metadata Hotfix

Task:
- Prevent unknown Gunicorn/Uvicorn discovery rows from overwriting generic systemd service metadata.

Scope:
- Update service ingestion so `gunicorn_uvicorn_services_discovery` only ingests/enriches `gunicorn`, `uvicorn`, or `daphne` services.
- Add a focused regression test.

Out of scope:
- Application ingestion.
- Migrations.
- Report redesign.
- AI planner.
- External bot.
- ToolPolicy/PlanTool changes.
- Runtime tool changes.
- Findings generation.
- Remediation/write actions.

Immediate next steps:
- Patch Phase 2 service ingestion filter.
- Update focused ingestion tests.
- Run requested verification commands.

Progress:
- Added filtering so `gunicorn_uvicorn_services_discovery` only ingests/enriches `gunicorn`, `uvicorn`, and `daphne` services.
- Skips missing, empty, or `unknown` `process_type` rows from that tool.
- Added regression coverage for generic systemd service metadata preservation and real Gunicorn enrichment.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_baseline_ingestion --noinput` passed: 10 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_baseline_ingestion tests.unit.test_sprint5_baseline --noinput` passed: 32 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 286 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.11A metadata hotfix is complete within the approved scope.
- No Application ingestion/migration/report/AI/tool activation/runtime/remediation changes were added.
- No commit or push was made.

## Archived Task - Phase 2 Sprint 2.10 Pilot Tool Enablement

Task:
- Implement only the Sprint 2.10 management command/helper for safe Phase 2 pilot tool enablement.

Scope:
- Add `enable_phase2_pilot_tools --plan-id <PLAN_ID>` with dry-run support.
- Enable only Phase 2 discovery tools required by `debian_nginx_opt`.
- Scope PlanTool creation/update to the selected plan only.
- Keep customer execution disabled for these tools.
- Add focused tests for safety, scoping, and baseline preflight readiness.

Out of scope:
- Migrations.
- Admin UI.
- Customer Portal behavior.
- Automatic scan creation.
- ToolRun/AgentJob creation inside the command.
- Baseline ingestion.
- Report changes.
- AI planner.
- External bot.
- Remediation/actions.
- Global activation for all plans.

Immediate next steps:
- Add the enablement helper and management command.
- Add focused unit tests.
- Run the requested verification commands.

Progress:
- Added the Phase 2 pilot enablement helper.
- Added the `enable_phase2_pilot_tools --plan-id <PLAN_ID> [--dry-run]` management command.
- Kept dry-run write-free.
- Scoped PlanTool creation/update to the selected plan only.
- Kept customer execution disabled for Phase 2 pilot tools.
- Added focused tests for command safety, policy/plan scoping, and Debian/Nginx baseline preflight readiness.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_pilot_enablement --noinput` passed: 11 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 275 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.10 implementation is complete within the approved scope.
- No migration/Admin UI/Portal/ingestion/report/AI/external bot/remediation/global activation changes were added.
- No commit or push was made.

## Archived Task - Phase 2 Sprint 2.9 Baseline Profiles

Task:
- Implement only the Sprint 2.9 baseline profile and runtime tool selection layer.

Scope:
- Add profile definitions for `legacy_cpanel`, `debian_nginx_opt`, and `minimal_linux`.
- Add `BaselineScan.profile_key` with default `legacy_cpanel`.
- Use the selected profile to decide baseline preflight and ToolRun/AgentJob creation.
- Keep default behavior identical to the current cPanel-oriented baseline.
- Add focused regression tests for profile tool selection and preflight scoping.

Out of scope:
- Phase 2 ingestion mapping.
- Report changes.
- ToolPolicy or PlanTool activation.
- AI planner.
- External bot.
- Remediation/actions.
- Customer-facing behavior changes.

Immediate next steps:
- Add profile definitions and model field migration.
- Update baseline orchestration to use selected profile tools.
- Add focused tests.
- Run the requested verification commands.

Progress:
- Added baseline profile definitions for `legacy_cpanel`, `debian_nginx_opt`, and `minimal_linux`.
- Added `BaselineScan.profile_key` with default `legacy_cpanel`.
- Updated baseline preflight and enqueue logic to use the selected profile's tool list.
- Kept default cPanel baseline behavior unchanged.
- Added a small BaselineScan Admin visibility improvement for `profile_key`.
- Added focused profile selection and preflight regression tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint5_baseline --noinput` passed: 21 tests.
- First full-suite run produced `OK` but hit the command timeout after test completion; rerun passed cleanly.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 264 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.9 implementation is complete within the approved scope.
- No ingestion/report/ToolPolicy activation/AI planner/external bot changes were added.
- No commit or push was made.

## Archived Task

Task:
- Sprint 1 Django SaaS Core implementation.

Scope:
- Set up Django project `scanner_platform`.
- Add PostgreSQL-ready settings, `requirements.txt`, and minimal setup notes.
- Create Sprint 1 apps: `accounts`, `servers`, `applications`, `plans`, `subscriptions`, `audit`, `core`.
- Implement Sprint 1 models only: Account, custom User, Server, Application, Plan, Subscription, AuditLog.
- Configure Django Admin for Sprint 1 models.
- Keep Matrix Admin as Django staff/superuser and customer roles as owner/operator/viewer.

Out of scope:
- Agent APIs.
- Remote Bootstrap.
- Baseline Scan.
- Scanner Runtime.
- Tool Registry.
- Policy Engine.
- Telegram.
- Diagnostic Agent.
- Celery.
- Payment gateway.
- Remediation/action features.

Immediate next steps:
- Inspect current scaffold and Python/Django availability.
- Create Django project/app files within Sprint 1 scope.
- Run Django checks and migration creation if dependencies are available.

Progress:
- Read AGENTS.md, PLANS.md, docs/CURRENT-TASKS.md, docs/DECISIONS.md, and execution plan as instructed.
- Added Django project `scanner_platform`.
- Added required Sprint 1 apps and models.
- Added Django Admin registrations.
- Added initial migrations.
- Added minimal Sprint 1 model tests.
- Updated README setup notes.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no missing migrations, with a PostgreSQL connection warning because local PostgreSQL is not running.
- `python manage.py test tests.unit --noinput` discovered 4 tests but failed before execution because no local PostgreSQL service was reachable to create a test database.
- AST syntax parsing succeeded for 49 Python files.
- No out-of-scope Sprint 2+ modules were implemented.

Completion:
- Sprint 1 implementation is complete pending commit.
- Remaining issue: rerun tests with PostgreSQL available.

## Archived Task - Push Sprint 1 Commit

Task:
- Push Sprint 1 commit `508a1e6` to `origin/main`.

Scope:
- Push existing local commit only.
- Update `LOG.md` and `docs/CURRENT-TASKS.md` before and after the push.

Out of scope:
- Any code changes.
- Any new Sprint 1 implementation.

Immediate next steps:
- Push `main` to `origin/main`.

Completion:
- Pushed `main` to `origin/main`.
- Included Sprint 1 commit `508a1e6` and tracking commit `f8726de`.
- Remaining work: rerun tests when PostgreSQL is available.

## Archived Task - Local Development Environment

Task:
- Prepare and verify the local development/testing environment for the current Sprint 1 Django codebase.

Scope:
- Verify `requirements.txt`.
- Add local development documentation with Windows PowerShell commands.
- Add PostgreSQL development database option via Docker Compose.
- Ensure `.env.example` covers required local variables.
- Run or document the requested setup/check/test commands.

Out of scope:
- Sprint 2.
- Agent APIs.
- Scanner Runtime.
- Remote Bootstrap.
- Baseline Scan.
- Tool Registry.
- Policy Engine.
- Telegram.
- Diagnostic Agent.
- Celery/Redis implementation.
- Business features or remediation actions.

Immediate next steps:
- Inspect current requirements and environment files.
- Add `docker-compose.dev.yml` and `docs/operations/LOCAL-DEVELOPMENT.md`.
- Run available local verification commands and record results.

Progress:
- Verified current requirements are sufficient for Sprint 1 local Django execution.
- Added Docker Compose PostgreSQL development service.
- Added Windows PowerShell local development guide.
- Updated `.env.example` for local PostgreSQL variables.
- Updated README setup notes.

Verification:
- Docker CLI and Docker Compose are installed.
- `docker compose -f docker-compose.dev.yml config` passed.
- Docker PostgreSQL startup failed because Docker Desktop Linux engine is not running.
- `python -m venv .venv` failed during `ensurepip`; partial `.venv` was removed.
- Activation command could not run because the venv was not created.
- `python -m pip install -r requirements.txt` succeeded in the user/global Python environment.
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no missing migrations, with expected PostgreSQL connection warning.
- `migrate`, `createsuperuser`, and `test` failed because PostgreSQL was unavailable.

Completion:
- Local setup documentation and Docker PostgreSQL option are in place.
- Remaining setup: start Docker Desktop or configure manual PostgreSQL, then rerun database-dependent commands.

## Archived Task - Local Development Documentation Adjustment

Task:
- Adjust local development setup documentation so Docker is optional only and manual Windows PostgreSQL setup is the primary path.

Scope:
- Update `docs/operations/LOCAL-DEVELOPMENT.md`.
- Update `README.md` if needed.
- Update `.env.example` only if wording/variables need clarification.
- Update `LOG.md` and `docs/CURRENT-TASKS.md`.

Out of scope:
- Product code changes.
- Sprint 2.
- Agent APIs.
- Scanner Runtime.
- Bootstrap.
- Baseline.
- Celery/Redis.
- Removing PostgreSQL requirement.
- Commit.

Immediate next steps:
- Revise local development docs.
- Confirm Docker is documented as optional only.
- Confirm manual PostgreSQL setup is documented clearly.

Progress:
- Updated `docs/operations/LOCAL-DEVELOPMENT.md` so primary setup is local Windows PostgreSQL.
- Kept `docker-compose.dev.yml` as an optional PostgreSQL helper only.
- Updated `README.md` to state PostgreSQL is required and Docker is not mandatory.
- Left product code unchanged.

Verification:
- Confirmed docs include `Primary PostgreSQL Setup on Windows`.
- Confirmed docs include `Optional PostgreSQL via Docker Desktop`.
- Confirmed README says PostgreSQL can be local Windows PostgreSQL or optional Docker Compose.
- `git diff --check` passed.

Completion:
- Documentation adjustment complete.
- No commit was made, per instruction.

## Archived Task - Fix Sprint 1 Staff User Test Fixture

Task:
- Fix only the failing Sprint 1 test `test_staff_user_without_account_has_no_customer_role`.

Scope:
- Update the test fixture to set a valid or unusable password before calling `full_clean()`.
- Run `python manage.py check`.
- Run `python manage.py makemigrations --check --dry-run`.
- Run `python manage.py test --noinput`.

Out of scope:
- Product behavior changes unless strictly necessary.
- Sprint 2.
- Agent APIs.
- Scanner Runtime.
- Bootstrap.
- Baseline.
- Tools/Policy.
- Telegram.

Immediate next steps:
- Update the test fixture only.
- Run the requested verification commands.

Progress:
- Updated only `tests/unit/test_sprint1_models.py`.
- Added `set_unusable_password()` to the staff/superuser fixture before `full_clean()`.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes detected.
- `python manage.py test --noinput` passed: 4 tests ran successfully.

Completion:
- Sprint 1 test fixture fix complete.

## Archived Task - Sprint 2 Agent Registration and Job Foundation

Task:
- Implement Sprint 2 only: server agent registration, heartbeat, job polling/result endpoints, `system_identity` allowlist, `BaselineScan` skeleton, and a minimal scanner runtime prototype.

Scope:
- `ScannerAgent` as `OneToOne(Server)`.
- `AgentRegistrationToken`.
- `AgentJob` with direct `account`, `server`, and `agent`.
- `BaselineScan` model skeleton only.
- Bearer token agent authentication.
- One-time registration token with hashed storage.
- Hashed agent token storage, raw returned once.
- Atomic single-job claiming with `claimed_at` and `claim_expires_at`.
- 5 minute default claim expiry.
- Reject result submissions after terminal status.
- Temporary hardcoded allowlist containing only `system_identity`.
- 64KB structured output cap.
- Minimal runtime prototype only for register, heartbeat, poll one job, execute `system_identity`, submit result.

Out of scope:
- Systemd service.
- Install flow.
- Remote Bootstrap.
- Full Baseline Scan.
- Finding.
- Full Tool Registry.
- Full Policy Engine.
- Telegram.
- Diagnostic Agent.
- Celery.
- Remediation/actions.

Immediate next steps:
- Add Sprint 2 models and migrations.
- Add agent auth/services/views/URLs.
- Add minimal `system_identity` handler and scanner runtime prototype.
- Add focused tests for token, auth, job claiming/result behavior, allowlist, and endpoint basics.

Progress:
- Added Sprint 2 models: `ScannerAgent`, `AgentRegistrationToken`, `AgentJob`, and `BaselineScan`.
- Added hashed token helpers for registration and agent bearer tokens.
- Added agent registration, heartbeat, single-job polling, and job result endpoints under `/api/agent/`.
- Added temporary Sprint 2 allowlist containing only `system_identity`.
- Added minimal scanner runtime prototype for register, heartbeat, poll one job, execute `system_identity`, and submit result.
- Added Django Admin coverage for Sprint 2 server/agent/job/baseline models.
- Added Sprint 2 focused tests for registration tokens, bearer auth, one-job claiming, allowlist rejection, result submission, claim requirement/expiry, output size limits, cross-agent ownership, `system_identity` output, and audit token safety.

Verification:
- `python manage.py makemigrations servers` created the Sprint 2 migration.
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes detected.
- `python manage.py test --noinput` passed: 16 tests ran successfully.
- `python manage.py migrate` applied `servers.0002_agentregistrationtoken_baselinescan_scanneragent_and_more` successfully.

Completion:
- Sprint 2 implementation is complete within the locked scope.
- No Remote Bootstrap, full Baseline Scan, Finding, full Tool Registry, full Policy Engine, Telegram, Diagnostic Agent, Celery, systemd/install flow, or remediation/actions were added.

## Archived Task - Sprint 3 Remote Bootstrap MVP

Task:
- Implement Sprint 3 only: Admin-only Remote Bootstrap MVP to install/start Scanner Runtime and verify heartbeat.

Scope:
- Create/use `apps/bootstrap`.
- Add `BootstrapSession`, `BootstrapStep`, `BootstrapCredential`, and `AgentInstallation`.
- Add Django Admin registrations.
- Add Admin-only synchronous bootstrap workflow with strict timeouts.
- Use Paramiko for SSH.
- Use fixed command templates, typed parameters, package allowlists, and no raw shell input.
- Encrypt temporary credentials with `BOOTSTRAP_CREDENTIAL_ENCRYPTION_KEY`.
- Use 30 minute credential TTL and cleanup on success, failure, cancellation, or expiry.
- Deploy runtime files via SFTP/tarball-style generated upload, not git clone.
- Install path `/opt/matrix_scanner`.
- Runtime config format JSON.
- systemd service `matrix-scanner-agent.service`.
- Verify agent heartbeat within 60 seconds using the Sprint 2 agent foundation.

Out of scope:
- Full Baseline Scan.
- Security Preflight.
- Diagnostic tools.
- Full Tool Registry.
- Full Policy Engine.
- Telegram.
- Diagnostic Agent.
- Celery.
- Remediation/actions.
- Customer Portal bootstrap.
- Self-install flow or install script.
- Free shell execution.

Immediate next steps:
- Add Bootstrap app models/admin/services/policy and migrations.
- Add Admin workflow hooks.
- Add focused mocked SSH/bootstrap tests.
- Run Django checks, migrations dry-run, tests, and diff check.

Progress:
- Added `apps/bootstrap`.
- Added Sprint 3 models: `BootstrapSession`, `BootstrapStep`, `BootstrapCredential`, and `AgentInstallation`.
- Added Matrix Admin-only Django Admin registrations, non-stored credential entry on session creation, and an Admin action to run selected bootstrap sessions.
- Added encrypted temporary bootstrap credential storage using `BOOTSTRAP_CREDENTIAL_ENCRYPTION_KEY`.
- Added credential TTL/cleanup helpers.
- Added fixed command template policy and package-manager allowlist handling.
- Added Paramiko SSH adapter.
- Added synchronous bootstrap workflow for SSH probe, privilege/systemd/package-manager checks, confirmed package install, runtime upload, JSON config install, systemd service install/start, and heartbeat verification.
- Added generated runtime service payload and systemd unit for `matrix-scanner-agent.service`.
- Added secret redaction helper for stored stdout/stderr/error text.
- Added Sprint 3 tests with mocked SSH paths and security regression checks.

Verification:
- Installed new local dependencies from `requirements.txt`: `paramiko` and `cryptography`.
- `python manage.py makemigrations bootstrap` created `apps/bootstrap/migrations/0001_initial.py`.
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes detected.
- `python manage.py test --noinput` passed: 27 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 3 implementation is complete within the locked scope.
- No full Baseline Scan, Security Preflight, diagnostic tools, full Tool Registry, full Policy Engine, Telegram, Diagnostic Agent, Celery, remediation/actions, customer Portal bootstrap, self-install flow, install script, or free shell execution were added.
- Changes are not committed, per instruction.

## Archived Task - Sprint 4 Tool Registry and Policy Engine MVP

Task:
- Implement Sprint 4 only: Tool Registry and Policy Engine MVP.

Scope:
- Create/use `apps/tools`.
- Add `ToolTemplate`, `ToolDefinition`, `ToolPolicy`, `PlanTool`, and `ToolRun`.
- Register Sprint 4 models in Django Admin.
- Convert `system_identity` into the first registry-backed tool.
- Enforce PlanTool and deny-by-default policy checks.
- Create `ToolRun` after policy approval and before `AgentJob`.
- Update Agent result ingestion to update linked `ToolRun`.
- Keep Sprint 2 agent job flow working and keep Sprint 3 BootstrapPolicy separate/unaffected.

Out of scope:
- Full Baseline Scan.
- Baseline orchestration.
- Security Preflight.
- Diagnostic Agent.
- Telegram.
- Celery.
- Remediation/actions.
- Customer-created tools.
- Admin Tool Builder Agent.
- New diagnostic tools beyond `system_identity`.
- External JSON Schema dependency.

Immediate next steps:
- Inspect existing Plan/Subscription/AgentJob code paths.
- Add tools app models, admin, setup helper, policy service, and migrations.
- Add focused Sprint 4 tests.
- Run Django checks, migration dry-run, tests, and diff check.

Progress:
- Added `apps/tools`.
- Added Sprint 4 models: `ToolTemplate`, `ToolDefinition`, `ToolPolicy`, `PlanTool`, and `ToolRun`.
- Added Django Admin registrations for all Sprint 4 models.
- Added idempotent `system_identity` setup helper and safe data migration.
- Added PlanTool enforcement and deny-by-default policy service.
- Added internal params validator for required fields, allowed fields, primitive types, unknown param rejection, and path canonicalization.
- Added blocked-path-before-allowed-path policy checks.
- Added ToolRun creation after policy approval and before AgentJob creation.
- Added AgentJob result ingestion update for linked ToolRun with redacted results.
- Kept Sprint 2 hardcoded allowlist as temporary fallback while registry-backed tools are available.
- Kept Sprint 3 BootstrapPolicy separate and unaffected.
- Added structured JSON redaction helper.
- Added focused Sprint 4 tests.

Verification:
- `python manage.py makemigrations tools` created `apps/tools/migrations/0001_initial.py`.
- Added `apps/tools/migrations/0002_seed_system_identity.py` to seed `system_identity` idempotently.
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes detected.
- `python manage.py test --noinput` passed: 42 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 4 implementation is complete within the locked scope.
- No full Baseline Scan, Baseline orchestration, Security Preflight, Diagnostic Agent, Telegram, Celery, remediation/actions, customer-created tools, Admin Tool Builder Agent, new diagnostic tools beyond `system_identity`, or external JSON Schema dependency were added.
- Changes are not committed, per instruction.

## Archived Task - Sprint 5 Baseline Scan Implementation

Task:
- Implement Sprint 5 only: Baseline Scan Implementation using the Sprint 4 Tool Registry and Policy Engine.

Scope:
- Add baseline scan orchestration service functions.
- Add `BaselineScanStep`, discovery models, and simple MVP `Finding`.
- Seed required baseline tools as registry-backed read-only tools.
- Add required read-only scanner runtime handlers only.
- Add Admin-only baseline workflow/action.
- Keep orchestration step-based and resumable through service functions.

Out of scope:
- Diagnostic Agent.
- Telegram.
- Celery.
- Remediation/actions.
- Portal UI.
- Full Security Preflight.
- Raw log ingestion.
- Raw `.env` storage.
- Free shell commands.
- Customer-created tools.
- Admin Tool Builder Agent.

Immediate next steps:
- Inspect current Sprint 2-4 models, tool policy service, runtime prototype, and admin registrations.
- Implement Sprint 5 models, orchestration, tool seeding, runtime handlers, and focused tests.
- Run Django checks, migration dry-run, tests, and diff check.

Progress:
- Expanded `BaselineScan` and added `BaselineScanStep`.
- Added discovery models: `DiscoveredService`, `DiscoveredDomain`, `LogSource`.
- Added simple MVP `Finding`.
- Added Application metadata and a uniqueness constraint for discovered application locations.
- Added baseline orchestration service functions: `start_baseline_scan`, `enqueue_next_baseline_tools`, and `ingest_completed_tool_runs`.
- Seeded required baseline tools as registry-backed read-only tools.
- Added read-only runtime handlers for required baseline tools.
- Added Admin-only baseline actions from Server and BaselineScan admin.
- Updated agent job polling to return the ToolRun timeout when a job is tied to a ToolRun.
- Added focused Sprint 5 tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 56 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 5 implementation is complete within the locked scope.
- No Diagnostic Agent, Telegram, Celery, remediation/actions, Portal UI, full Security Preflight, raw log ingestion, raw `.env` storage, free shell commands, customer-created tools, or Admin Tool Builder Agent were added.
- Changes are not committed, per instruction.

## Archived Task - Sprint 6 Admin and Portal MVP Screens

Task:
- Implement Sprint 6 only: Admin and Portal MVP Screens.

Scope:
- Create/use `apps/portal`.
- Add a minimal customer Portal using Django templates.
- Keep Portal views/templates separate from Django Admin.
- Add Portal-safe permissions, tenant-scoped views, templates, actions, and tests.
- Improve Django Admin usability where needed.

Out of scope:
- Telegram integration.
- Diagnostic Agent.
- Celery.
- Payments gateway.
- Remediation/actions.
- Admin Tool Builder Agent.
- Advanced reporting, PDF export, or email alerts.
- Customer Remote Bootstrap.
- React/Vue.
- User invitation/role management.
- Customer baseline start.

Immediate next steps:
- Add `apps.portal` structure, URLs, permissions, forms, views, and templates.
- Wire Portal URLs into the project.
- Add focused tests for authentication, tenant isolation, role permissions, token generation, safe display, and out-of-scope route absence.
- Run Django checks, migration dry-run, tests, and diff check.

Progress:
- Added `apps.portal` with Portal app config, permissions, forms, services, URLs, and views.
- Wired `/portal/` into project URLs and added `apps.portal` to installed apps.
- Added Portal login/logout/access-denied pages separate from Django Admin UI.
- Added Portal pages for dashboard, servers, add server, server detail, registration token generation, applications, pending applications, application detail/actions, findings, finding detail/actions, baseline scans, subscription/usage, and placeholders.
- Implemented tenant-scoped Portal querysets and role checks for owner/operator/viewer.
- Implemented owner-only registration token generation with raw token shown once and AuditLog without raw token metadata.
- Added read-only baseline/subscription visibility and placeholder pages for Telegram, diagnostics, and reports.
- Added safe display for application metadata, findings, baseline summaries, and server details without raw AgentJob or ToolRun output.
- Added minimal Admin branding for Matrix Scanner Admin.
- Added focused Sprint 6 tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 72 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 6 implementation is complete within the locked scope.
- No Telegram integration, Diagnostic Agent, Celery, payments gateway, remediation/actions, Admin Tool Builder Agent, advanced reporting, PDF export, email alerts, customer Remote Bootstrap, React/Vue, user invitation/role management, or customer baseline start were added.
- Changes are not committed, per instruction.

## Archived Task - Sprint 7 Telegram Integration MVP

Task:
- Implement Sprint 7 only: Telegram Integration MVP.

Scope:
- Create/use `apps/telegram_integration`.
- Add Telegram chat linking with short-lived hashed link tokens.
- Add Telegram webhook foundation using secret validation.
- Add read-only Telegram commands and safe notification records.
- Add owner-only Portal surface for Telegram link token generation.
- Keep Telegram separate from Diagnostic Agent, ToolRun, AgentJob, and remediation/actions.

Out of scope:
- Diagnostic Agent.
- Telegram Guided Diagnostics.
- DiagnosticSession creation from Telegram.
- ToolRun or AgentJob creation from Telegram.
- Remediation/actions.
- Write tools.
- Payments.
- Celery.
- Polling infrastructure.
- Per-account bot tokens.
- Customer-created tools.
- Admin Tool Builder Agent.

Immediate next steps:
- Add Telegram models, services, webhook views, URLs, Admin registration, and migrations.
- Add Portal Telegram link-token page/action.
- Add safe command formatting and notification suppression.
- Add focused tests for token safety, linking, webhook security, command scoping, notification redaction/suppression, and out-of-scope side effects.
- Run Django checks, migration dry-run, tests, and diff check.

Progress:
- Added `apps.telegram_integration` with Telegram chat links, one-time link tokens, notification records, Admin registration, webhook URL/view, and migration.
- Added global Telegram environment settings for `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_SECRET`; bot token is not stored in the database.
- Added secret-validated webhook handling for allowlisted read-only commands.
- Added Telegram chat linking with hashed one-time codes, TTL/used/revoked enforcement, private/group scope checks, and account-scoped active links.
- Added safe read-only command summaries for servers, applications, findings, account status, and latest baseline.
- Added notification record creation with redacted payloads, dedupe suppression, and an explicit Bot API delivery helper.
- Added notification event hooks for baseline completion, high/critical findings, agent offline/recovered, and bootstrap completed/failed.
- Added Portal Telegram settings page with owner/operator private link-code generation and owner-only group link-code generation.
- Added AuditLog entries for link code generation and chat link/unlink events without raw codes or secrets.
- Added focused Sprint 7 tests for token safety, linking, command scoping, webhook secret validation, notification redaction/suppression, Portal permissions, and out-of-scope side effects.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint7_telegram --noinput` passed: 13 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 85 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 7 implementation is complete within the locked scope.
- No Diagnostic Agent, Telegram Guided Diagnostics, DiagnosticSession creation, ToolRun creation, AgentJob creation, remediation/actions, write tools, payments, Celery, polling infrastructure, per-account bot tokens, customer-created tools, or Admin Tool Builder Agent were added.
- Changes are not committed, per instruction.

## Archived Task - Sprint 8 Diagnostic Agent MVP

Task:
- Implement Sprint 8 only: Diagnostic Agent MVP from Portal.

Scope:
- Create/use `apps/diagnostics`.
- Add DiagnosticSession, DiagnosticStep, and DiagnosticDecision models.
- Add deterministic diagnostic planning only, with no live LLM calls.
- Add Portal-only diagnostic session list/start/detail/approval flow.
- Require approval before each tool step creates a ToolRun.
- Execute diagnostic tools only through Tool Registry and ToolPolicy.
- Produce concise redacted diagnostic reports.

Out of scope:
- Telegram Guided Diagnostics.
- Telegram diagnostic commands, messages, or approvals.
- Live LLM execution.
- Remediation/actions.
- Write tools.
- Shell/free commands.
- Celery.
- Email alerts.
- PDF export.
- Advanced reporting.
- IncidentReport.
- Customer-created tools.
- Admin Tool Builder Agent.

Immediate next steps:
- Inspect existing Portal, ToolPolicy/ToolRun, baseline, and agent job flow.
- Add diagnostics app models, services, Admin registration, Portal URLs/views/templates, and migrations.
- Add focused tests for Portal permissions, tenant scoping, deterministic planning, approval gating, policy integration, redaction, and out-of-scope side effects.
- Run Django checks, migration dry-run, full test suite, and diff check.

Progress:
- Added `apps.diagnostics` with DiagnosticSession, DiagnosticStep, and DiagnosticDecision models, Admin registrations, services, Portal views, and initial migration.
- Wired diagnostics into the Portal under `/portal/diagnostics/`, including list, start, detail, and step approval routes.
- Added Portal templates for diagnostics list, start, and detail pages.
- Implemented deterministic planning over existing baseline tool keys only.
- Enforced approval before a diagnostic tool step creates a ToolRun.
- Integrated approved steps through the existing ToolPolicy path using `create_tool_run_job`; diagnostics do not create AgentJob directly.
- Added ToolRun result synchronization into DiagnosticStep summaries and concise final reports.
- Strengthened redaction for `APP_KEY` and API key style strings before diagnostic context/report display.
- Added focused Sprint 8 tests for login, staff blocking, role permissions, tenant scoping, application ownership, approval gating, ToolPolicy denial, max tool-run limits, ToolRun/AgentJob linking, result ingestion, redaction, no Telegram side effects, and safe Portal display.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint8_diagnostics --noinput` passed: 17 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 102 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 8 implementation is complete within the locked scope.
- No Telegram Guided Diagnostics, Telegram diagnostic commands/messages/approvals, live LLM execution, remediation/actions, write tools, shell/free commands, Celery, email alerts, PDF export, advanced reporting, IncidentReport, customer-created tools, or Admin Tool Builder Agent were added.
- Changes are not committed, per instruction.

## Archived Task - Sprint 9 Telegram Guided Diagnostics

Task:
- Implement Sprint 9 only: Telegram Guided Diagnostics.

Scope:
- Add private-chat-only Telegram diagnostic flow.
- Add `TelegramDiagnosticState`.
- Add Telegram diagnostic commands: `/diagnose`, `/cancel`, `/approve`, `/session`, `/report`.
- Add `callback_query` handling and inline keyboard responses with text fallback.
- Connect Telegram flow to existing diagnostics services.
- Keep ToolPolicy / ToolRun / AgentJob flow unchanged and only reached through diagnostics services.
- Keep all Telegram diagnostic output concise and redacted.

Out of scope:
- Group diagnostics.
- Remediation/actions.
- Write tools.
- Free shell commands.
- Direct AgentJob creation from Telegram.
- ToolPolicy bypass.
- Live LLM execution.
- Raw outputs or secrets in Telegram.

Immediate next steps:
- Inspect current Telegram and diagnostics services/models/webhook handling.
- Add diagnostic source fields, Telegram diagnostic state model, services, callback support, and admin registration.
- Add focused tests for private chat flow, role checks, tenant scoping, callbacks, approval replay protection, cancellation, redaction, and out-of-scope side effects.
- Run Django checks, migration dry-run, full test suite, and diff check.

Progress:
- Added `TelegramDiagnosticState` for private-chat diagnostic flow state without storing active state on `TelegramChatLink`.
- Added `DiagnosticSession.source` and nullable `source_chat_link` to distinguish Portal and Telegram sessions.
- Added Telegram diagnostic commands: `/diagnose`, `/cancel`, `/approve`, `/session`, and `/report`.
- Kept Sprint 7 read-only commands unchanged.
- Added `callback_query` handling and inline keyboard response payloads with constrained callback keys.
- Implemented private-chat-only diagnostic server, application, problem type, description, confirmation, approval, status, report, and cancellation flow.
- Enforced owner/operator-only Telegram diagnostics and blocked viewer/group diagnostics.
- Enforced one active Telegram diagnostic state per private chat with 30-minute expiry.
- Routed session creation and approval through existing diagnostics services; Telegram never creates AgentJob directly and never bypasses ToolPolicy.
- Added concise redacted Telegram diagnostic report formatting.
- Added AuditLog events for important Telegram diagnostic interactions without raw prompts, raw callbacks, raw updates, or secrets.
- Added focused Sprint 9 tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint9_telegram_diagnostics --noinput` passed: 16 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 118 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 9 implementation is complete within the locked scope.
- No group diagnostics, remediation/actions, write tools, free shell commands, direct AgentJob creation from Telegram, ToolPolicy bypass, live LLM execution, or raw outputs/secrets in Telegram were added.
- Changes are not committed, per instruction.

## Archived Task - Sprint 10 Tool Definition Proposal Builder

Task:
- Implement Sprint 10 only: Matrix Admin Tool Definition Proposal Builder MVP inside `apps/tools`.

Scope:
- Add ToolBuildRequest, ToolBuildProposal, ToolBuildReview, and ToolTestResult.
- Add deterministic proposal generation and validation only.
- Add Django Admin-only review actions.
- Allow conversion of approved proposals to draft/pending_review ToolDefinition records only.
- Keep Tool Registry and ToolPolicy as the source of truth.

Out of scope:
- New Django app.
- Live LLM/provider calls.
- Runtime handler/code generation.
- Shell/free-command generation.
- Remediation/actions, write tools, destructive tools, package installs, service restarts, or file edits.
- Customer Portal tool builder.
- Automatic enablement.
- Automatic PlanTool attachment.
- ToolRun or AgentJob creation.
- Execution on customer servers.

Immediate next steps:
- Inspect current tools models, services, admin, migrations, and tests.
- Add Sprint 10 models/services/Admin actions.
- Add focused safety and Admin access tests.
- Run Django checks, migration dry-run, full test suite, and diff check.

Progress:
- Added Sprint 10 Tool Definition Proposal Builder models inside `apps/tools`.
- Added deterministic proposal generation and validation services.
- Added Admin-only proposal generation, validation, approval, rejection, and conversion actions.
- Added conversion from approved proposal to draft ToolDefinition with inactive conservative ToolPolicy.
- Added mock validation ToolTestResult records only.
- Added Sprint 10 safety and Admin access tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint10_tool_builder --noinput` passed: 14 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 132 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 10 implementation is complete within the locked scope.
- No new app, live LLM, provider calls, runtime handler/code generation, shell/free commands, remediation/actions, write/destructive tools, automatic enablement, automatic PlanTool attachment, ToolRun creation, AgentJob creation, or customer server execution were added.
- Changes are not committed, per instruction.

## Archived Task - Sprint 11 Reports, Findings, and Knowledge Base Enhancement

Task:
- Implement Sprint 11 only: reports, finding groups, advisory recommendations, and safe knowledge/context storage.

Scope:
- Add Report, ReportSection, FindingGroup, KnowledgeEntry, KnowledgeSource, and Recommendation.
- Add synchronous explicit report generation from safe/redacted sources only.
- Add Admin registrations/actions for reports, report sections, finding groups, knowledge, recommendations, baseline report generation, diagnostic report generation, and finding group rebuild.
- Add Portal reports/finding group visibility and owner/operator report refresh actions with viewer read-only.
- Add small safe Telegram report summary support.

Out of scope:
- PDF export, email reports, scheduled reports, Celery/report worker, live LLM report generation, public API endpoints, remediation/actions, write tools, service restarts, package installs, file edits, ToolPolicy bypass, direct AgentJob creation, raw logs, raw `.env`, raw ToolRun output, raw AgentJob output, credentials, tokens, passwords, or private keys.

Immediate next steps:
- Inspect current Portal/Admin/report-adjacent models and routes.
- Add Sprint 11 models, services, admin actions, Portal views/templates, Telegram summary update, and tests.
- Run Django checks, migration dry-run, full test suite, and diff check.

Progress:
- Added `apps.reports` with Report, ReportSection, FindingGroup, KnowledgeEntry, KnowledgeSource, and Recommendation.
- Added synchronous redacted report generation services for baseline, diagnostic, server health, and findings summaries.
- Added finding group rebuild/deduplication and advisory-only recommendation creation.
- Added Django Admin registrations and actions for reports, report generation, and finding group rebuilds.
- Added Portal report list/detail/generation views, finding group list/detail views, findings filters, server report/group summaries, and diagnostic report links.
- Added safe Telegram `/report` fallback to the latest stored redacted report summary.
- Added Sprint 11 tests for report safety, grouping, portal tenant isolation, Admin visibility, recommendations, knowledge redaction, Telegram summaries, and out-of-scope exclusions.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 142 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 11 implementation is complete within the locked scope.
- No PDF export, email reports, scheduled reports/Celery, live LLM report generation, public API endpoints, remediation/actions, write tools, ToolPolicy bypass, direct AgentJob creation, or raw sensitive output display/storage were added.
- Changes are not committed, per instruction.

## Archived Task - Sprint 12 Stabilization, Security Hardening, and Release Preparation

Task:
- Implement Sprint 12 only: final MVP stabilization, security hardening, documentation cleanup, release readiness, and regression coverage.

Scope:
- Review and harden tenant isolation, permissions, secret handling, redaction, ToolPolicy enforcement, Admin/Portal/Telegram access, settings/env coverage, migrations, and operational documentation.
- Update README, local development, deployment notes, runbook, plans, execution plan, implementation checklist, and test plan.
- Add a release checklist document.
- Add or strengthen practical security/regression tests.

Out of scope:
- New product workflows, remediation/actions, write tools, live LLM execution, Celery/Redis implementation, payment gateway, PDF export, email reports, scheduled reports, customer Remote Bootstrap, ToolPolicy bypass, and direct AgentJob creation outside existing approved flows.

Immediate next steps:
- Inspect settings, environment variables, routes, services, and existing tests for Sprint 12 hardening gaps.
- Apply narrow documentation and test/security fixes only.
- Run Django checks, migration dry-run, migrate, full test suite, and diff check.

Progress:
- Updated MVP documentation to reflect the actual implemented sprint order, Sprint 4/5 ordering, Sprint 11 actual scope, and deferred features.
- Added `docs/operations/RELEASE-CHECKLIST.md` with local verification, environment, migration, Admin, Portal, Telegram, security, tenant isolation, deployment, and deferred-feature checks.
- Updated `.env.example` with CSRF and proxy/secure cookie settings needed for production readiness review.
- Added production-aware settings for `CSRF_TRUSTED_ORIGINS`, optional proxy SSL header, and secure session/CSRF cookies.
- Hardened AuditLog metadata by redacting secret-like values before validation/storage while still rejecting secret-like metadata keys.
- Hid raw `AgentJob.result` from Django Admin detail display.
- Added Sprint 12 regression tests for env coverage, AuditLog redaction, Portal staff/viewer denial, Telegram token/callback denial, bootstrap credential cleanup, revoked agent token denial, AgentJob double-submit rejection, ToolPolicy denial before ToolRun/AgentJob, and raw AgentJob result display prevention.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint12_stabilization --noinput` passed: 11 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py migrate` passed.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 153 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 12 implementation is complete within the locked stabilization scope.
- No new product workflows, remediation/actions, write tools, live LLM execution, Celery/Redis, payment gateway, PDF/email/scheduled reporting, customer Remote Bootstrap, ToolPolicy bypass, or direct AgentJob creation outside existing approved flows were added.
- Changes are not committed, per instruction.

## Archived Task - Phase 2 Sprint 2.1 Runtime Discovery Tool Contracts

Task:
- Prepare only the first Phase 2 implementation step: Runtime Discovery Tool Contracts and seeding structure for Debian/Nginx `/opt` discovery tools.

Scope:
- Pull local `main` to the deployed source-of-truth commit `762abd4`.
- Re-inspect current baseline, tools, diagnostics, and runtime code after the deployment fix.
- Add safe Tool Registry contract/seeding structure for planned Phase 2 runtime discovery tools.
- Keep the contracts non-executing until runtime handlers and baseline integration are implemented in later steps.

Out of scope:
- Runtime handler implementation.
- Baseline orchestration changes.
- UI redesign.
- External bot work.
- Live LLM work.
- Remediation/actions, write tools, free shell commands, or unsafe execution paths.

Immediate next steps:
- Add Phase 2 discovery tool specs and idempotent seeding helper.
- Add focused tests for contract safety, disabled-by-default behavior, and no ToolRun/AgentJob side effects.
- Run Django checks, migration dry-run, tests, and diff check.

Progress:
- Added Phase 2 discovery tool contract specs for Debian/Nginx `/opt` discovery tools.
- Added idempotent seeding helper that creates ToolTemplate, ToolDefinition, and inactive ToolPolicy records.
- Kept Phase 2 tools out of the current baseline and diagnostic tool sets until handlers and orchestration are implemented later.
- Added a data migration that seeds the contracts as approved/read-only but non-executable by default.
- Added focused tests for safe seeding, idempotency, baseline/diagnostic separation, and no ToolRun/AgentJob side effects.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_tool_contracts --noinput` passed: 4 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 157 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Phase 2 Sprint 2.1 contract/seeding preparation is complete.
- Runtime handlers, baseline integration, UI changes, external bot work, live LLM work, and remediation/write behavior remain out of scope and were not implemented.
- No commit or push was made.

## Archived Task - Phase 2 Sprint 2.2 systemd Services Discovery

Task:
- Implement only the Sprint 2.2 runtime safe execution helper and `systemd_services_discovery` runtime handler.

Scope:
- Add `scanner_runtime/safe_exec.py`.
- Use fixed code-defined argv lists with `subprocess.run(..., shell=False)`.
- Enforce runtime command timeout and output caps.
- Capture and redact stderr safely.
- Add `systemd_services_discovery` runtime collector using fixed read-only `systemctl` commands.
- Register only this handler in the runtime executor.
- Add focused unit tests for safe execution, parsing, handler routing, param rejection, and unsupported tools.

Out of scope:
- Baseline orchestration changes.
- Baseline profiles.
- `ingest_tool_result()` changes.
- `DiscoveredService` ingestion.
- ToolPolicy or PlanTool activation.
- Migrations to enable tools.
- Other Phase 2 runtime handlers.
- AI planner, external bot, remediation/actions, shell commands, raw unit files, raw `ExecStart`, or raw `Environment=...`.

Immediate next steps:
- Add safe execution helper.
- Add systemd collector/parser.
- Register the runtime handler in `scanner_runtime/prototype.py`.
- Add tests and run requested checks.

Progress:
- Added `scanner_runtime/safe_exec.py` with fixed argv-only command execution, `shell=False`, timeout handling, output cap enforcement, and redacted stderr.
- Added `systemd_services_discovery` parser and collector using fixed read-only `systemctl` commands.
- Registered only `systemd_services_discovery` in the runtime executor path.
- Added focused tests for safe execution, timeout/output caps, parser behavior, enabled-state merge, runtime execution routing, param rejection, and unsupported tool rejection.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_systemd_discovery --noinput` passed: 12 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 171 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 2.2 implementation is complete within the approved runtime-only scope.
- No baseline orchestration, baseline profile, ingestion, ToolPolicy/PlanTool activation, enabling migration, AI planner, external bot, or remediation/write behavior was added.
- No commit or push was made.

## Archived Task - Phase 2 Sprint 2.3 Nginx Sites Discovery

Task:
- Implement only the Sprint 2.3 runtime `nginx_sites_discovery` collector.

Scope:
- Add `scanner_runtime/nginx_discovery.py`.
- Read only allowlisted Nginx config sources.
- Parse Nginx `server` blocks with safe brace counting.
- Extract safe `server_name`, `listen`, `root`, `access_log`, `error_log`, and `proxy_pass` metadata.
- Reject non-empty params.
- Register only `nginx_sites_discovery` in the runtime executor.
- Add focused tests for parser behavior, path safety, symlink safety, include flagging, param rejection, and output safety.

Out of scope:
- Baseline orchestration changes.
- Baseline profile changes.
- `ingest_tool_result()` changes.
- `DiscoveredDomain`, `Application`, or `LogSource` writes.
- ToolPolicy or PlanTool activation.
- Migrations.
- Other Phase 2 runtime handlers.
- AI planner, external bot, remediation/actions, or shell command execution.

Immediate next steps:
- Add the Nginx discovery runtime module.
- Wire the handler into `scanner_runtime/prototype.py`.
- Add focused Sprint 2.3 tests.
- Run requested checks.

Progress:
- Added `scanner_runtime/nginx_discovery.py` as a pure file-reading runtime collector.
- Added allowlisted Nginx config candidate handling, safe symlink resolution checks, file size caps, and total scan cap.
- Added parser support for `server` blocks, `server_name`, `listen`, `root`, `access_log`, `error_log`, `proxy_pass`, comments, multiple domains, default servers, wildcard names, and include flagging without following includes.
- Added output safety rules for blocked paths, variable paths, credentialed/variable proxy targets, cert/key/auth directives, and raw config exclusion.
- Registered only `nginx_sites_discovery` in `scanner_runtime/prototype.py`.
- Added focused Sprint 2.3 tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_nginx_sites_discovery --noinput` passed: 12 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 185 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Completion:
- Sprint 2.3 implementation is complete within the approved runtime-only scope.
- No baseline orchestration, baseline profile, ingestion, ToolPolicy/PlanTool activation, migrations, AI planner, external bot, or remediation/write behavior was added.
- No commit or push was made.

## Archived Task - Phase 2 Sprint 2.4 /opt Applications Discovery

Task:
- Implement only the Sprint 2.4 runtime `opt_apps_discovery` collector.

Scope:
- Add `scanner_runtime/opt_discovery.py` as a pure file-reading runtime collector for `/opt`.
- Candidate directories: `/opt/*` and `/opt/*/*` only (max depth 2), with strict caps.
- Presence-based framework detection (Django/Python, Node, Laravel/PHP) using marker files only.
- Optional safe project name extraction from size-capped:
  - `pyproject.toml`
  - `package.json`
  - `composer.json`
  Extract only project `name`; ignore all other fields.
- Reject non-empty params.
- Register only `opt_apps_discovery` in `scanner_runtime/prototype.py`.
- Add focused tests for traversal caps, symlink safety, framework detection, safe name extraction, and output safety.

Out of scope:
- Baseline orchestration changes.
- Baseline profile changes.
- `ingest_tool_result()` changes.
- Any DB writes from runtime (no `Application`, `LogSource`, or `DiscoveredDomain` writes).
- ToolPolicy or PlanTool activation.
- Migrations.
- Other Phase 2 runtime handlers.
- AI planner, external bot, remediation/actions, or shell execution.

Progress:
- Added `scanner_runtime/opt_discovery.py` with `/opt`-rooted discovery, max-depth-2 candidate scanning, strict caps, symlink validation under `/opt`, and heavy/hidden directory skipping.
- Added marker-based framework detection for Django/Python, Node, and Laravel/PHP.
- Added safe project-name extraction from size-capped `pyproject.toml`, `package.json`, and `composer.json`.
- Returned `applications` and `summary` only, with redacted strings and no raw file contents.
- Registered only `opt_apps_discovery` in `scanner_runtime/prototype.py`.
- Added focused Sprint 2.4 tests.
- Fixed empty-marker parent directories being counted as applications and deduped applications by resolved realpath.
- Corrected the `pyproject.toml` name regex to use proper whitespace matching.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected; database connection timeout warning only.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_opt_apps_discovery --noinput` passed: 13 tests ran successfully with 2 symlink tests skipped in this Windows environment.
- `.\.venv\Scripts\python.exe manage.py test --noinput` was blocked by PostgreSQL connection timeout while creating the test database.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.4 implementation is complete except for a full-suite re-run after local PostgreSQL test database connectivity is restored.
- No baseline orchestration, baseline profile, ingestion, ToolPolicy/PlanTool activation, migrations, other Phase 2 handlers, AI planner, external bot, or remediation/write behavior was added.
- No commit or push was made.

## Archived Task - Phase 2 Sprint 2.5 Django Apps Discovery

Task:
- Implement only the Sprint 2.5 runtime `django_apps_discovery` collector.

Scope:
- Add `scanner_runtime/django_discovery.py` as a pure filesystem runtime collector for `/opt`.
- Candidate directories: `/opt/*` and `/opt/*/*` only (max depth 2), with strict caps.
- Detect Django roots using:
  - `manage.py`; or
  - strong project-root markers (`pyproject.toml`, `requirements.txt`, `Pipfile`, `poetry.lock`, `uv.lock`) plus Django indicators.
- Treat `wsgi.py`, `asgi.py`, `urls.py`, and `apps.py` as supporting markers only.
- Avoid nested false positives when a child package sits under an already selected Django root.
- Return only `applications` and `summary` with safe redacted metadata.
- Reject non-empty params.
- Register only `django_apps_discovery` in `scanner_runtime/prototype.py`.
- Add focused tests.

Out of scope:
- Baseline orchestration changes.
- Baseline profile changes.
- `ingest_tool_result()` changes.
- `Application` database writes.
- ToolPolicy or PlanTool activation.
- Migrations.
- Other Phase 2 runtime handlers.
- AI planner, external bot, remediation/actions, or shell execution.

Progress:
- Added `scanner_runtime/django_discovery.py` with `/opt`-rooted discovery, max-depth-2 candidate scanning, strict caps, symlink validation under `/opt`, and heavy/hidden directory skipping.
- Added Django root detection using `manage.py` or strong project-root markers plus Django indicators.
- Treated `wsgi.py`, `asgi.py`, `urls.py`, and `apps.py` as supporting markers only.
- Added nested candidate suppression so child Django packages are not emitted as standalone apps when an ancestor is already selected as a Django root.
- Returned `applications` and `summary` only, with redacted safe fields.
- Registered only `django_apps_discovery` in `scanner_runtime/prototype.py`.
- Added focused Sprint 2.5 tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_django_apps_discovery --noinput` passed: 15 tests ran successfully with 2 symlink tests skipped in this Windows environment.
- `.\.venv\Scripts\python.exe manage.py test --noinput` ran 200 tests before failing in `tests.unit.test_sprint8_diagnostics.Sprint8DiagnosticsTests.setUpClass` due to PostgreSQL connection timeout.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.5 implementation is complete except for a full-suite re-run after local PostgreSQL test database connectivity is stable.
- No baseline orchestration, baseline profile, ingestion, ToolPolicy/PlanTool activation, migrations, other Phase 2 handlers, AI planner, external bot, or remediation/write behavior was added.
- No commit or push was made.

## Archived Task - Phase 2 Sprint 2.6 Gunicorn/Uvicorn Services Discovery

Task:
- Implement only the Sprint 2.6 runtime `gunicorn_uvicorn_services_discovery` collector.

Scope:
- Add `scanner_runtime/gunicorn_uvicorn_discovery.py`.
- Discovery flow:
  - Run fixed `systemctl list-units --type=service --all --no-pager --plain --no-legend`.
  - Parse safe unit names.
  - Run fixed `systemctl show <capped units> --property=Id,Description,LoadState,ActiveState,SubState,UnitFileState,MainPID,FragmentPath,User,WorkingDirectory`.
- Use `safe_exec.py` only with fixed argv and `shell=False`.
- Reject non-empty params.
- Detect `gunicorn`, `uvicorn`, `daphne` from safe fields only (Id and redacted Description).
- Return only safe contract-compatible keys: `services`, `applications`, `summary`.
- Register only `gunicorn_uvicorn_services_discovery` in `scanner_runtime/prototype.py`.
- Add focused tests for parsing and safety constraints.

Out of scope:
- Baseline orchestration/profile/ingestion changes.
- ToolPolicy or PlanTool activation.
- Migrations.
- Other runtime handlers.
- Supervisor support.
- Port correlation.
- Unit file content reads.
- `/proc/<pid>/cmdline`.
- AI planner or external bot.

Progress:
- Added `scanner_runtime/gunicorn_uvicorn_discovery.py` with fixed two-step discovery:
  - `systemctl list-units --type=service --all --no-pager --plain --no-legend`
  - capped `systemctl show <unit names> --property=Id,Description,LoadState,ActiveState,SubState,UnitFileState,MainPID,FragmentPath,User,WorkingDirectory`
- Added safe unit-name extraction and show-unit cap enforcement.
- Added service typing (`gunicorn`, `uvicorn`, `daphne`, `unknown`) from safe fields only.
- Added safe metadata shaping with `/opt`-only working directory handling, safe fragment path allowlist, and related app path inference.
- Returned only top-level keys required by the seeded contract: `services`, `applications`, `summary`.
- Registered only `gunicorn_uvicorn_services_discovery` in `scanner_runtime/prototype.py`.
- Added focused Sprint 2.6 tests.

Verification:
- `python manage.py check` failed locally because shell `python` is not bound to the project venv.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` failed for the same shell `python` reason.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected and a database timeout warning.
- `python manage.py test tests.unit.test_phase2_gunicorn_uvicorn_services_discovery --noinput` failed for the same shell `python` reason.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_gunicorn_uvicorn_services_discovery --noinput` passed: 11 tests.
- `python manage.py test --noinput` failed for the same shell `python` reason.
- `.\.venv\Scripts\python.exe manage.py test --noinput` ran 216 tests before failing in `tests.unit.test_sprint2_agent_foundation.Sprint2AgentFoundationTests.setUpClass` due to PostgreSQL connection timeout.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.6 implementation is complete except for a clean full-suite run after PostgreSQL test connectivity is stable.
- No baseline/profile/ingestion changes, ToolPolicy/PlanTool activation, migrations, other handlers, AI planner, or external bot changes were added.
- No commit or push was made.

## Archived Task - Phase 2 Sprint 2.7 PostgreSQL Status Discovery

Task:
- Implement only the Sprint 2.7 runtime `postgres_status_discovery` collector.

Scope:
- Add `scanner_runtime/postgres_discovery.py`.
- Use fixed commands via `safe_exec.py`:
  - `systemctl list-units --type=service --all --no-pager --plain --no-legend`
  - capped `systemctl show <unit names> --property=Id,Description,LoadState,ActiveState,SubState,UnitFileState,MainPID,FragmentPath`
- Add optional fixed `pg_isready` probe without connection arguments.
- Normalize `pg_isready` health result to `ok|failed|not_available`.
- Reject non-empty params.
- Return contract-compatible top-level keys: `services`, `summary`.
- Register only `postgres_status_discovery` in `scanner_runtime/prototype.py`.
- Add focused Sprint 2.7 tests.

Out of scope:
- Baseline/profile/ingestion changes.
- ToolPolicy or PlanTool activation.
- Migrations.
- Other runtime handlers.
- `psql`, SQL queries, DB contents, `.pgpass`, credentials, connection strings.
- PostgreSQL config reads (`postgresql.conf`, `pg_hba.conf`).
- Port inspection.
- AI planner or external bot.

Progress:
- Added `scanner_runtime/postgres_discovery.py` with fixed-command safe collection flow.
- Added PostgreSQL unit discovery from:
  - `systemctl list-units --type=service --all --no-pager --plain --no-legend`
  - capped `systemctl show <unit names> --property=Id,Description,LoadState,ActiveState,SubState,UnitFileState,MainPID,FragmentPath`
- Added optional fixed `pg_isready` probe normalized to `ok|failed|not_available`.
- Enforced contract-compatible output keys: `services`, `summary`.
- Registered only `postgres_status_discovery` in `scanner_runtime/prototype.py`.
- Added focused Sprint 2.7 tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_postgres_status_discovery --noinput` passed: 9 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 239 tests (4 skipped).
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.7 implementation is complete within approved runtime-only scope.
- No baseline/profile/ingestion changes, ToolPolicy/PlanTool activation, migrations, other handlers, AI planner, or external bot changes were added.
- No commit or push was made.

## Archived Task - Phase 2 Sprint 2.8 Log Sources Discovery V2

Task:
- Implement only the Sprint 2.8 runtime `log_sources_discovery_v2` collector.

Scope:
- Add `scanner_runtime/log_sources_discovery_v2.py` using pure filesystem metadata only.
- Fixed allowlisted candidates only:
  - `/var/log/nginx`
  - `/var/log/postgresql`
  - `/var/log/syslog`
  - `/var/log/messages`
  - `/opt/*/logs`
  - `/opt/*/*/logs`
- Collect safe fields only: `path`, `type`, `exists`, `is_dir`, `size_bytes`, `modified_at`, `metadata.source`.
- Canonicalize paths and reject outside-allowlist paths.
- Reject non-empty params.
- Register only `log_sources_discovery_v2` in `scanner_runtime/prototype.py`.
- Add focused Sprint 2.8 tests.

Out of scope:
- Baseline/profile/ingestion changes.
- ToolPolicy or PlanTool activation.
- Migrations.
- Other runtime handlers.
- `journalctl`, `systemctl`, unit-file reads, service correlation.
- Any log content reads/parsing/tail/grep.
- Findings generation.
- AI planner or external bot.

Progress:
- Added `scanner_runtime/log_sources_discovery_v2.py` with metadata-only log source discovery.
- Added fixed allowlisted candidates for:
  - `/var/log/nginx`
  - `/var/log/postgresql`
  - `/var/log/syslog`
  - `/var/log/messages`
  - `/opt/*/logs`
  - `/opt/*/*/logs`
- Added safe metadata output fields only: `path`, `type`, `exists`, `is_dir`, `size_bytes`, `modified_at`, `metadata.source`.
- Added canonicalization and allowlist validation to reject unsafe/outside paths.
- Registered only `log_sources_discovery_v2` in `scanner_runtime/prototype.py`.
- Added focused Sprint 2.8 unit tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_log_sources_discovery_v2 --noinput` passed: 12 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 251 tests (4 skipped).
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.8 implementation is complete within approved runtime-only scope.
- No baseline/profile/ingestion changes, ToolPolicy/PlanTool activation, migrations, other handlers, AI planner, or external bot changes were added.
- No commit or push was made.

## Archived Task - Phase 2 Sprint 2.8 Log Sources Discovery V2 Hotfix

Task:
- Tighten `/opt` log source discovery after server smoke testing showed noisy internal/heavy directories and missing `/opt/.../logs` candidates.

Scope:
- Skip hidden/heavy/internal directories under `/opt`:
  `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `.cache`, `.config`, `.npm`, `.tox`, `tests`, `docs`, `static`, `staticfiles`, `templates`, `scripts`, `skills`, `dist`, `build`, `tmp`.
- Do not emit `/opt/*/logs` or `/opt/*/*/logs` if the logs path does not exist.
- Keep fixed system candidates even when missing.
- Preserve `/opt` realpath escape protection.
- Add regression tests for hidden/heavy/missing app log paths.

Out of scope:
- Baseline/profile/ingestion changes.
- ToolPolicy or PlanTool activation.
- Migrations.
- Other runtime handlers.
- AI planner or external bot.
- Log content reads/parsing or findings generation.

Progress:
- Updated `/opt` log source discovery to skip hidden/heavy/internal directories.
- Stopped emitting missing `/opt` app log candidates while preserving missing fixed system candidates.
- Preserved `/opt` realpath escape protection for app log paths.
- Added regression tests for `.git/logs`, `node_modules/logs`, missing `/opt/app/logs`, existing safe `/opt/app/logs`, and missing fixed system candidates.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_log_sources_discovery_v2 --noinput` passed: 18 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 257 tests (4 skipped).
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint 2.8 hotfix is complete within approved runtime-only scope.
- No baseline/profile/ingestion changes, ToolPolicy/PlanTool activation, migrations, other handlers, AI planner, external bot, log parsing, or findings generation were added.
- No commit or push was made.
## Archived Task - Corrected Execution Plan Remote Bootstrap Update

Task:
- Update `docs/planning/CORRECTED-EXECUTION-PLAN.md` only to include the accepted planning corrections.

Scope:
- Add a standalone Remote Bootstrap Runtime Completion sprint before relying on runtime-based tool execution.
- Document the current Remote Bootstrap foundation and the remaining gap in the installed bootstrap bundle.
- Adjust the first full tool cycle so the first preferred tool is less sensitive than `laravel_env_sanity`.
- Clarify that C5 can orchestrate existing safe tools, while command/script template execution depends on C6.

Out of scope:
- Code changes.
- Model/service/runtime changes.
- Migrations.
- Tests.
- Server execution.

Progress:
- Created `docs/planning/DECISION-REGISTER.md`.
- Recorded approved decisions for C1 through C12.
- Recorded deferred decisions separately.
- Recorded guardrails that require explicit approval to change.

Verification:
- `git diff --check` passed with line-ending warnings only.
- No code, migrations, tests, runtime/service/model changes, or server execution were performed.


Progress:
- Updated `docs/planning/CORRECTED-EXECUTION-PLAN.md` with Sprint C1.5 / Phase 0.5 for Remote Bootstrap Runtime Completion.
- Documented the existing Remote Bootstrap foundation and the remaining `sprint3-bootstrap-runtime` gap.
- Clarified that C5 can orchestrate existing safe tools only, while command/script template execution depends on C6.
- Updated C8 to prefer `laravel_log_health` or `apache_5xx_summary` first and defer `laravel_env_sanity`.
- Updated the recommended next sprint sequence and final roadmap chain.

Verification:
- `git diff --check` passed with line-ending warnings only.
- No code, migrations, runtime, model/service, test, or server execution changes were made.
## Archived Task - Decision Register Documentation

Task:
- Create `docs/planning/DECISION-REGISTER.md` as the official decision register for the corrected execution plan.

Scope:
- Record approved Sprint decisions from C1 through C12.
- Record deferred decisions separately.
- Record non-changeable guardrails that require explicit approval.
- Update documentation tracking only.

Out of scope:
- Code changes.
- Model/service/runtime changes.
- Migrations.
- Tests.
- Server execution.

## Archived Task - Sprint C2 Safe Context Builder MVP

Task:
- Implement the approved `Sprint C2 - Safe Context Builder MVP`.

Scope:
- Add a dedicated safe context builder app under `apps.ai_context`.
- Build deterministic, versioned, capped, redacted JSON context for later chat/planner use.
- Include safe summaries for account/server/baseline/applications/services/domains/logs/findings/reports/knowledge/recommendations.
- Include recent ToolRun metadata without raw output.
- Include available tool metadata based on enabled ToolDefinition, ToolPolicy, PlanTool, subscription, role, and server status.
- Enforce tenant scope and viewer read-only limitations.

Out of scope:
- Chat data model/UI.
- Live AI provider calls.
- Tool execution or direct AgentJob creation.
- Telegram changes.
- Remediation/actions.
- Report redesign.

Progress:
- Added `apps.ai_context` and registered it in settings.
- Added `build_safe_context()` service.
- Added focused tests for scoping, redaction, raw output exclusion, role-aware tools, caps, and safe summaries.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_safe_context_builder --noinput` passed: 6 tests.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 300 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint C2 implementation and verification are complete.
- Full suite was run because this sprint changes security-sensitive redaction/permissions/context behavior.

## Archived Task - Sprint C3 Admin Chat Data Model and Read-only UI

Task:
- Implement the approved `Sprint C3 - Admin Chat Data Model and Read-only UI`.

Scope:
- Add `apps.ai_chat`.
- Add `AdminChatSession`, `AdminChatMessage`, and `AdminChatDecision`.
- Add a minimal Portal chat list/detail/create/message path for owner/operator.
- Allow viewer read-only access where applicable but prevent active chat sends.
- Scope all chat data to the user's account.
- Store only redacted body/metadata/context snapshots.

Out of scope:
- Deterministic assistant responses.
- Live AI providers.
- Tool execution, ToolRun creation, or AgentJob creation.
- Telegram integration.
- Reports from chat.
- Remediation/actions.

Immediate next steps:
- Inspect Portal routing/view conventions.
- Add models and migration.
- Add focused tests for permissions, redaction, tenant isolation, and no execution side effects.

Progress:
- Added `apps.ai_chat` with chat session, message, and decision models.
- Added migration for the new chat models.
- Added redacted chat service helpers for session creation and user message storage.
- Added Portal chat list, start, detail, and message save routes.
- Added Portal templates and navigation entry for Chat.
- Added focused C3 tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_chat --noinput` passed: 7 tests.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected after the intended migration was created.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint6_portal --noinput` passed: 16 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 307 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint C3 implementation and verification are complete.
- Full suite was run because this sprint changes Portal permissions, redaction-sensitive chat storage, and tenant-scoped access behavior.

## Archived Task - Sprint C4 Deterministic Chat Responder

Task:
- Implement the approved `Sprint C4 - Deterministic Chat Responder`.

Scope:
- Add deterministic responder logic inside the chat service layer.
- Answer only from Safe Context.
- Store assistant replies redacted.
- Store response decision metadata in `AdminChatDecision`.
- Keep Portal chat flow read-only with no tool execution.

Out of scope:
- Live AI provider calls.
- Tool orchestration.
- ToolRun or AgentJob creation.
- Telegram.
- Reports from chat.
- Remediation/actions.

Immediate next steps:
- Add deterministic intent routing for status, findings, reports, tools, and general summary.
- Wire Portal message POST to create an assistant response.
- Add focused tests for deterministic replies, decision logging, redaction, and no execution side effects.

Progress:
- Added deterministic responder logic for status, findings, reports, available tools, and summary.
- Wired Portal chat message POST to generate an assistant response after saving the user message.
- Stored deterministic response decisions in `AdminChatDecision`.
- Added focused tests for responder output, decision logging, redaction, and no ToolRun/AgentJob side effects.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_chat --noinput` passed: 10 tests.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint6_portal --noinput` passed: 16 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 310 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint C4 implementation and verification are complete.
- Full suite was run because this sprint changes Portal chat behavior, decision logging, redaction-sensitive response storage, and permission-protected message flow.

## Archived Task - Sprint C5 Tool Orchestrator MVP

Task:
- Implement the approved `Sprint C5 - Tool Orchestrator MVP`.

Scope:
- Add `AdminChatToolRequest`.
- Allow chat to request existing available read-only tools only.
- Require owner/operator approval before execution.
- Execute only through existing `create_tool_run_job()`.
- Ensure ToolPolicy and PlanTool denial happen before ToolRun/AgentJob creation.
- Keep C5 params empty-only.

Out of scope:
- Command/script templates.
- Live AI.
- Arbitrary params.
- New tool creation.
- Report generation from chat.
- Telegram.
- Remediation/actions.

Immediate next steps:
- Add tool request model/migration.
- Add request/approve services.
- Add minimal Portal request/approve UI.
- Add focused tests for allowed and denied execution paths.

Progress:
- Added `AdminChatToolRequest` and migration.
- Added chat tool request and approval services.
- Added minimal Portal request/approve UI.
- Added focused tests for available tool execution, ToolPolicy denial, PlanTool denial, viewer denial, params rejection, and write-risk rejection.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_chat --noinput` passed: 16 tests.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected after the intended migration was created.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint6_portal tests.unit.test_sprint4_tools_policy --noinput` passed: 31 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 316 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint C5 implementation and verification are complete.
- Full suite was run because this sprint touches the ToolRun/AgentJob execution path and permission/policy enforcement.

## Archived Task - Sprint C6 Safe Command Execution Runtime

Task:
- Implement the approved `Sprint C6 - Safe Command Execution Runtime`.

Scope:
- Add `command_template` metadata support to ToolTemplate/ToolDefinition.
- Add a safe AgentJob execution payload for command-template jobs.
- Add runtime command-template executor using argv-only safe execution.
- Keep existing runtime handlers supported.
- Add focused tests for command-template security and runtime behavior.

Out of scope:
- `script_template`.
- Shell execution.
- Arbitrary commands.
- Tool Builder integration.
- New tool activation.
- Telegram.
- Live AI.
- Remediation/actions.

Immediate next steps:
- Add model fields and migration.
- Add command-template payload construction in `create_tool_run_job()`.
- Add runtime command-template executor.
- Add focused tests and run security regression checks.

Progress:
- Added command-template metadata fields to ToolTemplate and ToolDefinition.
- Added `AgentJob.execution_payload`.
- Added command-template payload building in `create_tool_run_job()`.
- Added runtime command-template execution with argv-only safe execution.
- Added focused C6 tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c6_command_templates --noinput` passed: 8 tests.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected after intended migrations.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint4_tools_policy tests.unit.test_sprint2_agent_foundation tests.unit.test_sprint3_bootstrap tests.unit.test_phase2_systemd_discovery --noinput` passed: 54 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 324 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint C6 implementation and verification are complete.
- Full suite was run because this sprint changes runtime, job execution payloads, and security enforcement.

## Archived Task - Sprint C7 Tool Builder from Chat

Task:
- Implement the approved `Sprint C7 - Tool Builder from Chat`.

Scope:
- Allow owner/operator chat users to create `ToolBuildRequest` and `ToolBuildProposal`.
- Restrict chat proposals to `command_template` only.
- Keep proposals inactive and review-only.
- Add validator coverage for argv-only, allowlisted binaries, and blocked dangerous content.
- Add chat/session traceability for builder requests.

Out of scope:
- Tool execution.
- ToolRun or AgentJob creation.
- Automatic enablement.
- `script_template`.
- Runtime-handler code generation.
- Live AI.
- Telegram.
- Remediation/actions.

Progress:
- Added `command_template` request metadata and chat trace fields to `ToolBuildRequest`.
- Added chat service flow to create builder requests/proposals.
- Extended Tool Builder validator and converter for `command_template`.
- Added minimal Portal chat UI for builder proposals.
- Added focused tests for chat builder flow and existing Tool Builder compatibility.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint10_tool_builder --noinput` passed: 18 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_chat --noinput` passed: 19 tests.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected after intended migration.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_chat tests.unit.test_sprint10_tool_builder tests.unit.test_sprint_c6_command_templates --noinput` passed: 45 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint C7 implementation and verification are complete.
- Full suite was not run because C7 stayed in the proposal layer and did not modify runtime execution semantics directly.

## Archived Task - Sprint C8 First Laravel/Apache Tool Cycle

Task:
- Implement the approved `Sprint C8 - First Laravel/Apache Tool Cycle`.

Scope:
- Add the first safe commercial command-template tool flow using `apache_5xx_summary`.
- Keep the tool read-only and summary-only with no raw log exposure.
- Connect proposal conversion/enablement prerequisites, chat tool request execution, safe runtime output capture, and deterministic result explanation.
- Preserve existing Tool Builder, ToolPolicy, PlanTool, ToolRun, and AgentJob guardrails.

Out of scope:
- `laravel_env_sanity`.
- Raw log display or storage.
- `script_template`.
- Live AI providers.
- Telegram changes.
- Remediation, write, restart, reload, or destructive actions.

Next steps:
- Inspect current chat, tool builder, and command-template execution paths for the minimum C8 end-to-end gap.
- Implement only the missing pieces for one approved safe tool cycle.
- Add focused tests around command-template seeding, execution safety, and chat-visible explanation.

Progress:
- Added `enable_command_template_pilot_tool` for explicit pilot-only enablement of one approved read-only command-template tool.
- Added safe `apache_5xx_summary` result summarization and recent tool-result explanation in safe context/chat.
- Synced terminal tool-run results back into `AdminChatToolRequest` and posted safe assistant summaries into the chat thread.
- Added escaped-brace rendering support for fixed `awk` command arguments without introducing free-form shell behavior.
- Added focused C8 tests for enablement, chat execution, safe result summaries, and viewer denial.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c8_first_tool_cycle --noinput` passed: 7 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 338 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint C8 implementation and verification are complete.
- Full suite was run because C8 changed tool execution, result propagation, and chat-visible security behavior.

## Archived Task - Sprint C9 Reports from Chat

Task:
- Implement the approved `Sprint C9 - Reports from Chat`.

Scope:
- Add `AdminChatReportDraft` with draft/review flow.
- Support separate `technical/internal` and `customer_summary` chat-generated report drafts.
- Keep reports deterministic and built from safe summaries only.
- Require review before conversion to final `Report`.

Out of scope:
- Raw ToolRun output.
- Raw AgentJob output.
- Raw logs or raw `.env`.
- PDF export.
- Live AI providers.
- Telegram changes.

Next steps:
- Inspect current reports foundation and add the smallest safe chat draft model and conversion path.
- Add minimal Portal chat actions for draft creation and visibility.
- Add Matrix Admin review/conversion actions in Admin and focused tests for redaction, scoping, and conversion.

Progress:
- Added `AdminChatReportDraft` with review-first status flow and optional final `Report` link.
- Added deterministic draft generation for `technical_internal` and `customer_summary`.
- Added Matrix Admin review and conversion services plus Admin actions.
- Added minimal Portal chat form/history for report drafts.
- Extended final `Report` types to include `technical_internal` and `customer_summary`.
- Added focused tests for draft creation, viewer denial, admin review/conversion, redaction, and account scoping.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations ai_chat reports` generated only the intended migrations.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c9_chat_reports --noinput` passed: 9 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c9_chat_reports tests.unit.test_admin_chat tests.unit.test_sprint11_reports --noinput` passed: 38 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 347 tests, 4 skipped.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Sprint C9 implementation and verification are complete.
- Full suite was run because C9 changed report redaction, report visibility, and review conversion behavior.

## Archived Task - Chat Report Rendering Fix

Task:
- Fix final chat-generated report rendering so `technical_internal` and `customer_summary` do not expose dict/list payloads in report sections.

Scope:
- Adjust chat report section generation and conversion output only.
- Keep approval flow, ToolRun/AgentJob execution, Safe Context schema, and policies unchanged.

Out of scope:
- Tool execution changes.
- AgentJob changes.
- Telegram.
- Live AI.
- Migrations unless unexpectedly required.

Next steps:
- Replace raw structured section payloads with readable multiline summaries.
- Ensure final chat-generated report sections store empty `data_redacted` where raw payloads are not needed.
- Add focused tests plus the requested chat/report regression.

Progress:
- Replaced raw dict/list-style chat report section payloads with readable multiline summary text.
- Cleared chat-generated final section `data_redacted` payloads where they were previously shown as raw objects in Portal.
- Kept `technical_internal` readable with structured lines for server status, baseline profile, tool activity, and finding summaries.
- Added focused tests for final `customer_summary` and `technical_internal` report rendering safety.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c9_chat_reports --noinput` passed: 11 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c9_chat_reports tests.unit.test_admin_chat tests.unit.test_sprint11_reports --noinput` passed: 40 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- Chat report rendering fix is complete.
- Full suite was not run because the change stayed inside chat-report rendering and conversion presentation, not runtime or policy execution.

## Archived Task - Sprint C10.5 Chat Responsibility Split

Task:
- Implement the approved corrective sprint that separates Matrix Admin internal chat from Customer Portal chat responsibilities.

Scope:
- Add a clear internal/admin versus portal/customer distinction in `AdminChatSession`.
- Remove Tool Builder proposal creation from Portal chat and block any Portal route that creates `ToolBuildRequest` or `ToolBuildProposal`.
- Keep Portal chat limited to safe context, approved read-only tool requests, and self-service customer-safe reports.
- Add a minimal staff-only internal chat UI that reuses `apps.ai_chat` services for messages, tool builder proposals, and internal reports.
- Let internal Matrix Admin reports auto-convert safely without a separate waiting approval while keeping manual review flow available for sensitive/manual cases.

Out of scope:
- Live AI providers.
- Telegram.
- Remediation/write/destructive tools.
- Raw logs, raw `.env`, credentials, raw ToolRun output, or raw AgentJob output.
- New runtime/tool execution paths outside the existing policy-backed flow.

Immediate next steps:
- Inspect current `apps.ai_chat`, `apps.portal`, templates, and root/admin routing.
- Add channel-aware chat session handling and internal staff-only views.
- Remove Portal tool-builder creation UI/routes and switch Portal chat reports to self-service final reports.
- Add focused regressions for portal/admin chat split, report safety, tool builder restrictions, and policy-backed tool requests.

Progress:
- Added `AdminChatSession.channel` with `portal_customer` and `admin_internal`.
- Added staff-only internal chat routes and templates under `/admin/internal-chat/`.
- Restricted Tool Builder chat proposal creation to internal admin chat only.
- Removed Portal Tool Builder creation UI and route.
- Switched Portal chat report generation to immediate customer-safe final report creation through the existing safe draft/content pipeline.
- Added internal immediate report creation while preserving manual draft review/conversion flow.
- Updated focused tests for Portal chat, internal chat, Tool Builder, and chat report behavior.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations ai_chat` created the intended migration.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no extra changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c10_5_chat_split --keepdb --noinput` passed: 5 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_chat --keepdb --noinput` passed: 20 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c9_chat_reports --keepdb --noinput` passed: 12 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint10_tool_builder --keepdb --noinput` passed: 18 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint6_portal --keepdb --noinput` passed: 16 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c8_first_tool_cycle --keepdb --noinput` passed: 7 tests.
- `.\.venv\Scripts\python.exe manage.py test --keepdb --noinput` passed: 356 tests, 4 skipped.

Completion status:
- Sprint C10.5 implementation and verification are complete.
- Full suite was run because this sprint changed permissions, report conversion behavior, and chat-visible tool execution flows.
- No live AI, Telegram, remediation/write/destructive tools, raw outputs, or policy bypasses were added.

## Archived Task - C10.5-B Admin Internal Chat UX and Navigation Fix

Task:
- Improve Django Admin discoverability and internal-chat usability after C10.5.

Scope:
- Add a clear Internal Chat link inside Django Admin.
- Refine internal chat list/detail templates using Django admin styling and simple local CSS only.
- Verify Portal still has no Tool Builder and internal chat remains staff-only.

Out of scope:
- Live AI.
- Telegram.
- Tool Builder in Portal.
- Runtime, policy, or orchestration changes except tiny view/template glue if necessary.

Immediate next steps:
- Add an Admin index entry for Internal Chat.
- Improve the internal chat templates for session list, create form, message flow, tools, Tool Builder, and reports.
- Add focused tests for admin visibility/access plus Portal/Admin split regression.

Progress:
- Added a visible `Internal Chat` module to Django Admin index.
- Reworked the internal chat list template into a clearer admin workspace with session creation and recent sessions.
- Reworked the internal chat detail template into a chat-style layout with separate areas for messages, tool requests, Tool Builder, and reports.
- Preserved Portal chat without Tool Builder.
- Preserved staff-only access for internal chat.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c10_5_chat_split tests.unit.test_admin_chat --keepdb --noinput` passed: 26 tests.
- `git diff --check` passed with line-ending warnings only.

Completion status:
- C10.5-B implementation and verification are complete.
- Full suite was not run because this hotfix stayed in admin navigation/templates plus focused access assertions, without changing execution, policy, or runtime behavior.
