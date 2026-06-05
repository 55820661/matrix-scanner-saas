from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.ai_chat.models import AdminChatDecision, AdminChatMessage, AdminChatReportDraft
from apps.ai_chat.services import (
    convert_chat_report_draft,
    create_chat_report_draft,
    create_chat_session,
    review_chat_report_draft,
)
from apps.applications.models import Application
from apps.plans.models import Plan
from apps.reports.models import Report
from apps.servers.models import BaselineScan, Finding, ScannerAgent, Server
from apps.subscriptions.models import Subscription
from apps.tools.models import ToolDefinition, ToolRun, ToolTemplate


class SprintC9ChatReportsTests(TestCase):
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
        self.other_owner = User.objects.create_user(
            username="other-owner",
            email="other@example.com",
            password="password",
            account=self.other_account,
            role=User.CustomerRole.OWNER,
        )
        self.admin = User.objects.create_superuser(
            username="admin",
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
            current_period_start=timezone.now(),
        )
        agent = ScannerAgent.objects.create(
            account=self.account,
            server=self.server,
            token_hash="hash",
            status=ScannerAgent.Status.ACTIVE,
            registered_at=timezone.now(),
        )
        template = ToolTemplate.objects.create(
            key="apache_5xx_summary_template",
            name="Apache summary template",
            runtime_handler_key="",
            execution_type=ToolTemplate.ExecutionType.COMMAND_TEMPLATE,
            command_argv_template=["awk", "BEGIN{{print 0}}", "/usr/local/apache/logs/access_log"],
            allowed_binaries=["awk"],
            blocked_tokens=[";", "&&", "||", "|", ">", "<", "`", "$"],
            is_active=True,
        )
        definition = ToolDefinition.objects.create(
            template=template,
            key="apache_5xx_summary",
            name="Apache 5xx summary",
            status=ToolDefinition.Status.ENABLED,
            risk_level=ToolDefinition.RiskLevel.READ_ONLY,
            execution_type=ToolTemplate.ExecutionType.COMMAND_TEMPLATE,
            timeout_seconds=30,
            max_output_bytes=4096,
        )
        ToolRun.objects.create(
            account=self.account,
            server=self.server,
            agent=agent,
            tool_definition=definition,
            status=ToolRun.Status.SUCCEEDED,
            requested_by=self.owner,
            requested_by_type=ToolRun.RequestedByType.USER,
            result_redacted={
                "output": {
                    "command": {
                        "stdout_redacted": "500 count=12 password=raw-secret",
                        "stderr_redacted": "",
                        "exit_code": 0,
                        "execution_time_seconds": 0.1,
                        "truncated": False,
                    }
                }
            },
            error_message="token=abc123",
            finished_at=timezone.now(),
        )
        scan = BaselineScan.objects.create(
            account=self.account,
            server=self.server,
            requested_by=self.admin,
            status=BaselineScan.Status.SUCCEEDED,
            summary={"services": 5, "domains": 2, "applications": 1, "findings": 1, "token": "abc123"},
        )
        Finding.objects.create(
            account=self.account,
            server=self.server,
            application=self.application,
            baseline_scan=scan,
            severity="high",
            title="HTTP 500 spike",
            evidence_summary="error rate increased, password=supersecret",
            fingerprint="http-500",
        )

    def test_owner_can_create_technical_report_draft_without_final_report(self):
        session = create_chat_session(user=self.owner, title="Reports", server_id=self.server.id, application_id=self.application.id)

        draft = create_chat_report_draft(
            user=self.owner,
            session=session,
            report_type=AdminChatReportDraft.DraftType.TECHNICAL_INTERNAL,
        )

        rendered = f"{draft.title_redacted} {draft.summary_redacted} {draft.sections_redacted} {draft.source_snapshot_redacted}"
        self.assertEqual(draft.status, AdminChatReportDraft.Status.PENDING_REVIEW)
        self.assertEqual(draft.report_type, AdminChatReportDraft.DraftType.TECHNICAL_INTERNAL)
        self.assertEqual(Report.objects.count(), 0)
        self.assertNotIn("raw-secret", rendered)
        self.assertNotIn("supersecret", rendered)
        self.assertNotIn("abc123", rendered)
        self.assertNotIn("stdout_redacted", rendered)
        self.assertTrue(
            AdminChatDecision.objects.filter(
                session=session,
                decision_type=AdminChatDecision.DecisionType.REPORT_REQUEST,
                output_json_redacted__report_draft_id=str(draft.id),
            ).exists()
        )

    def test_customer_and_technical_drafts_are_distinct(self):
        session = create_chat_session(user=self.owner, title="Reports", server_id=self.server.id)

        technical = create_chat_report_draft(
            user=self.owner,
            session=session,
            report_type=AdminChatReportDraft.DraftType.TECHNICAL_INTERNAL,
        )
        customer = create_chat_report_draft(
            user=self.owner,
            session=session,
            report_type=AdminChatReportDraft.DraftType.CUSTOMER_SUMMARY,
        )

        self.assertNotEqual(technical.report_type, customer.report_type)
        self.assertNotEqual(technical.title_redacted, customer.title_redacted)
        self.assertNotEqual(str(technical.sections_redacted), str(customer.sections_redacted))

    def test_viewer_cannot_create_report_draft(self):
        session = create_chat_session(user=self.owner, title="Reports", server_id=self.server.id)

        with self.assertRaises(PermissionDenied):
            create_chat_report_draft(
                user=self.viewer,
                session=session,
                report_type=AdminChatReportDraft.DraftType.CUSTOMER_SUMMARY,
            )

        self.assertEqual(AdminChatReportDraft.objects.count(), 0)

    def test_matrix_admin_review_and_convert_required_for_final_report(self):
        session = create_chat_session(user=self.owner, title="Reports", server_id=self.server.id)
        draft = create_chat_report_draft(
            user=self.owner,
            session=session,
            report_type=AdminChatReportDraft.DraftType.CUSTOMER_SUMMARY,
        )

        with self.assertRaises(ValidationError):
            convert_chat_report_draft(draft, reviewer=self.admin)

        review_chat_report_draft(draft, reviewer=self.admin, decision=AdminChatReportDraft.Status.APPROVED)
        report = convert_chat_report_draft(draft, reviewer=self.admin)
        draft.refresh_from_db()

        self.assertEqual(report.report_type, Report.ReportType.CUSTOMER_SUMMARY)
        self.assertEqual(draft.status, AdminChatReportDraft.Status.CONVERTED)
        self.assertEqual(draft.converted_report, report)
        self.assertEqual(report.sections.count(), len(draft.sections_redacted))

    def test_non_admin_cannot_review_or_convert(self):
        session = create_chat_session(user=self.owner, title="Reports", server_id=self.server.id)
        draft = create_chat_report_draft(
            user=self.owner,
            session=session,
            report_type=AdminChatReportDraft.DraftType.TECHNICAL_INTERNAL,
        )

        with self.assertRaises(PermissionDenied):
            review_chat_report_draft(draft, reviewer=self.owner, decision=AdminChatReportDraft.Status.APPROVED)
        with self.assertRaises(PermissionDenied):
            convert_chat_report_draft(draft, reviewer=self.owner)

    def test_portal_owner_can_create_draft_and_viewer_cannot_post(self):
        session = create_chat_session(user=self.owner, title="Reports", server_id=self.server.id)
        self.client.force_login(self.owner)
        owner_response = self.client.post(
            reverse("portal:chat_report_draft_create", args=[session.id]),
            {"report_type": AdminChatReportDraft.DraftType.CUSTOMER_SUMMARY},
        )
        self.assertEqual(owner_response.status_code, 302)
        self.assertEqual(AdminChatReportDraft.objects.count(), 1)

        self.client.force_login(self.viewer)
        viewer_response = self.client.post(
            reverse("portal:chat_report_draft_create", args=[session.id]),
            {"report_type": AdminChatReportDraft.DraftType.CUSTOMER_SUMMARY},
        )
        self.assertEqual(viewer_response.status_code, 403)

    def test_converted_report_is_account_scoped_in_portal(self):
        session = create_chat_session(user=self.owner, title="Reports", server_id=self.server.id)
        draft = create_chat_report_draft(
            user=self.owner,
            session=session,
            report_type=AdminChatReportDraft.DraftType.TECHNICAL_INTERNAL,
        )
        review_chat_report_draft(draft, reviewer=self.admin, decision=AdminChatReportDraft.Status.APPROVED)
        report = convert_chat_report_draft(draft, reviewer=self.admin)

        self.client.force_login(self.other_owner)
        response = self.client.get(reverse("portal:report_detail", args=[report.id]))

        self.assertEqual(response.status_code, 404)

    def test_rejected_draft_cannot_convert(self):
        session = create_chat_session(user=self.owner, title="Reports", server_id=self.server.id)
        draft = create_chat_report_draft(
            user=self.owner,
            session=session,
            report_type=AdminChatReportDraft.DraftType.CUSTOMER_SUMMARY,
        )
        review_chat_report_draft(draft, reviewer=self.admin, decision=AdminChatReportDraft.Status.REJECTED)

        with self.assertRaises(ValidationError):
            convert_chat_report_draft(draft, reviewer=self.admin)

    def test_chat_detail_shows_report_draft_history(self):
        session = create_chat_session(user=self.owner, title="Reports", server_id=self.server.id)
        create_chat_report_draft(
            user=self.owner,
            session=session,
            report_type=AdminChatReportDraft.DraftType.CUSTOMER_SUMMARY,
        )
        self.client.force_login(self.owner)

        response = self.client.get(reverse("portal:chat_session_detail", args=[session.id]))

        self.assertContains(response, "Report draft history")
        self.assertContains(response, "customer_summary")
        self.assertContains(response, "pending_review")
