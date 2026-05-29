from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.diagnostics.services import ALLOWED_DIAGNOSTIC_TOOLS
from apps.plans.models import Plan
from apps.servers.baseline import BASELINE_TOOL_KEYS
from apps.servers.models import AgentJob, ScannerAgent, Server
from apps.subscriptions.models import Subscription
from apps.tools.models import PlanTool, ToolDefinition, ToolRun
from apps.tools.services import ToolPolicyDenied, create_tool_run_job
from apps.tools.setup import PHASE2_DISCOVERY_TOOL_KEYS, ensure_phase2_discovery_tool_contracts


class Phase2ToolContractTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create(name="Phase 2 Customer")
        self.plan = Plan.objects.create(name="Phase 2 Plan")
        self.subscription = Subscription.objects.create(
            account=self.account,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
        )
        self.server = Server.objects.create(account=self.account, name="Debian Nginx Host", status=Server.Status.ACTIVE)
        self.agent = ScannerAgent.objects.create(
            account=self.account,
            server=self.server,
            token_hash="agent-token-hash",
            status=ScannerAgent.Status.ACTIVE,
            registered_at=timezone.now(),
            last_seen_at=timezone.now(),
        )
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="password",
            account=self.account,
            role=User.CustomerRole.OWNER,
        )

    def test_phase2_discovery_tool_contracts_are_seeded_safely(self):
        ensure_phase2_discovery_tool_contracts()

        for tool_key in PHASE2_DISCOVERY_TOOL_KEYS:
            tool = ToolDefinition.objects.select_related("template", "policy").get(key=tool_key)
            self.assertEqual(tool.template.runtime_handler_key, tool_key)
            self.assertEqual(tool.status, ToolDefinition.Status.APPROVED)
            self.assertEqual(tool.risk_level, ToolDefinition.RiskLevel.READ_ONLY)
            self.assertEqual(tool.category, "phase2_discovery")
            self.assertEqual(tool.input_schema, {"fields": {}, "required": []})
            self.assertEqual(tool.timeout_seconds, tool.template.default_timeout_seconds)
            self.assertLessEqual(tool.max_output_bytes, 64 * 1024)
            self.assertIn("/etc/shadow", tool.blocked_path_prefixes)
            self.assertIn("/opt/*/.env", tool.blocked_path_prefixes)
            self.assertIn("secret", tool.redaction_rules)
            self.assertFalse(tool.policy.is_active)
            self.assertFalse(tool.policy.allow_customer_run)
            self.assertFalse(tool.policy.allow_admin_run)
            self.assertFalse(tool.policy.allow_agent_run)
            self.assertFalse(PlanTool.objects.filter(plan=self.plan, tool_definition=tool).exists())

    def test_phase2_contracts_are_not_in_current_baseline_or_diagnostic_tool_sets(self):
        ensure_phase2_discovery_tool_contracts()

        for tool_key in PHASE2_DISCOVERY_TOOL_KEYS:
            self.assertNotIn(tool_key, BASELINE_TOOL_KEYS)
            self.assertNotIn(tool_key, ALLOWED_DIAGNOSTIC_TOOLS)

    def test_phase2_contract_seeding_is_idempotent(self):
        ensure_phase2_discovery_tool_contracts()
        ensure_phase2_discovery_tool_contracts()

        for tool_key in PHASE2_DISCOVERY_TOOL_KEYS:
            self.assertEqual(ToolDefinition.objects.filter(key=tool_key).count(), 1)

    def test_phase2_seeding_does_not_overwrite_existing_policy_or_plan_link_without_reset(self):
        ensure_phase2_discovery_tool_contracts()
        tool = ToolDefinition.objects.get(key="nginx_sites_discovery")
        policy = tool.policy
        policy.is_active = True
        policy.allow_customer_run = True
        policy.allow_admin_run = True
        policy.allow_agent_run = True
        policy.save(update_fields=["is_active", "allow_customer_run", "allow_admin_run", "allow_agent_run", "updated_at"])
        plan_tool = PlanTool.objects.create(plan=self.plan, tool_definition=tool, is_enabled=True)

        ensure_phase2_discovery_tool_contracts(connect_active_plans=True)

        policy.refresh_from_db()
        plan_tool.refresh_from_db()
        self.assertTrue(policy.is_active)
        self.assertTrue(policy.allow_customer_run)
        self.assertTrue(policy.allow_admin_run)
        self.assertTrue(policy.allow_agent_run)
        self.assertTrue(plan_tool.is_enabled)

    def test_phase2_seeding_reset_can_overwrite_policy_and_plan_link(self):
        ensure_phase2_discovery_tool_contracts()
        tool = ToolDefinition.objects.get(key="nginx_sites_discovery")
        policy = tool.policy
        policy.is_active = True
        policy.allow_customer_run = True
        policy.allow_admin_run = True
        policy.allow_agent_run = True
        policy.save(update_fields=["is_active", "allow_customer_run", "allow_admin_run", "allow_agent_run", "updated_at"])
        plan_tool = PlanTool.objects.create(plan=self.plan, tool_definition=tool, is_enabled=True)

        ensure_phase2_discovery_tool_contracts(connect_active_plans=True, reset_existing=True)

        policy.refresh_from_db()
        plan_tool.refresh_from_db()
        self.assertFalse(policy.is_active)
        self.assertFalse(policy.allow_customer_run)
        self.assertFalse(policy.allow_admin_run)
        self.assertFalse(policy.allow_agent_run)
        self.assertFalse(plan_tool.is_enabled)

    def test_phase2_contracts_do_not_create_jobs_or_runs_and_cannot_execute_yet(self):
        ensure_phase2_discovery_tool_contracts()

        with self.assertRaises(ToolPolicyDenied):
            create_tool_run_job(
                account=self.account,
                server=self.server,
                tool_key="nginx_sites_discovery",
                requested_by=self.owner,
                requested_by_type=ToolRun.RequestedByType.USER,
            )

        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)
