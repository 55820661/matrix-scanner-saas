from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.ai_chat.models import AdminChatMessage, AdminLiveAIRequestLog


class Command(BaseCommand):
    help = "Safely mark stale legacy pending Live AI audit rows as failed."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Apply the cleanup. Without this, the command is dry-run.")
        parser.add_argument("--dry-run", action="store_true", help="Show the stale row count without changing data.")
        parser.add_argument("--older-than-hours", type=int, default=24, help="Only touch pending rows older than this many hours.")

    def handle(self, *args, **options):
        apply = options["apply"]
        dry_run = options["dry_run"]
        older_than_hours = options["older_than_hours"]
        if apply and dry_run:
            raise CommandError("Use either --apply or --dry-run, not both.")
        if older_than_hours < 1:
            raise CommandError("--older-than-hours must be at least 1.")

        cutoff = timezone.now() - timedelta(hours=older_than_hours)
        queryset = AdminLiveAIRequestLog.objects.filter(
            status=AdminLiveAIRequestLog.Status.PENDING,
            latency_ms=0,
            created_at__lt=cutoff,
        )
        count = queryset.count()
        duplicate_messages = self._generic_duplicate_tool_messages()
        duplicate_count = len(duplicate_messages)
        mode = "apply" if apply else "dry-run"
        self.stdout.write(f"{mode}: found {count} stale legacy pending Live AI audit row(s).")
        self.stdout.write(f"{mode}: found {duplicate_count} legacy generic duplicate tool result message(s).")
        if not apply:
            return
        updated = queryset.update(
            status=AdminLiveAIRequestLog.Status.FAILED,
            error_class=AdminLiveAIRequestLog.ErrorClass.UNKNOWN_ERROR,
            fallback_used=False,
            updated_at=timezone.now(),
        )
        self.stdout.write(f"apply: marked {updated} row(s) as failed with error_class=unknown_error (legacy_stale).")
        deleted = 0
        if duplicate_messages:
            deleted, _ = AdminChatMessage.objects.filter(id__in=[message.id for message in duplicate_messages]).delete()
        self.stdout.write(f"apply: deleted {deleted} legacy generic duplicate tool result message(s).")

    def _generic_duplicate_tool_messages(self):
        candidates = AdminChatMessage.objects.filter(
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            metadata_redacted__source="tool_result_summary",
            metadata_redacted__has_key="tool_run_id",
        ).filter(metadata_redacted__has_key="tool_key").order_by("created_at", "id")
        duplicates = []
        for message in candidates:
            metadata = message.metadata_redacted or {}
            if metadata.get("chatkit_item_id"):
                continue
            tool_key = metadata.get("tool_key") or ""
            tool_run_id = metadata.get("tool_run_id") or ""
            if not tool_key or not tool_run_id:
                continue
            if (message.body_redacted or "").strip() != f"{tool_key} completed successfully.":
                continue
            if AdminChatMessage.objects.filter(
                session=message.session,
                sender_type=AdminChatMessage.SenderType.ASSISTANT,
                metadata_redacted__source="tool_result_summary",
                metadata_redacted__tool_run_id=tool_run_id,
                created_at__gt=message.created_at,
            ).exclude(id=message.id).exclude(body_redacted=message.body_redacted).exists():
                duplicates.append(message)
        return duplicates
