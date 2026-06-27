from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.ai_chat.models import AdminChatReportDraft, AdminChatSession
from apps.applications.models import Application
from apps.plans.models import Plan
from apps.servers.models import AgentJob, ScannerAgent, Server
from apps.subscriptions.models import Subscription
from apps.tools.models import PlanTool, ToolDefinition, ToolPolicy, ToolRun, ToolTemplate


class SprintC105ChatSplitTests(TestCase):
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
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
        self.server = Server.objects.create(account=self.account, name="web-1", status=Server.Status.ACTIVE)
        self.application = Application.objects.create(
            account=self.account,
            server=self.server,
            name="App",
            path="/opt/app",
            framework="django",
        )
        self.plan = Plan.objects.create(name="Pilot", is_active=True, max_servers=5, max_applications=20, max_users=5)
        Subscription.objects.create(
            account=self.account,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            current_period_start=timezone.now() - timedelta(days=1),
            current_period_end=timezone.now() + timedelta(days=30),
        )
        agent = ScannerAgent.objects.create(
            account=self.account,
            server=self.server,
            token_hash="hash",
            status=ScannerAgent.Status.ACTIVE,
            registered_at=timezone.now(),
        )
        template = ToolTemplate.objects.create(
            key="chat_system_identity_template",
            name="System identity",
            runtime_handler_key="system_identity",
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            output_schema={"summary": "object"},
            is_active=True,
        )
        self.definition = ToolDefinition.objects.create(
            template=template,
            key="chat_system_identity",
            name="System identity",
            status=ToolDefinition.Status.ENABLED,
            risk_level=ToolDefinition.RiskLevel.READ_ONLY,
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            default_params={},
            timeout_seconds=30,
            max_output_bytes=4096,
        )
        ToolPolicy.objects.create(
            tool_definition=self.definition,
            allow_customer_run=True,
            allow_admin_run=True,
            allow_agent_run=True,
            allowed_roles=[User.CustomerRole.OWNER, User.CustomerRole.OPERATOR],
            allowed_server_statuses=[Server.Status.ACTIVE],
            is_active=True,
        )
        PlanTool.objects.create(plan=self.plan, tool_definition=self.definition, is_enabled=True)
        self.agent = agent

    def test_portal_chat_detail_hides_tool_builder_and_old_builder_route_is_gone(self):
        self.client.force_login(self.owner)
        start_response = self.client.post(
            reverse("portal:chat_session_start"),
            {"title": "Portal chat", "server_id": self.server.id},
        )
        self.assertEqual(start_response.status_code, 302)
        session = AdminChatSession.objects.get()

        detail_response = self.client.get(reverse("portal:chat_session_detail", args=[session.id]))
        old_route_response = self.client.post(f"/portal/chat/{session.id}/tool-builder/create/", {})

        self.assertContains(detail_response, "Customer-safe report")
        self.assertNotContains(detail_response, "Tool builder proposal")
        self.assertEqual(old_route_response.status_code, 404)

    def test_staff_can_open_internal_chat_and_create_internal_session(self):
        self.client.force_login(self.admin)

        admin_index_response = self.client.get(reverse("admin:index"))
        list_response = self.client.get(reverse("admin_chat:sessions"))
        start_response = self.client.post(
            reverse("admin_chat:session_start"),
            {"title": "Internal chat", "account_id": self.account.id, "server_id": self.server.id},
        )

        session = AdminChatSession.objects.get(channel=AdminChatSession.Channel.ADMIN_INTERNAL)
        self.assertContains(admin_index_response, "Internal Chat")
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Staff-only internal workspace")
        self.assertEqual(start_response.status_code, 302)
        self.assertEqual(session.account, self.account)
        self.assertEqual(session.server, self.server)

    def test_non_staff_cannot_open_internal_chat(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse("admin_chat:sessions"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_admin_chat_can_create_tool_build_request_and_proposal(self):
        self.client.force_login(self.admin)
        session = AdminChatSession.objects.create(
            account=self.account,
            user=self.admin,
            server=self.server,
            channel=AdminChatSession.Channel.ADMIN_INTERNAL,
            title_redacted="Internal builder",
            last_message_at=timezone.now(),
        )

        detail_response = self.client.get(reverse("admin_chat:session_detail", args=[session.id]))
        builder_page = self.client.get(reverse("admin_chat:tool_builder_page", args=[session.id]))
        response = self.client.post(
            reverse("admin_chat:tool_build_create", args=[session.id]),
            {
                "title": "Apache 5xx summary",
                "desired_tool_key": "apache_5xx_summary",
                "command_argv_template": "apachectl\n-S",
                "allowed_binaries": "apachectl",
                "blocked_tokens": ";\n&&\n||\n|\n>\n<\n`\n$",
                "description": "Create a safe Apache summary tool.",
                "expected_output_description": "Safe summary counters only.",
            },
        )

        session.refresh_from_db()
        self.assertNotContains(detail_response, "<h2>Tool Builder</h2>", html=False)
        self.assertContains(detail_response, reverse("admin_chat:tool_builder_page", args=[session.id]))
        self.assertContains(builder_page, "Tool Builder")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(session.tool_build_requests.count(), 1)
        proposal = session.tool_build_requests.first().proposals.first()
        self.assertIsNotNone(proposal)
        self.assertEqual(proposal.status, "pending_review")

    def test_admin_chat_report_is_auto_converted_without_separate_review(self):
        self.client.force_login(self.admin)
        session = AdminChatSession.objects.create(
            account=self.account,
            user=self.admin,
            server=self.server,
            channel=AdminChatSession.Channel.ADMIN_INTERNAL,
            title_redacted="Internal reports",
            last_message_at=timezone.now(),
        )

        response = self.client.post(
            reverse("admin_chat:report_create", args=[session.id]),
            {"report_type": AdminChatReportDraft.DraftType.TECHNICAL_INTERNAL},
        )
        reports_page = self.client.get(reverse("admin_chat:reports_page", args=[session.id]))

        draft = session.report_drafts.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(draft.status, AdminChatReportDraft.Status.CONVERTED)
        self.assertIsNotNone(draft.converted_report)
        self.assertContains(reports_page, "Reports")
        rendered = f"{draft.converted_report.summary_redacted} {' '.join(section.body_redacted for section in draft.converted_report.sections.all())}"
        self.assertNotIn("stdout_redacted", rendered)
        self.assertNotIn("result_redacted", rendered)

    def test_portal_owner_can_request_ready_tool_only_through_policy_path(self):
        self.client.force_login(self.owner)
        start_response = self.client.post(
            reverse("portal:chat_session_start"),
            {"title": "Portal tool", "server_id": self.server.id},
        )
        self.assertEqual(start_response.status_code, 302)
        session = AdminChatSession.objects.get(channel=AdminChatSession.Channel.PORTAL_CUSTOMER)

        request_response = self.client.post(
            reverse("portal:chat_tool_request_create", args=[session.id]),
            {"tool_key": self.definition.key},
        )
        tool_request = session.tool_requests.get()
        approve_response = self.client.post(reverse("portal:chat_tool_request_approve", args=[session.id, tool_request.id]))

        tool_request.refresh_from_db()
        self.assertEqual(request_response.status_code, 302)
        self.assertEqual(approve_response.status_code, 302)
        self.assertEqual(tool_request.status, "queued")
        self.assertEqual(ToolRun.objects.count(), 1)
        self.assertEqual(AgentJob.objects.count(), 1)
        self.assertEqual(ToolRun.objects.get().requested_by_type, ToolRun.RequestedByType.USER)
