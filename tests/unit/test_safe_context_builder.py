import json

from django.core.exceptions import PermissionDenied
from django.test import TestCase, override_settings

from apps.accounts.models import Account, User
from apps.ai_chat.models import AdminChatToolRequest
from apps.ai_context.services import (
    DEFAULT_MAX_ITEMS,
    build_safe_context,
    prepare_safe_context_for_ai,
)
from apps.applications.models import Application
from apps.plans.models import Plan
from apps.reports.models import KnowledgeEntry, Report
from apps.servers.models import AgentJob, DiscoveredService, Finding, ScannerAgent, Server
from apps.subscriptions.models import Subscription
from apps.tools.models import PlanTool, ToolDefinition, ToolPolicy, ToolRun, ToolTemplate
from apps.core.tokens import hash_token


class SafeContextBuilderTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create(name="Acme")
        self.other_account = Account.objects.create(name="Other")
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="password",
            account=self.account,
            role=User.CustomerRole.OWNER,
        )
        self.viewer = User.objects.create_user(
            username="viewer",
            email="viewer@example.com",
            password="password",
            account=self.account,
            role=User.CustomerRole.VIEWER,
        )
        self.other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="password",
            account=self.other_account,
            role=User.CustomerRole.OWNER,
        )
        self.server = Server.objects.create(
            account=self.account,
            name="Production",
            hostname="prod.example.test",
            status=Server.Status.ACTIVE,
        )
        self.other_server = Server.objects.create(
            account=self.other_account,
            name="Other",
            hostname="other.example.test",
            status=Server.Status.ACTIVE,
        )
        self.plan = Plan.objects.create(name="Pilot")
        Subscription.objects.create(account=self.account, plan=self.plan, status=Subscription.Status.ACTIVE)

    def create_tool(self, *, key="context_test_tool", allow_customer=True, allowed_roles=None, plan_enabled=True):
        template = ToolTemplate.objects.create(
            key=key,
            name=key,
            runtime_handler_key=key,
            is_active=True,
        )
        definition = ToolDefinition.objects.create(
            template=template,
            key=key,
            name=key,
            status=ToolDefinition.Status.ENABLED,
            risk_level=ToolDefinition.RiskLevel.READ_ONLY,
        )
        ToolPolicy.objects.create(
            tool_definition=definition,
            allow_customer_run=allow_customer,
            allow_admin_run=True,
            allow_agent_run=True,
            allowed_roles=allowed_roles or [User.CustomerRole.OWNER, User.CustomerRole.OPERATOR],
            allowed_server_statuses=[Server.Status.ACTIVE],
            is_active=True,
        )
        PlanTool.objects.create(plan=self.plan, tool_definition=definition, is_enabled=plan_enabled)
        return definition

    def test_builds_versioned_account_scoped_context(self):
        Application.objects.create(
            account=self.account,
            server=self.server,
            name="App password=secret",
            path="/opt/app",
            framework="django",
        )

        context = build_safe_context(account=self.account, server=self.server, user=self.owner)

        self.assertEqual(context["context_version"], "1.0")
        self.assertEqual(context["account_summary"]["id"], str(self.account.id))
        self.assertEqual(context["server_summary"]["id"], str(self.server.id))
        serialized = json.dumps(context)
        self.assertNotIn("password=secret", serialized)
        self.assertIn("[REDACTED]", serialized)

    def test_cross_account_user_and_server_are_denied(self):
        with self.assertRaises(PermissionDenied):
            build_safe_context(account=self.account, server=self.server, user=self.other_user)
        with self.assertRaises(PermissionDenied):
            build_safe_context(account=self.account, server=self.other_server, user=self.owner)

    def test_raw_agent_job_and_toolrun_outputs_are_not_included(self):
        agent = ScannerAgent.objects.create(
            account=self.account,
            server=self.server,
            token_hash=hash_token("agent-token"),
            status=ScannerAgent.Status.ACTIVE,
        )
        definition = self.create_tool()
        job = AgentJob.objects.create(
            account=self.account,
            server=self.server,
            agent=agent,
            tool_key=definition.key,
            result={"DB_PASSWORD": "raw-secret"},
            status=AgentJob.Status.SUCCEEDED,
        )
        ToolRun.objects.create(
            account=self.account,
            server=self.server,
            agent=agent,
            tool_definition=definition,
            agent_job=job,
            status=ToolRun.Status.SUCCEEDED,
            result_redacted={"safe": "ok", "token": "raw-secret"},
            error_message="password=raw-secret",
        )

        context = build_safe_context(account=self.account, server=self.server, user=self.owner)

        serialized = json.dumps(context)
        self.assertNotIn("DB_PASSWORD", serialized)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("result_redacted", serialized)
        self.assertIn("has_result", serialized)

    def test_available_tools_respect_plan_policy_and_role(self):
        self.create_tool(key="allowed_tool")
        self.create_tool(key="disabled_plan_tool", plan_enabled=False)
        self.create_tool(key="customer_blocked_tool", allow_customer=False)

        owner_context = build_safe_context(account=self.account, server=self.server, user=self.owner)
        viewer_context = build_safe_context(account=self.account, server=self.server, user=self.viewer)

        owner_tools = {tool["key"] for tool in owner_context["available_tools"]}
        self.assertEqual(owner_tools, {"allowed_tool"})
        self.assertEqual(viewer_context["available_tools"], [])

    def test_sections_are_capped_and_safe_only(self):
        for index in range(DEFAULT_MAX_ITEMS + 3):
            Application.objects.create(
                account=self.account,
                server=self.server,
                name=f"App {index}",
                path=f"/opt/app-{index}",
            )

        context = build_safe_context(account=self.account, server=self.server, user=self.owner)

        self.assertEqual(len(context["applications_summary"]), DEFAULT_MAX_ITEMS)
        self.assertLessEqual(context["metadata"]["context_size_bytes"], context["metadata"]["max_context_bytes"])

    def test_safe_models_are_summarized_without_raw_sensitive_text(self):
        DiscoveredService.objects.create(
            account=self.account,
            server=self.server,
            name="nginx",
            status="active",
            metadata={"token": "secret-token"},
        )
        Finding.objects.create(
            account=self.account,
            server=self.server,
            title="Debug enabled",
            severity="high",
            evidence_summary="api_key=abc123",
            fingerprint="debug-enabled",
        )
        Report.objects.create(
            account=self.account,
            server=self.server,
            report_type=Report.ReportType.SERVER_HEALTH,
            title="Health",
            summary_redacted="password=secret",
        )
        KnowledgeEntry.objects.create(
            scope=KnowledgeEntry.Scope.ACCOUNT,
            account=self.account,
            title="Runbook",
            body_redacted="token=secret",
            status=KnowledgeEntry.Status.APPROVED,
            visibility=KnowledgeEntry.Visibility.CUSTOMER_VISIBLE,
        )

        context = build_safe_context(account=self.account, server=self.server, user=self.owner)

        serialized = json.dumps(context)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("abc123", serialized)
        self.assertNotIn("password=secret", serialized)
        self.assertNotIn("token=secret", serialized)
        self.assertIn("[REDACTED]", serialized)

    @override_settings(AI_SAFE_CONTEXT_MAX_BYTES=2048)
    def test_configured_hard_cap_truncates_context_without_breaking_json(self):
        for index in range(DEFAULT_MAX_ITEMS):
            Application.objects.create(
                account=self.account,
                server=self.server,
                name=f"Verbose App {index} " + ("x" * 240),
                path=f"/opt/{index}/" + ("y" * 400),
                metadata={"description": "z" * 600},
            )

        context = build_safe_context(account=self.account, server=self.server, user=self.owner)
        serialized = json.dumps(context, sort_keys=True)

        self.assertLessEqual(len(serialized.encode("utf-8")), 2048)
        self.assertTrue(context["metadata"]["truncated"])
        self.assertGreater(context["metadata"]["original_size_bytes"], 2048)
        self.assertEqual(context["metadata"]["final_size_bytes"], len(serialized.encode("utf-8")))
        self.assertEqual(context["metadata"]["max_size_bytes"], 2048)
        self.assertEqual(json.loads(serialized), context)
        self.assertEqual(context["account_summary"]["id"], str(self.account.id))
        self.assertEqual(context["server_summary"]["id"], str(self.server.id))

    def test_ai_payload_preparation_has_no_execution_side_effects(self):
        before = (
            AdminChatToolRequest.objects.count(),
            ToolRun.objects.count(),
            AgentJob.objects.count(),
        )

        payload = prepare_safe_context_for_ai(
            {
                "context_version": "1.0",
                "account_summary": {"id": str(self.account.id), "name": self.account.name},
                "server_summary": {"id": str(self.server.id), "name": self.server.name},
                "available_tools": [{"key": "status", "name": "Status"}],
            }
        )

        self.assertEqual(
            before,
            (
                AdminChatToolRequest.objects.count(),
                ToolRun.objects.count(),
                AgentJob.objects.count(),
            ),
        )
        self.assertFalse(payload["metadata"]["tools_enabled"])
        self.assertIn("Do not execute tools", " ".join(payload["safety_guidance"]["instructions"]))
