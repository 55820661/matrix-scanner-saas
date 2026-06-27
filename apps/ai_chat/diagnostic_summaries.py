from __future__ import annotations

from datetime import timedelta


TOOL_DISPLAY_LABELS_AR = {
    "log_sources_discovery_v2": "مصادر السجلات",
    "nginx_sites_discovery": "إعدادات Nginx",
    "gunicorn_uvicorn_services_discovery": "خدمات Gunicorn/Uvicorn",
    "systemd_services_discovery": "خدمات systemd",
    "postgres_status_discovery": "حالة PostgreSQL",
}


STATUS_LABELS_AR = {
    "succeeded": "نجح",
    "failed": "فشل",
    "timeout": "انتهت المهلة",
    "skipped": "تم تخطيه",
    "not_started": "لم يبدأ",
    "running": "قيد التنفيذ",
}


def tool_display_label_ar(tool_key: str) -> str:
    return TOOL_DISPLAY_LABELS_AR.get(tool_key or "", tool_key or "فحص غير معروف")


def diagnostic_status_label_ar(state: str) -> str:
    return STATUS_LABELS_AR.get((state or "").strip(), state or "غير معروف")


def normalize_reason_ar(reason: str) -> str:
    normalized = (reason or "").strip()
    lowered = normalized.casefold()
    if not normalized:
        return "لم يتم تحديد السبب."
    if any(token in lowered for token in ("not available", "غير متاح", "policy", "plan", "role", "server")):
        return "غير متاح لهذه الصلاحيات أو الخطة أو السيرفر."
    if any(token in lowered for token in ("permission", "denied", "صلاحية")):
        return "مرفوض بسبب الصلاحيات الحالية."
    if any(token in lowered for token in ("timeout", "مهلة", "timed out")):
        return "انتهت المهلة قبل اكتمال الفحص."
    if any(token in lowered for token in ("failed", "failure", "error", "exception", "فشل", "خطأ")):
        return "تعذر إكمال الفحص بسبب خطأ أثناء التنفيذ."
    if normalized.startswith("[") and normalized.endswith("]"):
        return "لم يتم تحديد السبب."
    return normalized


def _duration_seconds(item: dict) -> int | None:
    started_at = item.get("started_at")
    finished_at = item.get("finished_at")
    if started_at and finished_at:
        duration = finished_at - started_at
        return int(max(1, round(duration.total_seconds())))
    tool_run = item.get("tool_run")
    if not tool_run:
        return None
    started_at = getattr(tool_run, "started_at", None)
    finished_at = getattr(tool_run, "finished_at", None)
    if not started_at or not finished_at:
        return None
    duration = finished_at - started_at
    seconds = int(max(1, round(duration.total_seconds())))
    return seconds


def _duration_phrase_ar(item: dict) -> str:
    seconds = _duration_seconds(item)
    if seconds is None:
        return "، ولم تتوفر مدة التنفيذ."
    if seconds == 1:
        return " خلال ثانية واحدة."
    if seconds == 2:
        return " خلال ثانيتين."
    if 3 <= seconds <= 10:
        return f" خلال {seconds} ثوانٍ."
    return f" خلال {seconds} ثانية."


def _outcome_line_ar(item: dict) -> str:
    label = tool_display_label_ar(item.get("tool_key") or "")
    status_label = diagnostic_status_label_ar(item.get("state") or "")
    reason = normalize_reason_ar(item.get("reason") or item.get("summary") or "")
    state = item.get("state") or ""
    if state == "succeeded":
        return f"- {label}: {status_label}{_duration_phrase_ar(item)}"
    if state in {"skipped", "failed", "timeout", "not_started"}:
        if _duration_seconds(item) is not None:
            return f"- {label}: {status_label}{_duration_phrase_ar(item)[:-1]}، والسبب: {reason}."
        return f"- {label}: {status_label} لأن {reason}"
    return f"- {label}: {status_label}."


def bundle_summary_counts(bundle, outcomes: list[dict]) -> dict[str, int | str]:
    total_count = len(getattr(bundle, "tool_keys", ()) or ())
    executed_count = sum(1 for item in outcomes if item.get("kind") == "tool" and item.get("state") != "skipped")
    skipped_count = sum(1 for item in outcomes if item.get("state") == "skipped")
    failed_count = sum(1 for item in outcomes if item.get("state") in {"failed", "not_started"})
    timeout_count = sum(1 for item in outcomes if item.get("state") == "timeout")
    succeeded_count = sum(1 for item in outcomes if item.get("state") == "succeeded")
    return {
        "summary_quality": "structured_v1",
        "executed_count": executed_count,
        "succeeded_count": succeeded_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
        "timeout_count": timeout_count,
        "total_count": total_count,
    }


def _completion_level_ar(counts: dict[str, int | str]) -> str:
    executed_count = int(counts["executed_count"])
    total_count = int(counts["total_count"])
    if total_count <= 0:
        return "غير متاح — لم يتم تحديد عدد الفحوصات."
    if executed_count >= total_count:
        return "كامل — تم تنفيذ كل الفحوصات."
    if executed_count <= 1:
        return f"ضعيف — تم تنفيذ {executed_count} من أصل {total_count} فحوصات."
    return f"جزئي — تم تنفيذ {executed_count} من أصل {total_count} فحوصات."


def _risk_assessment_ar(counts: dict[str, int | str]) -> str:
    if int(counts["failed_count"]) or int(counts["timeout_count"]):
        return "يوجد نقص في نتيجة التشخيص بسبب فشل أو انتهاء مهلة بعض الفحوصات، ويجب مراجعتها قبل اتخاذ قرار تشغيلي."
    if int(counts["skipped_count"]):
        return "لا توجد مؤشرات حرجة من الفحوصات المنفذة، لكن الحكم غير مكتمل لأن بعض الفحوصات لم تُنفذ."
    return "لا توجد مؤشرات حرجة من الفحوصات المتاحة."


def _next_step_ar(outcomes: list[dict], counts: dict[str, int | str]) -> str:
    skipped_labels = [tool_display_label_ar(item.get("tool_key") or "") for item in outcomes if item.get("state") == "skipped"]
    pending_labels = [
        tool_display_label_ar(item.get("tool_key") or "")
        for item in outcomes
        if item.get("state") in {"failed", "timeout", "not_started"}
    ]
    if skipped_labels:
        joined = "، ".join(skipped_labels)
        return f"إذا كان المطلوب Health Check كامل، فعّل صلاحيات أو خطة الفحوصات التالية ثم أعد المحاولة: {joined}."
    if pending_labels:
        joined = "، ".join(pending_labels)
        return f"راجع الفحوصات التالية وأعد تنفيذها قبل اتخاذ قرار تشغيلي: {joined}."
    if int(counts["executed_count"]) == int(counts["total_count"]):
        return "يمكن اعتماد هذه النتيجة كفحص أولي، مع استكمال أي مراجعات تشغيلية إضافية عند الحاجة."
    return "استكمل الفحوصات الناقصة قبل اتخاذ قرار تشغيلي."


def summarize_diagnostic_bundle_results(bundle, outcomes: list[dict], language: str = "ar") -> str:
    counts = bundle_summary_counts(bundle, outcomes)
    succeeded_items = [item for item in outcomes if item.get("state") == "succeeded"]
    incomplete_items = [item for item in outcomes if item.get("state") != "succeeded"]
    lines = [
        f"اكتمل {bundle.label_ar}.",
        "",
        "الفحوصات المنفذة:",
    ]
    if succeeded_items:
        lines.extend(_outcome_line_ar(item) for item in succeeded_items)
    else:
        lines.append("- لا توجد فحوصات منفذة بنجاح.")
    lines.extend(["", "الفحوصات المتخطاة أو غير المكتملة:"])
    if incomplete_items:
        lines.extend(_outcome_line_ar(item) for item in incomplete_items)
    else:
        lines.append("لا توجد فحوصات متخطاة.")
    lines.extend(
        [
            "",
            "التقييم العام:",
            _risk_assessment_ar(counts),
            "",
            "مستوى اكتمال التشخيص:",
            _completion_level_ar(counts),
            "",
            "الخطوة المقترحة:",
            _next_step_ar(outcomes, counts),
        ]
    )
    return "\n".join(lines)
