from apps.core.redaction import redact_secrets


def summarize_tool_run_result(tool_run):
    if not tool_run or not isinstance(tool_run.result_redacted, dict):
        return ""
    tool_key = getattr(tool_run.tool_definition, "key", "")
    status = tool_run.status
    if tool_key == "apache_5xx_summary":
        return _summarize_apache_5xx_summary(tool_run.result_redacted, status=status)
    if status == "succeeded":
        return f"{tool_key or 'tool'} completed successfully."
    if status in {"failed", "rejected", "timeout", "cancelled"}:
        return f"{tool_key or 'tool'} did not complete successfully."
    return ""


def _summarize_apache_5xx_summary(result, *, status):
    if status != "succeeded":
        return "Apache 5xx summary did not complete successfully."
    command = ((result or {}).get("output") or {}).get("command") or {}
    stdout = redact_secrets(command.get("stdout_redacted") or "")
    truncated = bool(command.get("truncated"))
    total = 0
    files_with_matches = 0
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        count_text = line.rsplit(":", 1)[-1] if ":" in line else line
        try:
            count = int(count_text.strip())
        except (TypeError, ValueError):
            continue
        total += count
        if count > 0:
            files_with_matches += 1
    if total <= 0:
        summary = "Apache 5xx summary: no 5xx responses were found in the checked access logs."
    else:
        noun = "file" if files_with_matches == 1 else "files"
        summary = (
            f"Apache 5xx summary: {total} matching 5xx responses were found across "
            f"{files_with_matches} log {noun}."
        )
    if truncated:
        summary += " Output was truncated."
    return summary
