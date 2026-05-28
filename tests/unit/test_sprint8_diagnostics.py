from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.applications.models import Application
from apps.diagnostics.models import DiagnosticDecision, DiagnosticSession, DiagnosticStep
from apps.diagnostics.services import sync_completed_tool_runs
from apps.plans.models import Plan
from apps.servers.models import AgentJob, Finding, ScannerAgent, Server
from apps.subscriptions.models import Subscription
from apps.telegram_integration.models import TelegramNotification
from apps.tools.models import PlanTool, ToolDefinition, ToolRun
from apps.tools.setup import ensure_baseline_tools


class Sprint8DiagnosticsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.account = Account.objects.create(name="Acme")
        self.other_account = Account.objects.create(name="Other")
        self.plan = Plan.objects.create(name="Starter", max_servers=5, max_applications=20, max_users=5, max_diagnostic_sessions_per_month=20)
        self.subscription = Subscription.objects.create(
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
            registered_at=timezone.now(),
        )
        self.application = Application.objects.create(
            account=self.account,
            server=self.server,
            name="Laravel App",
            domain="app.example.com",
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
            fingerprint="diag-finding",
        )

    def login(self, user):
        self.client.force_login(user)

    def start_session(self, user=None, **overrides):
        self.login(user or self.owner)
        data = {
            "server_id": self.server.id,
            "application_id": "",
            "problem_type": DiagnosticSession.ProblemType.CUSTOM,
            "user_prompt": "Please diagnose password=raw-secret",
        }
        data.update(overrides)
        return self.client.post(reverse("portal:diagnostic_start"), data)

    def first_step(self):
        return DiagnosticStep.objects.get(step_type=DiagnosticStep.StepType.RUN_TOOL)

    def test_diagnostic_session_requires_portal_login(self):
        response = self.client.get(reverse("portal:diagnostics"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("portal:login"), response["Location"])

    def test_staff_without_account_is_blocked(self):
        self.login(self.staff)

        response = self.client.get(reverse("portal:diagnostics"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("portal:access_denied"))

    def test_owner_and_operator_can_start_but_viewer_cannot(self):
        owner_response = self.start_session(self.owner)
        self.assertEqual(owner_response.status_code, 302)
        self.assertEqual(DiagnosticSession.objects.filter(requested_by=self.owner).count(), 1)

        operator_response = self.start_session(self.operator)
        self.assertEqual(operator_response.status_code, 302)
        self.assertEqual(DiagnosticSession.objects.filter(requested_by=self.operator).count(), 1)

        self.login(self.viewer)
        viewer_response = self.client.get(reverse("portal:diagnostic_start"))
        self.assertEqual(viewer_response.status_code, 403)

    def test_session_scoped_to_account_server_and_application(self):
        self.start_session(application_id=self.application.id)
        session = DiagnosticSession.objects.get()

        self.assertEqual(session.account, self.account)
        self.assertEqual(session.server, self.server)
        self.assertEqual(session.application, self.application)

    def test_cross_account_diagnostic_session_access_denied(self):
        session = DiagnosticSession.objects.create(
            account=self.other_account,
            server=self.other_server,
            requested_by=None,
            status=DiagnosticSession.Status.WAITING_FOR_APPROVAL,
        )
        self.login(self.owner)

        response = self.client.get(reverse("portal:diagnostic_detail", args=[session.id]))

        self.assertEqual(response.status_code, 404)

    def test_application_from_another_server_or_account_rejected(self):
        self.login(self.owner)

        response = self.client.post(
            reverse("portal:diagnostic_start"),
            {
                "server_id": self.server.id,
                "application_id": self.other_application.id,
                "problem_type": DiagnosticSession.ProblemType.CUSTOM,
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(DiagnosticSession.objects.count(), 0)

    def test_planner_requires_approval_before_creating_toolrun(self):
        self.start_session()
        session = DiagnosticSession.objects.get()
        step = self.first_step()

        self.assertEqual(session.status, DiagnosticSession.Status.WAITING_FOR_APPROVAL)
        self.assertEqual(step.status, DiagnosticStep.Status.AWAITING_APPROVAL)
        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    def test_approval_creates_toolrun_and_agentjob_only_through_policy(self):
        self.start_session()
        session = DiagnosticSession.objects.get()
        step = self.first_step()

        response = self.client.post(reverse("portal:diagnostic_step_approve", args=[session.id, step.id]))

        self.assertEqual(response.status_code, 302)
        step.refresh_from_db()
        self.assertIsNotNone(step.tool_run)
        self.assertIsNotNone(step.tool_run.agent_job)
        self.assertEqual(AgentJob.objects.count(), 1)
        self.assertEqual(ToolRun.objects.count(), 1)
        self.assertEqual(step.tool_run.agent_job, AgentJob.objects.get())

    def test_non_read_only_tool_is_rejected(self):
        tool = ToolDefinition.objects.get(key="system_identity")
        tool.risk_level = ToolDefinition.RiskLevel.WRITE_ACTION
        tool.save(update_fields=["risk_level", "updated_at"])
        self.start_session()
        session = DiagnosticSession.objects.get()
        step = self.first_step()

        self.client.post(reverse("portal:diagnostic_step_approve", args=[session.id, step.id]))

        step.refresh_from_db()
        session.refresh_from_db()
        self.assertEqual(step.status, DiagnosticStep.Status.FAILED)
        self.assertEqual(session.status, DiagnosticSession.Status.FAILED)
        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    def test_disabled_or_not_in_plan_tool_is_rejected(self):
        PlanTool.objects.filter(plan=self.plan, tool_definition__key="system_identity").delete()
        self.start_session()
        session = DiagnosticSession.objects.get()
        step = self.first_step()

        self.client.post(reverse("portal:diagnostic_step_approve", args=[session.id, step.id]))

        step.refresh_from_db()
        self.assertEqual(step.status, DiagnosticStep.Status.FAILED)
        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    def test_max_tool_run_limit_is_enforced(self):
        self.start_session()
        session = DiagnosticSession.objects.get()
        session.max_tool_runs = 0
        session.save(update_fields=["max_tool_runs", "updated_at"])
        step = self.first_step()

        self.client.post(reverse("portal:diagnostic_step_approve", args=[session.id, step.id]))

        session.refresh_from_db()
        step.refresh_from_db()
        self.assertEqual(session.status, DiagnosticSession.Status.FAILED)
        self.assertEqual(step.status, DiagnosticStep.Status.FAILED)
        self.assertEqual(ToolRun.objects.count(), 0)

    def test_viewer_cannot_approve_diagnostic_step(self):
        self.start_session()
        session = DiagnosticSession.objects.get()
        step = self.first_step()
        self.login(self.viewer)

        response = self.client.post(reverse("portal:diagnostic_step_approve", args=[session.id, step.id]))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(ToolRun.objects.count(), 0)

    def test_completed_toolrun_updates_step_and_final_report_redacts(self):
        self.start_session()
        session = DiagnosticSession.objects.get()
        step = self.first_step()
        self.client.post(reverse("portal:diagnostic_step_approve", args=[session.id, step.id]))
        step.refresh_from_db()
        tool_run = step.tool_run
        tool_run.status = ToolRun.Status.SUCCEEDED
        tool_run.result_redacted = {"DB_PASSWORD": "raw-secret", "hostname": "prod"}
        tool_run.finished_at = timezone.now()
        tool_run.save(update_fields=["status", "result_redacted", "finished_at", "updated_at"])

        sync_completed_tool_runs(session)

        step.refresh_from_db()
        session.refresh_from_db()
        self.assertEqual(step.status, DiagnosticStep.Status.SUCCEEDED)
        self.assertEqual(session.status, DiagnosticSession.Status.SUCCEEDED)
        self.assertNotIn("raw-secret", step.result_summary_redacted)
        self.assertNotIn("raw-secret", session.final_report_redacted)

    def test_prompt_and_decision_context_exclude_raw_secrets(self):
        self.start_session(user_prompt="DB_PASSWORD=raw-secret and token=abc")
        session = DiagnosticSession.objects.get()
        decision = DiagnosticDecision.objects.get(session=session)

        self.assertNotIn("raw-secret", session.user_prompt_redacted)
        self.assertNotIn("abc", session.user_prompt_redacted)
        self.assertNotIn("raw-secret", str(decision.input_context_redacted))
        self.assertNotIn("raw-secret", str(decision.output_json_redacted))

    def test_no_telegram_or_remediation_side_effects(self):
        self.start_session()
        session = DiagnosticSession.objects.get()
        step = self.first_step()
        before_notifications = TelegramNotification.objects.count()

        self.client.post(reverse("portal:diagnostic_step_approve", args=[session.id, step.id]))

        self.assertEqual(TelegramNotification.objects.count(), before_notifications)
        self.assertFalse(hasattr(session, "incidentreport"))

    def test_no_raw_toolrun_agentjob_output_displayed_in_portal(self):
        self.start_session()
        session = DiagnosticSession.objects.get()
        step = self.first_step()
        self.client.post(reverse("portal:diagnostic_step_approve", args=[session.id, step.id]))
        step.refresh_from_db()
        job = step.tool_run.agent_job
        job.result = {"APP_KEY": "raw-secret"}
        job.save(update_fields=["result", "updated_at"])
        step.tool_run.result_redacted = {"APP_KEY": "raw-secret"}
        step.tool_run.status = ToolRun.Status.SUCCEEDED
        step.tool_run.finished_at = timezone.now()
        step.tool_run.save(update_fields=["result_redacted", "status", "finished_at", "updated_at"])

        response = self.client.get(reverse("portal:diagnostic_detail", args=[session.id]))
        content = response.content.decode()

        self.assertNotIn("raw-secret", content)
        self.assertNotIn("AgentJob", content)
        self.assertNotIn("ToolRun", content)

    def test_model_rejects_application_from_different_server(self):
        session = DiagnosticSession(
            account=self.account,
            server=self.server,
            application=self.other_application,
            requested_by=self.owner,
        )

        with self.assertRaises(ValidationError):
            session.full_clean()
