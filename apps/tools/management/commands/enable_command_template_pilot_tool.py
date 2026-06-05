from django.core.management.base import BaseCommand, CommandError

from apps.plans.models import Plan
from apps.tools.command_template_enablement import enable_command_template_pilot_tool
from apps.tools.models import ToolDefinition


class Command(BaseCommand):
    help = "Enable one approved read-only command-template tool for a selected pilot plan."

    def add_arguments(self, parser):
        parser.add_argument("--plan-id", type=int, required=True, help="Plan ID to enable the pilot tool for.")
        parser.add_argument("--tool-key", type=str, required=True, help="ToolDefinition key to enable.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without writing ToolDefinition, ToolPolicy, or PlanTool rows.",
        )

    def handle(self, *args, **options):
        plan_id = options["plan_id"]
        tool_key = options["tool_key"]
        dry_run = options["dry_run"]
        if not Plan.objects.filter(id=plan_id).exists():
            raise CommandError(f"Plan with id {plan_id} does not exist.")
        if not ToolDefinition.objects.filter(key=tool_key).exists():
            raise CommandError(f"ToolDefinition with key {tool_key} does not exist.")
        try:
            result = enable_command_template_pilot_tool(plan_id=plan_id, tool_key=tool_key, dry_run=dry_run)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        mode = "DRY RUN" if dry_run else "APPLIED"
        self.stdout.write(f"{mode}: command-template pilot enablement for plan {result.plan_id} ({result.plan_name})")
        self.stdout.write(f"tool_key={result.tool_key}")
        self.stdout.write(f"definition_changes={len(result.definition_changes)}")
        self.stdout.write(f"policy_changes={len(result.policy_changes)}")
        self.stdout.write(f"plan_tool_changes={len(result.plan_tool_changes)}")
        self.stdout.write(f"skipped={len(result.skipped)}")
        for item in result.definition_changes + result.policy_changes + result.plan_tool_changes + result.skipped:
            self.stdout.write(str(item))
