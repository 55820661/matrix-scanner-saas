from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.ai_chat.models import AdminChatDecision, AdminChatMessage, AdminChatSession, AdminChatToolRequest
from apps.ai_chat.services import (
    add_user_message,
    add_user_message_and_response,
    approve_tool_request,
    create_admin_chat_session,
    create_tool_build_request_from_chat,
    create_chat_session,
    create_tool_request,
)
from apps.applications.models import Application
from apps.plans.models import Plan
from apps.reports.models import Report
from apps.servers.models import AgentJob, Finding, ScannerAgent, Server
from apps.subscriptions.models import Subscription
from apps.tools.models import PlanTool, ToolDefinition, ToolPolicy, ToolRun, ToolTemplate
from apps.tools.services import ToolPolicyDenied
from apps.tools.models import ToolBuildProposal, ToolBuildRequest


class AdminChatTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.account = Account.objects.create(name="Acme")
        self.other_account = Account.objects.create(name="Other")
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
        self.staff = User.objects.create_superuser(
            username="staff",
            email="staff@example.com",
            password="password",
        )
        self.server = Server.objects.create(account=self.account, name="Production", status=Server.Status.ACTIVE)
        self.other_server = Server.objects.create(account=self.other_account, name="Other", status=Server.Status.ACTIVE)
        self.plan = Plan.objects.create(name="Pilot", max_servers=5, max_applications=20, max_users=5)
        self.subscription = Subscription.objects.create(
            account=self.account,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            current_period_start=timezone.now() - timedelta(days=1),
            current_period_end=timezone.now() + timedelta(days=30),
        )
        self.agent = ScannerAgent.objects.create(
            account=self.account,
            server=self.server,
            token_hash="agent-token-hash",
            status=ScannerAgent.Status.ACTIVE,
            registered_at=timezone.now(),
        )
        self.application = Application.objects.create(
            account=self.account,
            server=self.server,
            name="Matrix App",
            path="/opt/matrix",
            framework="django",
        )

    def login(self, user):
        self.client.force_login(user)

    def create_tool(self, *, key="chat_safe_tool", plan_enabled=True, allow_customer=True, risk_level=ToolDefinition.RiskLevel.READ_ONLY):
        template = ToolTemplate.objects.create(
            key=f"{key}_template",
            name=f"{key} template",
            runtime_handler_key=key,
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            output_schema={"summary": "object"},
            is_active=True,
        )
        definition = ToolDefinition.objects.create(
            template=template,
            key=key,
            name=key,
            status=ToolDefinition.Status.ENABLED,
            risk_level=risk_level,
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            default_params={},
            timeout_seconds=30,
            max_output_bytes=4096,
        )
        policy = ToolPolicy.objects.create(
            tool_definition=definition,
            allow_customer_run=allow_customer,
            allow_admin_run=True,
            allow_agent_run=True,
            allowed_roles=[User.CustomerRole.OWNER, User.CustomerRole.OPERATOR],
            allowed_server_statuses=[Server.Status.ACTIVE],
            is_active=True,
        )
        plan_tool = PlanTool.objects.create(plan=self.plan, tool_definition=definition, is_enabled=plan_enabled)
        return definition, policy, plan_tool

    def test_owner_can_create_chat_session_with_redacted_snapshot(self):
        session = create_chat_session(
            user=self.owner,
            title="Investigate token=super-secret",
            server_id=self.server.id,
            application_id=self.application.id,
        )

        self.assertEqual(session.account, self.account)
        self.assertEqual(session.server, self.server)
        self.assertEqual(session.application, self.application)
        self.assertIn("[REDACTED]", session.title_redacted)
        self.assertEqual(session.context_snapshot_redacted["context_version"], "1.0")
        self.assertNotIn("super-secret", str(session.context_snapshot_redacted))

    def test_operator_can_create_and_post_message(self):
        self.login(self.operator)

        response = self.client.post(
            reverse("portal:chat_session_start"),
            {"title": "Ops chat", "server_id": self.server.id, "application_id": self.application.id},
        )

        session = AdminChatSession.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(session.user, self.operator)

        detail_response = self.client.post(
            reverse("portal:chat_session_detail", args=[session.id]),
            {"body": "Please check api_key=secret-value"},
        )
        user_message = AdminChatMessage.objects.get(session=session, sender_type=AdminChatMessage.SenderType.USER)
        assistant_message = AdminChatMessage.objects.get(session=session, sender_type=AdminChatMessage.SenderType.ASSISTANT)

        self.assertEqual(detail_response.status_code, 302)
        self.assertIn("[REDACTED]", user_message.body_redacted)
        self.assertNotIn("secret-value", user_message.body_redacted)
        self.assertNotEqual(assistant_message.body_redacted, "")
        self.assertEqual(AdminChatDecision.objects.filter(session=session).count(), 1)

    def test_viewer_can_view_but_cannot_start_or_send(self):
        session = create_chat_session(user=self.owner, title="View only", server_id=self.server.id)
        self.login(self.viewer)

        list_response = self.client.get(reverse("portal:chat_sessions"))
        detail_response = self.client.get(reverse("portal:chat_session_detail", args=[session.id]))
        start_response = self.client.post(reverse("portal:chat_session_start"), {"title": "blocked"})
        post_response = self.client.post(reverse("portal:chat_session_detail", args=[session.id]), {"body": "blocked"})

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "View only")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(start_response.status_code, 403)
        self.assertEqual(post_response.status_code, 403)
        self.assertEqual(AdminChatMessage.objects.count(), 0)

    def test_staff_without_account_is_blocked_from_portal_chat(self):
        self.login(self.staff)

        response = self.client.get(reverse("portal:chat_sessions"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("portal:access_denied"))

    def test_cross_account_server_and_session_are_blocked(self):
        with self.assertRaisesMessage(Exception, "Selected server is not available."):
            create_chat_session(user=self.owner, title="Bad scope", server_id=self.other_server.id)

        other_session = AdminChatSession.objects.create(
            account=self.other_account,
            user=None,
            server=self.other_server,
            title_redacted="Other account",
        )
        self.login(self.owner)

        response = self.client.get(reverse("portal:chat_session_detail", args=[other_session.id]))

        self.assertEqual(response.status_code, 404)

    def test_service_rejects_viewer_message(self):
        session = create_chat_session(user=self.owner, title="View only", server_id=self.server.id)

        with self.assertRaises(PermissionDenied):
            add_user_message(user=self.viewer, session=session, body="blocked")

    def test_chat_does_not_create_toolrun_or_agentjob(self):
        session = create_chat_session(user=self.owner, title="No execution", server_id=self.server.id)

        add_user_message_and_response(user=self.owner, session=session, body="Check services")

        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    def test_deterministic_finding_response_logs_redacted_decision(self):
        Finding.objects.create(
            account=self.account,
            server=self.server,
            title="token=raw-secret exposed",
            severity="critical",
            evidence_summary="token=raw-secret",
            fingerprint="chat-finding-1",
        )
        session = create_chat_session(user=self.owner, title="Findings", server_id=self.server.id)

        _, assistant_message = add_user_message_and_response(user=self.owner, session=session, body="Any critical findings?")
        decision = AdminChatDecision.objects.get(session=session)

        self.assertIn("Findings in safe context", assistant_message.body_redacted)
        self.assertIn("[REDACTED]", assistant_message.body_redacted)
        self.assertNotIn("raw-secret", str(decision.input_context_redacted))
        self.assertNotIn("raw-secret", str(decision.output_json_redacted))
        self.assertEqual(decision.decision_type, AdminChatDecision.DecisionType.ANSWER)

    def test_deterministic_report_response_uses_safe_reports(self):
        Report.objects.create(
            account=self.account,
            server=self.server,
            report_type=Report.ReportType.SERVER_HEALTH,
            title="Server Health",
            summary_redacted="password=[REDACTED]",
        )
        session = create_chat_session(user=self.owner, title="Reports", server_id=self.server.id)

        _, assistant_message = add_user_message_and_response(user=self.owner, session=session, body="Show report summary")

        self.assertIn("Reports in safe context", assistant_message.body_redacted)
        self.assertIn("Server Health", assistant_message.body_redacted)
        self.assertNotIn("password=secret", assistant_message.body_redacted)

    def test_deterministic_tools_response_does_not_execute(self):
        session = create_chat_session(user=self.owner, title="Tools", server_id=self.server.id)

        _, assistant_message = add_user_message_and_response(user=self.owner, session=session, body="What tools are available?")

        self.assertIn("tools", assistant_message.body_redacted.lower())
        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    def test_owner_can_request_and_approve_available_tool(self):
        definition, _policy, _plan_tool = self.create_tool()
        session = create_chat_session(user=self.owner, title="Tool request", server_id=self.server.id)

        tool_request = create_tool_request(user=self.owner, session=session, tool_key=definition.key)
        tool_run = approve_tool_request(user=self.owner, tool_request=tool_request)
        tool_request.refresh_from_db()

        self.assertEqual(tool_request.status, AdminChatToolRequest.Status.QUEUED)
        self.assertEqual(tool_request.tool_run, tool_run)
        self.assertEqual(tool_request.approved_by, self.owner)
        self.assertEqual(ToolRun.objects.count(), 1)
        self.assertEqual(AgentJob.objects.count(), 1)
        self.assertEqual(tool_run.agent_job.tool_key, definition.key)
        self.assertEqual(tool_run.requested_by_type, ToolRun.RequestedByType.USER)

    def test_unavailable_tool_request_is_rejected_before_toolrun(self):
        definition, _policy, plan_tool = self.create_tool(key="disabled_plan_tool", plan_enabled=False)
        session = create_chat_session(user=self.owner, title="Tool request", server_id=self.server.id)

        with self.assertRaises(ValidationError):
            create_tool_request(user=self.owner, session=session, tool_key=definition.key)

        self.assertEqual(AdminChatToolRequest.objects.count(), 0)
        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)
        self.assertFalse(plan_tool.is_enabled)

    def test_tool_policy_denial_blocks_before_job_on_approval(self):
        definition, policy, _plan_tool = self.create_tool(key="policy_denied_tool")
        session = create_chat_session(user=self.owner, title="Tool request", server_id=self.server.id)
        tool_request = create_tool_request(user=self.owner, session=session, tool_key=definition.key)
        policy.allow_customer_run = False
        policy.save(update_fields=["allow_customer_run", "updated_at"])

        with self.assertRaises(ToolPolicyDenied):
            approve_tool_request(user=self.owner, tool_request=tool_request)
        tool_request.refresh_from_db()

        self.assertEqual(tool_request.status, AdminChatToolRequest.Status.FAILED)
        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    def test_plan_tool_denial_blocks_before_job_on_approval(self):
        definition, _policy, plan_tool = self.create_tool(key="plan_denied_tool")
        session = create_chat_session(user=self.owner, title="Tool request", server_id=self.server.id)
        tool_request = create_tool_request(user=self.owner, session=session, tool_key=definition.key)
        plan_tool.is_enabled = False
        plan_tool.save(update_fields=["is_enabled", "updated_at"])

        with self.assertRaises(ToolPolicyDenied):
            approve_tool_request(user=self.owner, tool_request=tool_request)

        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    def test_viewer_cannot_approve_tool_request(self):
        definition, _policy, _plan_tool = self.create_tool(key="viewer_denied_tool")
        session = create_chat_session(user=self.owner, title="Tool request", server_id=self.server.id)
        tool_request = create_tool_request(user=self.owner, session=session, tool_key=definition.key)

        with self.assertRaises(PermissionDenied):
            approve_tool_request(user=self.viewer, tool_request=tool_request)

        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    def test_chat_tool_request_rejects_params_and_write_risk_tools(self):
        definition, _policy, _plan_tool = self.create_tool(
            key="write_risk_tool",
            risk_level=ToolDefinition.RiskLevel.WRITE_ACTION,
        )
        session = create_chat_session(user=self.owner, title="Tool request", server_id=self.server.id)

        with self.assertRaises(ValidationError):
            create_tool_request(user=self.owner, session=session, tool_key=definition.key, params={"path": "/tmp"})
        with self.assertRaises(ValidationError):
            create_tool_request(user=self.owner, session=session, tool_key=definition.key)

        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    def test_owner_can_create_command_template_tool_build_proposal_from_chat(self):
        session = create_admin_chat_session(
            user=self.staff,
            account_id=self.account.id,
            title="Build tool",
            server_id=self.server.id,
        )

        build_request, proposal = create_tool_build_request_from_chat(
            user=self.staff,
            session=session,
            title="Apache 5xx summary",
            desired_tool_key="apache_5xx_summary",
            description="Create a safe Apache summary tool.",
            command_argv_template=["apachectl", "-S"],
            allowed_binaries=["apachectl"],
            blocked_tokens=[";", "&&", "||", "|", ">", "<", "`", "$"],
            expected_output_description="Safe summary counters only.",
        )

        self.assertEqual(build_request.source_chat_session, session)
        self.assertEqual(build_request.desired_execution_type, "command_template")
        self.assertEqual(proposal.status, ToolBuildProposal.Status.PENDING_REVIEW)
        self.assertEqual(proposal.proposed_definition["definition"]["execution_type"], "command_template")
        self.assertFalse(proposal.proposed_policy["is_active"])
        self.assertEqual(ToolDefinition.objects.filter(status=ToolDefinition.Status.ENABLED, key="apache_5xx_summary").count(), 0)
        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    def test_viewer_cannot_create_tool_build_proposal_from_chat(self):
        session = create_admin_chat_session(
            user=self.staff,
            account_id=self.account.id,
            title="Build tool",
            server_id=self.server.id,
        )

        with self.assertRaises(PermissionDenied):
            create_tool_build_request_from_chat(
                user=self.viewer,
                session=session,
                title="Blocked proposal",
                desired_tool_key="blocked_tool",
                command_argv_template=["apachectl", "-S"],
                allowed_binaries=["apachectl"],
            )

        self.assertEqual(ToolBuildRequest.objects.count(), 0)
        self.assertEqual(ToolBuildProposal.objects.count(), 0)

    def test_dangerous_command_template_from_chat_is_rejected_and_not_executed(self):
        session = create_admin_chat_session(
            user=self.staff,
            account_id=self.account.id,
            title="Build tool",
            server_id=self.server.id,
        )

        build_request, proposal = create_tool_build_request_from_chat(
            user=self.staff,
            session=session,
            title="Restart nginx",
            desired_tool_key="restart_nginx",
            command_argv_template=["systemctl", "restart", "nginx"],
            allowed_binaries=["systemctl"],
            blocked_tokens=[";", "&&", "||", "|", ">", "<", "`", "$"],
            expected_output_description="Would restart nginx.",
        )

        self.assertEqual(build_request.status, ToolBuildRequest.Status.PROPOSED)
        self.assertEqual(proposal.status, ToolBuildProposal.Status.VALIDATION_FAILED)
        self.assertTrue(any("forbidden" in error.lower() for error in proposal.validation_errors))
        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    def test_portal_owner_cannot_create_tool_build_proposal_from_portal_chat(self):
        session = create_chat_session(user=self.owner, title="Portal build", server_id=self.server.id)

        with self.assertRaises(PermissionDenied):
            create_tool_build_request_from_chat(
                user=self.owner,
                session=session,
                title="Blocked portal proposal",
                desired_tool_key="blocked_portal_tool",
                command_argv_template=["apachectl", "-S"],
                allowed_binaries=["apachectl"],
            )

        self.assertEqual(ToolBuildRequest.objects.count(), 0)
        self.assertEqual(ToolBuildProposal.objects.count(), 0)
