from io import StringIO

from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.ai_chat.models import AdminChatDecision, AdminChatMessage, AdminChatToolRequest
from apps.ai_chat.services import (
    add_user_message_and_response,
    approve_tool_request,
    create_chat_session,
    create_tool_request,
)
from apps.plans.models import Plan
from apps.servers.models import AgentJob, ScannerAgent, Server
from apps.subscriptions.models import Subscription
from apps.tools.models import PlanTool, ToolBuildRequest, ToolBuildReview, ToolDefinition, ToolPolicy, ToolRun, ToolTemplate
from apps.tools.services import (
    convert_tool_build_proposal,
    generate_tool_build_proposal,
    review_tool_build_proposal,
    update_tool_run_from_job,
)


class SprintC8FirstToolCycleTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create(name="Pilot Account")
        self.plan = Plan.objects.create(name="Pilot Plan", is_active=True)
        self.other_plan = Plan.objects.create(name="Other Plan", is_active=True)
        Subscription.objects.create(
            account=self.account,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
        )
        self.server = Server.objects.create(
            account=self.account,
            name="Apache Host",
            hostname="apache.example.com",
            status=Server.Status.ACTIVE,
        )
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
        self.operator = User.objects.create_user(
            username="operator",
            email="operator@example.com",
            password="password",
            account=self.account,
            role=User.CustomerRole.OPERATOR,
        )
        self.viewer = User.objects.create_user(
            username="viewer",
            email="viewer@example.com",
            password="password",
            account=self.account,
            role=User.CustomerRole.VIEWER,
        )
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )

    def call_enablement(self, *, plan_id=None, tool_key=None, dry_run=False):
        out = StringIO()
        options = {"stdout": out}
        if plan_id is not None:
            options["plan_id"] = plan_id
        if tool_key is not None:
            options["tool_key"] = tool_key
        if dry_run:
            options["dry_run"] = True
        call_command("enable_command_template_pilot_tool", **options)
        return out.getvalue()

    def create_converted_apache_summary_tool(self, *, key="apache_5xx_summary"):
        build_request = ToolBuildRequest.objects.create(
            requested_by=self.owner,
            title="Apache 5xx summary",
            description_redacted="Count 5xx responses from the Apache access log without returning raw lines.",
            desired_tool_key=key,
            desired_handler_key="",
            desired_execution_type=ToolTemplate.ExecutionType.COMMAND_TEMPLATE,
            command_argv_template=[
                "awk",
                'BEGIN{{c=0}}/" 5[0-9][0-9] "/{{c++}}END{{print c}}',
                "/usr/local/apache/logs/access_log",
            ],
            allowed_binaries=["awk"],
            blocked_tokens=[";", "&&", "||", "|", ">", "<", "`", "$", "\n", "\r"],
            expected_output_description_redacted="Return a single numeric count of matching 5xx responses.",
            status=ToolBuildRequest.Status.DRAFT,
        )
        proposal = generate_tool_build_proposal(build_request, actor_user=self.owner)
        review_tool_build_proposal(proposal, reviewer=self.admin, decision=ToolBuildReview.Decision.APPROVED)
        return convert_tool_build_proposal(proposal, actor_user=self.admin)

    def test_enablement_dry_run_makes_no_db_changes(self):
        definition = self.create_converted_apache_summary_tool()
        before_status = definition.status
        before_policy = ToolPolicy.objects.get(tool_definition=definition)

        output = self.call_enablement(plan_id=self.plan.id, tool_key=definition.key, dry_run=True)

        definition.refresh_from_db()
        before_policy.refresh_from_db()
        self.assertIn("DRY RUN", output)
        self.assertEqual(definition.status, before_status)
        self.assertFalse(before_policy.is_active)
        self.assertFalse(before_policy.allow_customer_run)
        self.assertEqual(PlanTool.objects.filter(tool_definition=definition).count(), 0)

    def test_command_requires_plan_id_and_tool_key(self):
        definition = self.create_converted_apache_summary_tool()
        with self.assertRaises(CommandError):
            self.call_enablement(tool_key=definition.key)
        with self.assertRaises(CommandError):
            self.call_enablement(plan_id=self.plan.id)

    def test_enablement_activates_selected_tool_for_selected_plan_only(self):
        definition = self.create_converted_apache_summary_tool()

        output = self.call_enablement(plan_id=self.plan.id, tool_key=definition.key)

        definition.refresh_from_db()
        policy = ToolPolicy.objects.get(tool_definition=definition)
        selected_plan_tool = PlanTool.objects.get(plan=self.plan, tool_definition=definition)
        self.assertIn("APPLIED", output)
        self.assertEqual(definition.status, ToolDefinition.Status.ENABLED)
        self.assertTrue(policy.is_active)
        self.assertTrue(policy.allow_customer_run)
        self.assertTrue(policy.allow_admin_run)
        self.assertTrue(policy.allow_agent_run)
        self.assertEqual(policy.allowed_roles, ["owner", "operator"])
        self.assertEqual(policy.allowed_server_statuses, ["active"])
        self.assertTrue(selected_plan_tool.is_enabled)
        self.assertFalse(PlanTool.objects.filter(plan=self.other_plan, tool_definition=definition).exists())

    def test_enablement_rejects_non_read_only_or_non_converted_tools(self):
        definition = self.create_converted_apache_summary_tool(key="unsafe_summary")
        definition.risk_level = ToolDefinition.RiskLevel.WRITE_ACTION
        definition.save(update_fields=["risk_level", "updated_at"])

        with self.assertRaises(CommandError):
            self.call_enablement(plan_id=self.plan.id, tool_key=definition.key)

        template = ToolTemplate.objects.create(
            key="direct_command_template",
            name="Direct",
            description="Direct command template without proposal conversion.",
            runtime_handler_key="",
            execution_type=ToolTemplate.ExecutionType.COMMAND_TEMPLATE,
            command_argv_template=["awk", "BEGIN{{print 0}}"],
            allowed_binaries=["awk"],
            blocked_tokens=[";", "&&", "||", "|", ">", "<", "`", "$"],
        )
        direct_definition = ToolDefinition.objects.create(
            template=template,
            key="direct_command_template",
            name="Direct",
            description="Direct command template without proposal conversion.",
            status=ToolDefinition.Status.DRAFT,
            risk_level=ToolDefinition.RiskLevel.READ_ONLY,
            execution_type=ToolTemplate.ExecutionType.COMMAND_TEMPLATE,
            timeout_seconds=30,
            max_output_bytes=65536,
        )

        with self.assertRaises(CommandError):
            self.call_enablement(plan_id=self.plan.id, tool_key=direct_definition.key)

    def test_tool_result_sync_updates_chat_request_and_posts_safe_assistant_summary(self):
        definition = self.create_converted_apache_summary_tool()
        self.call_enablement(plan_id=self.plan.id, tool_key=definition.key)
        session = create_chat_session(user=self.owner, title="Apache review", server_id=self.server.id)

        tool_request = create_tool_request(user=self.owner, session=session, tool_key=definition.key)
        tool_run = approve_tool_request(user=self.owner, tool_request=tool_request)
        job = tool_run.agent_job
        self.assertEqual(job.execution_payload["argv"][1], 'BEGIN{c=0}/" 5[0-9][0-9] "/{c++}END{print c}')
        job.status = AgentJob.Status.SUCCEEDED
        job.result = {
            "status": "succeeded",
            "output": {
                "command": {
                    "exit_code": 0,
                    "stdout_redacted": "12\n",
                    "stderr_redacted": "",
                    "execution_time_seconds": 0.05,
                    "truncated": False,
                }
            },
            "error": "",
        }
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "result", "finished_at", "updated_at"])

        update_tool_run_from_job(job)

        tool_request.refresh_from_db()
        session.refresh_from_db()
        assistant_message = (
            AdminChatMessage.objects.filter(session=session, sender_type=AdminChatMessage.SenderType.ASSISTANT)
            .order_by("-created_at")
            .first()
        )
        self.assertEqual(tool_request.status, AdminChatToolRequest.Status.SUCCEEDED)
        self.assertIsNotNone(assistant_message)
        self.assertIn("12 matching 5xx responses", assistant_message.body_redacted)
        self.assertNotIn("/usr/local/apache/logs/access_log", assistant_message.body_redacted)
        self.assertEqual(ToolRun.objects.count(), 1)
        self.assertEqual(AgentJob.objects.count(), 1)
        self.assertTrue(
            AdminChatDecision.objects.filter(
                session=session,
                decision_type=AdminChatDecision.DecisionType.TOOL_REQUEST,
                output_json_redacted__status=AdminChatToolRequest.Status.SUCCEEDED,
            ).exists()
        )

    def test_deterministic_chat_result_response_uses_safe_summary(self):
        definition = self.create_converted_apache_summary_tool()
        self.call_enablement(plan_id=self.plan.id, tool_key=definition.key)
        session = create_chat_session(user=self.owner, title="Apache review", server_id=self.server.id)
        tool_request = create_tool_request(user=self.owner, session=session, tool_key=definition.key)
        tool_run = approve_tool_request(user=self.owner, tool_request=tool_request)
        job = tool_run.agent_job
        job.status = AgentJob.Status.SUCCEEDED
        job.result = {
            "status": "succeeded",
            "output": {
                "command": {
                    "exit_code": 0,
                    "stdout_redacted": "0\n",
                    "stderr_redacted": "",
                    "execution_time_seconds": 0.02,
                    "truncated": False,
                }
            },
            "error": "",
        }
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "result", "finished_at", "updated_at"])
        update_tool_run_from_job(job)

        _, assistant_message = add_user_message_and_response(
            user=self.owner,
            session=session,
            body="What was the latest tool result?",
        )

        self.assertIn("no 5xx responses", assistant_message.body_redacted.lower())
        self.assertNotIn("stdout_redacted", assistant_message.body_redacted)

    def test_viewer_cannot_create_or_approve_enabled_chat_tool(self):
        definition = self.create_converted_apache_summary_tool()
        self.call_enablement(plan_id=self.plan.id, tool_key=definition.key)
        session = create_chat_session(user=self.owner, title="Apache review", server_id=self.server.id)

        with self.assertRaises(PermissionDenied):
            create_tool_request(user=self.viewer, session=session, tool_key=definition.key)

        tool_request = create_tool_request(user=self.owner, session=session, tool_key=definition.key)
        with self.assertRaises(PermissionDenied):
            approve_tool_request(user=self.viewer, tool_request=tool_request)
