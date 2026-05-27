from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.applications.models import Application
from apps.bootstrap.policy import render_command
from apps.plans.models import Plan
from apps.servers.baseline import (
    BASELINE_TOOL_KEYS,
    BaselineScanError,
    ingest_completed_tool_runs,
    start_baseline_scan,
)
from apps.servers.models import (
    AgentJob,
    BaselineScan,
    BaselineScanStep,
    DiscoveredDomain,
    DiscoveredService,
    Finding,
    LogSource,
    ScannerAgent,
    Server,
)
from apps.subscriptions.models import Subscription
from apps.tools.models import PlanTool, ToolDefinition, ToolRun
from apps.tools.setup import ensure_baseline_tools


class Sprint5BaselineTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create(name="Acme")
        self.plan = Plan.objects.create(name="Baseline")
        self.subscription = Subscription.objects.create(
            account=self.account,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
        )
        self.server = Server.objects.create(account=self.account, name="Production", status=Server.Status.ACTIVE)
        self.agent = ScannerAgent.objects.create(
            account=self.account,
            server=self.server,
            token_hash="agent-token-hash",
            status=ScannerAgent.Status.ACTIVE,
            registered_at=timezone.now(),
            last_seen_at=timezone.now(),
        )
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
        ensure_baseline_tools()

    def create_scan(self, account=None, server=None):
        return BaselineScan.objects.create(
            account=account or self.account,
            server=server or self.server,
            requested_by=self.admin,
        )

    def mark_step_succeeded(self, scan, tool_key, result):
        step = scan.steps.select_related("tool_run", "tool_run__agent_job").get(step_key=tool_key)
        tool_run = step.tool_run
        job = tool_run.agent_job
        job.status = AgentJob.Status.SUCCEEDED
        job.result = result
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "result", "finished_at", "updated_at"])
        tool_run.status = ToolRun.Status.SUCCEEDED
        tool_run.result_redacted = result
        tool_run.finished_at = job.finished_at
        tool_run.save(update_fields=["status", "result_redacted", "finished_at", "updated_at"])
        return step

    def test_all_baseline_tools_seeded_as_enabled_read_only(self):
        for tool_key in BASELINE_TOOL_KEYS:
            tool = ToolDefinition.objects.get(key=tool_key)
            self.assertEqual(tool.status, ToolDefinition.Status.ENABLED)
            self.assertEqual(tool.risk_level, ToolDefinition.RiskLevel.READ_ONLY)
            self.assertTrue(tool.policy.is_active)
            self.assertTrue(PlanTool.objects.filter(plan=self.plan, tool_definition=tool, is_enabled=True).exists())

        self.assertEqual(ToolDefinition.objects.get(key="cpanel_domain_scanner").max_output_bytes, 256 * 1024)

    def test_baseline_refuses_if_required_tool_missing_from_plan(self):
        tool = ToolDefinition.objects.get(key="services_status")
        PlanTool.objects.filter(plan=self.plan, tool_definition=tool).delete()
        scan = self.create_scan()

        with self.assertRaises(BaselineScanError):
            start_baseline_scan(scan)

        scan.refresh_from_db()
        self.assertEqual(scan.status, BaselineScan.Status.FAILED)
        self.assertEqual(AgentJob.objects.count(), 0)
        self.assertEqual(ToolRun.objects.count(), 0)

    def test_tool_run_and_agent_job_created_only_through_policy_approval(self):
        scan = self.create_scan()

        start_baseline_scan(scan)

        self.assertEqual(BaselineScanStep.objects.filter(baseline_scan=scan).count(), len(BASELINE_TOOL_KEYS))
        self.assertEqual(ToolRun.objects.count(), len(BASELINE_TOOL_KEYS))
        self.assertEqual(AgentJob.objects.count(), len(BASELINE_TOOL_KEYS))
        self.assertEqual(ToolRun.objects.filter(agent_job__isnull=False).count(), len(BASELINE_TOOL_KEYS))

    def test_no_agent_job_when_policy_denies(self):
        tool = ToolDefinition.objects.get(key="panel_detector")
        tool.status = ToolDefinition.Status.DISABLED
        tool.save(update_fields=["status", "updated_at"])
        scan = self.create_scan()

        with self.assertRaises(BaselineScanError):
            start_baseline_scan(scan)

        self.assertEqual(AgentJob.objects.count(), 0)
        self.assertEqual(ToolRun.objects.count(), 0)

    def test_completed_application_result_creates_pending_review_application(self):
        scan = self.create_scan()
        start_baseline_scan(scan)

        self.mark_step_succeeded(
            scan,
            "application_discovery",
            {
                "applications": [
                    {
                        "name": "Example",
                        "domain": "example.com",
                        "path": "/home/acme/public_html",
                        "framework": "unknown",
                    }
                ]
            },
        )
        ingest_completed_tool_runs(scan)

        app = Application.objects.get(account=self.account, server=self.server, path="/home/acme/public_html")
        self.assertEqual(app.review_status, Application.ReviewStatus.PENDING_REVIEW)
        self.assertEqual(app.domain, "example.com")

    def test_duplicate_applications_domains_and_log_sources_are_not_duplicated(self):
        scan = self.create_scan()
        start_baseline_scan(scan)
        self.mark_step_succeeded(
            scan,
            "cpanel_domain_scanner",
            {"domains": [{"domain": "example.com", "document_root": "/home/acme/../acme/public_html"}]},
        )
        self.mark_step_succeeded(
            scan,
            "application_discovery",
            {"applications": [{"name": "Example", "domain": "example.com", "path": "/home/acme/public_html"}]},
        )
        self.mark_step_succeeded(
            scan,
            "log_sources_discovery",
            {"log_sources": [{"path": "/home/acme/public_html/storage/logs/laravel.log", "type": "laravel"}]},
        )

        ingest_completed_tool_runs(scan)
        ingest_completed_tool_runs(scan)

        self.assertEqual(DiscoveredDomain.objects.count(), 1)
        self.assertEqual(Application.objects.count(), 1)
        self.assertEqual(LogSource.objects.count(), 1)
        self.assertEqual(DiscoveredDomain.objects.get().document_root, "/home/acme/public_html")

    def test_laravel_env_stores_allowlisted_keys_only(self):
        scan = self.create_scan()
        start_baseline_scan(scan)
        self.mark_step_succeeded(
            scan,
            "laravel_discovery",
            {
                "applications": [
                    {
                        "name": "Laravel",
                        "domain": "app.example.com",
                        "path": "/home/acme/app",
                        "framework": "laravel",
                        "env": {
                            "APP_ENV": "production",
                            "APP_DEBUG": "false",
                            "APP_KEY": "base64:secret",
                            "DB_PASSWORD": "secret",
                            "AWS_SECRET_ACCESS_KEY": "secret",
                            "CUSTOM_TOKEN": "secret",
                        },
                    }
                ]
            },
        )

        ingest_completed_tool_runs(scan)

        app = Application.objects.get(path="/home/acme/app")
        self.assertEqual(app.metadata["laravel_env"], {"APP_ENV": "production", "APP_DEBUG": "false"})
        self.assertNotIn("APP_KEY", app.metadata["laravel_env"])
        self.assertNotIn("DB_PASSWORD", app.metadata["laravel_env"])

    def test_existing_approved_application_is_not_overwritten_aggressively(self):
        app = Application.objects.create(
            account=self.account,
            server=self.server,
            name="Approved App",
            domain="example.com",
            path="/home/acme/public_html",
            framework="laravel",
            review_status=Application.ReviewStatus.APPROVED,
        )
        scan = self.create_scan()
        start_baseline_scan(scan)
        self.mark_step_succeeded(
            scan,
            "application_discovery",
            {
                "applications": [
                    {
                        "name": "New Name",
                        "domain": "example.com",
                        "path": "/home/acme/public_html",
                        "framework": "unknown",
                        "metadata": {"source": "baseline"},
                    }
                ]
            },
        )

        ingest_completed_tool_runs(scan)

        app.refresh_from_db()
        self.assertEqual(app.name, "Approved App")
        self.assertEqual(app.review_status, Application.ReviewStatus.APPROVED)
        self.assertEqual(app.metadata["source"], "baseline")

    def test_blocked_path_output_is_ignored(self):
        scan = self.create_scan()
        start_baseline_scan(scan)
        self.mark_step_succeeded(
            scan,
            "application_discovery",
            {"applications": [{"name": "Root App", "domain": "root.example.com", "path": "/root/public_html"}]},
        )
        self.mark_step_succeeded(
            scan,
            "log_sources_discovery",
            {"log_sources": [{"path": "/home/acme/.ssh/id_rsa", "type": "private_key"}]},
        )

        ingest_completed_tool_runs(scan)

        self.assertEqual(Application.objects.count(), 0)
        self.assertEqual(LogSource.objects.count(), 0)

    def test_webroot_risk_creates_finding_without_raw_secrets(self):
        scan = self.create_scan()
        start_baseline_scan(scan)
        self.mark_step_succeeded(
            scan,
            "webroot_risk_checker",
            {
                "findings": [
                    {
                        "title": "Exposed env",
                        "severity": "high",
                        "path": "/home/acme/public_html/.env",
                        "evidence_summary": "DB_PASSWORD=secret",
                        "fingerprint": "webroot-risk:env",
                    }
                ]
            },
        )

        ingest_completed_tool_runs(scan)

        finding = Finding.objects.get(fingerprint="webroot-risk:env")
        self.assertEqual(finding.status, Finding.Status.OPEN)
        self.assertNotIn("secret", finding.evidence_summary)
        self.assertIn("[REDACTED]", finding.evidence_summary)

    def test_services_result_is_ingested(self):
        scan = self.create_scan()
        start_baseline_scan(scan)
        self.mark_step_succeeded(scan, "services_status", {"services": [{"name": "httpd", "status": "running"}]})

        ingest_completed_tool_runs(scan)

        self.assertEqual(DiscoveredService.objects.get(name="httpd").status, "running")

    def test_baseline_scan_status_transitions_to_succeeded(self):
        scan = self.create_scan()
        start_baseline_scan(scan)
        scan.refresh_from_db()
        self.assertEqual(scan.status, BaselineScan.Status.RUNNING)
        self.assertEqual(scan.current_step, "waiting_for_agent_results")

        for step in scan.steps.all():
            self.mark_step_succeeded(scan, step.step_key, {})

        ingest_completed_tool_runs(scan)

        scan.refresh_from_db()
        self.assertEqual(scan.status, BaselineScan.Status.SUCCEEDED)
        self.assertEqual(scan.current_step, "completed")

    def test_cross_account_baseline_scan_denied(self):
        other_account = Account.objects.create(name="Other")
        scan = self.create_scan(account=other_account, server=self.server)

        with self.assertRaises(BaselineScanError):
            start_baseline_scan(scan)

        self.assertEqual(AgentJob.objects.count(), 0)

    def test_no_telegram_diagnostic_or_celery_side_effects(self):
        scan = self.create_scan()
        start_baseline_scan(scan)

        self.assertEqual(AgentJob.objects.count(), len(BASELINE_TOOL_KEYS))
        self.assertFalse(any(job.tool_key.startswith("telegram") for job in AgentJob.objects.all()))
        self.assertFalse(any(job.tool_key.startswith("diagnostic") for job in AgentJob.objects.all()))
        self.assertEqual(render_command("remote_os_probe"), "cat /etc/os-release")
