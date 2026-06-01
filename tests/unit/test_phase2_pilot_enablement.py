from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.applications.models import Application
from apps.plans.models import Plan
from apps.reports.models import Report
from apps.servers.baseline import start_baseline_scan
from apps.servers.baseline_profiles import DEBIAN_NGINX_OPT_TOOL_KEYS, PROFILE_DEBIAN_NGINX_OPT, PROFILE_LEGACY_CPANEL
from apps.servers.models import AgentJob, BaselineScan, DiscoveredDomain, DiscoveredService, LogSource, ScannerAgent, Server
from apps.subscriptions.models import Subscription
from apps.tools.models import PlanTool, ToolDefinition, ToolPolicy, ToolRun
from apps.tools.setup import BASELINE_TOOL_KEYS, PHASE2_DISCOVERY_TOOL_KEYS, ensure_baseline_tools, ensure_phase2_discovery_tool_contracts


class Phase2PilotEnablementTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create(name="Pilot")
        self.plan = Plan.objects.create(name="Pilot Plan")
        self.other_plan = Plan.objects.create(name="Other Plan")
        self.subscription = Subscription.objects.create(
            account=self.account,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
        )
        self.server = Server.objects.create(account=self.account, name="Production", status=Server.Status.ACTIVE)
        self.agent = ScannerAgent.objects.create(
            account=self.account,
            server=self.server,
            token_hash="agent-token-hash",
            status=ScannerAgent.Status.ACTIVE,
            registered_at=timezone.now(),
            last_seen_at=timezone.now(),
        )
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
        ensure_baseline_tools()

    def call_enablement(self, *, plan_id=None, dry_run=False):
        out = StringIO()
        options = {"stdout": out}
        if plan_id is not None:
            options["plan_id"] = plan_id
        if dry_run:
            options["dry_run"] = True
        call_command("enable_phase2_pilot_tools", **options)
        return out.getvalue()

    def create_scan(self, profile_key=PROFILE_DEBIAN_NGINX_OPT):
        return BaselineScan.objects.create(
            account=self.account,
            server=self.server,
            requested_by=self.admin,
            profile_key=profile_key,
        )

    def phase2_snapshot(self):
        return {
            "definitions": list(
                ToolDefinition.objects.filter(key__in=PHASE2_DISCOVERY_TOOL_KEYS)
                .order_by("key")
                .values("key", "status", "risk_level")
            ),
            "policies": list(
                ToolPolicy.objects.filter(tool_definition__key__in=PHASE2_DISCOVERY_TOOL_KEYS)
                .order_by("tool_definition__key")
                .values(
                    "tool_definition__key",
                    "is_active",
                    "allow_agent_run",
                    "allow_admin_run",
                    "allow_customer_run",
                    "allowed_roles",
                    "allowed_server_statuses",
                )
            ),
            "plan_tools": list(
                PlanTool.objects.filter(tool_definition__key__in=PHASE2_DISCOVERY_TOOL_KEYS)
                .order_by("plan_id", "tool_definition__key")
                .values("plan_id", "tool_definition__key", "is_enabled")
            ),
            "tool_runs": ToolRun.objects.count(),
            "agent_jobs": AgentJob.objects.count(),
        }

    def test_dry_run_makes_no_db_changes(self):
        before = self.phase2_snapshot()

        output = self.call_enablement(plan_id=self.plan.id, dry_run=True)

        self.assertIn("DRY RUN", output)
        self.assertEqual(self.phase2_snapshot(), before)

    def test_command_requires_plan_id(self):
        with self.assertRaises(CommandError):
            self.call_enablement()

    def test_invalid_plan_id_fails_safely(self):
        before = self.phase2_snapshot()

        with self.assertRaises(CommandError):
            self.call_enablement(plan_id=999999)

        self.assertEqual(self.phase2_snapshot(), before)

    def test_command_enables_only_selected_phase2_tools(self):
        self.call_enablement(plan_id=self.plan.id)

        enabled_keys = set(
            ToolDefinition.objects.filter(status=ToolDefinition.Status.ENABLED).values_list("key", flat=True)
        )
        self.assertTrue(set(PHASE2_DISCOVERY_TOOL_KEYS).issubset(enabled_keys))
        self.assertTrue(set(BASELINE_TOOL_KEYS).issubset(enabled_keys))
        self.assertEqual(set(PHASE2_DISCOVERY_TOOL_KEYS), set(DEBIAN_NGINX_OPT_TOOL_KEYS) - {"system_identity"})

    def test_tool_definitions_become_enabled_only_for_read_only_phase2_tools(self):
        ensure_phase2_discovery_tool_contracts(connect_active_plans=False, activate_policy=False)
        unsafe = ToolDefinition.objects.get(key="postgres_status_discovery")
        unsafe.risk_level = ToolDefinition.RiskLevel.WRITE_ACTION
        unsafe.status = ToolDefinition.Status.APPROVED
        unsafe.save(update_fields=["risk_level", "status", "updated_at"])

        self.call_enablement(plan_id=self.plan.id)

        unsafe.refresh_from_db()
        self.assertEqual(unsafe.status, ToolDefinition.Status.APPROVED)
        self.assertEqual(unsafe.risk_level, ToolDefinition.RiskLevel.WRITE_ACTION)
        enabled_phase2 = set(
            ToolDefinition.objects.filter(key__in=PHASE2_DISCOVERY_TOOL_KEYS, status=ToolDefinition.Status.ENABLED)
            .values_list("key", flat=True)
        )
        self.assertNotIn("postgres_status_discovery", enabled_phase2)

    def test_tool_policy_is_active_for_agent_and_admin_but_not_customer(self):
        self.call_enablement(plan_id=self.plan.id)

        for policy in ToolPolicy.objects.filter(tool_definition__key__in=PHASE2_DISCOVERY_TOOL_KEYS):
            self.assertTrue(policy.is_active)
            self.assertTrue(policy.allow_agent_run)
            self.assertTrue(policy.allow_admin_run)
            self.assertFalse(policy.allow_customer_run)
            self.assertEqual(policy.allowed_roles, ["owner", "operator"])
            self.assertEqual(policy.allowed_server_statuses, ["active"])

    def test_plan_tool_created_only_for_selected_plan(self):
        self.call_enablement(plan_id=self.plan.id)

        selected_links = PlanTool.objects.filter(
            plan=self.plan,
            tool_definition__key__in=PHASE2_DISCOVERY_TOOL_KEYS,
            is_enabled=True,
        )
        other_links = PlanTool.objects.filter(
            plan=self.other_plan,
            tool_definition__key__in=PHASE2_DISCOVERY_TOOL_KEYS,
        )
        self.assertEqual(selected_links.count(), len(PHASE2_DISCOVERY_TOOL_KEYS))
        self.assertEqual(other_links.count(), 0)

    def test_command_creates_no_tool_runs_or_agent_jobs(self):
        self.call_enablement(plan_id=self.plan.id)

        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    def test_debian_nginx_opt_preflight_passes_after_enablement(self):
        self.call_enablement(plan_id=self.plan.id)
        scan = self.create_scan(profile_key=PROFILE_DEBIAN_NGINX_OPT)

        start_baseline_scan(scan)

        step_keys = set(scan.steps.values_list("step_key", flat=True))
        self.assertEqual(step_keys, set(DEBIAN_NGINX_OPT_TOOL_KEYS))
        self.assertEqual(ToolRun.objects.count(), len(DEBIAN_NGINX_OPT_TOOL_KEYS))
        self.assertEqual(AgentJob.objects.count(), len(DEBIAN_NGINX_OPT_TOOL_KEYS))

    def test_legacy_profile_remains_unaffected(self):
        self.call_enablement(plan_id=self.plan.id)
        scan = self.create_scan(profile_key=PROFILE_LEGACY_CPANEL)

        start_baseline_scan(scan)

        self.assertEqual(set(scan.steps.values_list("step_key", flat=True)), set(BASELINE_TOOL_KEYS))
        self.assertFalse(set(scan.steps.values_list("step_key", flat=True)) & set(PHASE2_DISCOVERY_TOOL_KEYS))

    def test_no_ingestion_or_report_side_effects(self):
        self.call_enablement(plan_id=self.plan.id)

        self.assertEqual(DiscoveredService.objects.count(), 0)
        self.assertEqual(DiscoveredDomain.objects.count(), 0)
        self.assertEqual(Application.objects.count(), 0)
        self.assertEqual(LogSource.objects.count(), 0)
        self.assertEqual(Report.objects.count(), 0)
