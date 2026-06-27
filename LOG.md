# Log

Operational notes for repository work. Update this file before and after every requested implementation, repository-changing command, or multi-step operation.

## 2026-06-27 - C10.10-H2 Progressive Bundle UX Start

Intent:
- Make Admin Live AI diagnostic bundles progressive and non-blocking.
- Show one immediate running message and finalize one combined result after background ToolRuns complete.

Scope:
- Add stable bundle execution correlation metadata and idempotent running/result messages.
- Move bundle result aggregation into the existing ToolRun completion sync path.
- Add automatic history refresh only while a diagnostic bundle is running.

Out of scope:
- Migrations, write/remediation/shell tools, raw logs or secrets, Portal, Telegram, and customer-facing AI.

## 2026-06-27 - C10.10-H2 Progressive Bundle UX Complete

Result:
- Removed bundle ToolRun polling from the ChatKit request and return one immediate running message.
- Added stable execution correlation plus idempotent running/result message IDs.
- Finalized the combined result from the existing ToolRun completion sync callback after all expected runs terminate.
- Added a staff-only status endpoint and bounded frontend polling to refresh ChatKit history automatically.
- Kept individual bundle tool messages suppressed and lowered ignored visible-delete logging to info.
- No migrations or changes to Portal, Telegram, customer-facing AI, tool safety policy, or write capabilities.

Verification:
- `python manage.py check` and `makemigrations --check --dry-run` passed with no changes.
- Required unit modules passed: 34, 13, 9, 8, 8, 5, 7, and 20 tests respectively.
- `git diff --check` passed with line-ending warnings only.

## 2026-06-27 - C10.10-H3 Auto-Refresh Running Diagnostic Bundles Start

Intent:
- Make running diagnostic bundles appear and finalize in Live Admin AI without a manual browser refresh.
- Replace full-page reload behavior with bounded thread/history refresh while a bundle is still running.

Scope:
- Rework Live Admin ChatKit frontend polling and running-state indicator behavior.
- Extend the staff-only bundle status payload only as needed for safe bundle metadata and completion detection.
- Add focused regression coverage for running-state polling, stop conditions, and duplicate prevention.

Out of scope:
- Migrations, Portal, Telegram, customer-facing AI, write/remediation/shell actions, raw logs, raw JSON, and secrets.

## 2026-06-27 - C10.10-H3 Auto-Refresh Running Diagnostic Bundles Complete

Result:
- Replaced full-page reload behavior with bounded diagnostic-bundle polling that remounts ChatKit and rehydrates thread history when the same bundle reaches a final state.
- Added a visible in-panel running indicator while a diagnostic bundle is still executing.
- Extended the staff-only bundle status endpoint with safe execution and item identifiers needed for completion detection, without exposing raw outputs, logs, JSON, or secrets.
- Kept duplicate prevention unchanged by relying on stored `chatkit_item_id` values and the existing idempotent running/result message rules.
- No migrations or changes to Portal, Telegram, customer-facing AI, write/remediation behavior, or tool scope were made.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 14 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_ai_tool_request_flow --keepdb --noinput` passed: 34 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_live_ai_history_hydration --keepdb --noinput` passed: 9 tests.
- `git diff --check` passed with line-ending warnings only.

## 2026-06-26 - C10.10 Multi-Tool Diagnostic Bundles Start

Intent:
- Add Admin Live AI diagnostic bundles for broad read-only server checks.
- Keep execution restricted to existing approved read-only tools and produce one combined Arabic result.

Scope:
- Add code-only bundle registry/resolver.
- Execute bundle tools through existing ToolPolicy, PlanTool, allowlist, and selected-server validation.
- Preserve idempotent start/result messages and no raw output exposure.

Out of scope:
- Migrations, new tool definitions, write/destructive actions, remediation, shell execution, uploads, Portal AI, Telegram AI, and customer-facing AI.

## 2026-06-26 - C10.10 Multi-Tool Diagnostic Bundles Complete

Result:
- Added a code-only diagnostic bundle registry for server health and web stack checks.
- Resolved broad server-health execution intent to bundle execution while preserving specific single-tool requests such as log-source checks.
- Executed bundle tools through the existing read-only allowlist, ToolPolicy, PlanTool, selected-server validation, ToolRun, and AgentJob path.
- Added one bundle start message and one combined Arabic result summary with stable ChatKit IDs and bundle metadata.
- Suppressed per-tool chat start/result messages for bundle-triggered ToolRuns so the chat shows a unified bundle experience.
- Skipped unavailable/disallowed bundle tools with safe reasons in the final summary.
- Updated Live AI instructions and request analysis for diagnostic bundle behavior.
- No migrations, Portal changes, Telegram changes, write tools, remediation, uploads, or shell execution were added.

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

## 2026-06-26 - C10.9-H7 Idempotent Tool Result Chat Messages Start

Intent:
- Ensure each Live AI ToolRun has one visible start message and one visible final result/failure/timeout message.
- Add safe cleanup for duplicate detailed result summaries already present in data.

Scope:
- Make tool result/start message creation idempotent by ChatKit item ID and tool run/request/source metadata.
- Preserve the best existing detailed result message when duplicates are found.
- Add focused tests and run the required regression suite.

Out of scope:
- Migrations, Portal/Telegram/customer-facing changes, write/destructive tools, remediation, shell execution, uploads, and policy expansion.

## 2026-06-26 - C10.9-H7 Idempotent Tool Result Chat Messages Complete

Result:
- Made Live AI tool result follow-up messages idempotent by stable ChatKit item ID and by tool request/run/source metadata.
- Added start-message dedupe for `tool_orchestrator` messages so each tool request keeps one start message.
- Kept repeated sync calls from creating duplicate result messages after a follow-up already exists.
- Extended `cleanup_live_ai_legacy_test_data` to find duplicate detailed result summaries and keep the best message by state/status metadata, ChatKit ID, and recency.
- Added focused tests for repeated sync, no duplicate ChatKit IDs, one start message, and cleanup of duplicate detailed summaries.
- No migrations, Portal changes, Telegram changes, write tools, remediation, uploads, or shell execution were added.

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

## 2026-06-26 - C10.9-H6 Remove Duplicate Generic Tool Success Messages Start

Intent:
- Prevent generic tool success chat messages from being saved when detailed Arabic result summaries exist.
- Add safe cleanup for legacy duplicate generic success messages.

Scope:
- Review Live AI/tool result message creation paths.
- Keep detailed Arabic `tool_result_summary` messages visible with stable ChatKit IDs.
- Extend cleanup support with dry-run/apply coverage for old duplicate generic messages.

Out of scope:
- Migrations, Portal/Telegram/customer-facing changes, write/destructive tools, remediation, shell execution, uploads, and policy expansion.

## 2026-06-26 - C10.9-H6 Remove Duplicate Generic Tool Success Messages Complete

Result:
- Stopped tool-result sync from creating generic `<tool_key> completed successfully.` messages when a detailed result message already exists for the same `ToolRun`.
- Switched sync-created chat result messages to the chat-safe summary path and ensured stable `chatkit_item_id` assignment.
- Preserved the existing Apache 5xx result summarizer used by C8.
- Extended `cleanup_live_ai_legacy_test_data` with dry-run/apply cleanup for old generic duplicate tool-result messages that have a later detailed message for the same run.
- Added regressions for no duplicate generic message, ChatKit history visibility, cleanup dry-run/apply, preserving detailed messages, and preserving non-matching tool messages.
- No migrations, Portal changes, Telegram changes, write tools, remediation, uploads, or shell execution were added.

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

## 2026-06-26 - C10.9-H5 Clean Direct Execution Chat Output Start

Intent:
- Clean Live Admin AI chat output when explicit read-only tool execution succeeds.
- Avoid showing AI suggestion/approval wording before backend start/result messages.
- Remove duplicated Arabic summary/explanation headings from result output.

Scope:
- Suppress suggestion text only after explicit user execution intent creates a ToolRun/AgentJob.
- Preserve normal advisory suggestions when the user asks what to check.
- Keep existing read-only allowlist, policy, plan, selected-server, and no-remediation constraints.

Out of scope:
- New tools, policy expansion, write/destructive actions, shell execution, uploads, Portal AI, Telegram AI, customer-facing behavior, and migrations.

## 2026-06-26 - C10.9-H5 Clean Direct Execution Chat Output Complete

Result:
- Buffered Live AI provider text when explicit direct execution intent maps to safe read-only tool proposals.
- Suppressed AI suggestion/approval wording only after backend orchestration created a ToolRun/AgentJob.
- Stored suppressed direct-execution AI text as a hidden placeholder so tool requests still retain a message reference.
- Excluded hidden placeholders from ChatKit history hydration.
- Kept advisory suggestion text visible for non-execution questions.
- Prevented duplicate `الخلاصة:` and `التفسير:` headings when the result summary is already a complete chat body.
- No migrations, Portal changes, Telegram changes, write tools, remediation, uploads, or shell execution were added.

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

## 2026-06-26 - C10.9-H4 Direct Execution Intent and Real Tool Result Summaries Start

Intent:
- Fix Live Admin AI read-only tool handling when an admin explicitly asks to run a safe diagnostic check.
- Improve Arabic chat summaries from real redacted tool results instead of generic success text.

Scope:
- Add deterministic execution-intent resolution from the user's latest message only.
- Keep execution restricted to enabled approved read-only tools, existing allowlist, policy, plan, and selected-server scope.
- Add a real `log_sources_discovery_v2` summary and safe generic fallback without raw JSON, raw logs, or secrets.

Out of scope:
- Write/destructive tools, arbitrary commands, remediation, uploads, Portal AI, Telegram AI, customer-facing AI, migrations, and tool policy expansion.

## 2026-06-26 - C10.9-H4 Direct Execution Intent and Real Tool Result Summaries Complete

Result:
- Added explicit direct execution-intent detection for approved read-only diagnostic checks.
- Added a deterministic resolver from the user's latest message/scope to safe tool proposals when Live AI omits `TOOL_REQUEST_PROPOSAL`.
- Updated Live AI instructions and request analysis so direct admin execution requests do not ask for extra approval.
- Added Arabic result summaries from `ToolRun.result_redacted`, including a structured `log_sources_discovery_v2` summary with counts, existing/missing paths, permission status, and metadata-only/no raw log explanation.
- Kept execution behind the existing allowlist, available-tools context, read-only enablement, policy, plan, and selected-server validation.
- No migrations, Portal changes, Telegram changes, write tools, remediation, uploads, or shell execution were added.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_admin_ai_tool_request_flow --keepdb --noinput` passed: 27 tests.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_live_ai_failure_finalization --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_live_ai_history_hydration --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_sprint_c8_first_tool_cycle --keepdb --noinput` passed: 7 tests after sequential rerun because the first parallel run hit a database deadlock.
- `python manage.py test tests.unit.test_admin_chat --keepdb --noinput` passed: 20 tests after sequential rerun because the first parallel run hit a database deadlock.
- `git diff --check` passed with line-ending warnings only.

## 2026-06-25 - C10.8-H4 ChatKit History Hydration and Audit Scope Start

Intent:
- Fix Live Admin AI history hydration and stop creating Live AI audit rows for ChatKit history/init requests.

Scope:
- Ensure stored `AdminChatMessage` rows hydrate through `AdminChatKitStore.load_thread_items` with stable item IDs.
- Restrict `AdminLiveAIRequestLog` creation to actual generation requests.
- Add focused history/audit-scope tests while preserving prompt behavior, Safe Context, tools/actions, Portal, and Telegram boundaries.

Out of scope:
- New models, migrations, prompt changes, diagnostic behavior changes, tools, ToolRun, AgentJob, remediation, Portal AI, Telegram AI, and customer deterministic chat changes.

## 2026-06-25 - C10.8-H4 ChatKit History Hydration and Audit Scope Complete

Result:
- Confirmed saved Live AI messages live in `AdminChatMessage`; the issue was hydration/audit scoping, not persistence.
- Changed fallback ChatKit item IDs for stored messages without `chatkit_item_id` to stable `admin_msg_<id>` values.
- Kept `AdminChatKitStore.load_thread_items` hydrating from the current `AdminChatSession` messages in ascending order.
- Restricted `AdminLiveAIRequestLog` creation to generation request types only: `threads.create`, `threads.add_user_message`, and `threads.retry_after_item`.
- Prevented `items.list`, `threads.get_by_id`, and other history/init requests from creating pending audit rows.
- Fixed non-streaming ChatKit response sizing for byte payloads.
- Added focused H4 tests for history hydration, item roles/text/IDs, no audit for history/init, generation audit finalization, no ToolRun/AgentJob, and Portal boundary.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_live_ai_failure_finalization --keepdb --noinput` passed: 5 tests.
- `python manage.py test tests.unit.test_live_ai_history_hydration --keepdb --noinput` passed: 5 tests.
- `git diff --check` passed with line-ending warnings only.

## 2026-06-25 - C10.8-H3 Live AI UI Cleanup and Message Persistence Start

Intent:
- Remove custom Live AI status/error strips and make Live Admin AI messages persist visibly after refresh.

Scope:
- Remove the custom status/error strip underneath ChatKit.
- Use the existing `AdminChatMessage` session transcript for Live AI user/assistant messages.
- Enable ChatKit history loading from `AdminChatKitStore` instead of keeping frontend-only state.
- Add tests for persistence, history configuration, no raw Safe Context/secrets, audit continuity, and no ToolRun/AgentJob side effects.

Out of scope:
- Prompt behavior, diagnostic intent detection, Safe Context builder changes, tools/actions, ToolRun/AgentJob, remediation, Portal AI, Telegram AI, customer chat changes, prompt management, and migrations unless strictly necessary.

## 2026-06-25 - C10.8-H3 Live AI UI Cleanup and Message Persistence Complete

Result:
- Removed the custom Live Admin AI status/error strip from the template and JavaScript.
- Stopped writing custom ready/unavailable/load-failure messages under ChatKit.
- Enabled ChatKit history loading with `history: { enabled: true }`.
- Confirmed Live AI messages are persisted through the existing `AdminChatMessage` transcript and loaded through `AdminChatKitStore.load_thread_items`.
- Added regressions for user/assistant persistence, refresh/history loading, no raw Safe Context or secrets in transcript, audit continuity, and no ToolRun/AgentJob side effects.
- No migrations, prompt behavior changes, Safe Context changes, tools/actions, Portal AI, Telegram AI, or customer chat changes were made.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_live_ai_failure_finalization --keepdb --noinput` passed: 5 tests.
- `git diff --check` passed with line-ending warnings only.

## 2026-06-25 - C10.8-H2 Remove Visible Live AI Deterministic Fallback Start

Intent:
- Remove visible deterministic fallback UI from the Live Admin AI experience so ChatKit appears as one clean admin assistant surface.

Scope:
- Remove the visible `Deterministic fallback` button and fallback panel when Live Admin AI is available.
- Replace Live AI UI/error messages that mention deterministic fallback with generic safe messages.
- Preserve backend deterministic chat behavior for non-Live/disabled states and Portal/customer chat.
- Add focused tests for Live UI text removal, JS message cleanup, success/failure paths, and no ToolRun/AgentJob boundaries.

Out of scope:
- Prompt behavior, diagnostic reasoning, Safe Context/provider input, audit schema, migrations, tools/actions, remediation, Portal AI, Telegram AI, and customer deterministic chat changes.

## 2026-06-25 - C10.8-H2 Remove Visible Live AI Deterministic Fallback Complete

Result:
- Removed the visible `Deterministic fallback` button from the Live Admin AI header.
- Stopped rendering the deterministic fallback panel underneath ChatKit when Live Admin AI is available; the deterministic form remains available only for non-Live/disabled states.
- Changed Live AI UI failure copy to generic retry/refresh messages without mentioning deterministic fallback.
- Renamed the JS error path from fallback display behavior to `showError()` and kept `clearError()` on retry/success.
- Updated the generic Live AI backend error message text only; no backend deterministic fallback logic was removed.
- Preserved Portal/customer deterministic chat, C10.8-A behavior, H1 audit finalization, tools/actions, ToolRun/AgentJob, and migrations unchanged.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_live_ai_failure_finalization --keepdb --noinput` passed: 5 tests.
- `git diff --check` passed with line-ending warnings only.

## 2026-06-24 - C10.8-H1 Live AI Failure State & Audit Finalization Start

Intent:
- Fix Live Admin AI failure paths so request audit records never remain pending after stream or endpoint errors.

Scope:
- Finalize `AdminLiveAIRequestLog` as failed when the SSE/streaming iterator raises after `StreamingHttpResponse` is created.
- Add safe diagnostic logging with IDs/status/class/latency only.
- Reset stale Live AI UI failure state on retry and successful same-origin responses.
- Add focused hotfix tests while preserving C10.8-A prompt behavior and no-tools/no-Portal/no-Telegram boundaries.

Out of scope:
- Prompt behavior changes, migrations, new UI buttons, quick actions, tools, ToolRun, AgentJob, command execution, remediation, Portal AI, Telegram AI, and deterministic customer chat changes.

## 2026-06-24 - C10.8-H1 Live AI Failure State & Audit Finalization Complete

Result:
- Added a safe streaming wrapper around Live Admin AI `StreamingHttpResponse` iteration so exceptions raised after response creation finalize audit as failed.
- Classified pre-streaming and streaming failures with existing Live AI error classes and recorded non-zero latency, `fallback_used=True`, and safe response size defaults.
- Added safe failure breadcrumbs with only session/audit/status/error/model/latency metadata and no raw exception text, prompts, context, messages, responses, env, or secrets.
- Updated the ChatKit frontend fetch hook to clear stale failure messages before retry and after successful same-origin responses.
- Added focused hotfix tests for pre-stream failures, streaming generator failures, no pending audit leftovers, success after failure, frontend stale-error reset, and Portal/tool boundaries.
- No migrations, prompt behavior changes, buttons, quick actions, tools, ToolRun/AgentJob, command execution, remediation, Portal AI, or Telegram AI changes were made.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_live_ai_failure_finalization --keepdb --noinput` passed: 5 tests.
- `git diff --check` passed with line-ending warnings only.

## 2026-06-24 - C10.8-A Admin AI Agent Behavior Start

Intent:
- Improve Live Admin AI behavior so diagnostic questions receive structured contextual reasoning while ordinary questions remain concise.

Scope:
- Inspect the current Live Admin AI base prompt source.
- Strengthen hardcoded base instructions for internal operational advisory behavior, Safe Context-only reasoning, limitations, and read-only suggested checks.
- Add internal diagnostic-intent detection from redacted conversation text without schema changes.
- Add focused tests for diagnostic/non-diagnostic behavior, safety boundaries, audit continuity, and Portal deterministic behavior.

Out of scope:
- Prompt profile models, migrations, Admin prompt UI, new buttons, quick actions, tools/function calling, ToolRun/AgentJob creation, command execution, remediation, uploads, Portal AI, Telegram AI, and customer-facing AI changes.

## 2026-06-24 - C10.8-A Admin AI Agent Behavior Complete

Result:
- Confirmed the current Live Admin AI base prompt is hardcoded as `LIVE_AI_INSTRUCTIONS` in `apps/ai_chat/live_ai.py` and passed to OpenAI through `instructions=`.
- Expanded the hardcoded instructions for internal operational advisory behavior, Safe Context-only reasoning, diagnostic structure, limitations, and read-only suggested checks.
- Added internal diagnostic-intent detection from redacted conversation text and a safe `<REQUEST_ANALYSIS>` block in provider input.
- Kept UI unchanged: no Diagnostic Brief button, no quick action, no prompt profile model, and no migration.
- Preserved no tools, no ToolRun/AgentJob, no command execution, no remediation, no Portal AI, and no Telegram AI boundaries.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `python manage.py test tests.unit.test_admin_ai_agent_behavior --keepdb --noinput` passed: 8 tests.
- `git diff --check` passed with line-ending warnings only.

## 2026-06-24 - C10.7-A Admin Live AI Governance Layer Start

Intent:
- Add governance, audit visibility, and safer error classification for staff-only Live Admin AI.

Scope:
- Record a safe audit row for each Live AI request, including status, latency, context/response sizes, model, scoped entities, and classified errors.
- Add readonly Django Admin visibility for Live AI audit records.
- Show non-secret Live AI operational status on the Admin Internal Chat page.
- Keep Live AI limited to Safe Context only with no tools, actions, uploads, remediation, Portal AI, or Telegram AI.

Out of scope:
- Any new AI capability, tool/function calling, command execution, remediation, uploads, Portal/customer deterministic behavior changes, Telegram changes, and secret/raw prompt logging.

## 2026-06-24 - C10.7-A Admin Live AI Governance Layer Complete

Result:
- Added `AdminLiveAIRequestLog` as a dedicated per-request governance audit table with a single migration.
- Wired Live Admin AI requests to create/update audit rows for success, disabled, missing config, validation/auth failures, rate limits, timeouts, upstream errors, and unknown failures.
- Added readonly Django Admin visibility for Live AI request logs with status/model/user/account/date filters and user/session/error search.
- Added non-secret Live AI status, model, rate limit, and Safe Context cap visibility to Admin Internal Chat.
- Redacted the ChatKit request payload before server processing so SSE responses do not echo raw secret-like user input.
- Kept Portal, Telegram, tools/actions, uploads, remediation, and deterministic customer chat behavior unchanged.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no additional changes.
- `python manage.py test tests.unit.test_live_admin_chat --keepdb --noinput` passed: 13 tests.
- `python manage.py test tests.unit.test_admin_live_ai_governance --keepdb --noinput` passed: 8 tests.
- `git diff --check` passed with line-ending warnings only.

## 2026-06-22 - C10.6-H1 ChatKit Frontend Initialization Hotfix Start

Intent:
- Fix the production ChatKit browser initialization schema mismatch and permanent static discovery.

Scope:
- Verify and apply the current Custom Server options shape.
- Relocate the Admin ChatKit JavaScript into an app-owned static directory discoverable by Django.
- Add focused frontend-config and static-discovery tests.

Out of scope:
- Backend provider logic, Portal, Telegram, tools/actions, Hosted Agent Builder, migrations, and live infrastructure changes.

## 2026-06-22 - C10.6-H1 ChatKit Frontend Initialization Hotfix Complete

Result:
- Corrected the current ChatKit options contract to `api: { url, domainKey, fetch }` and `header: { enabled: false }`.
- Added the required public domain-key configuration and fail-closed UI availability check.
- Relocated `live_chatkit.js` into the `ai_chat` app static directory for automatic Django discovery.
- Added regressions for static discovery, valid Custom Server options, missing domain-key handling, feature flags, access boundaries, and no execution-object creation.
- Did not change the streaming endpoint, provider behavior, Safe Context, Portal, Telegram, tools/actions, or database schema.

Verification:
- Django check passed and no migrations were detected.
- All 13 focused Live Admin ChatKit tests passed against the existing test database.
- `findstatic` found the app-owned asset and `collectstatic --dry-run` included it among 128 files.
- `git diff --check` passed.

## 2026-06-22 - C10.6 Live Admin ChatKit with Custom Server MVP Start

Intent:
- Add the first conservative Live AI experience to staff-only Admin Internal Chat using ChatKit Custom Server Integration.

Scope:
- Add a disabled-by-default feature flag and server-only OpenAI configuration.
- Add an embedded ChatKit panel and same-origin, CSRF-protected custom server endpoint.
- Use fresh `build_safe_context()` plus `prepare_safe_context_for_ai()` for every live response.
- Stream text responses, persist only completed assistant messages, record safe failure metadata, rate-limit staff users, and retain deterministic fallback.
- Add ASGI/Nginx/CSP deployment documentation and focused mock-provider tests.

Out of scope:
- Portal/Telegram Live AI, tools/function calling/actions, automatic ToolRequest, ToolRun/AgentJob creation, uploads, remediation, AI reports, Hosted Agent Builder, Codex CLI runtime, server changes, and migrations.

## 2026-06-22 - C10.6 Live Admin ChatKit with Custom Server MVP Complete

Result:
- Added a disabled-by-default, staff-only embedded ChatKit panel and same-origin Custom Server streaming endpoint.
- Added fresh capped/redacted Safe Context provider input, server-only OpenAI configuration, rate limiting, timeout/failure/disconnect handling, completed-response persistence, and safe audit metadata.
- Preserved deterministic fallback and left Portal, Telegram, tools/actions, execution objects, uploads, remediation, and AI reports unchanged.
- Added ChatKit/OpenAI/Uvicorn dependencies and deployment/smoke documentation; no migrations or live infrastructure changes were made.
- Retained `docs/index.html` as a non-served user reference only; its Hosted integration is not used by the application.

Verification:
- `python manage.py check` passed with no issues.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- 42 focused and related tests reached `OK` using an in-memory SQLite override; the wrapper timed out after success while closing the temporary test database.
- PostgreSQL rerun remains pending because the local service is stopped and unavailable to the current process.
- `pip check` passed with no broken requirements.
- Python compilation passed using a temporary bytecode cache; the repository cache directory is not writable by the current process.
## 2026-06-22 - C10.6-Pre Safe Context Hard Cap and Live AI Readiness Start

Intent:
- Close the Safe Context size and payload-safety gap before any Live AI implementation.

Scope:
- Add deterministic structured hard-cap enforcement and safe truncation metadata.
- Add a second-redaction, allowlisted AI-ready payload builder.
- Add canary-secret, size-cap, priority-preservation, JSON-integrity, and no-execution tests.
- Add environment-backed byte-limit configuration and concise documentation.

Out of scope:
- ChatKit, Live AI, OpenAI calls, ASGI/SSE, Telegram, Portal changes, automatic tool requests, ToolRun/AgentJob execution, remediation, uploads, and migrations.

## 2026-06-22 - C10.6-Pre Safe Context Hard Cap and Live AI Readiness Complete

Result:
- Enforced a deterministic structured hard byte cap for Safe Context.
- Added safe size metadata without storing or logging discarded content.
- Added `prepare_safe_context_for_ai()` with second redaction, allowlisted fields, critical-finding priority, prompt-injection guidance, and `tools_enabled=false`.
- Added `AI_SAFE_CONTEXT_MAX_BYTES=65536` environment-backed configuration.
- Expanded generic secret redaction for OpenAI-style keys and explicit canary markers.
- Added focused pure and database integration tests without adding migrations or external dependencies.

Verification:
- `python manage.py test tests.unit.test_ai_context --noinput` passed: 5 tests.
- Standard PostgreSQL test startup failed before test execution because the local service is stopped and cannot be started with current permissions.
- Safe Context integration passed with an in-memory SQLite override: 8 tests.
- Related admin chat, chat reports, reports, and tool-result regressions reached `OK` with the SQLite override: 49 tests; the shell wrapper timed out after printing the successful result.
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Rerun the focused and related suites against PostgreSQL when the local service is available.
- C10.6 Live AI/ChatKit remains separate and unimplemented.

## 2026-06-20 - Sprint C10.5-C Current State Reconciliation Start

Intent:
- Reconcile project documentation with the actual implemented and manually verified state before new development.

Scope:
- Correct roadmap status through C10.5-B.
- Record the completed C10-A Matrix/Siyaq manual pilot and deferred C10-B Laravel/Apache/Innvii pilot.
- Record C10.6 Live Admin AI Chatbot MVP as the next proposed sprint before Telegram.
- Documentation only; no application code, migrations, runtime, permissions, tool execution, Portal/Admin Chat logic, Telegram, Live AI implementation, or server operations.

## 2026-06-20 - Sprint C10.5-C Current State Reconciliation Complete

Result:
- Reconciled the corrected execution plan with completed C1-C9, the successful manual C10-A Matrix/Siyaq pilot, completed C10.5/C10.5-B, and deferred C10-B.
- Recorded C10.6 Live Admin AI Chatbot MVP as the next proposed sprint before Telegram.
- Updated README and execution reporting, and archived historical active-task headings.
- Confirmed Telegram C11/C12 and Live AI have not started.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed with no issues.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- C10.6 is proposed but not implemented and requires its own approved implementation scope.
- No application code, migrations, runtime, permissions, execution paths, Portal/Admin Chat logic, Telegram, Live AI, or server state were changed.

## 2026-06-05 - Sprint C2 Safe Context Builder MVP Start

Intent:
- Execute Sprint C2 from the approved corrected Matrix Scanner SaaS roadmap.

Scope:
- Add dedicated `apps/ai_context` safe context builder.
- Build versioned, redacted, summarized, capped JSON context.
- Include `available_tools` metadata respecting ToolPolicy and PlanTool.
- Add focused tests for scoping, redaction, raw output exclusion, caps, and tool policy filtering.

Out of scope:
- Live AI provider calls, chat UI/models, tool execution, direct AgentJob access, raw outputs/secrets, and Sprint C3 implementation.

Testing note:
- Per updated instruction, use focused Sprint tests by default.
- C2 touches redaction/permissions context, so full suite may be used as a security regression gate if needed and will be reported explicitly.

## 2026-06-05 - Sprint C1.5 Remote Bootstrap Runtime Completion Start

Intent:
- Execute Sprint C1.5 from the approved corrected Matrix Scanner SaaS roadmap.

Scope:
- Update Remote Bootstrap so the installed bundle is a real polling Runtime/Agent rather than registration/heartbeat only.
- Reuse existing bootstrap foundation and tests.
- Preserve Matrix Admin-only bootstrap, `/opt/matrix_scanner`, and `matrix-scanner-agent.service`.
- Ensure generated config includes `base_url`, `registration_token` or `agent_token`, `poll_interval_seconds`, and `runtime_mode`.

Out of scope:
- Portal/customer bootstrap, new raw shell/arbitrary commands, remediation/write/destructive actions, server/VM execution, and Sprint C2 implementation.

Result:
- Updated bootstrap archive generation to package the current `scanner_runtime` modules.
- Replaced the generated heartbeat-only `agent_service.py` with a polling runtime service using `scanner_runtime.prototype`.
- The generated runtime service now supports registration, heartbeat, polling, allowlisted AgentJob execution, and job result submission.
- Added `runtime_mode = polling_agent` to the generated bootstrap config.
- Preserved `/opt/matrix_scanner` and `matrix-scanner-agent.service`.
- Added focused tests for runtime archive contents, config shape, and systemd service target.
- Added Sprint C1.5 report to `docs/planning/تقارير التنفيذ.md`.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint3_bootstrap --noinput` passed: 13 tests.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 294 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Sprint C1.5 is complete.
- Proceed to `Sprint C2 - Safe Context Builder MVP` after the C1.5 commit if no untracked official files remain.
- No Portal/customer bootstrap, raw shell/arbitrary command expansion, remediation/write/destructive behavior, server/VM execution, or Sprint C2 implementation was performed.

## 2026-06-05 - Sprint C1 Current State and Documentation Alignment Start

Intent:
- Execute Sprint C1 from the approved corrected Matrix Scanner SaaS roadmap.

Scope:
- Align documentation around the approved planning references.
- Confirm `DECISION-REGISTER.md` is the official decision reference.
- Confirm `CORRECTED-EXECUTION-PLAN.md` is the top execution reference after `ROADMAP-CORRECTION.md`.
- Document that the first real implementation Sprint after C1 is `Sprint C1.5 - Remote Bootstrap Runtime Completion`.
- Run non-destructive validation commands.

Out of scope:
- Product code changes, model/service/runtime changes, migrations beyond dry-run checks, server execution, and Sprint C1.5 implementation.

Result:
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

Remaining:
- Sprint C1 is complete.
- Proceed to `Sprint C1.5 - Remote Bootstrap Runtime Completion` only after owner approval.
- No product code, migration, runtime/service/model change, or server execution was performed.

## 2026-06-05 - Decision Register Approval Update

Intent:
- Mark the corrected execution decision register as approved.

Scope:
- Update `docs/planning/DECISION-REGISTER.md` status.
- Update documentation tracking only.

Result:
- Marked `docs/planning/DECISION-REGISTER.md` as `Approved`.
- Added `Approved by project owner on 2026-06-05.`
- Recorded that the decision register is the official decision reference.
- Recorded that `docs/planning/CORRECTED-EXECUTION-PLAN.md` is the top execution reference after `docs/planning/ROADMAP-CORRECTION.md`.
- Recorded that the first real implementation Sprint after documentation alignment is `Sprint C1.5 - Remote Bootstrap Runtime Completion`.

Verification:
- `git diff --check` passed with line-ending warnings only.
- No code, migrations, tests, runtime changes, or server execution were performed.

## 2026-06-05 - Roadmap Tool Runtime Correction Detail Start

Intent:
- Apply the attached detailed correction to `docs/planning/ROADMAP-CORRECTION.md`.

Scope:
- Strengthen the roadmap reference around command-template-first tools.
- Clarify Admin AI Chatbot's responsibilities for selecting/proposing tools.
- Clarify Runtime/Agent as a safe restricted command executor.
- Clarify Tool Registry to Runtime execution flow and new-tool approval flow.

Out of scope:
- Product code changes, migrations, command-template runtime implementation, ToolPolicy/PlanTool changes, AI implementation, Telegram implementation, commits, and pushes.

Result:
- Strengthened `docs/planning/ROADMAP-CORRECTION.md` with detailed command-template-first tool semantics.
- Added sections covering proposed tool shape, Admin AI Chatbot responsibilities, Runtime/Agent responsibilities, Tool Registry to Runtime relationship, new-tool proposal/validation flow, and tool type classification.
- Kept `runtime_handler` as an advanced later option and `command_template` / `script_template` as the current preferred model.

Verification:
- Confirmed the roadmap contains the expected command-template details, including `nginx_error_tail`, `ToolBuildRequest`, `ToolBuildProposal`, `command_template`, `script_template`, and `runtime_handler`.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No product code, migration, command-template runtime implementation, ToolPolicy/PlanTool change, AI implementation, Telegram implementation, commit, or push was made.

## 2026-06-04 - Tool Model Correction Start

Intent:
- Apply the attached correction about Matrix Scanner tool concepts to the roadmap/execution planning docs.

Scope:
- Clarify that the preferred current tool model is `command_template`, not one runtime handler per tool.
- Clarify Runtime/Agent as a safe restricted command executor for approved read-only command templates.
- Keep runtime handlers as an advanced later option.
- Update the corrected execution plan and roadmap reference wording accordingly.

Out of scope:
- Product code changes, migrations, runtime command-template implementation, ToolPolicy/PlanTool activation, AI implementation, Telegram implementation, commits, and pushes.

Result:
- Updated `docs/planning/ROADMAP-CORRECTION.md` to add an explicit correction for tool concepts and Runtime/Agent responsibilities.
- Updated `docs/planning/CORRECTED-EXECUTION-PLAN.md` so the execution roadmap is command-template-first instead of handler-first.
- Renamed the phase 5 concept from runtime capability/handler hardening to `Safe Command Execution Runtime`.
- Clarified that runtime handlers are advanced later options, while the current preferred model is approved read-only command/script templates in Tool Registry.

Verification:
- Confirmed both Markdown files read correctly as UTF-8.
- Confirmed both files include the Safe Command Execution Runtime concept.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No product code, migration, runtime command-template implementation, ToolPolicy/PlanTool activation, AI implementation, Telegram implementation, commit, or push was made.

## 2026-06-04 - Corrected Execution Plan Start

Intent:
- Study the roadmap correction reference and current project state, then create a detailed implementation plan Markdown file for the next phases.

Scope:
- Use `docs/planning/ROADMAP-CORRECTION.md` as the guiding reference.
- Reconcile the plan with the implemented SaaS, Agent, Tool Registry, Baseline, Reports, Telegram foundation, and Phase 2 discovery state.
- Create a new Markdown execution plan for upcoming phases.

Out of scope:
- Product code changes, migrations, runtime handlers, ToolPolicy/PlanTool activation, AI/Telegram implementation, commits, and pushes.

Result:
- Added `docs/planning/CORRECTED-EXECUTION-PLAN.md` as the detailed implementation plan based on the roadmap correction and current code state.
- The plan reconciles the existing SaaS, Agent, Runtime, Tool Registry, baseline profiles, Phase 2 ingestion, reports, diagnostics, Telegram foundation, and Tool Builder with the corrected one-AI architecture.
- The plan defines phases for current-state lock, architecture cleanup, Safe Context Builder, Admin Chat, Tool Orchestrator, runtime capabilities, Tool Builder in chat, first full tool cycle, reports from chat, internal pilot, Telegram interface, and Telegram pilot.

Verification:
- Read the generated Markdown as UTF-8 and confirmed Arabic content is intact.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No product code, migration, runtime handler, ToolPolicy/PlanTool activation, AI implementation, Telegram implementation, commit, or push was made.

## 2026-06-04 - Roadmap Correction Reference Start

Intent:
- Convert the Word document `docs/planning/خطة_تصحيح_المسار_Matrix_Scanner_SaaS.docx` into a Markdown reference plan for the next project phases.

Scope:
- Read the Word document carefully.
- Create a Markdown reference document under project planning docs.
- Keep the content focused on the corrected roadmap: one Admin AI Chatbot, safe context, tool orchestration, runtime hardening, tool creation flow, reports, internal pilot, and Telegram later.

Out of scope:
- Product code changes, migrations, runtime changes, ToolPolicy/PlanTool changes, AI implementation, Telegram implementation, commits, and pushes.

Result:
- Added `docs/planning/ROADMAP-CORRECTION.md` as a Markdown reference copy of the roadmap correction Word document.
- Preserved the corrected architecture: one Admin AI Chatbot with SaaS Backend, Tool Registry/Policy, Runtime/Agent, Reports Engine, and Telegram as supporting service layers.
- Captured phases 0 through 11 from current-state stabilization through Safe Context, Admin Chat, Tool Orchestrator, Runtime hardening, Tool Builder flow, reports, internal pilot, Telegram interface, and Telegram pilot.

Verification:
- Read the generated Markdown as UTF-8 and confirmed Arabic content is intact.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No product code, migrations, runtime handlers, ToolPolicy/PlanTool changes, AI implementation, Telegram implementation, commit, or push was made.

## 2026-06-04 - Phase 2 Sprint 2.11B Start

Intent:
- Implement only Phase 2 application ingestion and deduplication for `opt_apps_discovery` and `django_apps_discovery`.

Scope:
- Add nullable `Application.baseline_scan` attribution.
- Ingest safe application outputs from `opt_apps_discovery` and `django_apps_discovery`.
- Deduplicate by the existing `account + server + domain + path` application location.
- Apply safe framework priority so Django enriches generic Python/unknown application records.
- Update application summary counts to use scan attribution where available while preserving legacy compatibility.
- Add focused tests for deduplication, metadata safety, approved app preservation, and summary accuracy.

Out of scope:
- Report redesign, AI planner, external bot, ToolPolicy/PlanTool changes, runtime tool changes, findings generation, remediation/write actions, and service-to-application relationship modeling.

Result:
- Added nullable `Application.baseline_scan` attribution with migration `applications.0003_application_baseline_scan`.
- Added Phase 2 application ingestion for `opt_apps_discovery` and `django_apps_discovery`.
- Deduplicated Phase 2 applications by existing `account + server + domain + path` location.
- Added framework priority so Django enriches Python/unknown app records and unknown does not overwrite more specific frameworks.
- Preserved approved applications from aggressive name/framework/status overwrites while still enriching metadata and scan attribution.
- Updated application summary counting to prefer scan-scoped applications, with legacy cPanel fallback preserved.
- Added focused tests for app creation, deduplication, framework priority, malformed/unsafe inputs, secret redaction, approved app preservation, scan attribution, summary accuracy, and legacy behavior.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_baseline_ingestion --noinput` passed: 15 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint5_baseline --noinput` passed: 22 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 291 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No report redesign, AI planner, external bot, ToolPolicy/PlanTool change, runtime tool change, finding generation, remediation/write behavior, or service-to-application relationship model was added.
- No commit or push was made.

## 2026-06-04 - Phase 2 Sprint 2.11B Nested App Hotfix Start

Intent:
- Prevent `opt_apps_discovery` nested internal package candidates from being ingested as standalone Applications when a parent application is already detected.

Scope:
- Skip clearly internal depth-2 `opt_apps_discovery` candidates without systemd hints or strong standalone markers.
- Preserve top-level apps and nested apps with strong standalone indicators.
- Keep `django_apps_discovery` enrichment for real parent Django apps.

Out of scope:
- Migrations, report redesign, AI planner, external bot, ToolPolicy/PlanTool changes, runtime tool changes, findings generation, remediation/write actions, and service-to-application relationship modeling.

Result:
- Added nested internal candidate filtering for `opt_apps_discovery` application ingestion.
- Candidates nested under a detected parent app are skipped when they are depth 2+, lack a systemd/explicit app hint, and only contain weak markers such as `wsgi.py`, `asgi.py`, or `requirements.txt`.
- Top-level `/opt` applications continue to ingest.
- Nested applications with strong markers such as `package.json` or explicit systemd hints continue to ingest.
- `django_apps_discovery` still enriches the real parent Django application.
- Added regression coverage for parent apps, internal package skips, nested standalone app preservation, and Django parent enrichment.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_baseline_ingestion --noinput` passed: 16 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint5_baseline --noinput` passed: 22 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 292 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No migrations, report redesign, AI planner, external bot, ToolPolicy/PlanTool changes, runtime tool changes, findings generation, remediation/write behavior, or service-to-application relationship model was added.
- No commit or push was made.

## 2026-06-01 - Phase 2 Sprint 2.11A Start

Intent:
- Implement only Phase 2 services, domains, and log source ingestion plus scan-scoped summary counts for models that already support `baseline_scan`.

Scope:
- Ingest `systemd_services_discovery`, `gunicorn_uvicorn_services_discovery`, and `postgres_status_discovery` into `DiscoveredService`.
- Ingest `nginx_sites_discovery.domains[]` into `DiscoveredDomain`.
- Ingest `log_sources_discovery_v2.log_sources[]` into `LogSource`.
- Tolerate malformed output, skip unsafe values, redact/cap metadata, and preserve legacy ingestion.
- Make summary counts scan-scoped for `DiscoveredService`, `DiscoveredDomain`, `LogSource`, and `Finding`.
- Keep applications at 0 for Phase 2 in this sprint.

Out of scope:
- Application ingestion, `Application.baseline_scan` migration, report redesign, AI planner, external bot, ToolPolicy/PlanTool changes, runtime tools, findings generation from Phase 2, remediation/actions, and write behavior.

Result:
- Added safe Phase 2 service ingestion for `systemd_services_discovery`, `gunicorn_uvicorn_services_discovery`, and `postgres_status_discovery`.
- Added safe Phase 2 domain ingestion for `nginx_sites_discovery.domains[]`.
- Added safe Phase 2 log source ingestion for `log_sources_discovery_v2.log_sources[]`.
- Added metadata filtering/redaction/capping helpers and merge behavior for duplicate service/domain/log records.
- Updated `summarize_scan()` to count `DiscoveredService`, `DiscoveredDomain`, `LogSource`, and `Finding` by `baseline_scan`.
- Kept applications at `0` in baseline summary for this sprint and did not add application ingestion or migrations.
- Added focused Phase 2 baseline ingestion tests and updated the Sprint 5 Phase 2 expectation.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_baseline_ingestion --noinput` passed: 10 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 285 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Application ingestion and application scan attribution remain deferred to Sprint 2.11B.
- No Application migration, report redesign, AI planner, external bot, ToolPolicy/PlanTool change, runtime tool change, finding generation, remediation, or write behavior was added.
- No commit or push was made.

## 2026-06-04 - Phase 2 Sprint 2.11A Metadata Hotfix Start

Intent:
- Prevent `gunicorn_uvicorn_services_discovery` entries with missing, empty, or `unknown` `process_type` from overwriting generic systemd service metadata.

Scope:
- Filter Gunicorn/Uvicorn service ingestion to only `gunicorn`, `uvicorn`, or `daphne` process types.
- Add a regression test proving generic systemd service metadata is not overwritten by unknown Gunicorn/Uvicorn entries.

Out of scope:
- Application ingestion, migrations, reports, AI planner, external bot, ToolPolicy/PlanTool changes, runtime tools, findings generation, remediation/actions, and write behavior.

Result:
- Added a Phase 2 service ingestion guard so `gunicorn_uvicorn_services_discovery` only ingests/enriches services with `process_type` of `gunicorn`, `uvicorn`, or `daphne`.
- Unknown, missing, or empty `process_type` rows from that tool are skipped and cannot overwrite systemd metadata.
- Updated regression coverage so generic `cron.service` remains sourced from `systemd_services_discovery`, while real Gunicorn services still enrich existing service records without duplicates.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_baseline_ingestion --noinput` passed: 10 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_baseline_ingestion tests.unit.test_sprint5_baseline --noinput` passed: 32 tests.
- First full-suite run found one outdated Sprint 5 fixture expecting an untyped Gunicorn row to ingest; fixture was corrected to use `process_type="gunicorn"`.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 286 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No Application ingestion, migrations, report redesign, AI planner, external bot, ToolPolicy/PlanTool changes, runtime tool changes, findings generation, remediation, or write behavior was added.
- No commit or push was made.

## 2026-06-01 - Phase 2 Sprint 2.10 Start

Intent:
- Implement only the approved Sprint 2.10 safe Phase 2 pilot tool enablement command/helper.

Scope:
- Add a management command requiring `--plan-id` to enable Phase 2 read-only discovery tools for one selected pilot plan.
- Add dry-run support that reports intended ToolDefinition, ToolPolicy, and PlanTool changes without writes.
- Enable only the Phase 2 tools required by the `debian_nginx_opt` baseline profile.
- Keep `allow_customer_run=False` and create/update PlanTool only for the selected plan.
- Add focused tests for dry-run safety, plan scoping, policy shape, preflight success, and no ToolRun/AgentJob/report/ingestion side effects.

Out of scope:
- Migrations, Admin UI, customer Portal behavior, automatic scan creation, ToolRun/AgentJob creation inside the command, baseline ingestion, reports, AI planner, external bot, remediation/actions, global plan activation, and unrelated refactors.

Result:
- Added `apps/tools/phase2_enablement.py` with scoped Phase 2 pilot enablement logic.
- Added `enable_phase2_pilot_tools --plan-id <PLAN_ID> [--dry-run]`.
- Dry-run reports intended ToolDefinition, ToolPolicy, and PlanTool changes without writing.
- Actual run seeds missing Phase 2 contracts, enables only selected Phase 2 read-only discovery ToolDefinitions, activates admin/agent ToolPolicy with `allow_customer_run=False`, and creates/enables PlanTool rows only for the selected plan.
- The command does not create ToolRuns, AgentJobs, baseline scans, reports, or ingestion side effects.
- Added focused Sprint 2.10 tests for dry-run safety, plan-id requirements, invalid plan handling, selected-plan scoping, non-read-only skip behavior, policy shape, no ToolRun/AgentJob side effects, and Debian/Nginx baseline preflight readiness.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_pilot_enablement --noinput` passed: 11 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 275 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No migration, Admin UI, Portal behavior, ingestion, report, AI planner, external bot, remediation, or global activation changes were added.
- No commit or push was made.

## 2026-05-31 - Phase 2 Sprint 2.9 Start

Intent:
- Implement only the approved Sprint 2.9 baseline profile and runtime tool selection support.

Scope:
- Add stable baseline profile definitions for `legacy_cpanel`, `debian_nginx_opt`, and `minimal_linux`.
- Add `BaselineScan.profile_key` with default `legacy_cpanel`.
- Update baseline preflight and job creation to use the selected profile tool list.
- Preserve current/default cPanel baseline behavior exactly for `legacy_cpanel`.
- Add focused tests for profile selection, preflight scoping, and no Phase 2 ingestion side effects.

Out of scope:
- Phase 2 ingestion mapping, report changes, ToolPolicy/PlanTool activation, AI planner, external bot, remediation/actions, customer-facing behavior changes, and unrelated refactors.

Result:
- Added `apps/servers/baseline_profiles.py` with stable profile definitions for `legacy_cpanel`, `debian_nginx_opt`, and `minimal_linux`.
- Added `BaselineScan.profile_key` with default `legacy_cpanel` and a migration.
- Updated baseline preflight and ToolRun/AgentJob creation to use the selected scan profile tool list.
- Preserved the legacy cPanel baseline tool list as the default behavior.
- Exposed `profile_key` in BaselineScan Admin list display/filter only.
- Added focused tests for default profile behavior, profile-specific tool creation, selected-tool preflight scoping, failure-before-job-creation, and no Phase 2 ingestion side effects.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint5_baseline --noinput` passed: 21 tests.
- First full-suite run produced `OK` but hit the command timeout after test completion; reran with a longer timeout.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 264 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No Phase 2 result ingestion is implemented yet.
- Phase 2 ToolPolicy/PlanTool activation remains a separate Matrix Admin operation.
- No commit or push was made.

## 2026-05-27 - Documentation and Scaffolding Commit Preparation

Intent:
- Add required task-tracking guidance to `AGENTS.md`.
- Create `LOG.md` and `docs/CURRENT-TASKS.md`.
- Commit and push the planning, skills, documentation, and scaffold structure created for Matrix Scanner SaaS.

Scope:
- Documentation and project scaffolding only.
- No Sprint 1 implementation code.
- No Django models, migrations, agent APIs, bootstrap, baseline, Telegram, or Diagnostic Agent implementation.

Result before commit:
- Added planning, decision, security, data model, API contract, environment, testing, and sprint-spec documentation.
- Added scaffold directories with `.gitkeep` files only.
- Added required task-tracking rule to `AGENTS.md`.
- Created `LOG.md` and `docs/CURRENT-TASKS.md`.
- Staged intended repository files for commit.
- No tests were run because this change is documentation and scaffolding only.

Result after commit and push:
- Created commit `34ce9bc` with message `docs: add planning docs and project scaffold`.
- Pushed `main` to `origin/main`.
- Follow-up task-tracking update recorded in this file and `docs/CURRENT-TASKS.md`.

## 2026-05-27 - Sprint 1 Start

Intent:
- Implement Sprint 1 only: Django SaaS core foundation, PostgreSQL-ready settings, requirements, Sprint 1 apps, Sprint 1 models, and Django Admin registrations.

Scope:
- Project `scanner_platform`.
- Apps: `accounts`, `servers`, `applications`, `plans`, `subscriptions`, `audit`, `core`.
- Models: Account, custom User, Server, Application, Plan, Subscription, AuditLog.
- No agent APIs, Scanner Runtime, Remote Bootstrap, Baseline Scan, Tool Registry, Policy Engine, Telegram, Diagnostic Agent, Celery, payment gateway, or remediation.

Pre-start:
- Read required planning and decision files.
- Updated `docs/CURRENT-TASKS.md` before implementation.

Result:
- Added Django project `scanner_platform`.
- Added PostgreSQL-ready settings with local `.env` loading and default PostgreSQL `DATABASE_URL`.
- Added `requirements.txt` with Django and psycopg.
- Added Sprint 1 apps and models only: Account, custom User, Server, Application, Plan, Subscription, AuditLog.
- Added Django Admin registrations with list displays, filters, and search fields.
- Added initial migrations for all Sprint 1 models.
- Added minimal Sprint 1 model tests.
- Updated README setup notes.

Verification:
- Installed requirements with network approval after the first sandboxed pip attempt could not reach package versions.
- `python manage.py check` passed with no issues.
- `python manage.py makemigrations --check --dry-run` reported no missing migrations. It emitted a PostgreSQL connection warning because no local PostgreSQL service is available at `localhost:5432`.
- `python manage.py test tests.unit --noinput` discovered 4 tests but failed before running them because Django could not create a PostgreSQL test database without a running local PostgreSQL service.
- Parsed 49 Python files successfully with an AST syntax check.
- Confirmed no out-of-scope modules such as agent APIs, bootstrap, baseline, Tool Registry, Policy Engine, Telegram, Diagnostic Agent, Celery, payment gateway, or remediation were implemented.

Remaining issue:
- Run the Django tests again once PostgreSQL is running and `DATABASE_URL` points to a reachable database.

## 2026-05-27 - Push Sprint 1 Commit

Intent:
- Push existing Sprint 1 commit `508a1e6` to `origin/main`.

Scope:
- Git push only.
- No code changes.

Result:
- Pushed `main` to `origin/main`.
- Remote advanced from `cb3fcd0` to `f8726de`.
- Sprint 1 implementation commit `508a1e6` is now on GitHub.

## 2026-05-27 - Local Development Environment Preparation

Intent:
- Prepare and verify local development/testing setup for the existing Sprint 1 Django codebase only.

Scope:
- Requirements review.
- Local setup documentation with Windows PowerShell commands.
- PostgreSQL dev database option via Docker Compose.
- `.env.example` review/update.
- Run or document requested setup/check/test commands.

Out of scope:
- Sprint 2 work, agent APIs, Scanner Runtime, Bootstrap, Baseline, Tool Registry, Policy Engine, Telegram, Diagnostic Agent, Celery implementation, payment gateway, product features, or remediation.

Result:
- Verified `requirements.txt` remains sufficient for the current Sprint 1 Django codebase: Django and psycopg.
- Added `docker-compose.dev.yml` with a PostgreSQL 16 development service.
- Added `docs/operations/LOCAL-DEVELOPMENT.md` with Windows PowerShell setup commands, Docker PostgreSQL setup, manual PostgreSQL alternative, and troubleshooting.
- Updated `.env.example` with local PostgreSQL variables and removed unused Celery/Redis variables from the current local setup.
- Updated README to point to the local development guide and include the PowerShell setup flow.

Verification:
- `docker --version` and `docker compose version` are installed.
- `docker compose -f docker-compose.dev.yml config` passed.
- `docker compose -f docker-compose.dev.yml up -d postgres` failed because Docker Desktop Linux engine is not running.
- `python -m venv .venv` failed during `ensurepip`; the partial `.venv` was removed.
- `.\.venv\Scripts\Activate.ps1` could not run because the venv was not created successfully.
- `python -m pip install -r requirements.txt` succeeded using the user/global Python environment; requirements were already satisfied.
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no missing migrations, with the expected PostgreSQL connection warning because no database was reachable.
- `python manage.py migrate --noinput`, `python manage.py createsuperuser --noinput --username admin --email admin@example.com`, and `python manage.py test --noinput` failed because PostgreSQL was unavailable.

Remaining setup:
- Start Docker Desktop or configure manual PostgreSQL, then rerun migrate, createsuperuser, and tests.

## 2026-05-27 - Local Development Documentation Adjustment

Intent:
- Clarify local development setup so manual Windows PostgreSQL is the primary path and Docker Compose is optional only.

Scope:
- Documentation and environment setup text only.
- No product code changes.
- No Sprint 2 work.
- No Celery/Redis additions.
- PostgreSQL remains required.

Result:
- Updated local development docs to make Windows PostgreSQL the primary/manual path.
- Kept Docker Compose as an optional PostgreSQL helper only.
- Updated README to state PostgreSQL is required and Docker is not mandatory.
- No product code changed.

Verification:
- Verified documentation contains manual Windows PostgreSQL setup steps: install PostgreSQL, create user/database, set `DATABASE_URL`, run migrations and tests.
- Verified Docker section is titled optional and says Docker Desktop must be running with the Linux engine.
- `git diff --check` passed.
- No commit made.

## 2026-05-27 - Sprint 1 Test Fixture Fix

Intent:
- Fix the failing Sprint 1 staff-user test by giving the test user a valid/unusable password before `full_clean()`.

Scope:
- Test fixture only unless a product-code change is strictly necessary.
- No Sprint 2 work.
- No agent, Scanner Runtime, Bootstrap, Baseline, Tool Registry, Policy Engine, Telegram, or Diagnostic Agent work.

Result:
- Updated only the Sprint 1 test fixture.
- The staff/superuser test now calls `set_unusable_password()` before `full_clean()`.
- No product behavior changed.

Verification:
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes detected.
- `python manage.py test --noinput` passed: 4 tests ran successfully.

## 2026-05-27 - Sprint 2 Start

Intent:
- Implement Sprint 2 agent registration and job foundation within the locked scope.

Scope:
- Add `ScannerAgent`, `AgentRegistrationToken`, `AgentJob`, and `BaselineScan` skeleton.
- Add agent registration, heartbeat, one-job polling, and result submission endpoints.
- Add bearer token authentication for agents.
- Add temporary `system_identity` allowlist only.
- Add minimal scanner runtime prototype for register, heartbeat, poll one job, execute `system_identity`, and submit result.

Out of scope:
- Systemd, install flow, Remote Bootstrap, full Baseline Scan, Finding, full Tool Registry, full Policy Engine, Telegram, Diagnostic Agent, Celery, and remediation/actions.

Result:
- Added Sprint 2 agent foundation models and admin registrations.
- Added hashed registration and agent token helpers.
- Added agent registration, heartbeat, one-job polling, and job result APIs.
- Added atomic job claiming with `claimed_at`, `claim_expires_at`, and 5 minute default expiry.
- Added result submission guards for terminal jobs, unclaimed jobs, expired claims, output size, and agent ownership.
- Added temporary hardcoded allowlist with `system_identity` only.
- Added `BaselineScan` as a model skeleton only.
- Added a minimal scanner runtime prototype limited to register, heartbeat, poll one job, execute `system_identity`, and submit result.
- Added Sprint 2 unit/integration tests for the new agent foundation, including claim expiry and output size checks.

Verification:
- `python manage.py makemigrations servers` created `apps/servers/migrations/0002_agentregistrationtoken_baselinescan_scanneragent_and_more.py`.
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes detected.
- `python manage.py test --noinput` passed: 16 tests ran successfully.
- `python manage.py migrate` applied the Sprint 2 migration successfully.

Remaining:
- No known Sprint 2 implementation issues.
- Changes are not committed yet.

## 2026-05-27 - Sprint 3 Start

Intent:
- Implement Sprint 3 Remote Bootstrap MVP within the locked scope.

Scope:
- Admin-only Remote Bootstrap using Paramiko.
- Add `apps/bootstrap` with BootstrapSession, BootstrapStep, BootstrapCredential, and AgentInstallation.
- Use fixed command templates, typed parameters, package allowlists, encrypted temporary credentials, 30 minute TTL, and credential cleanup.
- Install/start Scanner Runtime under `/opt/matrix_scanner` using JSON config and `matrix-scanner-agent.service`.
- Verify heartbeat only.

Out of scope:
- Full Baseline Scan, Security Preflight, diagnostic tools, full Tool Registry, full Policy Engine, Telegram, Diagnostic Agent, Celery, remediation/actions, customer Portal bootstrap, self-install flow, install script, and free shell execution.

Result:
- Added `apps/bootstrap` with BootstrapSession, BootstrapStep, BootstrapCredential, and AgentInstallation.
- Added Matrix Admin-only Admin registrations, non-stored credential entry on session creation, and a synchronous Admin action for running selected bootstrap sessions.
- Added Paramiko SSH adapter.
- Added BootstrapPolicy fixed command templates and package manager allowlist handling.
- Added encrypted temporary credentials using `BOOTSTRAP_CREDENTIAL_ENCRYPTION_KEY`.
- Added 30 minute credential TTL and cleanup behavior that clears encrypted payloads and sets `destroyed_at`.
- Added generated runtime upload payload, JSON config handling, and systemd unit for `matrix-scanner-agent.service`.
- Added heartbeat verification step using Sprint 2 ScannerAgent state.
- Added secret redaction for stored command output and failure text.
- Added Sprint 3 tests for Admin-only access, credential encryption/expiry/cleanup, policy rejection, package confirmation, step statuses, mocked SSH success/failure, out-of-scope record absence, and audit metadata safety.

Verification:
- Installed new dependencies from `requirements.txt`: `paramiko` and `cryptography`.
- `python manage.py makemigrations bootstrap` created `apps/bootstrap/migrations/0001_initial.py`.
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes detected.
- `python manage.py test --noinput` passed: 27 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No known Sprint 3 implementation issues.
- Changes are not committed yet, per instruction.

## 2026-05-28 - Sprint 4 Start

Intent:
- Implement Sprint 4 Tool Registry and Policy Engine MVP within the locked scope.

Scope:
- Add `apps/tools` with ToolTemplate, ToolDefinition, ToolPolicy, PlanTool, and ToolRun.
- Register `system_identity` as the first registry-backed read-only tool.
- Enforce ToolPolicy and PlanTool for new tool/job creation.
- Create ToolRun after policy approval and before AgentJob.
- Update AgentJob result ingestion to update linked ToolRun with redacted results.

Out of scope:
- Full Baseline Scan, Baseline orchestration, Security Preflight, Diagnostic Agent, Telegram, Celery, remediation/actions, customer-created tools, Admin Tool Builder Agent, new diagnostic tools beyond `system_identity`, and external JSON Schema dependencies.

Result:
- Added `apps/tools` with ToolTemplate, ToolDefinition, ToolPolicy, PlanTool, and ToolRun.
- Added Admin registrations for all Sprint 4 models.
- Added idempotent `system_identity` registry setup and safe data migration.
- Added ToolPolicy/PlanTool deny-by-default service.
- Added internal parameter validation and path policy checks.
- Added ToolRun creation after policy approval and before AgentJob creation.
- Updated AgentJob result ingestion to update linked ToolRun with redacted output.
- Kept Sprint 2 hardcoded allowlist as a temporary fallback.
- Kept Sprint 3 BootstrapPolicy separate and unaffected.
- Added structured JSON redaction helper.
- Added Sprint 4 tests covering registry, policy denials, PlanTool enforcement, params/path policy, ToolRun updates, Sprint 2 polling, and BootstrapPolicy separation.

Verification:
- `python manage.py makemigrations tools` created `apps/tools/migrations/0001_initial.py`.
- Added `apps/tools/migrations/0002_seed_system_identity.py`.
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` passed with no changes detected.
- `python manage.py test --noinput` passed: 42 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No known Sprint 4 implementation issues.
- Changes are not committed yet, per instruction.

## 2026-05-28 - Sprint 5 Start

Intent:
- Implement Sprint 5 Baseline Scan Implementation within the locked scope.

Scope:
- Add baseline orchestration that uses ToolDefinition, ToolPolicy, ToolRun, and AgentJob.
- Add BaselineScanStep, DiscoveredService, DiscoveredDomain, LogSource, and simple MVP Finding.
- Seed the required baseline tools as read-only registry-backed tools.
- Add only the required read-only runtime handlers for baseline tools.
- Add Admin-only baseline workflow/action and focused tests.

Out of scope:
- Diagnostic Agent, Telegram, Celery, remediation/actions, Portal UI, full Security Preflight, raw log ingestion, raw `.env` storage, free shell commands, customer-created tools, and Admin Tool Builder Agent.

Pre-start:
- Read the required agent, log, current task, decision, plan, security, structure, checklist, and test plan documents.
- Updated `docs/CURRENT-TASKS.md` before implementation.

Result:
- Expanded `BaselineScan` with request/user, current step, summary, and error fields.
- Added `BaselineScanStep`, `DiscoveredService`, `DiscoveredDomain`, `LogSource`, and simple MVP `Finding`.
- Added Application metadata and unique discovered-location constraint.
- Added step-based baseline orchestration services that fail fast before creating jobs if required tools are not allowed by the active plan.
- Added ingestion for completed ToolRuns into services, domains, applications, Laravel safe env metadata, log source metadata, and finding evidence summaries.
- Added idempotent baseline tool setup and a data migration for the required read-only tools.
- Added read-only scanner runtime handlers for the required baseline tools.
- Added Matrix Admin-only baseline actions in Django Admin.
- Adjusted AgentJob result size enforcement to use each job's stored output cap.
- Updated agent polling responses to return the linked ToolRun timeout where available.
- Added Sprint 5 tests covering baseline seeding, policy failure, ToolRun/AgentJob creation, result ingestion, deduplication, Laravel env allowlist, blocked path handling, findings redaction, status transitions, tenant isolation, and out-of-scope side effects.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 56 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No known Sprint 5 implementation issues.
- Changes are not committed, per instruction.

## 2026-05-28 - Sprint 6 Start

Intent:
- Implement Sprint 6 Admin and Portal MVP Screens within the locked scope.

Scope:
- Create/use `apps/portal`.
- Add customer Portal templates, views, permissions, role checks, and tenant-scoped querysets.
- Add Portal pages for dashboard, servers, add server, server detail, registration token generation, applications, findings, baseline visibility, subscription/usage, and placeholders.
- Improve Django Admin usability where useful without changing product behavior outside Sprint 6.
- Add focused tests for Portal access, tenant isolation, role behavior, token safety, action audits, and safe display.

Out of scope:
- Telegram integration, Diagnostic Agent, Celery, payments gateway, remediation/actions, Admin Tool Builder Agent, advanced reporting, PDF/email output, customer Remote Bootstrap, React/Vue, user invitation/role management, and customer baseline start.

Pre-start:
- Read the required agent, log, current task, decision, plan, interface, security, structure, checklist, and test plan documents.
- Updated `docs/CURRENT-TASKS.md` before implementation.

## 2026-05-28 - Sprint 11 Start

Intent:
- Implement Sprint 11 Reports, Findings, and Knowledge Base Enhancement within the locked scope.

Scope:
- Add Report, ReportSection, FindingGroup, KnowledgeEntry, KnowledgeSource, and Recommendation.
- Add synchronous explicit report generation from safe/redacted sources.
- Add Admin registrations/actions for report generation and finding group rebuild.
- Improve Portal report and finding group visibility with account scoping and role permissions.
- Add small safe Telegram report summary support.

Out of scope:
- PDF export, email reports, scheduled reports, Celery/report workers, live LLM report generation, public API endpoints, remediation/actions, write tools, service restarts, package installs, file edits, ToolPolicy bypass, direct AgentJob creation, raw logs, raw `.env`, raw ToolRun output, raw AgentJob output, credentials, tokens, passwords, or private keys.

Pre-start:
- Read required agent, log, current task, decision, plan, interface, security, structure, checklist, and test-plan documents.
- Updated `docs/CURRENT-TASKS.md` before implementation.

Result:
- Added ToolBuildRequest, ToolBuildProposal, ToolBuildReview, and ToolTestResult models inside `apps/tools`.
- Added deterministic builder services for proposal generation, validation, review, and conversion.
- Added mock/sandbox validation only; no customer server execution path was added.
- Added Django Admin registrations and actions for generating, validating, approving, rejecting, and converting proposals.
- Conversion creates a ToolDefinition only as draft or pending_review and creates an inactive conservative ToolPolicy.
- Kept PlanTool attachment manual only and did not add automatic enablement.
- Redacted proposal text, review notes, validation output, and test result data before storage.
- Added AuditLog entries for request submission, proposal generation, validation, approval/rejection, and conversion without raw prompts/logs/secrets.
- Added focused Sprint 10 tests covering Admin-only access, safe storage, validation denials, safe conversion, no automatic enablement/PlanTool, no ToolRun/AgentJob, no customer server execution, and ToolPolicy source-of-truth behavior.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint10_tool_builder --noinput` passed: 14 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 132 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No known Sprint 10 implementation issues.
- Changes are not committed, per instruction.

Result:
- Added `TelegramDiagnosticState` to manage private-chat Telegram guided diagnostic flow state separately from `TelegramChatLink`.
- Added `DiagnosticSession.source` and nullable `source_chat_link` for Portal vs Telegram attribution.
- Added Telegram guided diagnostic commands: `/diagnose`, `/cancel`, `/approve`, `/session`, and `/report`.
- Added `callback_query` handling to the Telegram webhook and inline keyboard response payloads with constrained callback keys.
- Implemented private-chat-only server selection, application selection, problem type selection, bounded/redacted description capture, confirmation, approval, status, report, and cancellation flow.
- Enforced owner/operator-only diagnostic actions and blocked viewer and group/supergroup diagnostics.
- Enforced one active Telegram diagnostic state per private chat and 30-minute state expiry.
- Connected Telegram session creation and approval to existing diagnostics services and ToolPolicy-backed ToolRun/AgentJob creation.
- Added replay controls so repeated approvals are rejected once a step is no longer awaiting approval.
- Added concise redacted Telegram final report output and avoided raw ToolRun, AgentJob, logs, `.env`, stdout/stderr, credentials, tokens, and passwords.
- Added AuditLog entries for important Telegram diagnostic interactions without raw prompts, raw callback payloads, raw Telegram updates, or secrets.
- Added Sprint 9 tests covering unlinked/group/viewer denial, owner/operator flow, account-scoped server/application selection, cross-account callback rejection, one active state, cancellation, expiry, approval, replay prevention, webhook callbacks, Sprint 7 command compatibility, group summary behavior, and final report redaction.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint9_telegram_diagnostics --noinput` passed: 16 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 118 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No known Sprint 9 implementation issues.
- Changes are not committed, per instruction.

Result:
- Added `apps.diagnostics` with DiagnosticSession, DiagnosticStep, and DiagnosticDecision models plus Admin registrations and initial migration.
- Added deterministic diagnostic services that plan one approved read-only baseline tool step at a time.
- Added user approval gating before any diagnostic ToolRun is created.
- Integrated approved diagnostic steps through the existing ToolPolicy service via `create_tool_run_job`; diagnostics do not create AgentJob directly.
- Added ToolRun status/result synchronization into DiagnosticStep summaries and final DiagnosticSession reports.
- Added Portal diagnostics list, start, detail, and step approval views/templates under `/portal/diagnostics/`.
- Enforced Portal tenant scoping and owner/operator action permissions; viewers remain read-only.
- Strengthened shared redaction for `APP_KEY` and API key style strings before diagnostic context/report display.
- Added Sprint 8 tests covering Portal access, staff blocking, owner/operator/viewer permissions, tenant and application ownership, deterministic planning, approval gating, ToolPolicy denial, max tool-run limits, ToolRun/AgentJob linkage through ToolRun, result ingestion, final report redaction, no Telegram side effects, and safe Portal display.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint8_diagnostics --noinput` passed: 17 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 102 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No known Sprint 8 implementation issues.
- Changes are not committed, per instruction.

## 2026-05-28 - Sprint 9 Start

Intent:
- Implement Sprint 9 Telegram Guided Diagnostics within the locked scope.

Scope:
- Add private-chat-only Telegram diagnostic state and guided command/callback flow.
- Add Telegram diagnostic commands: `/diagnose`, `/cancel`, `/approve`, `/session`, and `/report`.
- Add callback_query handling and inline keyboard responses.
- Connect Telegram diagnostics to existing diagnostics services and ToolPolicy-backed approval workflow.
- Add minimal DiagnosticSession source fields for Portal vs Telegram attribution.
- Keep Telegram output concise and redacted.

Out of scope:
- Group diagnostics, remediation/actions, write tools, free shell commands, direct AgentJob creation from Telegram, ToolPolicy bypass, live LLM execution, and raw outputs/secrets in Telegram.

Pre-start:
- Read the required agent, log, current task, decision, plan, interface, security, structure, checklist, and test plan documents.
- Updated `docs/CURRENT-TASKS.md` before implementation.

## 2026-05-28 - Sprint 10 Start

Intent:
- Implement Sprint 10 Tool Definition Proposal Builder MVP inside `apps/tools`.

Scope:
- Add Matrix Admin-only ToolBuildRequest, ToolBuildProposal, ToolBuildReview, and ToolTestResult.
- Add deterministic proposal generation and validation.
- Add Admin review actions and conversion to draft/pending_review ToolDefinition only.
- Add mock/sandbox validation only.
- Keep Tool Registry and ToolPolicy as the source of truth.

Out of scope:
- New Django app, live LLM/provider calls, executable/runtime handler generation, shell/free command generation, remediation/actions, write/destructive tools, customer Portal tool builder, automatic enablement, automatic PlanTool attachment, ToolRun or AgentJob creation, and customer server execution.

Pre-start:
- Read the required agent, log, current task, decision, plan, interface, security, structure, checklist, and test plan documents.
- Updated `docs/CURRENT-TASKS.md` before implementation.

Result:
- Added `apps.telegram_integration` with `TelegramChatLink`, `TelegramLinkToken`, and `TelegramNotification` models, Admin registrations, and initial migration.
- Added Telegram webhook foundation at `/telegram/webhook/<secret>/` with path/header secret validation.
- Added global Telegram settings loaded from environment: `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_SECRET`; no bot token is stored in the database.
- Implemented hashed, one-time Telegram link tokens with TTL, used/revoked checks, private/group scope validation, and raw code shown once through Portal.
- Implemented read-only allowlisted Telegram commands: `/start`, `/link`, `/unlink`, `/help`, `/menu`, `/servers`, `/apps`, `/findings`, `/status`, and `/baseline`.
- Implemented account-scoped Telegram command summaries that avoid raw ToolRun output, AgentJob results, logs, `.env`, bootstrap credentials, SSH credentials, and secrets.
- Added safe notification records for Sprint 7 notification types with redacted payloads, dedupe suppression, and an explicit Bot API delivery helper.
- Added notification event hooks for baseline completion, high/critical findings, agent offline/recovered, and bootstrap completed/failed.
- Added Portal Telegram settings page and route, with owner/operator private link-code generation and owner-only group link-code generation.
- Added AuditLog entries for Telegram link-code generation and chat link/unlink events without raw codes or sensitive metadata.
- Added Sprint 7 tests covering token hashing/use/expiry/revocation, linking, Portal permissions, webhook secret enforcement, tenant scoping, read-only command behavior, notification redaction/suppression, event notification creation, and no DiagnosticSession/ToolRun/AgentJob creation from Telegram commands.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint7_telegram --noinput` passed: 13 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 85 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No known Sprint 7 implementation issues.
- Changes are not committed, per instruction.

## 2026-05-28 - Sprint 8 Start

Intent:
- Implement Sprint 8 Diagnostic Agent MVP within the locked scope.

Scope:
- Create/use `apps/diagnostics`.
- Add DiagnosticSession, DiagnosticStep, and DiagnosticDecision models.
- Add deterministic planning with read-only baseline tools only.
- Add Portal-only diagnostic session start/detail/approval flow.
- Require user approval before each diagnostic tool step creates a ToolRun.
- Use Tool Registry and ToolPolicy for every diagnostic ToolRun.
- Store concise redacted final reports on DiagnosticSession.

Out of scope:
- Telegram Guided Diagnostics, Telegram diagnostic commands/messages/approvals, live LLM execution, remediation/actions, write tools, shell/free commands, Celery, email alerts, PDF export, advanced reporting, IncidentReport, customer-created tools, and Admin Tool Builder Agent.

Pre-start:
- Read the required agent, log, current task, decision, plan, interface, security, structure, checklist, and test plan documents.
- Updated `docs/CURRENT-TASKS.md` before implementation.

Result:
- Added `apps.portal` with app config, permissions, forms, services, views, and URLs.
- Added Portal templates for dashboard, servers, add server, server detail, registration token generation, applications, findings, baseline scans, subscription/usage, login/logout/access-denied, and placeholders.
- Wired `/portal/` into the project and registered `apps.portal`.
- Implemented Portal access rules requiring authentication, account linkage, active account, and owner/operator/viewer role.
- Implemented tenant-scoped querysets and account ownership checks for every Portal object lookup.
- Implemented owner-only server creation and owner-only registration token generation.
- Ensured registration token raw value is shown once, stored hashed only, and audited without raw token metadata.
- Implemented application approve/ignore/archive actions and finding acknowledge/ignore actions with AuditLog entries.
- Added read-only baseline scan and subscription/usage views.
- Kept baseline start and remote bootstrap Admin-only by not exposing Portal routes for those actions.
- Added safe display rules for application metadata, finding evidence, baseline summaries, and server details without raw AgentJob or ToolRun output.
- Added minimal Django Admin branding for Matrix Scanner Admin.
- Added Sprint 6 tests covering login, staff blocking, tenant isolation, role permissions, token generation safety, action auditing, subscription read-only behavior, bootstrap route absence, and secret/output display safety.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 72 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No known Sprint 6 implementation issues.
- Changes are not committed, per instruction.

## 2026-05-28 - Sprint 7 Start

Intent:
- Implement Sprint 7 Telegram Integration MVP within the locked scope.

Scope:
- Create/use `apps/telegram_integration`.
- Add Telegram webhook foundation with secret validation.
- Add short-lived one-time Telegram link tokens stored hashed only.
- Add private and group chat linking rules.
- Add read-only Telegram command handling and safe summaries.
- Add safe notification records with dedupe/suppression.
- Add owner-only Portal surface for Telegram link token generation.

Out of scope:
- Diagnostic Agent, Telegram Guided Diagnostics, DiagnosticSession creation from Telegram, ToolRun or AgentJob creation from Telegram, remediation/actions, write tools, payments, Celery, polling infrastructure, per-account bot tokens, customer-created tools, and Admin Tool Builder Agent.

Pre-start:
- Read the required agent, log, current task, decision, plan, interface, security, structure, checklist, and test plan documents.
- Updated `docs/CURRENT-TASKS.md` before implementation.

## 2026-05-28 - Sprint 11 Completed

Result:
- Added `apps.reports` and registered it in Django settings.
- Added Report, ReportSection, FindingGroup, KnowledgeEntry, KnowledgeSource, and Recommendation with migration.
- Added report generation services using redacted snapshots only from approved safe sources.
- Added finding group rebuild/deduplication and advisory-only recommendations with no execution path.
- Added Report, ReportSection, FindingGroup, KnowledgeEntry, KnowledgeSource, and Recommendation Admin screens.
- Added Admin actions for baseline report generation, diagnostic report generation, and finding group rebuilds.
- Added Portal report list/detail/generation pages, finding group list/detail pages, findings filters, server latest report/group summary, and diagnostic report links.
- Updated Telegram `/report` to return a short latest safe report summary when no active diagnostic session report is present.
- Added Sprint 11 tests for safe report content, grouping, Portal scoping, Admin visibility, advisory recommendations, knowledge redaction, Telegram report summary, and out-of-scope exclusions.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 142 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No known Sprint 11 implementation issues.
- Changes are not committed, per instruction.

## 2026-05-28 - Sprint 12 Start

Intent:
- Implement Sprint 12 stabilization, security hardening, and release preparation within the locked scope.

Scope:
- Final verification, tenant isolation review, permission review, secret/redaction review, ToolPolicy enforcement review, Admin/Portal/Telegram access review, settings/env validation, migration consistency checks, documentation cleanup, release checklist, manual smoke checklist, and focused regression tests.

Out of scope:
- New product workflows, remediation/actions, write tools, live LLM execution, Celery/Redis implementation, payment gateway, PDF export, email reports, scheduled reports, customer Remote Bootstrap, ToolPolicy bypass, and direct AgentJob creation outside existing approved flows.

Pre-start:
- Read the required agent, log, current task, decision, plan, interface, security, structure, checklist, test plan, README, local development, deployment notes, and runbook documents.
- Updated `docs/CURRENT-TASKS.md` before implementation.

Result:
- Updated README, local development, deployment notes, runbook, PLANS, execution plan, implementation checklist, test plan, and decisions docs for MVP release readiness.
- Added `docs/operations/RELEASE-CHECKLIST.md`.
- Documented Celery/Redis, PDF/email/scheduled reports, payment gateway, customer Remote Bootstrap, live LLM, remediation/write/destructive tools, PostgreSQL RLS, multi-account membership, full self-install automation, and advanced knowledge matching as deferred.
- Added `.env.example` entries for CSRF trusted origins, proxy SSL header, and secure session/CSRF cookies.
- Added settings support for CSRF trusted origins, optional proxy SSL header, and secure cookies.
- Hardened AuditLog metadata value redaction before validation/storage.
- Hid raw `AgentJob.result` from Django Admin detail display.
- Added Sprint 12 security regression tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint12_stabilization --noinput` passed: 11 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py migrate` passed.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 153 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No known Sprint 12 implementation issues.
- Changes are not committed, per instruction.

## 2026-05-29 - Phase 2 Sprint 2.1 Start

Intent:
- Prepare only Phase 2 Sprint 2.1: runtime discovery tool contracts and seeding structure for Debian/Nginx `/opt`-based servers.

Scope:
- Update local `main` to deployed source-of-truth commit `762abd4`.
- Re-inspect current baseline, tool registry, diagnostics, and runtime code.
- Add non-executing Tool Registry contracts and idempotent seeding helper for the new Phase 2 discovery tools.
- Add focused tests for safe contract defaults and absence of ToolRun/AgentJob side effects.

Out of scope:
- Runtime handler implementation, baseline orchestration changes, UI redesign, external bot work, live LLM work, remediation/actions, write tools, free shell commands, and unsafe execution paths.

Pre-start:
- Fast-forwarded local `main` to `762abd4 fix: auto-ingest baseline after agent job result`.
- Confirmed working tree was clean before task-tracking updates.
- Re-inspected current code paths before implementation.

Result:
- Added Phase 2 discovery tool contracts for Debian/Nginx `/opt` runtime discovery:
  `systemd_services_discovery`, `nginx_sites_discovery`, `opt_apps_discovery`, `django_apps_discovery`,
  `gunicorn_uvicorn_services_discovery`, `postgres_status_discovery`, and `log_sources_discovery_v2`.
- Added an idempotent seeding helper that creates ToolTemplate, ToolDefinition, and inactive ToolPolicy records.
- Added a safe data migration to seed the contracts as approved/read-only but non-executable by default.
- Kept the new contracts out of current `BASELINE_TOOL_KEYS` and diagnostic allowed tools to avoid requesting runtime handlers that are not implemented yet.
- Added focused Phase 2 contract tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_tool_contracts --noinput` passed: 4 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 157 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Implement runtime handlers in later Phase 2 steps before enabling these tools or adding them to baseline/diagnostics.
- No commit or push was made.

## 2026-05-29 - Phase 2 Sprint 2.2 Start

Intent:
- Implement only the approved Sprint 2.2 runtime safe execution helper and `systemd_services_discovery` handler.

Scope:
- Add a runtime helper for fixed argv-only read-only command execution using `subprocess.run(..., shell=False)`.
- Enforce timeouts, output size caps, safe stderr capture, and redaction.
- Add `systemd_services_discovery` using fixed `systemctl` read-only commands.
- Register only this handler in the runtime executor.
- Add focused tests for safety, parsing, runtime execution routing, param rejection, and unsupported tools.

Out of scope:
- Baseline orchestration, baseline profiles, baseline ingestion, `DiscoveredService` updates, ToolPolicy/PlanTool activation, enabling migrations, other Phase 2 handlers, AI planner, external bot, remediation/actions, shell execution, raw unit file reads, raw `ExecStart`, and raw `Environment=...`.

Result:
- Added `scanner_runtime/safe_exec.py` with fixed argv-list command execution, `subprocess.run(..., shell=False)`, timeout enforcement, output cap enforcement, and redacted stderr handling.
- Added `systemd_services_discovery` runtime parsing and collection using fixed read-only `systemctl` commands only.
- Added structured `services` and `summary` output with safe fields only.
- Registered only `systemd_services_discovery` in the runtime executor; runtime still creates no ToolRun or AgentJob.
- Added focused Sprint 2.2 tests for safe execution, parser behavior, enabled-state merge, runtime routing, param rejection, and unsupported tool rejection.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_systemd_discovery --noinput` passed: 12 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 171 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Baseline/profile/ingestion integration and ToolPolicy/PlanTool activation remain deferred.
- No commit or push was made.

## 2026-05-31 - Phase 2 Sprint 2.8 Hotfix Start

Intent:
- Tighten `log_sources_discovery_v2` `/opt` log discovery after server smoke testing showed noisy internal/heavy directories and missing app log candidates.

Scope:
- Skip hidden/heavy/internal directories under `/opt` during log source candidate discovery.
- Emit `/opt/*/logs` and `/opt/*/*/logs` candidates only when the logs path exists.
- Preserve fixed system log candidates even when missing.
- Preserve realpath escape protection for `/opt` log paths.
- Add focused regression tests.

Out of scope:
- Baseline/profile/ingestion changes, ToolPolicy/PlanTool activation, migrations, other runtime handlers, AI planner, external bot, log content reads, and findings generation.

Result:
- Updated `/opt` log source discovery to skip hidden/heavy/internal directories:
  `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `.cache`, `.config`, `.npm`, `.tox`, `tests`, `docs`, `static`, `staticfiles`, `templates`, `scripts`, `skills`, `dist`, `build`, `tmp`.
- Stopped emitting missing `/opt/*/logs` and `/opt/*/*/logs` candidates.
- Kept fixed system candidates emitted even when missing.
- Preserved `/opt` realpath escape validation for app log paths.
- Added regression tests for hidden/heavy/missing app log paths and fixed system missing paths.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_log_sources_discovery_v2 --noinput` passed: 18 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 257 tests (4 skipped).
- `git diff --check` passed with line-ending warnings only.

Remaining:
- No commit or push was made.

## 2026-05-31 - Phase 2 Sprint 2.8 Start

Intent:
- Implement only the approved Sprint 2.8 runtime `log_sources_discovery_v2` collector.

Scope:
- Add `scanner_runtime/log_sources_discovery_v2.py` with pure filesystem metadata collection (no content reads, no shell commands).
- Allow only fixed candidates:
  - `/var/log/nginx`
  - `/var/log/postgresql`
  - `/var/log/syslog`
  - `/var/log/messages`
  - `/opt/*/logs`
  - `/opt/*/*/logs`
- Return only safe metadata fields and contract-compatible top-level keys: `log_sources`, `summary`.
- Reject non-empty params.
- Register only `log_sources_discovery_v2` in runtime executor.
- Add focused Sprint 2.8 tests.

Out of scope:
- Baseline/profile/ingestion changes, ToolPolicy/PlanTool activation, migrations, other runtime handlers, AI planner, external bot, `journalctl`, `systemctl`, service correlation, unit file reads, log parsing, and findings generation.

Result:
- Added `scanner_runtime/log_sources_discovery_v2.py` implementing `collect_log_sources_v2(params=None)` with pure filesystem metadata only.
- Added fixed allowlisted candidates only:
  - `/var/log/nginx`
  - `/var/log/postgresql`
  - `/var/log/syslog`
  - `/var/log/messages`
  - `/opt/*/logs`
  - `/opt/*/*/logs`
- Collected safe metadata fields only: `path`, `type`, `exists`, `is_dir`, `size_bytes`, `modified_at`, `metadata.source`.
- Added path canonicalization and allowlist enforcement for `/opt` patterns.
- Enforced params rejection, graceful `OSError/PermissionError` handling, redacted strings, and output cap.
- Registered only `log_sources_discovery_v2` in `scanner_runtime/prototype.py`.
- Added focused Sprint 2.8 tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_log_sources_discovery_v2 --noinput` passed: 12 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 251 tests (4 skipped).
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Baseline/profile/ingestion integration and ToolPolicy/PlanTool activation remain deferred.
- No commit or push was made.

## 2026-05-30 - Phase 2 Sprint 2.4 Start

Intent:
- Implement only the approved Sprint 2.4 runtime `opt_apps_discovery` collector for Debian/Nginx `/opt` servers.

Scope:
- Add `scanner_runtime/opt_discovery.py` as a pure file-reading runtime collector rooted at `/opt` only (max depth 2), with strict caps.
- Use presence-based framework detection for Django/Python, Node, and Laravel/PHP without reading source files.
- Optionally extract only a safe project name from size-capped `pyproject.toml`, `package.json`, and `composer.json`.
- Reject non-empty params.
- Register only `opt_apps_discovery` in the runtime executor.
- Add focused unit tests for traversal, symlink safety, framework detection, safe name extraction, and output safety.

Out of scope:
- Baseline orchestration, baseline profiles, baseline ingestion, any DB writes from runtime, ToolPolicy/PlanTool activation, migrations, other Phase 2 handlers, AI planner, external bot, remediation/actions, and shell command execution.

Result:
- Added `scanner_runtime/opt_discovery.py` as a pure file-reading runtime collector rooted at `/opt` only.
- Added max-depth-2 candidate discovery, strict caps, symlink realpath validation under `/opt`, heavy/hidden directory skipping, marker-based framework detection, safe project-name extraction, redaction, and JSON output cap enforcement.
- Returned `applications` and `summary` only, matching the Phase 2 ToolDefinition contract.
- Registered only `opt_apps_discovery` in the runtime executor; runtime still creates no ToolRun or AgentJob.
- Added focused Sprint 2.4 tests.
- Fixed candidate handling so directories without detection markers are not appended as applications, deduped by resolved realpath, and corrected the `pyproject.toml` name regex.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected; database connection timeout warning only.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_opt_apps_discovery --noinput` passed: 13 tests ran successfully with 2 symlink tests skipped in this Windows environment.
- `.\.venv\Scripts\python.exe manage.py test --noinput` was blocked by PostgreSQL connection timeout while creating the test database.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Re-run the full test suite once the local PostgreSQL test database connection is available.
- Baseline/profile/ingestion integration and ToolPolicy/PlanTool activation remain deferred.
- No commit or push was made.

## 2026-05-30 - Phase 2 Sprint 2.5 Start

Intent:
- Implement only the approved Sprint 2.5 runtime `django_apps_discovery` collector for safe Django application metadata under `/opt`.

Scope:
- Add `scanner_runtime/django_discovery.py` as a pure filesystem runtime collector rooted at `/opt` only (max depth 2), with strict caps.
- Detect Django application roots using `manage.py` or strong project-root markers plus Django indicators.
- Treat `wsgi.py`, `asgi.py`, `urls.py`, and `apps.py` as supporting markers only.
- Suppress nested Django package false positives when an ancestor is already selected as a Django root.
- Optionally read only size-capped `pyproject.toml` for a safe project name.
- Reject non-empty params.
- Register only `django_apps_discovery` in the runtime executor.
- Add focused unit tests for detection, nested package suppression, symlink safety, output safety, and unsupported tool behavior.

Out of scope:
- Baseline orchestration, baseline profiles, baseline ingestion, `Application` DB writes, ToolPolicy/PlanTool activation, migrations, other Phase 2 handlers, AI planner, external bot, remediation/actions, and shell command execution.

Result:
- Added `scanner_runtime/django_discovery.py` as a pure filesystem runtime collector rooted at `/opt` only.
- Added max-depth-2 candidate scanning, symlink realpath validation under `/opt`, heavy/hidden directory skipping, strict stat/output caps, and redacted JSON output.
- Added Django root detection using `manage.py` or strong project-root markers plus Django indicators.
- Treated `wsgi.py`, `asgi.py`, `urls.py`, and `apps.py` as supporting markers only.
- Suppressed nested Django package false positives when an ancestor is already selected as a Django root.
- Registered only `django_apps_discovery` in the runtime executor; runtime still creates no ToolRun or AgentJob.
- Added focused Sprint 2.5 tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_django_apps_discovery --noinput` passed: 15 tests ran successfully with 2 symlink tests skipped in this Windows environment.
- `.\.venv\Scripts\python.exe manage.py test --noinput` ran 200 tests before failing in `tests.unit.test_sprint8_diagnostics.Sprint8DiagnosticsTests.setUpClass` due to PostgreSQL connection timeout.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Re-run the full test suite once the local PostgreSQL test database connection is stable.
- Baseline/profile/ingestion integration and ToolPolicy/PlanTool activation remain deferred.
- No commit or push was made.

## 2026-05-31 - Phase 2 Sprint 2.6 Start

Intent:
- Implement only the approved Sprint 2.6 runtime `gunicorn_uvicorn_services_discovery` collector.

Scope:
- Add `scanner_runtime/gunicorn_uvicorn_discovery.py` using fixed `systemctl list-units` and capped `systemctl show` execution through `safe_exec.py`.
- Reject non-empty params.
- Detect `gunicorn`, `uvicorn`, and `daphne` from safe fields only (unit Id and redacted Description).
- Return only safe structured metadata and contract-compatible top-level keys: `services`, `applications`, and `summary`.
- Register only `gunicorn_uvicorn_services_discovery` in the runtime executor.
- Add focused unit tests for parsing, safety, redaction, and runtime routing behavior.

Out of scope:
- Baseline orchestration, baseline profiles, baseline ingestion, ToolPolicy/PlanTool activation, migrations, other runtime handlers, AI planner, external bot, Supervisor support, port correlation, unit file content parsing, `/proc/<pid>/cmdline`, and any write/restart actions.

Result:
- Added `scanner_runtime/gunicorn_uvicorn_discovery.py` with a safe two-step discovery flow:
  - fixed `systemctl list-units --type=service --all --no-pager --plain --no-legend`
  - fixed capped `systemctl show <unit names> --property=Id,Description,LoadState,ActiveState,SubState,UnitFileState,MainPID,FragmentPath,User,WorkingDirectory`
- Enforced unit cap before `systemctl show` and rejected non-empty params.
- Added safe parsing for `gunicorn`, `uvicorn`, and `daphne` from unit Id + redacted Description only.
- Excluded unsafe fields and sources (`ExecStart`, `Environment`, unit file contents, `/proc/<pid>/cmdline`).
- Returned only contract-compatible top-level keys: `services`, `applications`, `summary`.
- Registered only `gunicorn_uvicorn_services_discovery` in `scanner_runtime/prototype.py`.
- Added focused Sprint 2.6 tests.

Verification:
- `python manage.py check` failed locally because shell `python` is not using the project venv and cannot import Django.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` failed for the same shell `python` reason.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected and a database timeout warning.
- `python manage.py test tests.unit.test_phase2_gunicorn_uvicorn_services_discovery --noinput` failed for the same shell `python` reason.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_gunicorn_uvicorn_services_discovery --noinput` passed: 11 tests ran successfully.
- `python manage.py test --noinput` failed for the same shell `python` reason.
- `.\.venv\Scripts\python.exe manage.py test --noinput` ran 216 tests before failing in `tests.unit.test_sprint2_agent_foundation.Sprint2AgentFoundationTests.setUpClass` due to PostgreSQL connection timeout.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Re-run full suite after local PostgreSQL test connection is stable.
- Baseline/profile/ingestion integration and ToolPolicy/PlanTool activation remain deferred.
- No commit or push was made.

## 2026-05-31 - Phase 2 Sprint 2.7 Start

Intent:
- Implement only the approved Sprint 2.7 runtime `postgres_status_discovery` collector.

Scope:
- Add `scanner_runtime/postgres_discovery.py` with fixed-command discovery via `safe_exec.py`:
  - `systemctl list-units --type=service --all --no-pager --plain --no-legend`
  - capped `systemctl show <unit names> --property=Id,Description,LoadState,ActiveState,SubState,UnitFileState,MainPID,FragmentPath`
- Parse safe PostgreSQL service variants (`postgresql.service`, `postgresql@*.service`, obvious distro variants).
- Add optional fixed `pg_isready` probe (no host/user/db/password args), normalized to `ok|failed|not_available`.
- Reject non-empty params.
- Register only `postgres_status_discovery` in runtime executor.
- Add focused unit tests and run requested validation commands.

Out of scope:
- Baseline/profile/ingestion changes, ToolPolicy/PlanTool activation, migrations, other runtime handlers, AI planner, external bot, `psql`/SQL queries, `.pgpass`, connection strings, config file reads, and port inspection.

Result:
- Added `scanner_runtime/postgres_discovery.py` implementing `collect_postgres_status(params=None)`.
- Implemented safe fixed-command flow via `safe_exec.py`:
  - `systemctl list-units --type=service --all --no-pager --plain --no-legend`
  - capped `systemctl show <unit names> --property=Id,Description,LoadState,ActiveState,SubState,UnitFileState,MainPID,FragmentPath`
  - optional fixed `pg_isready` probe normalized to `ok|failed|not_available`.
- Added safe parsing for PostgreSQL units (`postgresql.service`, `postgresql@*.service`, obvious variants).
- Returned contract-compatible top-level keys only: `services`, `summary`.
- Added strict safety behavior: reject non-empty params, no raw diagnostics with secret-like key names, no `psql`, no config reads, no credentials, no connection strings.
- Registered only `postgres_status_discovery` in `scanner_runtime/prototype.py`.
- Added focused Sprint 2.7 tests.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_postgres_status_discovery --noinput` passed: 9 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 239 tests (4 skipped).
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Baseline/profile/ingestion integration and ToolPolicy/PlanTool activation remain deferred.
- No commit or push was made.

## 2026-05-30 - Phase 2 Sprint 2.3 Start

Intent:
- Implement only the approved Sprint 2.3 runtime `nginx_sites_discovery` collector.

Scope:
- Add a pure file-reading Nginx discovery runtime module.
- Read only `/etc/nginx/nginx.conf`, direct files under `/etc/nginx/sites-enabled/*`, and direct `*.conf` files under `/etc/nginx/conf.d/*.conf`.
- Handle safe symlinks from `sites-enabled` only when resolved targets remain under allowlisted Nginx roots.
- Parse safe server block metadata without storing raw config text.
- Register only `nginx_sites_discovery` in the runtime executor.
- Add focused tests for parsing, safety, symlink behavior, params rejection, and unsupported tool behavior.

Out of scope:
- Baseline orchestration, baseline profiles, baseline ingestion, `DiscoveredDomain`, `Application`, or `LogSource` writes, ToolPolicy/PlanTool activation, migrations, other Phase 2 handlers, AI planner, external bot, remediation/actions, and shell command execution.

Result:
- Added `scanner_runtime/nginx_discovery.py` as a pure file-reading runtime collector.
- Added code-defined Nginx config sources, safe source validation, safe symlink handling, per-file size cap, and total scanned bytes cap.
- Added Nginx `server` block parsing for safe `server_name`, `listen`, `root`, `access_log`, `error_log`, and `proxy_pass` metadata.
- Ignored cert/key/auth directives, rejected variable filesystem paths, dropped credentialed/variable proxy targets, and avoided returning raw config text.
- Registered only `nginx_sites_discovery` in the runtime executor; runtime still creates no ToolRun or AgentJob.
- Added focused Sprint 2.3 tests for parsing, safety, symlink behavior via read validation outcomes, include flagging, params rejection, and unsupported tool behavior.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_phase2_nginx_sites_discovery --noinput` passed: 12 tests ran successfully.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 185 tests ran successfully.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- Baseline/profile/ingestion integration and ToolPolicy/PlanTool activation remain deferred.
- No commit or push was made.
## 2026-06-05 - Corrected Execution Plan Remote Bootstrap Update Start

Intent:
- Update only `docs/planning/CORRECTED-EXECUTION-PLAN.md` with the approved planning corrections.

Scope:
- Add Remote Bootstrap Runtime Completion as a standalone planning/implementation sprint.
- Clarify the current Remote Bootstrap foundation versus the remaining runtime bundle gap.
- Change the first full tool cycle away from `laravel_env_sanity` as the initial preferred tool.
- Clarify the dependency between C5 Tool Orchestrator and C6 Safe Command Execution Runtime.

Out of scope:
- Code, migrations, tests, runtime/service/model changes, and any server execution.

Result:
- Updated `docs/planning/CORRECTED-EXECUTION-PLAN.md` only.
- Added Sprint C1.5 / Phase 0.5: Remote Bootstrap Runtime Completion.
- Documented that the current Remote Bootstrap foundation exists, but the installed bundle is still `sprint3-bootstrap-runtime` with registration + heartbeat only.
- Clarified that C5 Tool Orchestrator can use existing safe execution paths only, and command/script template execution waits for C6.
- Changed C8 first preferred tool to `laravel_log_health` or `apache_5xx_summary`, with `laravel_env_sanity` deferred until safety controls are proven.

Verification:
- `git diff --check` passed with line-ending warnings only.
- No code, migrations, tests, runtime/service/model changes, or server execution were performed.
## 2026-06-05 - Decision Register Documentation Start

Intent:
- Create an official decision register for the corrected execution plan.

Scope:
- Add `docs/planning/DECISION-REGISTER.md`.
- Capture approved Sprint decisions, deferred decisions, and guardrails requiring explicit approval.
- Update tracking documentation only.

Out of scope:
- Code, migrations, tests, runtime/service/model changes, and server execution.

Result:
- Created `docs/planning/DECISION-REGISTER.md`.
- Captured the approved corrected execution decisions across C1 through C12.
- Captured deferred decisions and guardrails requiring explicit approval to change.

Verification:
- `git diff --check` passed with line-ending warnings only.
- No code, migrations, tests, runtime/service/model changes, or server execution were performed.

## 2026-06-05 - Sprint C2 Safe Context Builder MVP Start

Intent:
- Implement the approved `Sprint C2 - Safe Context Builder MVP`.

Scope:
- Add a dedicated `apps.ai_context` app.
- Add a deterministic safe context builder service that returns versioned, capped, redacted JSON.
- Include safe account, server, baseline, applications, services, domains, logs, findings, reports, knowledge, recommendations, recent ToolRun metadata, risk summary, and available tools metadata.
- Enforce tenant scope, role-aware tool availability, ToolPolicy/PlanTool checks, and no raw output exposure.
- Add focused unit tests.

Out of scope:
- Chat UI/models, live AI providers, tool execution, direct AgentJob creation, Telegram behavior, remediation/actions, and report redesign.

Result:
- Added `apps.ai_context` with `build_safe_context()`.
- Registered `apps.ai_context` in `INSTALLED_APPS`.
- Safe context output now includes `context_version`, metadata, capped summaries, recent ToolRun metadata without raw results, and policy-aware available tool metadata.
- Added redaction and tenant-scope safeguards before returning context.
- Added focused tests for account scoping, redaction, raw output exclusion, tool availability, caps, and safe summary fields.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_safe_context_builder --noinput` passed: 6 tests.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 300 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Testing note:
- Full suite was run for Sprint C2 because this sprint touches security-sensitive redaction, permissions, and tenant-scoped context behavior.

## 2026-06-05 - Sprint C3 Admin Chat Data Model and Read-only UI Start

Intent:
- Implement the approved `Sprint C3 - Admin Chat Data Model and Read-only UI`.

Scope:
- Add dedicated `apps.ai_chat` app.
- Add `AdminChatSession`, `AdminChatMessage`, and `AdminChatDecision` models.
- Add Portal read-only/basic chat screens for account-scoped owner/operator use.
- Store redacted messages and metadata only.
- Prevent tool execution, ToolRun creation, AgentJob creation, live AI calls, and Telegram behavior.
- Add focused tests for permissions, tenant scope, redaction, and no execution side effects.

Out of scope:
- Deterministic responder logic, live AI provider calls, tool orchestration, reports from chat, Telegram, remediation/actions, and any direct AgentJob creation.

Result:
- Added dedicated `apps.ai_chat` app.
- Added `AdminChatSession`, `AdminChatMessage`, and `AdminChatDecision` models with redacted fields and account/server/application scope validation.
- Added Django Admin registration for review of redacted chat records.
- Added Portal chat list/detail/start/message routes and templates.
- Owner/operator can start sessions and save user messages; viewer can view but cannot start or post.
- Chat MVP stores user messages only and creates no ToolRun or AgentJob.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_chat --noinput` passed: 7 tests.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected after the intended migration was created.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint6_portal --noinput` passed: 16 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 307 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Testing note:
- Full suite was run for Sprint C3 because this sprint changes Portal permissions, redaction-sensitive chat storage, and tenant-scoped access behavior.

## 2026-06-05 - Sprint C4 Deterministic Chat Responder Start

Intent:
- Implement the approved `Sprint C4 - Deterministic Chat Responder`.

Scope:
- Add deterministic context-only chat responses for status, summaries, findings, reports, and available tools.
- Store response decisions in `AdminChatDecision`.
- Store assistant replies as redacted `AdminChatMessage` records.
- Rebuild safe context when responding and store only capped/redacted decision output.

Out of scope:
- Live AI provider calls, tool execution, ToolRun/AgentJob creation, Telegram, report generation from chat, and remediation/actions.

Result:
- Added deterministic intent routing for status, findings, reports, available tools, and general summary questions.
- Added context-only assistant response generation using `build_safe_context()`.
- Added `AdminChatDecision` logging for deterministic answer decisions.
- Updated Portal chat message POST to save the user message and generate an assistant response.
- Kept C4 free of live AI, ToolRun creation, AgentJob creation, Telegram, and remediation behavior.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_chat --noinput` passed: 10 tests.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint6_portal --noinput` passed: 16 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 310 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Testing note:
- Full suite was run for Sprint C4 because this sprint changes Portal chat behavior, decision logging, redaction-sensitive response storage, and permission-protected message flow.

## 2026-06-05 - Sprint C5 Tool Orchestrator MVP Start

Intent:
- Implement the approved `Sprint C5 - Tool Orchestrator MVP`.

Scope:
- Add chat tool request model and service flow.
- Allow owner/operator to request and approve existing available read-only tools only.
- Route execution only through `create_tool_run_job()` so ToolDefinition, ToolPolicy, PlanTool, ToolRun, and AgentJob checks remain authoritative.
- Keep MVP params empty only to avoid arbitrary parameter submission in C5.
- Add focused tests for policy denial, plan denial, approval permissions, and no direct AgentJob creation.

Out of scope:
- Command/script template execution, live AI, arbitrary params, new tools, report generation, Telegram, remediation/actions, and direct AgentJob creation.

Result:
- Added `AdminChatToolRequest`.
- Added request and approval services for available chat tools.
- Approval calls existing `create_tool_run_job()` only, preserving ToolDefinition, ToolPolicy, PlanTool, ToolRun, and AgentJob enforcement.
- Added minimal Portal UI for requesting and approving tools from server-scoped chat sessions.
- Kept C5 parameterless for chat tool requests and did not add command/script template execution.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_chat --noinput` passed: 16 tests.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected after the intended migration was created.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint6_portal tests.unit.test_sprint4_tools_policy --noinput` passed: 31 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 316 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Testing note:
- Full suite was run for Sprint C5 because this sprint touches the ToolRun/AgentJob execution path and permission/policy enforcement.
- An initial regression command used a non-existent test module name; it was corrected to `tests.unit.test_sprint4_tools_policy` and rerun successfully.

## 2026-06-05 - Sprint C6 Safe Command Execution Runtime Start

Intent:
- Implement the approved `Sprint C6 - Safe Command Execution Runtime`.

Scope:
- Add command-template execution metadata to tool registry models.
- Add safe AgentJob execution payload for command-template jobs.
- Execute command templates in runtime using argv-only `safe_exec` with `shell=False`.
- Enforce allowed binaries, blocked tokens, timeout, output cap, redaction, exit code, execution time, and truncated flag.
- Keep runtime-handler tools supported.

Out of scope:
- `script_template`, shell execution, arbitrary commands, new tool activation, Tool Builder integration, Telegram, live AI, remediation/actions, and report changes.

Result:
- Added `execution_type`, command argv template, allowed binaries, and blocked tokens to ToolTemplate and ToolDefinition.
- Added `AgentJob.execution_payload` for runtime-safe execution metadata.
- Added command-template payload construction in `create_tool_run_job()`.
- Added runtime `command_templates` executor using `safe_exec.run_fixed_command(..., shell=False)`.
- Enhanced `safe_exec` with execution time and optional truncation metadata while preserving old behavior by default.
- Kept `script_template` denied and runtime-handler tools supported.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c6_command_templates --noinput` passed: 8 tests.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected after intended migrations.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint4_tools_policy tests.unit.test_sprint2_agent_foundation tests.unit.test_sprint3_bootstrap tests.unit.test_phase2_systemd_discovery --noinput` passed: 54 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 324 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Testing note:
- Full suite was run for Sprint C6 because this sprint changes runtime, job execution payloads, and security enforcement.

## 2026-06-05 - Sprint C7 Tool Builder from Chat Start

Intent:
- Implement the approved `Sprint C7 - Tool Builder from Chat`.

Scope:
- Allow chat to create `ToolBuildRequest` and `ToolBuildProposal` for `command_template` only.
- Keep proposals draft/review-only and inactive.
- Add safe validation for argv-only command template proposals.
- Link chat-created builder requests back to the originating session/message.

Out of scope:
- Tool execution, ToolRun creation, AgentJob creation, automatic enablement, `script_template`, runtime-handler code generation, live AI, Telegram, and remediation/actions.

Result:
- Extended `ToolBuildRequest` with `command_template` proposal metadata and optional chat trace fields.
- Added chat service flow to create `ToolBuildRequest` and `ToolBuildProposal` from Portal chat.
- Extended Tool Builder generator, validator, and converter to support safe `command_template` proposals without breaking existing `runtime_handler` behavior.
- Added minimal chat UI for creating tool builder proposals and viewing their status.
- Kept proposals inactive and review-only; no ToolRun or AgentJob is created by this flow.

Verification:
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint10_tool_builder --noinput` passed: 18 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_chat --noinput` passed: 19 tests.
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected after intended migration.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_chat tests.unit.test_sprint10_tool_builder tests.unit.test_sprint_c6_command_templates --noinput` passed: 45 tests.
- `git diff --check` passed with line-ending warnings only.

Testing note:
- Full suite was not run for Sprint C7 because this sprint did not change runtime execution semantics or agent/job security paths directly.
- Focused regression was run against chat, tool builder, and C6 command-template validation/runtime compatibility.

## 2026-06-05 - Sprint C8 First Laravel/Apache Tool Cycle Start

Intent:
- Implement the approved `Sprint C8 - First Laravel/Apache Tool Cycle`.

Scope:
- Prove the first end-to-end chat-driven commercial tool cycle using a safe `command_template`.
- Use `apache_5xx_summary` as the first tool under DR-013.
- Keep outputs limited to counters and safe summaries only.
- Connect chat request, policy-checked execution, safe runtime result capture, and deterministic explanation.

Out of scope:
- `laravel_env_sanity`.
- Raw log display or storage.
- `script_template`.
- Live AI providers.
- Telegram changes.
- Remediation, write, restart, reload, or destructive actions.

Result:
- Added explicit pilot enablement for one approved read-only `command_template` tool through `enable_command_template_pilot_tool`.
- Added safe tool-result summarization for `apache_5xx_summary`.
- Synced terminal `ToolRun` status back into linked chat tool requests and posted a safe assistant summary into the chat thread.
- Extended safe context and deterministic chat responses so recent tool results can be explained without exposing raw command output.
- Added escaped-brace support for argv templates so safe fixed `awk` expressions can be rendered without enabling free-form shell behavior.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c8_first_tool_cycle --noinput` passed: 7 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 338 tests, 4 skipped.
- `git diff --check` passed with line-ending warnings only.

Testing note:
- Full suite was run for Sprint C8 because this sprint touched tool execution, AgentJob-to-ToolRun result propagation, chat-visible security boundaries, and policy-backed customer tool execution.

## 2026-06-05 - Sprint C9 Reports from Chat Start

Intent:
- Implement the approved `Sprint C9 - Reports from Chat`.

Scope:
- Add a safe draft/review flow for chat-generated reports.
- Prefer `AdminChatReportDraft`.
- Support separate `technical/internal` and `customer_summary` report drafts.
- Keep all content deterministic, redacted, and based on safe summaries only.

Out of scope:
- Raw ToolRun or AgentJob output.
- Raw logs or raw `.env`.
- PDF export.
- Live AI providers.
- Telegram changes.

Result:
- Added `AdminChatReportDraft` as the review-first chat report model.
- Added deterministic draft generation for `technical_internal` and `customer_summary`.
- Added Matrix Admin review and conversion flow from chat draft to final `Report`.
- Extended Portal chat with minimal report-draft creation and history visibility.
- Kept all draft and final report content limited to safe summaries and redacted sections only.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations ai_chat reports` generated only the intended migrations.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c9_chat_reports --noinput` passed: 9 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c9_chat_reports tests.unit.test_admin_chat tests.unit.test_sprint11_reports --noinput` passed: 38 tests.
- `.\.venv\Scripts\python.exe manage.py test --noinput` passed: 347 tests, 4 skipped.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `git diff --check` passed with line-ending warnings only.

Testing note:
- Full suite was run for Sprint C9 because this sprint changed report redaction, report visibility, review conversion, and Portal permissions around chat-generated reports.

## 2026-06-06 - Chat Report Rendering Fix Start

Intent:
- Apply a narrow fix so final chat-generated reports render readable summaries instead of raw dict/list payloads.

Scope:
- Limit changes to `technical_internal` and `customer_summary` chat report draft/report conversion rendering.
- Keep report approval flow, tool execution, safe context schema, and policies unchanged.

Out of scope:
- ToolRun or AgentJob execution changes.
- Safe Context schema changes.
- Telegram, live AI, or migrations unless unexpectedly required.

Result:
- Reworked chat-report section generation so `technical_internal` and `customer_summary` use readable multiline summaries instead of dict/list payload bodies.
- Removed structured payloads from chat-generated final report section `data_redacted` where they were only being shown as raw objects in Portal.
- Kept technical detail available as readable lines for status, profile, findings, and recent tool activity.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c9_chat_reports --noinput` passed: 11 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c9_chat_reports tests.unit.test_admin_chat tests.unit.test_sprint11_reports --noinput` passed: 40 tests.
- `git diff --check` passed with line-ending warnings only.

Testing note:
- Full suite was not run for this fix because the change stayed inside chat-report rendering and conversion output formatting.
- Focused regression was run against chat reports, admin chat, and report services because this fix touched report redaction presentation and conversion output only.

## 2026-06-06 - Sprint C10.5 Chat Responsibility Split Start

Intent:
- Implement the approved corrective sprint that separates Matrix Admin internal chat from Customer Portal chat.

Scope:
- Add a clear internal/admin versus portal/customer distinction in chat sessions and services.
- Remove Tool Builder creation from Portal chat.
- Keep Portal chat limited to safe context, approved read-only tool requests, and self-service customer-safe reports.
- Add a minimal staff-only internal chat UI that reuses existing `apps.ai_chat` logic for messages, tool builder proposals, and internal reports.
- Preserve existing policy-backed ToolRun/AgentJob execution flow and manual report approval flow for sensitive/manual cases.

Out of scope:
- Live AI providers.
- Telegram.
- Remediation/write/destructive tools.
- Raw logs, raw `.env`, credentials, raw ToolRun output, or raw AgentJob output.
- Runtime/tool execution policy changes beyond existing approved paths.

Testing note:
- Run focused regressions for admin chat, portal chat, tool builder, reports, and tool result summary.
- Escalate to full suite because this sprint changes permissions, report conversion behavior, and chat-visible execution flows.

Result:
- Added explicit `portal_customer` versus `admin_internal` chat session channels.
- Removed Tool Builder creation paths from Portal chat UI and routing.
- Added a staff-only internal chat UI under `/admin/internal-chat/`.
- Restricted chat Tool Builder proposal creation to internal admin chat only.
- Kept Portal chat limited to safe context, approved read-only tool requests, and immediate customer-safe reports.
- Added immediate safe chat report conversion for Portal customer summaries and Matrix Admin internal reports.
- Preserved the manual draft review/conversion flow for internal review cases.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations ai_chat` created the intended migration for `AdminChatSession.channel`.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no extra changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c10_5_chat_split --keepdb --noinput` passed: 5 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_admin_chat --keepdb --noinput` passed: 20 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c9_chat_reports --keepdb --noinput` passed: 12 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint10_tool_builder --keepdb --noinput` passed: 18 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint6_portal --keepdb --noinput` passed: 16 tests.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c8_first_tool_cycle --keepdb --noinput` passed: 7 tests.
- `.\.venv\Scripts\python.exe manage.py test --keepdb --noinput` passed: 356 tests, 4 skipped.

Remaining:
- Sprint C10.5 is complete within the approved scope.
- No live AI, Telegram, remediation/write/destructive tools, raw outputs, or policy bypasses were added.

## 2026-06-07 - C10.5-B Admin Internal Chat UX and Navigation Fix Start

Intent:
- Improve the discoverability and usability of the staff-only internal chat added in C10.5.

Scope:
- Add a clear Internal Chat entry point inside Django Admin.
- Improve the internal chat templates so they read as a usable Matrix Admin chatbot surface.
- Keep Portal chat without Tool Builder and keep internal chat staff-only.

Out of scope:
- Live AI.
- Telegram.
- Tool Builder restoration in Portal.
- Business-logic expansion beyond minor view/template glue if strictly needed.

Result:
- Added a clear `Internal Chat` entry to the Django Admin index.
- Reworked the internal chat list page into a clearer two-panel admin workspace.
- Reworked the internal chat detail page into a chat-like layout with distinct sections for messages, tool requests, Tool Builder, and reports.
- Preserved Portal chat without Tool Builder and kept internal chat staff-only.

Verification:
- `.\.venv\Scripts\python.exe manage.py check` passed.
- `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` passed with no changes detected.
- `.\.venv\Scripts\python.exe manage.py test tests.unit.test_sprint_c10_5_chat_split tests.unit.test_admin_chat --keepdb --noinput` passed: 26 tests.
- `git diff --check` passed with line-ending warnings only.

Remaining:
- C10.5-B is complete within the approved scope.
- No live AI, Telegram, Tool Builder-in-Portal, runtime, or policy changes were introduced.
## 2026-06-25 - C10.9-A AI Read-Only Tool Request Flow Start

Intent:
- Add a safe Admin Live AI read-only tool request proposal flow that requires explicit staff approval before any ToolRun or AgentJob is created.

Scope:
- Parse hidden internal tool proposals from Live AI assistant output.
- Validate proposals against an explicit read-only allowlist and existing ToolPolicy/plan/server guardrails.
- Create pending AdminChatToolRequest records only for valid proposals.
- Add staff-only approve/reject handling inside Admin Internal Chat.
- Add a dry-run/apply management command for stale legacy pending Live AI audit cleanup.

Out of scope:
- Direct AI tool execution, auto-approval, write/destructive/remediation tools, arbitrary shell, uploads, Portal AI, Telegram AI, customer-facing AI, and subscription/payment changes.

Result:
- Added hidden Live AI tool proposal parsing with display/storage stripping for `<TOOL_REQUEST_PROPOSAL>` blocks.
- Added an explicit first-phase read-only allowlist and validation against existing ToolDefinition, ToolPolicy, PlanTool, server status, and active scanner-agent execution path.
- Created `AdminChatToolRequest` records only for valid Live AI proposals; no ToolRun or AgentJob is created until staff approval.
- Added staff-only approve/reject UI flow in Admin Internal Chat; rejection maps to the existing cancelled status and creates no execution objects.
- Added `cleanup_live_ai_legacy_test_data` with dry-run default and explicit `--apply` for stale pending Live AI audit rows.

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

Remaining:
- C10.9-B can add safe result summarization back into AI chat if needed.
## 2026-06-25 - C10.9-H1 Auto-Execute Approved Read-Only Tools with Result Follow-up Start

Intent:
- Change valid Live AI read-only tool proposals from pending approval to automatic execution through the existing policy-backed ToolRun/AgentJob path, then add a bounded result follow-up message.

Scope:
- Auto-execute only allowlisted, enabled, read-only tools permitted by ToolPolicy and PlanTool for the selected server.
- Add backend polling for a short bounded period after ToolRun/AgentJob creation.
- Add safe chat follow-up for succeeded, failed, timed-out, or not-started execution states.
- Update Live AI instructions so it does not ask the admin to wait unless backend execution and follow-up are actually queued.

Out of scope:
- Write/destructive/remediation tools, arbitrary shell, uploads, Portal AI, Telegram AI, customer-facing AI, and any Portal/customer deterministic behavior changes.

Result:
- Valid Live AI read-only tool proposals now create `AdminChatToolRequest`, immediately queue ToolRun/AgentJob through the existing `create_tool_run_job()` policy path, and store a start message only after execution records exist.
- Added bounded follow-up polling via `wait_for_tool_execution_result()` with safe succeeded, failed, timeout, and not-started chat summaries.
- Updated Live AI instructions so it does not tell the admin to wait or claim completion unless backend execution/follow-up confirms state.
- Preserved allowlist, ToolPolicy, PlanTool, server scoping, no raw proposal JSON, and no raw unsafe output in transcripts.

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

Remaining:
- C10.9-H1 is complete within scope.
## 2026-06-25 - C10.9-H2 Tool Execution Completion Loop Start

Intent:
- Ensure every Live AI-triggered read-only ToolRun produces a visible completion/failure/timeout follow-up in the same ChatKit lifecycle, and remove stale explicit-approval UI copy.

Scope:
- Stream tool start and final follow-up items back to ChatKit after actual ToolRun/AgentJob creation.
- Keep saved final result messages in history with explicit result metadata.
- Support multiple proposal blocks in one Live AI response with a combined final explanation.
- Update Admin Live AI header copy to the current auto-execution behavior.

Out of scope:
- Write/destructive/remediation tools, arbitrary commands, uploads, Portal AI, Telegram AI, customer-facing AI, migrations, and tool policy expansion.

Result:
- Streamed Live AI tool start and final follow-up messages back through ChatKit in the same response lifecycle.
- Ensured saved final tool messages use explicit metadata sources: `tool_result_summary`, `tool_result_failed`, `tool_result_timeout`, or `tool_result_not_started`.
- Added `chatkit_item_id` metadata to start/final tool messages so history hydration and immediate ChatKit display stay aligned without duplicate saves.
- Added multi-tool handling with a combined final explanation for multiple proposal blocks, including partial success/failure coverage.
- Updated the Admin Live AI header to: `Safe Context only. Approved read-only tools may run automatically. No write actions, uploads, or remediation.`

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

Remaining:
- C10.9-H2 is complete within scope.
## 2026-06-26 - C10.10-H1 ChatKit Delete Thread Item Idempotency Start

Intent:
- Prevent ChatKit internal `delete_thread_item` lifecycle calls from breaking Live Admin AI streams.

Scope:
- Make missing item deletes no-op.
- Allow cleanup of empty suppressed placeholders only.
- Preserve visible admin chat history, tool result summaries, Portal, Telegram, and customer-facing behavior.

Out of scope:
- User-facing message deletion, migrations, new tool capabilities, remediation/write actions, uploads, Portal AI, and Telegram AI.

Result:
- Made `AdminChatKitStore.delete_thread_item` idempotent for ChatKit lifecycle calls.
- Missing items return safely without exception.
- Empty suppressed/internal handled placeholders are hard-deleted.
- Visible user messages, visible assistant messages, tool result summaries, and diagnostic bundle summaries are preserved and only logged internally when ChatKit asks to delete them.
- Added focused regression tests for missing deletes, placeholder cleanup, visible history preservation, and refresh history behavior.

Verification:
- `python manage.py check` failed because the global Python environment has no Django installed.
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

Remaining:
- C10.10-H1 is complete within scope.

## 2026-06-25 - C10.9-H3 Adaptive Tool Follow-up and Arabic Result Summary Start

Intent:
- Improve Live AI tool follow-up timing so near-complete ToolRuns do not show premature timeout, and make backend tool start/final messages Arabic and more useful for Arabic conversations.

Scope:
- Increase single/multi-tool wait windows and add final grace refresh before timeout.
- Improve success/failure/timeout/not-started backend chat messages in Arabic.
- Summarize safe structured ToolRun output more clearly without raw JSON, secrets, large logs, or stack traces.
- Keep multi-tool proposal execution and combined explanation behavior.

Out of scope:
- Write/destructive/remediation tools, arbitrary commands, uploads, Portal AI, Telegram AI, customer-facing AI, migrations, and production-history cleanup.

Result:
- Increased Live AI tool follow-up waits to 45 seconds for a single tool and an adaptive multi-tool window capped at 120 seconds.
- Added a final 5-second grace wait and refresh before returning timeout.
- Converted backend start/success/failure/timeout/not-started messages to Arabic user-facing wording.
- Improved safe ToolRun result summaries from structured redacted results without exposing raw JSON, secrets, large logs, or stack traces.
- Preserved multiple proposal execution, combined mixed-result explanation, and no execution from free-text tool names without proposal blocks.

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

Remaining:
- C10.9-H3 is complete within scope.
