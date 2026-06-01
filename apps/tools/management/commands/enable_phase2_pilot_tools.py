from django.core.management.base import BaseCommand, CommandError

from apps.plans.models import Plan
from apps.tools.phase2_enablement import enable_phase2_pilot_tools


class Command(BaseCommand):
    help = "Enable Phase 2 read-only discovery tools for one selected pilot plan."

    def add_arguments(self, parser):
        parser.add_argument("--plan-id", type=int, required=True, help="Plan ID to enable Phase 2 discovery tools for.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without writing ToolDefinition, ToolPolicy, or PlanTool rows.",
        )

    def handle(self, *args, **options):
        plan_id = options["plan_id"]
        dry_run = options["dry_run"]
        if not Plan.objects.filter(id=plan_id).exists():
            raise CommandError(f"Plan with id {plan_id} does not exist.")

        result = enable_phase2_pilot_tools(plan_id=plan_id, dry_run=dry_run)
        mode = "DRY RUN" if dry_run else "APPLIED"
        self.stdout.write(f"{mode}: Phase 2 pilot enablement for plan {result.plan_id} ({result.plan_name})")
        for warning in result.dependency_warnings:
            self.stdout.write(self.style.WARNING(f"dependency: {warning}"))
        self.stdout.write(f"definition_changes={len(result.definition_changes)}")
        self.stdout.write(f"policy_changes={len(result.policy_changes)}")
        self.stdout.write(f"plan_tool_changes={len(result.plan_tool_changes)}")
        self.stdout.write(f"skipped={len(result.skipped)}")
        for item in result.definition_changes + result.policy_changes + result.plan_tool_changes + result.skipped:
            self.stdout.write(str(item))
