from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.ai_chat.models import AdminLiveAIRequestLog


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
        mode = "apply" if apply else "dry-run"
        self.stdout.write(f"{mode}: found {count} stale legacy pending Live AI audit row(s).")
        if not apply:
            return
        updated = queryset.update(
            status=AdminLiveAIRequestLog.Status.FAILED,
            error_class=AdminLiveAIRequestLog.ErrorClass.UNKNOWN_ERROR,
            fallback_used=False,
            updated_at=timezone.now(),
        )
        self.stdout.write(f"apply: marked {updated} row(s) as failed with error_class=unknown_error (legacy_stale).")
