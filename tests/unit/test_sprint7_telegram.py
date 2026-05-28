from datetime import timedelta
import json

from django.apps import apps as django_apps
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.applications.models import Application
from apps.audit.models import AuditLog
from apps.core.tokens import generate_raw_token, hash_token
from apps.servers.models import AgentJob, BaselineScan, Finding, ScannerAgent, Server
from apps.telegram_integration.models import TelegramChatLink, TelegramLinkToken, TelegramNotification
from apps.telegram_integration.services import (
    create_notification,
    handle_update,
    link_chat_with_code,
)
from apps.tools.models import ToolRun


class Sprint7TelegramTests(TestCase):
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
        self.server = Server.objects.create(account=self.account, name="Production", status=Server.Status.ACTIVE)
        self.other_server = Server.objects.create(account=self.other_account, name="Other", status=Server.Status.ACTIVE)
        self.agent = ScannerAgent.objects.create(
            account=self.account,
            server=self.server,
            token_hash="hash",
            status=ScannerAgent.Status.ACTIVE,
        )
        self.application = Application.objects.create(
            account=self.account,
            server=self.server,
            name="Laravel App",
            domain="app.example.com",
            path="/home/acme/app",
            framework="laravel",
            review_status=Application.ReviewStatus.PENDING_REVIEW,
        )
        Application.objects.create(
            account=self.other_account,
            server=self.other_server,
            name="Other App",
            domain="other.example.com",
            path="/home/other/app",
        )
        self.finding = Finding.objects.create(
            account=self.account,
            server=self.server,
            application=self.application,
            title="Exposed env",
            severity="critical",
            evidence_summary="DB_PASSWORD=raw-secret",
            fingerprint="finding-1",
        )
        Finding.objects.create(
            account=self.other_account,
            server=self.other_server,
            title="Other finding",
            severity="high",
            evidence_summary="safe",
            fingerprint="finding-2",
        )
        BaselineScan.objects.create(
            account=self.account,
            server=self.server,
            status=BaselineScan.Status.SUCCEEDED,
            summary={"applications": 1, "findings": 1, "services": 1, "unsafe": "raw-secret"},
            started_at=timezone.now() - timedelta(minutes=5),
            finished_at=timezone.now(),
        )

    def update(self, *, chat_id=1001, chat_type="private", text="/help", user_id=9001, title="Acme Chat"):
        return {
            "message": {
                "message_id": 1,
                "text": text,
                "chat": {"id": chat_id, "type": chat_type, "title": title},
                "from": {"id": user_id, "is_bot": False, "first_name": "Tester"},
            }
        }

    def login(self, user):
        self.client.force_login(user)

    def link_private_chat(self, account=None, user=None, chat_id=1001):
        account = account or self.account
        user = user or self.owner
        token, raw_code = TelegramLinkToken.create_for_account(
            account=account,
            created_by=user,
            chat_scope=TelegramLinkToken.ChatScope.PRIVATE,
        )
        link = link_chat_with_code(self.update(chat_id=chat_id, text=f"/link {raw_code}"), raw_code)
        return token, raw_code, link

    def test_link_token_is_hashed_and_raw_shown_once(self):
        self.login(self.owner)

        response = self.client.post(reverse("portal:telegram"), {"chat_scope": "private"})

        self.assertEqual(response.status_code, 200)
        token = TelegramLinkToken.objects.get(account=self.account)
        content = response.content.decode()
        self.assertIn("One-time link code", content)
        self.assertNotIn(token.token_hash, content)
        self.assertTrue(AuditLog.objects.filter(action="portal.telegram_link_issued", account=self.account).exists())

    def test_expired_revoked_and_used_link_tokens_are_rejected(self):
        for field in ("expired", "revoked", "used"):
            raw_code = generate_raw_token()
            token = TelegramLinkToken.objects.create(
                account=self.account,
                created_by=self.owner,
                token_hash=hash_token(raw_code),
                chat_scope=TelegramLinkToken.ChatScope.PRIVATE,
                expires_at=timezone.now() + timedelta(minutes=30),
            )
            if field == "expired":
                token.expires_at = timezone.now() - timedelta(minutes=1)
            elif field == "revoked":
                token.revoked_at = timezone.now()
            else:
                token.used_at = timezone.now()
            token.save()

            response = handle_update(self.update(chat_id=2000 + token.id, text=f"/link {raw_code}"))

            self.assertIn("invalid, expired, revoked, or already used", response)

    def test_private_chat_link_scopes_to_account_and_user(self):
        _token, _raw_code, link = self.link_private_chat()

        self.assertEqual(link.account, self.account)
        self.assertEqual(link.user, self.owner)
        self.assertEqual(link.chat_type, TelegramChatLink.ChatType.PRIVATE)
        self.assertTrue(link.is_active)

    def test_group_chat_linking_is_owner_only(self):
        self.login(self.owner)
        owner_response = self.client.post(reverse("portal:telegram"), {"chat_scope": "group"})
        self.assertEqual(owner_response.status_code, 200)

        self.login(self.operator)
        operator_response = self.client.post(reverse("portal:telegram"), {"chat_scope": "group"})
        self.assertEqual(operator_response.status_code, 403)

        self.login(self.viewer)
        viewer_response = self.client.post(reverse("portal:telegram"), {"chat_scope": "private"})
        self.assertEqual(viewer_response.status_code, 403)

    def test_unlinked_chat_can_only_get_linking_help(self):
        response = handle_update(self.update(text="/servers"))
        help_response = handle_update(self.update(text="/help"))

        self.assertIn("not linked", response)
        self.assertIn("Link this chat", help_response)

    def test_servers_command_only_shows_linked_account_data(self):
        self.link_private_chat()

        response = handle_update(self.update(text="/servers"))

        self.assertIn("Production", response)
        self.assertNotIn("Other", response)

    def test_cross_account_chat_cannot_fetch_other_account_data(self):
        self.link_private_chat(account=self.account, user=self.owner, chat_id=1001)
        other_user = User.objects.create_user(
            username="other_owner",
            email="other@example.com",
            password="password",
            account=self.other_account,
            role=User.CustomerRole.OWNER,
        )
        self.link_private_chat(account=self.other_account, user=other_user, chat_id=2002)

        first_response = handle_update(self.update(chat_id=1001, text="/apps"))
        second_response = handle_update(self.update(chat_id=2002, text="/apps"))

        self.assertIn("Laravel App", first_response)
        self.assertNotIn("Other App", first_response)
        self.assertIn("Other App", second_response)
        self.assertNotIn("Laravel App", second_response)

    def test_viewer_commands_are_read_only(self):
        TelegramChatLink.objects.create(
            account=self.account,
            user=self.viewer,
            telegram_chat_id=3003,
            telegram_user_id=3003,
            chat_type=TelegramChatLink.ChatType.PRIVATE,
            status=TelegramChatLink.Status.ACTIVE,
            linked_at=timezone.now(),
        )
        jobs_before = AgentJob.objects.count()
        runs_before = ToolRun.objects.count()

        response = handle_update(self.update(chat_id=3003, text="/status"))

        self.assertIn("Status for", response)
        self.assertEqual(AgentJob.objects.count(), jobs_before)
        self.assertEqual(ToolRun.objects.count(), runs_before)

    def test_notifications_are_redacted_and_duplicate_dedupe_is_suppressed(self):
        _token, _raw_code, link = self.link_private_chat()

        first = create_notification(
            chat_link=link,
            notification_type=TelegramNotification.NotificationType.FINDING_CREATED,
            finding=self.finding,
            payload={"message": "DB_PASSWORD=raw-secret", "api_token": "another-secret"},
            dedupe_key="finding-1",
        )
        second = create_notification(
            chat_link=link,
            notification_type=TelegramNotification.NotificationType.FINDING_CREATED,
            finding=self.finding,
            payload={"message": "DB_PASSWORD=raw-secret"},
            dedupe_key="finding-1",
        )

        self.assertNotIn("raw-secret", json.dumps(first.payload_redacted))
        self.assertNotIn("another-secret", json.dumps(first.payload_redacted))
        self.assertEqual(first.status, TelegramNotification.Status.PENDING)
        self.assertEqual(second.status, TelegramNotification.Status.SUPPRESSED)

    def test_required_events_create_safe_notification_records(self):
        self.link_private_chat()

        finding = Finding.objects.create(
            account=self.account,
            server=self.server,
            title="Critical issue",
            severity="high",
            evidence_summary="private_key=raw-secret",
            fingerprint="finding-signal",
        )
        self.server.agent_status = "offline"
        self.server.save(update_fields=["agent_status", "updated_at"])

        finding_notification = TelegramNotification.objects.get(
            notification_type=TelegramNotification.NotificationType.FINDING_CREATED,
            finding=finding,
        )
        offline_notification = TelegramNotification.objects.get(
            notification_type=TelegramNotification.NotificationType.AGENT_OFFLINE,
            server=self.server,
        )
        self.assertNotIn("raw-secret", json.dumps(finding_notification.payload_redacted))
        self.assertEqual(offline_notification.status, TelegramNotification.Status.PENDING)

    @override_settings(TELEGRAM_WEBHOOK_SECRET="webhook-secret")
    def test_webhook_secret_is_required(self):
        response = self.client.post(
            reverse("telegram_integration:webhook", args=["wrong"]),
            data=json.dumps(self.update(text="/help")),
            content_type="application/json",
        )
        ok_response = self.client.post(
            reverse("telegram_integration:webhook", args=["webhook-secret"]),
            data=json.dumps(self.update(text="/help")),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(ok_response.status_code, 200)

    def test_telegram_commands_create_no_diagnostic_toolrun_or_agentjob(self):
        self.link_private_chat()
        jobs_before = AgentJob.objects.count()
        runs_before = ToolRun.objects.count()
        try:
            diagnostic_session = django_apps.get_model("diagnostics", "DiagnosticSession")
            diagnostics_before = diagnostic_session.objects.count()
        except LookupError:
            diagnostic_session = None
            diagnostics_before = 0

        response = handle_update(self.update(text="/servers"))

        self.assertIn("Production", response)
        self.assertEqual(AgentJob.objects.count(), jobs_before)
        self.assertEqual(ToolRun.objects.count(), runs_before)
        if diagnostic_session:
            self.assertEqual(diagnostic_session.objects.count(), diagnostics_before)

    def test_raw_outputs_and_secrets_are_not_in_telegram_responses(self):
        AgentJob.objects.create(
            account=self.account,
            server=self.server,
            agent=self.agent,
            tool_key="system_identity",
            result={"DB_PASSWORD": "raw-secret", "safe": "ok"},
            status=AgentJob.Status.SUCCEEDED,
        )
        self.application.metadata = {"laravel_env": {"DB_PASSWORD": "raw-secret"}}
        self.application.save(update_fields=["metadata", "updated_at"])
        self.link_private_chat()

        responses = [
            handle_update(self.update(text="/apps")),
            handle_update(self.update(text="/findings")),
            handle_update(self.update(text="/baseline")),
            handle_update(self.update(text="/status")),
        ]
        combined = "\n".join(responses)

        self.assertNotIn("raw-secret", combined)
        self.assertNotIn("AgentJob", combined)
        self.assertNotIn("ToolRun", combined)
