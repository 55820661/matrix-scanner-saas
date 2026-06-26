from apps.core.redaction import redact_secrets


MAX_CHAT_SUMMARY_LENGTH = 3000


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


def summarize_tool_result_for_chat(tool_definition, result_redacted, language="ar"):
    if language != "ar":
        return summarize_tool_run_result_like(tool_definition, result_redacted)
    result = result_redacted if isinstance(result_redacted, dict) else {}
    if not result:
        return _safe_chat_text(
            "اكتمل الفحص بنجاح، لكن النتيجة التفصيلية لا تحتوي ملخصًا قابلًا للعرض المختصر. "
            "يمكن مراجعة سجل التشغيل للتفاصيل."
        )
    tool_key = getattr(tool_definition, "key", "") or ""
    if tool_key == "apache_5xx_summary":
        return summarize_tool_run_result_like(tool_definition, result_redacted)
    if tool_key == "log_sources_discovery_v2":
        summary = _summarize_log_sources_discovery_v2_for_chat(result)
        if summary:
            return summary
    return _summarize_generic_result_for_chat(result)


def summarize_tool_run_result_like(tool_definition, result_redacted):
    fake = type("ToolRunLike", (), {"tool_definition": tool_definition, "result_redacted": result_redacted, "status": "succeeded"})
    return summarize_tool_run_result(fake)


def _safe_chat_text(value, *, limit=MAX_CHAT_SUMMARY_LENGTH):
    text = redact_secrets(str(value or "")).strip()
    if len(text) > limit:
        return f"{text[:limit]}..."
    return text


def _as_dict(value):
    return value if isinstance(value, dict) else {}


def _as_list(value):
    return value if isinstance(value, list) else []


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _format_paths(items, *, exists, limit=8):
    paths = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("exists") is not exists:
            continue
        path = _safe_chat_text(item.get("path") or "", limit=240)
        if path:
            paths.append(path)
    return paths[:limit]


def _summarize_log_sources_discovery_v2_for_chat(result):
    summary = _as_dict(result.get("summary") or _as_dict(result.get("output")).get("summary"))
    log_sources = _as_list(result.get("log_sources") or _as_dict(result.get("output")).get("log_sources"))
    if not summary and not log_sources:
        return ""
    total = _safe_int(summary.get("sources_total"))
    existing_count = _safe_int(summary.get("sources_existing"))
    missing_count = _safe_int(summary.get("sources_missing"))
    permission_denied = _safe_int(summary.get("permission_denied"))
    existing_paths = _format_paths(log_sources, exists=True)
    missing_paths = _format_paths(log_sources, exists=False)
    notes = {str(note) for note in _as_list(summary.get("notes"))}

    lines = ["اكتمل فحص مصادر السجلات بنجاح.", "", "الخلاصة:"]
    if total is not None:
        lines.append(f"- تم فحص {total} مصادر سجلات.")
    if existing_count is not None:
        lines.append(f"- يوجد {existing_count} مصادر متاحة.")
    if missing_count is not None:
        lines.append(f"- يوجد {missing_count} مصادر غير موجودة.")
    if permission_denied is not None:
        if permission_denied:
            lines.append(f"- توجد {permission_denied} مشاكل صلاحيات عند قراءة الميتاداتا.")
        else:
            lines.append("- لا توجد مشاكل صلاحيات في الوصول إلى الميتاداتا.")

    if existing_paths:
        lines.extend(["", "المصادر الموجودة:"])
        lines.extend(f"- {path}" for path in existing_paths)
    if missing_paths:
        lines.extend(["", "المصادر غير الموجودة:"])
        lines.extend(f"- {path}" for path in missing_paths)

    if {"metadata_only", "no_content_reads"} & notes:
        lines.extend(
            [
                "",
                "التفسير:",
                "الفحص اعتمد على الميتاداتا فقط ولم يقرأ محتوى السجلات الخام، وبالتالي هو فحص آمن وقراءة فقط.",
            ]
        )
    return _safe_chat_text("\n".join(lines))


def _summarize_generic_result_for_chat(result):
    lines = ["اكتمل الفحص بنجاح."]
    summary = result.get("summary") or _as_dict(result.get("output")).get("summary")
    if isinstance(summary, str) and summary.strip():
        lines.extend(["", "الخلاصة:", f"- {_safe_chat_text(summary, limit=500)}"])
    elif isinstance(summary, dict):
        bullets = _generic_summary_bullets(summary)
        if bullets:
            lines.extend(["", "الخلاصة:", *bullets])

    output = _as_dict(result.get("output"))
    output_bullets = _generic_summary_bullets(output)
    if output_bullets:
        if "الخلاصة:" not in lines:
            lines.extend(["", "الخلاصة:"])
        lines.extend(output_bullets)

    if len(lines) <= 1:
        lines.append(
            "النتيجة التفصيلية لا تحتوي ملخصًا قابلًا للعرض المختصر. يمكن مراجعة سجل التشغيل للتفاصيل."
        )
    return _safe_chat_text("\n".join(_dedupe_lines(lines[:12])))


def _generic_summary_bullets(data):
    bullets = []
    interesting_fragments = (
        "total",
        "count",
        "found",
        "existing",
        "missing",
        "error",
        "warning",
        "permission_denied",
        "status",
        "items",
    )
    for key, value in data.items():
        key_text = str(key)
        if not any(fragment in key_text.lower() for fragment in interesting_fragments):
            continue
        if isinstance(value, (str, int, float, bool)) and str(value).strip():
            bullets.append(f"- {_safe_chat_text(key_text, limit=80)}: {_safe_chat_text(value, limit=240)}")
        elif isinstance(value, list):
            bullets.append(f"- {_safe_chat_text(key_text, limit=80)}: {len(value)}")
        if len(bullets) >= 6:
            break
    return bullets


def _dedupe_lines(lines):
    seen = set()
    result = []
    for line in lines:
        marker = line.strip()
        if marker and marker in seen:
            continue
        if marker:
            seen.add(marker)
        result.append(line)
    return result
