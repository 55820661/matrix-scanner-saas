# Matrix Scanner SaaS Tool Design Skill

## Purpose
Use this skill when adding or reviewing ToolTemplates, ToolDefinitions, bootstrap tools, diagnostic tools, baseline tools, or runtime handlers.

## Tool Contract
Each ToolTemplate should define:
- `template_key`
- display name
- description
- category: baseline, diagnostic, bootstrap, reporting, or internal
- risk level
- max runtime seconds
- max output chars
- input schema
- output schema
- handler function

Each ToolDefinition should define:
- `tool_key`
- linked ToolTemplate
- version and lifecycle status
- enabled/disabled status
- risk level
- default typed parameters
- allowed roles and plan availability
- server/app compatibility where needed

## Handler Rules
- Handlers are plain Python functions or small classes.
- Handlers return structured data, not preformatted Portal or Telegram text.
- Handlers should not know whether the caller is CLI, Telegram, scheduler, or AI.
- Handlers should use scanner modules for raw collection and report modules for summaries.
- Handlers must handle missing files, missing commands, permission errors, and timeouts.
- Handlers must not accept raw command, shell, script, or raw query parameters.
- Handlers must keep output deterministic, bounded, and redaction-friendly.

## Registry Pattern
ToolTemplate code is the source of executable truth:

```text
template_key -> handler function
```

ToolDefinition rows are controlled metadata:
- enabled/disabled and lifecycle.
- display text.
- roles and plan availability.
- typed parameters.
- output type and risk metadata.
- versioning.

AgentJob should be created only after policy approval. The Scanner Runtime should reject unknown or unsupported tool keys defensively.

Tool Registry and Policy Engine foundation must be implemented before full Baseline Scan implementation. Before that foundation exists, any early agent tool must use a small hardcoded allowlist and be replaced by registry-backed execution as soon as the foundation lands.

## Bootstrap Tools
- Bootstrap tools are not customer diagnostic tools.
- Bootstrap tools are Matrix Admin only.
- Sprint 3 bootstrap tools may install/start the Scanner Runtime and verify heartbeat only.
- Package installation requires explicit Matrix Admin confirmation.
- Execution must use fixed command templates with typed parameters.
- Credentials must have TTL, encrypted storage, cleanup, and full audit.

## Policy Checks
- User permission and account ownership.
- ToolDefinition enabled and approved where required.
- Tool available in the account plan.
- Risk level is allowed for MVP.
- Parameters match schema and bounds.
- Paths are canonical and baseline-discovered or explicitly allowed.
- Runtime and output limits are set.
- Output is redacted before storage and display.
- Output is redacted before AI prompts and Telegram delivery.

## Output Rules
- Keep normal command output concise.
- Full reports are only for `generate_report`.
- Include evidence, probable cause, and suggested action for diagnostic tools.
- Do not include secrets or excessive raw logs.
- Return machine-readable fields for severity, evidence, limitations, and findings when possible.

## Testing Checklist
- Authorized invocation succeeds.
- Unauthorized invocation is denied.
- Disabled tool is denied.
- Unknown `tool_key` is denied.
- Handler failure is logged and returned as a safe error.
- Output is truncated when above the configured limit.
- Cross-account tool execution is denied.
- Unsafe params such as `command`, `shell`, `script`, and `raw_query` are denied.
- Secret values are redacted before persistence.
