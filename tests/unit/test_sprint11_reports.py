from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.audit.models import AuditLog
from apps.diagnostics.models import DiagnosticSession
from apps.reports.models import FindingGroup, KnowledgeEntry, Recommendation, Report
from apps.reports.services import (
    create_baseline_report,
    create_diagnostic_report,
    create_findings_summary,
    create_recommendation,
    rebuild_finding_groups,
)
from apps.servers.models import AgentJob, BaselineScan, Finding, ScannerAgent, Server
from apps.telegram_integration.models import TelegramChatLink
from apps.telegram_integration.services import handle_update_response


class Sprint11ReportsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.account = Account.objects.create(name="Customer")
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
        self.other_owner = User.objects.create_user(
            username="other-owner",
            email="other@example.com",
            password="password",
            account=self.other_account,
            role=User.CustomerRole.OWNER,
        )
        self.admin = get_user_model().objects.create_superuser(
            username="matrix-admin",
            email="admin@example.com",
            password="password",
        )
        self.server = Server.objects.create(
            account=self.account,
            name="web-1",
            hostname="web-1.example.com",
            status=Server.Status.ACTIVE,
            agent_status="active",
        )
        self.other_server = Server.objects.create(account=self.other_account, name="other-web")

    def make_baseline_scan(self):
        scan = BaselineScan.objects.create(
            account=self.account,
            server=self.server,
            requested_by=self.admin,
            status=BaselineScan.Status.SUCCEEDED,
            summary={"services": 2, "domains": 1, "applications": 1, "findings": 1, "token": "abc123"},
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )
        Finding.objects.create(
            account=self.account,
            server=self.server,
            baseline_scan=scan,
            severity="critical",
            title="Public env file",
            description="APP_KEY=base64:secret",
            evidence_summary="password=supersecret token=abc123 exposed env summary",
            fingerprint="webroot-env",
        )
        return scan

    def test_baseline_report_uses_redacted_safe_fields_only(self):
        scan = self.make_baseline_scan()
        agent = ScannerAgent.objects.create(
            account=self.account,
            server=self.server,
            token_hash="hash1",
            status=ScannerAgent.Status.ACTIVE,
        )
        AgentJob.objects.create(
            account=self.account,
            server=self.server,
            agent=agent,
            tool_key="application_discovery",
            result={"raw": "DB_PASSWORD=raw-secret"},
        )

        report = create_baseline_report(scan, user=self.admin)
        rendered = f"{report.summary_redacted} {report.source_snapshot_redacted} " + " ".join(
            section.body_redacted + str(section.data_redacted) for section in report.sections.all()
        )

        self.assertNotIn("supersecret", rendered)
        self.assertNotIn("abc123", rendered)
        self.assertNotIn("raw-secret", rendered)
        self.assertIn("[REDACTED]", rendered)

    def test_diagnostic_report_uses_final_redacted_report_only(self):
        session = DiagnosticSession.objects.create(
            account=self.account,
            server=self.server,
            requested_by=self.owner,
            status=DiagnosticSession.Status.SUCCEEDED,
            problem_type=DiagnosticSession.ProblemType.CUSTOM,
            summary_redacted="Safe summary",
            final_report_redacted="Safe final report. token=abc123",
            tool_run_count=0,
        )

        report = create_diagnostic_report(session, user=self.owner)
        rendered = f"{report.summary_redacted} {report.source_snapshot_redacted} " + " ".join(
            section.body_redacted + str(section.data_redacted) for section in report.sections.all()
        )

        self.assertIn("Safe final report", rendered)
        self.assertNotIn("abc123", rendered)

    def test_finding_group_deduplicates_by_normalized_fingerprint(self):
        Finding.objects.create(
            account=self.account,
            server=self.server,
            severity="high",
            title="Same risk",
            evidence_summary="safe",
            fingerprint="WEBROOT-RISK ",
        )
        Finding.objects.create(
            account=self.account,
            server=self.server,
            severity="low",
            title="Same risk again",
            evidence_summary="safe again",
            fingerprint="webroot-risk",
        )

        groups = rebuild_finding_groups(account=self.account, server=self.server)

        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group.occurrence_count, 2)
        self.assertEqual(group.normalized_fingerprint, "webroot-risk")
        self.assertEqual(group.severity, "high")

    def test_cross_account_report_and_finding_group_access_denied_in_portal(self):
        scan = self.make_baseline_scan()
        report = create_baseline_report(scan, user=self.admin)
        rebuild_finding_groups(account=self.account, server=self.server)
        group = FindingGroup.objects.get(account=self.account)
        self.client.force_login(self.other_owner)

        report_response = self.client.get(reverse("portal:report_detail", args=[report.id]))
        group_response = self.client.get(reverse("portal:finding_group_detail", args=[group.id]))

        self.assertEqual(report_response.status_code, 404)
        self.assertEqual(group_response.status_code, 404)

    def test_admin_and_portal_report_visibility(self):
        scan = self.make_baseline_scan()
        create_baseline_report(scan, user=self.admin)

        self.client.force_login(self.admin)
        admin_response = self.client.get("/admin/reports/report/")
        self.assertEqual(admin_response.status_code, 200)

        self.client.force_login(self.owner)
        portal_response = self.client.get(reverse("portal:reports"))
        self.assertContains(portal_response, "Baseline report")

        self.client.force_login(self.other_owner)
        other_response = self.client.get(reverse("portal:reports"))
        self.assertNotContains(other_response, "Baseline report for web-1")

    def test_viewer_cannot_generate_report_but_owner_can(self):
        self.make_baseline_scan()
        self.client.force_login(self.viewer)
        viewer_response = self.client.post(reverse("portal:report_generate"), {"report_type": Report.ReportType.FINDINGS})
        self.assertEqual(viewer_response.status_code, 403)

        self.client.force_login(self.owner)
        owner_response = self.client.post(reverse("portal:report_generate"), {"report_type": Report.ReportType.FINDINGS})

        self.assertEqual(owner_response.status_code, 302)
        self.assertEqual(Report.objects.filter(report_type=Report.ReportType.FINDINGS).count(), 1)

    def test_recommendations_are_advisory_only_and_do_not_execute(self):
        scan = self.make_baseline_scan()
        report = create_baseline_report(scan, user=self.admin)
        before_jobs = AgentJob.objects.count()

        create_recommendation(
            report=report,
            title="Restart service now",
            body="run command to fix button",
            priority="high",
            created_by=self.admin,
        )

        recommendation = Recommendation.objects.latest("created_at")
        self.assertEqual(AgentJob.objects.count(), before_jobs)
        self.assertNotIn("run command", recommendation.body_redacted.lower())
        self.assertNotIn("fix button", recommendation.body_redacted.lower())

    def test_knowledge_entry_redacts_secrets_and_scopes_customer_visibility(self):
        KnowledgeEntry.objects.create(
            scope=KnowledgeEntry.Scope.ACCOUNT,
            account=self.account,
            title="Safe context token=abc123",
            body_redacted="password=supersecret customer note",
            status=KnowledgeEntry.Status.APPROVED,
            visibility=KnowledgeEntry.Visibility.CUSTOMER_VISIBLE,
            created_by=self.admin,
        )

        entry = KnowledgeEntry.objects.get()
        self.assertNotIn("abc123", entry.title)
        self.assertNotIn("supersecret", entry.body_redacted)

        self.client.force_login(self.owner)
        response = self.client.get(reverse("portal:reports"))
        self.assertContains(response, "Safe context")

    def test_telegram_report_summary_is_short_and_redacted(self):
        Report.objects.create(
            account=self.account,
            server=self.server,
            generated_by=self.admin,
            report_type=Report.ReportType.SERVER_HEALTH,
            title="Server health",
            summary_redacted="password=supersecret " + ("safe " * 300),
            generated_at=timezone.now(),
        )
        TelegramChatLink.objects.create(
            account=self.account,
            user=self.owner,
            server=self.server,
            telegram_chat_id=12345,
            telegram_user_id=54321,
            chat_type=TelegramChatLink.ChatType.PRIVATE,
            title="owner",
            status=TelegramChatLink.Status.ACTIVE,
            linked_at=timezone.now(),
        )

        response = handle_update_response(
            {
                "message": {
                    "text": "/report",
                    "chat": {"id": 12345, "type": "private"},
                    "from": {"id": 54321},
                }
            }
        )

        self.assertIn("Latest report", response["text"])
        self.assertNotIn("supersecret", response["text"])
        self.assertLessEqual(len(response["text"]), 1100)

    def test_pdf_email_scheduled_and_execution_side_effects_are_not_implemented(self):
        before_jobs = AgentJob.objects.count()
        scan = self.make_baseline_scan()
        create_findings_summary(self.account, user=self.owner)
        create_baseline_report(scan, user=self.admin)

        self.client.force_login(self.owner)
        pdf_response = self.client.get("/portal/reports/export.pdf")

        self.assertEqual(pdf_response.status_code, 404)
        self.assertEqual(AgentJob.objects.count(), before_jobs)
        self.assertFalse(AuditLog.objects.filter(action__icontains="email").exists())
