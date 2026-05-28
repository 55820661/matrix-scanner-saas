from datetime import timedelta
import json

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.applications.models import Application
from apps.diagnostics.models import DiagnosticSession, DiagnosticStep
from apps.plans.models import Plan
from apps.servers.models import AgentJob, Finding, ScannerAgent, Server
from apps.subscriptions.models import Subscription
from apps.telegram_integration.models import TelegramChatLink, TelegramDiagnosticState
from apps.telegram_integration.services import handle_update_response
from apps.tools.models import ToolRun
from apps.tools.setup import ensure_baseline_tools


class Sprint9TelegramDiagnosticsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.account = Account.objects.create(name="Acme")
        self.other_account = Account.objects.create(name="Other")
        self.plan = Plan.objects.create(name="Starter", max_servers=5, max_applications=20, max_users=5, max_diagnostic_sessions_per_month=20)
        Subscription.objects.create(
            account=self.account,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            current_period_start=timezone.now() - timedelta(days=1),
            current_period_end=timezone.now() + timedelta(days=30),
        )
        ensure_baseline_tools(connect_active_plans=True, reset_existing=True)
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
        self.server = Server.objects.create(account=self.account, name="Production", status=Server.Status.ACTIVE)
        self.other_server = Server.objects.create(account=self.other_account, name="Other", status=Server.Status.ACTIVE)
        self.agent = ScannerAgent.objects.create(
            account=self.account,
            server=self.server,
            token_hash="hash",
            status=ScannerAgent.Status.ACTIVE,
            registered_at=timezone.now(),
        )
        self.application = Application.objects.create(
            account=self.account,
            server=self.server,
            name="Laravel App",
            path="/home/acme/app",
            framework="laravel",
        )
        self.other_application = Application.objects.create(
            account=self.other_account,
            server=self.other_server,
            name="Other App",
            path="/home/other/app",
        )
        Finding.objects.create(
            account=self.account,
            server=self.server,
            application=self.application,
            title="Debug enabled",
            severity="critical",
            evidence_summary="APP_KEY=raw-secret",
            fingerprint="tg-diag-finding",
        )
        self.link = TelegramChatLink.objects.create(
            account=self.account,
            user=self.owner,
            telegram_chat_id=1001,
            telegram_user_id=9001,
            chat_type=TelegramChatLink.ChatType.PRIVATE,
            title="Owner",
            status=TelegramChatLink.Status.ACTIVE,
            linked_at=timezone.now(),
        )

    def update(self, text, *, chat_id=1001, chat_type="private", user_id=9001):
        return {
            "message": {
                "message_id": 1,
                "text": text,
                "chat": {"id": chat_id, "type": chat_type},
                "from": {"id": user_id, "is_bot": False},
            }
        }

    def callback(self, data, *, chat_id=1001, chat_type="private", user_id=9001):
        return {
            "callback_query": {
                "id": "cb-1",
                "data": data,
                "message": {"message_id": 1, "chat": {"id": chat_id, "type": chat_type}},
                "from": {"id": user_id, "is_bot": False},
            }
        }

    def run_to_confirmation(self):
        handle_update_response(self.update("/diagnose"))
        handle_update_response(self.callback(f"dg:sv:{self.server.id}"))
        handle_update_response(self.callback(f"dg:app:{self.application.id}"))
        handle_update_response(self.callback("dg:pt:custom"))
        return handle_update_response(self.update("DB_PASSWORD=raw-secret"))

    def confirm_session(self):
        self.run_to_confirmation()
        return handle_update_response(self.callback("dg:confirm"))

    def test_unlinked_chat_cannot_start_diagnostics(self):
        response = handle_update_response(self.update("/diagnose", chat_id=2002))

        self.assertIn("not linked", response["text"])
        self.assertEqual(TelegramDiagnosticState.objects.count(), 0)

    def test_group_chat_cannot_start_diagnostics(self):
        TelegramChatLink.objects.create(
            account=self.account,
            telegram_chat_id=-1001,
            chat_type=TelegramChatLink.ChatType.GROUP,
            title="Group",
            status=TelegramChatLink.Status.ACTIVE,
            linked_at=timezone.now(),
        )

        response = handle_update_response(self.update("/diagnose", chat_id=-1001, chat_type="group"))

        self.assertIn("Group chats support alerts", response["text"])
        self.assertEqual(TelegramDiagnosticState.objects.count(), 0)

    def test_viewer_cannot_start_or_approve_diagnostics(self):
        self.link.user = self.viewer
        self.link.save(update_fields=["user", "updated_at"])

        start_response = handle_update_response(self.update("/diagnose"))
        approve_response = handle_update_response(self.update("/approve"))

        self.assertIn("cannot start or approve", start_response["text"])
        self.assertIn("No active diagnostic session", approve_response["text"])

    def test_owner_and_operator_can_start_from_private_chat(self):
        owner_response = handle_update_response(self.update("/diagnose"))
        self.assertIn("Select a server", owner_response["text"])

        TelegramDiagnosticState.objects.all().delete()
        self.link.user = self.operator
        self.link.save(update_fields=["user", "updated_at"])
        operator_response = handle_update_response(self.update("/diagnose"))
        self.assertIn("Select a server", operator_response["text"])

    def test_server_selection_is_account_scoped_and_cross_account_denied(self):
        handle_update_response(self.update("/diagnose"))

        response = handle_update_response(self.callback(f"dg:sv:{self.other_server.id}"))

        self.assertIn("not available", response["text"])
        state = TelegramDiagnosticState.objects.get()
        self.assertIsNone(state.selected_server)

    def test_application_selection_must_match_account_and_server(self):
        handle_update_response(self.update("/diagnose"))
        handle_update_response(self.callback(f"dg:sv:{self.server.id}"))

        response = handle_update_response(self.callback(f"dg:app:{self.other_application.id}"))

        self.assertIn("not available", response["text"])
        state = TelegramDiagnosticState.objects.get()
        self.assertIsNone(state.selected_application)

    def test_one_active_session_per_chat_enforced(self):
        handle_update_response(self.update("/diagnose"))

        response = handle_update_response(self.update("/diagnose"))

        self.assertIn("already active", response["text"])
        self.assertEqual(TelegramDiagnosticState.objects.count(), 1)

    def test_cancel_cancels_state_safely(self):
        handle_update_response(self.update("/diagnose"))

        response = handle_update_response(self.update("/cancel"))

        self.assertIn("cancelled", response["text"])
        state = TelegramDiagnosticState.objects.get()
        self.assertEqual(state.state, TelegramDiagnosticState.State.CANCELLED)

    def test_expired_state_rejected(self):
        handle_update_response(self.update("/diagnose"))
        state = TelegramDiagnosticState.objects.get()
        state.expires_at = timezone.now() - timedelta(minutes=1)
        state.save(update_fields=["expires_at", "updated_at"])

        response = handle_update_response(self.callback(f"dg:sv:{self.server.id}"))

        self.assertIn("No active diagnostic flow", response["text"])
        state.refresh_from_db()
        self.assertEqual(state.state, TelegramDiagnosticState.State.EXPIRED)

    def test_confirm_creates_telegram_source_session(self):
        response = self.confirm_session()

        session = DiagnosticSession.objects.get()
        self.assertIn("Diagnostic session started", response["text"])
        self.assertEqual(session.source, DiagnosticSession.Source.TELEGRAM)
        self.assertEqual(session.source_chat_link, self.link)
        self.assertEqual(session.requested_by, self.owner)
        self.assertNotIn("raw-secret", session.user_prompt_redacted)

    def test_approve_only_next_step_and_repeated_approval_does_not_duplicate_jobs(self):
        self.confirm_session()

        first = handle_update_response(self.update("/approve"))
        second = handle_update_response(self.update("/approve"))

        self.assertIn("Step approved", first["text"])
        self.assertIn("No diagnostic step is waiting", second["text"])
        self.assertEqual(ToolRun.objects.count(), 1)
        self.assertEqual(AgentJob.objects.count(), 1)
        self.assertEqual(ToolRun.objects.get().agent_job, AgentJob.objects.get())

    def test_toolrun_agentjob_created_only_through_diagnostic_policy_path(self):
        self.confirm_session()

        handle_update_response(self.callback("dg:approve"))

        step = DiagnosticStep.objects.get(step_type=DiagnosticStep.StepType.RUN_TOOL)
        self.assertIsNotNone(step.tool_run)
        self.assertIsNotNone(step.tool_run.agent_job)
        self.assertEqual(step.tool_run.requested_by, self.owner)

    def test_final_telegram_report_redacts_secrets(self):
        self.confirm_session()
        handle_update_response(self.update("/approve"))
        tool_run = ToolRun.objects.get()
        tool_run.status = ToolRun.Status.SUCCEEDED
        tool_run.result_redacted = {"APP_KEY": "raw-secret", "hostname": "prod"}
        tool_run.finished_at = timezone.now()
        tool_run.save(update_fields=["status", "result_redacted", "finished_at", "updated_at"])

        response = handle_update_response(self.update("/report"))

        self.assertIn("Diagnostic report", response["text"])
        self.assertNotIn("raw-secret", response["text"])
        self.assertNotIn("AgentJob", response["text"])
        self.assertNotIn("ToolRun", response["text"])

    @override_settings(TELEGRAM_WEBHOOK_SECRET="webhook-secret")
    def test_callback_query_webhook_supported_and_secret_validated(self):
        bad = self.client.post(
            reverse("telegram_integration:webhook", args=["wrong"]),
            data=json.dumps(self.callback("dg:session")),
            content_type="application/json",
        )
        good = self.client.post(
            reverse("telegram_integration:webhook", args=["webhook-secret"]),
            data=json.dumps(self.callback("dg:session")),
            content_type="application/json",
        )

        self.assertEqual(bad.status_code, 403)
        self.assertEqual(good.status_code, 200)

    def test_sprint7_read_only_commands_still_work(self):
        response = handle_update_response(self.update("/servers"))

        self.assertIn("Production", response["text"])

    def test_groups_remain_summaries_only_not_diagnostics(self):
        TelegramChatLink.objects.create(
            account=self.account,
            telegram_chat_id=-2002,
            chat_type=TelegramChatLink.ChatType.SUPERGROUP,
            title="Ops Group",
            status=TelegramChatLink.Status.ACTIVE,
            linked_at=timezone.now(),
        )

        status_response = handle_update_response(self.update("/status", chat_id=-2002, chat_type="supergroup"))
        diagnose_response = handle_update_response(self.update("/diagnose", chat_id=-2002, chat_type="supergroup"))

        self.assertIn("Status for", status_response["text"])
        self.assertIn("Group chats support alerts", diagnose_response["text"])
        self.assertEqual(DiagnosticSession.objects.count(), 0)
