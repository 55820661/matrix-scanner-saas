import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.audit.models import AuditLog
from apps.bootstrap.models import BootstrapCredential, BootstrapSession
from apps.bootstrap.services import cleanup_session_credentials
from apps.plans.models import Plan
from apps.reports.models import Report
from apps.reports.services import create_findings_summary
from apps.servers.models import AgentJob, Finding, ScannerAgent, Server
from apps.subscriptions.models import Subscription
from apps.telegram_integration.models import TelegramChatLink, TelegramLinkToken
from apps.telegram_integration.services import handle_update_response, link_chat_with_code
from apps.tools.models import PlanTool, ToolDefinition, ToolRun
from apps.tools.services import ToolPolicyDenied, create_tool_run_job
from apps.tools.setup import ensure_system_identity_tool


class Sprint12StabilizationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.account = Account.objects.create(name="Customer")
        self.other_account = Account.objects.create(name="Other")
        self.owner = User.objects.create_user(
            username="owner",
            email="owner12@example.com",
            password="password",
            account=self.account,
            role=User.CustomerRole.OWNER,
        )
        self.viewer = User.objects.create_user(
            username="viewer",
            email="viewer12@example.com",
            password="password",
            account=self.account,
            role=User.CustomerRole.VIEWER,
        )
        self.admin = get_user_model().objects.create_superuser(
            username="matrix-admin-12",
            email="admin12@example.com",
            password="password",
        )
        self.server = Server.objects.create(account=self.account, name="web-1", status=Server.Status.ACTIVE)
        self.other_server = Server.objects.create(account=self.other_account, name="other-web", status=Server.Status.ACTIVE)
        self.agent = ScannerAgent.objects.create(
            account=self.account,
            server=self.server,
            token_hash="initial",
            status=ScannerAgent.Status.ACTIVE,
            registered_at=timezone.now(),
            last_seen_at=timezone.now(),
        )
        self.plan = Plan.objects.create(name="Release Plan")
        Subscription.objects.create(account=self.account, plan=self.plan, status=Subscription.Status.ACTIVE)
        _template, self.tool = ensure_system_identity_tool()

    def issue_agent_token(self):
        raw_token = self.agent.issue_token()
        self.agent.save(update_fields=["token_hash", "updated_at"])
        return raw_token

    def test_env_example_contains_release_required_variables(self):
        env_text = Path(".env.example").read_text(encoding="utf-8")

        for key in [
            "DATABASE_URL",
            "DJANGO_SECRET_KEY",
            "DJANGO_DEBUG",
            "DJANGO_ALLOWED_HOSTS",
            "CSRF_TRUSTED_ORIGINS",
            "BOOTSTRAP_CREDENTIAL_ENCRYPTION_KEY",
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_WEBHOOK_SECRET",
            "PUBLIC_BASE_URL",
            "DJANGO_SECURE_PROXY_SSL_HEADER",
            "DJANGO_SESSION_COOKIE_SECURE",
            "DJANGO_CSRF_COOKIE_SECURE",
        ]:
            self.assertIn(f"{key}=", env_text)

    def test_auditlog_redacts_secret_values_and_rejects_secret_keys(self):
        audit = AuditLog.objects.create(
            actor_type=AuditLog.ActorType.SYSTEM,
            account=self.account,
            action="release.secret_value_scan",
            metadata={"note": "password=supersecret", "safe": "ok"},
        )

        self.assertEqual(audit.metadata["note"], "password=[REDACTED]")
        with self.assertRaises(ValidationError):
            AuditLog.objects.create(
                actor_type=AuditLog.ActorType.SYSTEM,
                account=self.account,
                action="release.secret_key_scan",
                metadata={"token": "abc123"},
            )

    def test_staff_without_account_is_blocked_from_portal(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("portal:dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("portal:access_denied"), response["Location"])

    def test_viewer_post_actions_are_denied(self):
        finding = Finding.objects.create(
            account=self.account,
            server=self.server,
            title="Finding",
            severity="high",
            evidence_summary="safe",
            fingerprint="viewer-post-denied",
        )
        self.client.force_login(self.viewer)

        response = self.client.post(reverse("portal:finding_action", args=[finding.id, "acknowledge"]))

        self.assertEqual(response.status_code, 403)

    def test_revoked_and_expired_telegram_link_tokens_are_rejected(self):
        revoked, raw_revoked = TelegramLinkToken.create_for_account(
            account=self.account,
            created_by=self.owner,
            chat_scope=TelegramLinkToken.ChatScope.PRIVATE,
        )
        revoked.revoked_at = timezone.now()
        revoked.save(update_fields=["revoked_at"])
        expired, raw_expired = TelegramLinkToken.create_for_account(
            account=self.account,
            created_by=self.owner,
            chat_scope=TelegramLinkToken.ChatScope.PRIVATE,
        )
        expired.expires_at = timezone.now()
        expired.save(update_fields=["expires_at"])
        update = {"message": {"chat": {"id": 991, "type": "private"}, "from": {"id": 1991}, "text": ""}}

        with self.assertRaises(Exception):
            link_chat_with_code(update, raw_revoked)
        with self.assertRaises(Exception):
            link_chat_with_code(update, raw_expired)

    def test_telegram_cross_account_callback_is_rejected(self):
        other_owner = User.objects.create_user(
            username="other-owner-12",
            email="other12@example.com",
            password="password",
            account=self.other_account,
            role=User.CustomerRole.OWNER,
        )
        TelegramChatLink.objects.create(
            account=self.other_account,
            user=other_owner,
            telegram_chat_id=4567,
            telegram_user_id=7654,
            chat_type=TelegramChatLink.ChatType.PRIVATE,
            status=TelegramChatLink.Status.ACTIVE,
            linked_at=timezone.now(),
        )

        response = handle_update_response(
            {
                "callback_query": {
                    "data": f"dg:sv:{self.server.id}",
                    "message": {"chat": {"id": 4567, "type": "private"}},
                    "from": {"id": 7654},
                }
            }
        )

        self.assertIn("No active diagnostic flow", response["text"])

    def test_bootstrap_credential_cleanup_clears_payload(self):
        session = BootstrapSession.objects.create(
            account=self.account,
            server=self.server,
            created_by=self.admin,
            target_host="127.0.0.1",
            ssh_user="root",
            auth_method=BootstrapSession.AuthMethod.PASSWORD,
            confirm_package_install=True,
        )
        credential = BootstrapCredential.objects.create(
            session=session,
            credential_type=BootstrapCredential.CredentialType.SSH_PASSWORD,
            encrypted_payload="encrypted-password",
            expires_at=BootstrapCredential.default_expiry(),
        )

        cleanup_session_credentials(session)

        credential.refresh_from_db()
        self.assertEqual(credential.encrypted_payload, "")
        self.assertIsNotNone(credential.destroyed_at)

    def test_inactive_or_revoked_agent_token_denied(self):
        raw_token = self.issue_agent_token()
        self.agent.status = ScannerAgent.Status.REVOKED
        self.agent.revoked_at = timezone.now()
        self.agent.save(update_fields=["status", "revoked_at", "updated_at"])

        response = self.client.post(
            "/api/agent/heartbeat/",
            data=json.dumps({"agent_version": "1.0"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 401)

    def test_agentjob_terminal_double_submit_is_rejected(self):
        PlanTool.objects.get_or_create(plan=self.plan, tool_definition=self.tool)
        raw_token = self.issue_agent_token()
        _tool_run, job = create_tool_run_job(account=self.account, server=self.server, tool_key=self.tool.key)
        self.client.get("/api/agent/jobs/next/", HTTP_AUTHORIZATION=f"Bearer {raw_token}")
        first = self.client.post(
            f"/api/agent/jobs/{job.id}/result/",
            data=json.dumps({"status": AgentJob.Status.SUCCEEDED, "output": {"hostname": "web-1"}}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )
        second = self.client.post(
            f"/api/agent/jobs/{job.id}/result/",
            data=json.dumps({"status": AgentJob.Status.SUCCEEDED, "output": {"hostname": "web-1"}}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)
        self.assertIn("terminal", second.json()["error"])

    def test_toolpolicy_denial_happens_before_toolrun_or_agentjob(self):
        self.tool.status = ToolDefinition.Status.DISABLED
        self.tool.save(update_fields=["status", "updated_at"])

        with self.assertRaises(ToolPolicyDenied):
            create_tool_run_job(account=self.account, server=self.server, tool_key=self.tool.key, requested_by=self.owner)

        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    def test_raw_agentjob_result_not_displayed_in_admin_telegram_or_reports(self):
        raw_secret = "DB_PASSWORD=raw-secret"
        job = AgentJob.objects.create(
            account=self.account,
            server=self.server,
            agent=self.agent,
            tool_key="system_identity",
            status=AgentJob.Status.SUCCEEDED,
            result={"raw": raw_secret},
        )
        Finding.objects.create(
            account=self.account,
            server=self.server,
            title="Safe finding",
            severity="info",
            evidence_summary="safe evidence",
            fingerprint="safe-finding",
        )
        report = create_findings_summary(self.account, user=self.owner)
        TelegramChatLink.objects.create(
            account=self.account,
            user=self.owner,
            server=self.server,
            telegram_chat_id=8888,
            telegram_user_id=888,
            chat_type=TelegramChatLink.ChatType.PRIVATE,
            status=TelegramChatLink.Status.ACTIVE,
            linked_at=timezone.now(),
        )
        self.client.force_login(self.admin)
        admin_response = self.client.get(f"/admin/servers/agentjob/{job.id}/change/")
        telegram_response = handle_update_response(
            {
                "message": {
                    "text": "/report",
                    "chat": {"id": 8888, "type": "private"},
                    "from": {"id": 888},
                }
            }
        )
        rendered_report = f"{report.summary_redacted} {report.source_snapshot_redacted} " + " ".join(
            section.body_redacted + str(section.data_redacted) for section in report.sections.all()
        )

        self.assertNotContains(admin_response, raw_secret)
        self.assertNotIn(raw_secret, telegram_response["text"])
        self.assertNotIn(raw_secret, rendered_report)
