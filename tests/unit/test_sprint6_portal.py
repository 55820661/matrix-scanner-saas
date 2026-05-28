from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.applications.models import Application
from apps.audit.models import AuditLog
from apps.plans.models import Plan
from apps.servers.models import AgentJob, AgentRegistrationToken, BaselineScan, Finding, ScannerAgent, Server
from apps.subscriptions.models import Subscription


class Sprint6PortalTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.account = Account.objects.create(name="Acme")
        self.other_account = Account.objects.create(name="Other")
        self.plan = Plan.objects.create(name="Starter", max_servers=5, max_applications=20, max_users=5)
        self.subscription = Subscription.objects.create(
            account=self.account,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            current_period_start=timezone.now() - timedelta(days=1),
            current_period_end=timezone.now() + timedelta(days=30),
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
        self.staff = User.objects.create_superuser(
            username="staff",
            email="staff@example.com",
            password="password",
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
            metadata={"laravel_env": {"APP_ENV": "production", "DB_PASSWORD": "secret"}},
            review_status=Application.ReviewStatus.PENDING_REVIEW,
        )
        self.other_application = Application.objects.create(
            account=self.other_account,
            server=self.other_server,
            name="Other App",
            domain="other.example.com",
            path="/home/other/app",
            review_status=Application.ReviewStatus.PENDING_REVIEW,
        )
        self.finding = Finding.objects.create(
            account=self.account,
            server=self.server,
            application=self.application,
            title="Exposed env",
            severity="critical",
            evidence_summary="DB_PASSWORD=[REDACTED]",
            fingerprint="finding-1",
        )
        self.other_finding = Finding.objects.create(
            account=self.other_account,
            server=self.other_server,
            title="Other finding",
            severity="high",
            evidence_summary="safe",
            fingerprint="finding-2",
        )

    def login(self, user):
        self.client.force_login(user)

    def test_portal_requires_login(self):
        response = self.client.get(reverse("portal:dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("portal:login"), response["Location"])

    def test_staff_without_account_is_blocked(self):
        self.login(self.staff)

        response = self.client.get(reverse("portal:dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("portal:access_denied"))

    def test_customer_sees_only_own_account_data(self):
        self.login(self.owner)

        response = self.client.get(reverse("portal:servers"))
        content = response.content.decode()

        self.assertContains(response, "Production")
        self.assertNotIn("Other", content)

    def test_cross_account_url_ids_return_404(self):
        self.login(self.owner)

        response = self.client.get(reverse("portal:server_detail", args=[self.other_server.id]))

        self.assertEqual(response.status_code, 404)

    def test_viewer_cannot_post_actions(self):
        self.login(self.viewer)

        app_response = self.client.post(reverse("portal:application_action", args=[self.application.id, "approve"]))
        finding_response = self.client.post(reverse("portal:finding_action", args=[self.finding.id, "acknowledge"]))

        self.assertEqual(app_response.status_code, 403)
        self.assertEqual(finding_response.status_code, 403)

    def test_owner_can_add_server(self):
        self.login(self.owner)

        response = self.client.post(
            reverse("portal:server_add"),
            {"name": "New Server", "hostname": "new.example.com", "public_ip": ""},
        )

        self.assertEqual(response.status_code, 302)
        server = Server.objects.get(name="New Server")
        self.assertEqual(server.account, self.account)
        self.assertEqual(server.status, Server.Status.PENDING)
        self.assertEqual(AgentRegistrationToken.objects.filter(server=server).count(), 0)

    def test_owner_can_generate_registration_token_once(self):
        self.login(self.owner)

        response = self.client.post(reverse("portal:registration_token", args=[self.server.id]))

        self.assertEqual(response.status_code, 200)
        token = AgentRegistrationToken.objects.get(server=self.server)
        content = response.content.decode()
        self.assertIn("Raw token", content)
        self.assertNotIn(token.token_hash, content)
        self.assertEqual(token.created_by, self.owner)
        self.assertGreater(token.expires_at, timezone.now())
        self.assertTrue(AuditLog.objects.filter(action="portal.registration_issued", account=self.account).exists())

    def test_raw_registration_token_is_not_stored(self):
        self.login(self.owner)

        response = self.client.post(reverse("portal:registration_token", args=[self.server.id]))
        token = AgentRegistrationToken.objects.get(server=self.server)
        content = response.content.decode()

        self.assertNotEqual(token.token_hash, "")
        self.assertNotIn("registration_token", AuditLog.objects.get(action="portal.registration_issued").metadata)
        self.assertNotIn(token.token_hash, content)

    def test_operator_cannot_generate_registration_token(self):
        self.login(self.operator)

        response = self.client.post(reverse("portal:registration_token", args=[self.server.id]))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(AgentRegistrationToken.objects.count(), 0)

    def test_operator_can_approve_ignore_applications_and_acknowledge_findings(self):
        self.login(self.operator)

        approve_response = self.client.post(reverse("portal:application_action", args=[self.application.id, "approve"]))
        self.application.refresh_from_db()
        self.assertEqual(approve_response.status_code, 302)
        self.assertEqual(self.application.review_status, Application.ReviewStatus.APPROVED)

        ignore_response = self.client.post(reverse("portal:application_action", args=[self.application.id, "ignore"]))
        self.application.refresh_from_db()
        self.assertEqual(ignore_response.status_code, 302)
        self.assertEqual(self.application.review_status, Application.ReviewStatus.IGNORED)

        ack_response = self.client.post(reverse("portal:finding_action", args=[self.finding.id, "acknowledge"]))
        self.finding.refresh_from_db()
        self.assertEqual(ack_response.status_code, 302)
        self.assertEqual(self.finding.status, Finding.Status.ACKNOWLEDGED)

    def test_viewer_cannot_approve_ignore_archive_or_acknowledge(self):
        self.login(self.viewer)

        for action in ("approve", "ignore", "archive"):
            response = self.client.post(reverse("portal:application_action", args=[self.application.id, action]))
            self.assertEqual(response.status_code, 403)
        response = self.client.post(reverse("portal:finding_action", args=[self.finding.id, "acknowledge"]))
        self.assertEqual(response.status_code, 403)

    def test_application_actions_work_and_audit(self):
        self.login(self.owner)

        for action, expected_status in (
            ("approve", Application.ReviewStatus.APPROVED),
            ("ignore", Application.ReviewStatus.IGNORED),
            ("archive", Application.ReviewStatus.ARCHIVED),
        ):
            response = self.client.post(reverse("portal:application_action", args=[self.application.id, action]))
            self.application.refresh_from_db()
            self.assertEqual(response.status_code, 302)
            self.assertEqual(self.application.review_status, expected_status)
            self.assertTrue(AuditLog.objects.filter(action=f"portal.application.{action}").exists())

    def test_finding_actions_work_and_audit(self):
        self.login(self.owner)

        ack_response = self.client.post(reverse("portal:finding_action", args=[self.finding.id, "acknowledge"]))
        self.finding.refresh_from_db()
        self.assertEqual(ack_response.status_code, 302)
        self.assertEqual(self.finding.status, Finding.Status.ACKNOWLEDGED)
        self.assertTrue(AuditLog.objects.filter(action="portal.finding.acknowledge").exists())

        ignore_response = self.client.post(reverse("portal:finding_action", args=[self.finding.id, "ignore"]))
        self.finding.refresh_from_db()
        self.assertEqual(ignore_response.status_code, 302)
        self.assertEqual(self.finding.status, Finding.Status.IGNORED)
        self.assertTrue(AuditLog.objects.filter(action="portal.finding.ignore").exists())

    def test_subscription_page_is_read_only(self):
        self.login(self.owner)

        response = self.client.get(reverse("portal:subscription"))
        post_response = self.client.post(reverse("portal:subscription"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Billing changes and payments are not available")
        self.assertEqual(post_response.status_code, 405)

    def test_remote_bootstrap_is_unavailable_from_portal(self):
        self.login(self.owner)

        response = self.client.get("/portal/bootstrap/")

        self.assertEqual(response.status_code, 404)

    def test_no_raw_toolrun_agentjob_output_or_secrets_displayed(self):
        AgentJob.objects.create(
            account=self.account,
            server=self.server,
            agent=self.agent,
            tool_key="system_identity",
            result={"DB_PASSWORD": "raw-secret", "safe": "ok"},
            status=AgentJob.Status.SUCCEEDED,
        )
        BaselineScan.objects.create(
            account=self.account,
            server=self.server,
            status=BaselineScan.Status.SUCCEEDED,
            summary={"applications": 1, "findings": 1, "services": 1, "unsafe": "raw-secret"},
        )
        self.login(self.owner)

        server_response = self.client.get(reverse("portal:server_detail", args=[self.server.id]))
        app_response = self.client.get(reverse("portal:application_detail", args=[self.application.id]))
        baseline_response = self.client.get(reverse("portal:baseline_scans"))

        combined = server_response.content.decode() + app_response.content.decode() + baseline_response.content.decode()
        self.assertNotIn("raw-secret", combined)
        self.assertNotIn("DB_PASSWORD", combined)
        self.assertNotIn("AgentJob", combined)
