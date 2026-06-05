from django.core.exceptions import PermissionDenied
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import Account, User
from apps.ai_chat.models import AdminChatDecision, AdminChatMessage, AdminChatSession
from apps.ai_chat.services import add_user_message, add_user_message_and_response, create_chat_session
from apps.applications.models import Application
from apps.reports.models import Report
from apps.servers.models import AgentJob, Finding, Server
from apps.tools.models import ToolRun


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
        self.application = Application.objects.create(
            account=self.account,
            server=self.server,
            name="Matrix App",
            path="/opt/matrix",
            framework="django",
        )

    def login(self, user):
        self.client.force_login(user)

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
