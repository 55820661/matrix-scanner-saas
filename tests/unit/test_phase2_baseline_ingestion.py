from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.applications.models import Application
from apps.plans.models import Plan
from apps.servers.baseline import ingest_completed_tool_runs, start_baseline_scan
from apps.servers.baseline_profiles import PROFILE_DEBIAN_NGINX_OPT
from apps.servers.models import (
    AgentJob,
    BaselineScan,
    DiscoveredDomain,
    DiscoveredService,
    Finding,
    LogSource,
    ScannerAgent,
    Server,
)
from apps.subscriptions.models import Subscription
from apps.tools.models import ToolRun
from apps.tools.phase2_enablement import enable_phase2_pilot_tools
from apps.tools.setup import ensure_baseline_tools


class Phase2BaselineIngestionTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create(name="Pilot")
        self.plan = Plan.objects.create(name="Pilot Plan")
        Subscription.objects.create(account=self.account, plan=self.plan, status=Subscription.Status.ACTIVE)
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
        enable_phase2_pilot_tools(plan_id=self.plan.id)

    def create_started_scan(self):
        scan = BaselineScan.objects.create(
            account=self.account,
            server=self.server,
            requested_by=self.admin,
            profile_key=PROFILE_DEBIAN_NGINX_OPT,
        )
        start_baseline_scan(scan)
        return scan

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

    def complete_remaining_steps(self, scan):
        for step in scan.steps.all():
            if step.tool_run.status == ToolRun.Status.PENDING or step.tool_run.status == ToolRun.Status.QUEUED:
                self.mark_step_succeeded(scan, step.step_key, {})

    def test_systemd_services_discovery_creates_discovered_service(self):
        scan = self.create_started_scan()
        self.mark_step_succeeded(
            scan,
            "systemd_services_discovery",
            {
                "services": [
                    {
                        "service_name": "nginx.service",
                        "active_state": "active",
                        "load_state": "loaded",
                        "description": "Nginx web server",
                    }
                ]
            },
        )

        ingest_completed_tool_runs(scan)

        service = DiscoveredService.objects.get(name="nginx.service")
        self.assertEqual(service.baseline_scan, scan)
        self.assertEqual(service.status, "active")
        self.assertEqual(service.metadata["source"], "systemd_services_discovery")
        self.assertEqual(service.metadata["load_state"], "loaded")

    def test_gunicorn_enriches_same_service_without_duplicate(self):
        scan = self.create_started_scan()
        self.mark_step_succeeded(
            scan,
            "systemd_services_discovery",
            {
                "services": [
                    {"service_name": "cron.service", "active_state": "active"},
                    {"service_name": "matrix-scanner-saas.service", "active_state": "active"},
                ]
            },
        )
        self.mark_step_succeeded(
            scan,
            "gunicorn_uvicorn_services_discovery",
            {
                "services": [
                    {
                        "service_name": "cron.service",
                        "active_state": "active",
                        "process_type": "unknown",
                        "related_app_path": "/opt/not-real",
                    },
                    {
                        "service_name": "matrix-scanner-saas.service",
                        "active_state": "active",
                        "process_type": "gunicorn",
                        "related_app_path": "/opt/matrix-scanner-saas",
                    }
                ]
            },
        )

        ingest_completed_tool_runs(scan)

        self.assertEqual(DiscoveredService.objects.count(), 2)
        cron = DiscoveredService.objects.get(name="cron.service")
        self.assertEqual(cron.metadata["source"], "systemd_services_discovery")
        self.assertNotIn("process_type", cron.metadata)
        self.assertNotIn("related_app_path", cron.metadata)
        self.assertEqual(DiscoveredService.objects.filter(name="matrix-scanner-saas.service").count(), 1)
        service = DiscoveredService.objects.get(name="matrix-scanner-saas.service")
        self.assertEqual(service.metadata["source"], "gunicorn_uvicorn_services_discovery")
        self.assertEqual(service.metadata["process_type"], "gunicorn")
        self.assertEqual(service.metadata["related_app_path"], "/opt/matrix-scanner-saas")

    def test_postgres_status_discovery_creates_service_with_health_metadata(self):
        scan = self.create_started_scan()
        self.mark_step_succeeded(
            scan,
            "postgres_status_discovery",
            {
                "services": [
                    {
                        "service_name": "postgresql@15-main.service",
                        "active_state": "active",
                        "sub_state": "running",
                        "health_check": "ok",
                    }
                ]
            },
        )

        ingest_completed_tool_runs(scan)

        service = DiscoveredService.objects.get(name="postgresql@15-main.service")
        self.assertEqual(service.status, "active")
        self.assertEqual(service.metadata["health_check"], "ok")
        self.assertEqual(service.metadata["sub_state"], "running")

    def test_malformed_service_items_are_ignored_safely(self):
        scan = self.create_started_scan()
        self.mark_step_succeeded(
            scan,
            "systemd_services_discovery",
            {"services": ["bad", {}, {"active_state": "active"}, {"service_name": ""}]},
        )

        ingest_completed_tool_runs(scan)

        self.assertEqual(DiscoveredService.objects.count(), 0)

    def test_nginx_sites_discovery_creates_discovered_domain(self):
        scan = self.create_started_scan()
        self.mark_step_succeeded(
            scan,
            "nginx_sites_discovery",
            {
                "domains": [
                    {
                        "domain": "Example.COM",
                        "document_root": "/opt/example/public",
                        "listen_ports": [80, 443],
                        "proxy_pass": "http://127.0.0.1:8020",
                        "source_path": "/etc/nginx/sites-enabled/example",
                    }
                ]
            },
        )

        ingest_completed_tool_runs(scan)

        domain = DiscoveredDomain.objects.get(domain="example.com")
        self.assertEqual(domain.baseline_scan, scan)
        self.assertEqual(domain.document_root, "/opt/example/public")
        self.assertEqual(domain.metadata["source"], "nginx_sites_discovery")
        self.assertEqual(domain.metadata["listen_ports"], [80, 443])

    def test_malformed_and_placeholder_nginx_domains_are_ignored(self):
        scan = self.create_started_scan()
        self.mark_step_succeeded(
            scan,
            "nginx_sites_discovery",
            {"domains": ["bad", {}, {"domain": "_"}, {"domain": "default"}, {"domain": ""}]},
        )

        ingest_completed_tool_runs(scan)

        self.assertEqual(DiscoveredDomain.objects.count(), 0)

    def test_log_sources_discovery_v2_creates_log_source(self):
        scan = self.create_started_scan()
        self.mark_step_succeeded(
            scan,
            "log_sources_discovery_v2",
            {
                "log_sources": [
                    {
                        "path": "/var/log/nginx",
                        "type": "nginx_log_dir",
                        "exists": True,
                        "is_dir": True,
                        "size_bytes": 4096,
                        "modified_at": "2026-06-01T00:00:00Z",
                    }
                ]
            },
        )

        ingest_completed_tool_runs(scan)

        log_source = LogSource.objects.get(path="/var/log/nginx")
        self.assertEqual(log_source.baseline_scan, scan)
        self.assertEqual(log_source.source_type, "nginx_log_dir")
        self.assertTrue(log_source.exists)
        self.assertEqual(log_source.size_bytes, 4096)
        self.assertEqual(log_source.metadata["source"], "log_sources_discovery_v2")

    def test_log_source_malformed_items_and_raw_secrets_are_ignored_or_redacted(self):
        scan = self.create_started_scan()
        self.mark_step_succeeded(
            scan,
            "log_sources_discovery_v2",
            {
                "log_sources": [
                    "bad",
                    {},
                    {"path": "/root/secret.log", "type": "unsafe"},
                    {
                        "path": "/var/log/postgresql",
                        "type": "postgresql_log_dir",
                        "exists": True,
                        "metadata": {"note": "DB_PASSWORD=secret"},
                    },
                ]
            },
        )

        ingest_completed_tool_runs(scan)

        self.assertEqual(LogSource.objects.count(), 1)
        serialized = str(LogSource.objects.get().metadata)
        self.assertNotIn("secret", serialized)
        self.assertIn("[REDACTED]", serialized)

    def test_opt_apps_discovery_creates_application(self):
        scan = self.create_started_scan()
        self.mark_step_succeeded(
            scan,
            "opt_apps_discovery",
            {
                "applications": [
                    {
                        "path": "/opt/example",
                        "name": "Example",
                        "framework": "python",
                        "detection": ["pyproject.toml"],
                        "metadata": {"note": "DB_PASSWORD=secret"},
                    }
                ]
            },
        )

        ingest_completed_tool_runs(scan)

        app = Application.objects.get(path="/opt/example")
        self.assertEqual(app.baseline_scan, scan)
        self.assertEqual(app.name, "Example")
        self.assertEqual(app.framework, "python")
        self.assertEqual(app.review_status, Application.ReviewStatus.PENDING_REVIEW)
        serialized = str(app.metadata)
        self.assertIn("opt_apps_discovery", serialized)
        self.assertNotIn("secret", serialized)
        self.assertIn("[REDACTED]", serialized)

    def test_django_apps_discovery_enriches_same_path_without_duplicate(self):
        scan = self.create_started_scan()
        self.mark_step_succeeded(
            scan,
            "opt_apps_discovery",
            {"applications": [{"path": "/opt/example", "name": "Example", "framework": "python"}]},
        )
        self.mark_step_succeeded(
            scan,
            "django_apps_discovery",
            {
                "applications": [
                    {
                        "path": "/opt/example",
                        "name": "Example Django",
                        "framework": "django",
                        "project_package": "config",
                        "has_manage_py": True,
                        "has_wsgi": True,
                    }
                ]
            },
        )

        ingest_completed_tool_runs(scan)

        self.assertEqual(Application.objects.count(), 1)
        app = Application.objects.get(path="/opt/example")
        self.assertEqual(app.framework, "django")
        self.assertEqual(app.baseline_scan, scan)
        self.assertEqual(app.metadata["source"], "django_apps_discovery")
        self.assertEqual(app.metadata["project_package"], "config")
        self.assertTrue(app.metadata["has_manage_py"])

    def test_opt_apps_discovery_skips_nested_internal_packages_under_parent_app(self):
        scan = self.create_started_scan()
        self.mark_step_succeeded(
            scan,
            "opt_apps_discovery",
            {
                "applications": [
                    {
                        "path": "/opt/whatsapp-saas",
                        "name": "WhatsApp SaaS",
                        "framework": "python",
                        "detection": ["pyproject.toml"],
                        "depth": 1,
                    },
                    {
                        "path": "/opt/whatsapp-saas/config",
                        "name": "config",
                        "framework": "python",
                        "detection": ["wsgi.py", "asgi.py"],
                        "depth": 2,
                        "has_systemd_unit_hint": False,
                    },
                    {
                        "path": "/opt/whatsapp-saas/conversation_relay_service",
                        "name": "conversation_relay_service",
                        "framework": "python",
                        "detection": ["requirements.txt"],
                        "depth": 2,
                        "has_systemd_unit_hint": False,
                    },
                    {
                        "path": "/opt/whatsapp-saas/worker",
                        "name": "worker",
                        "framework": "python",
                        "detection": ["requirements.txt"],
                        "depth": 2,
                        "has_systemd_unit_hint": True,
                    },
                    {
                        "path": "/opt/whatsapp-saas/frontend",
                        "name": "frontend",
                        "framework": "node",
                        "detection": ["package.json"],
                        "depth": 2,
                        "has_systemd_unit_hint": False,
                    },
                    {
                        "path": "/opt/matrix-scanner-saas",
                        "name": "Matrix Scanner",
                        "framework": "python",
                        "detection": ["pyproject.toml"],
                        "depth": 1,
                    },
                ]
            },
        )
        self.mark_step_succeeded(
            scan,
            "django_apps_discovery",
            {
                "applications": [
                    {
                        "path": "/opt/whatsapp-saas",
                        "name": "WhatsApp SaaS",
                        "framework": "django",
                        "project_package": "config",
                    }
                ]
            },
        )

        ingest_completed_tool_runs(scan)

        paths = set(Application.objects.values_list("path", flat=True))
        self.assertIn("/opt/whatsapp-saas", paths)
        self.assertIn("/opt/matrix-scanner-saas", paths)
        self.assertIn("/opt/whatsapp-saas/worker", paths)
        self.assertIn("/opt/whatsapp-saas/frontend", paths)
        self.assertNotIn("/opt/whatsapp-saas/config", paths)
        self.assertNotIn("/opt/whatsapp-saas/conversation_relay_service", paths)
        parent = Application.objects.get(path="/opt/whatsapp-saas")
        self.assertEqual(parent.framework, "django")
        self.assertEqual(parent.metadata["source"], "django_apps_discovery")

    def test_application_framework_priority_keeps_specific_framework(self):
        scan = self.create_started_scan()
        self.mark_step_succeeded(
            scan,
            "opt_apps_discovery",
            {"applications": [{"path": "/opt/nodeapp", "name": "Node App", "framework": "node"}]},
        )
        self.mark_step_succeeded(
            scan,
            "django_apps_discovery",
            {"applications": [{"path": "/opt/nodeapp", "name": "Node App", "framework": "unknown"}]},
        )

        ingest_completed_tool_runs(scan)

        self.assertEqual(Application.objects.get(path="/opt/nodeapp").framework, "node")

    def test_malformed_and_unsafe_phase2_applications_are_ignored(self):
        scan = self.create_started_scan()
        self.mark_step_succeeded(
            scan,
            "opt_apps_discovery",
            {
                "applications": [
                    "bad",
                    {},
                    {"name": "missing path"},
                    {"path": "/root/app", "name": "unsafe"},
                    {"path": "/home/acme/.ssh/app", "name": "ssh"},
                ]
            },
        )

        ingest_completed_tool_runs(scan)

        self.assertEqual(Application.objects.count(), 0)

    def test_approved_application_is_not_overwritten_aggressively(self):
        app = Application.objects.create(
            account=self.account,
            server=self.server,
            name="Approved",
            domain="",
            path="/opt/approved",
            framework="python",
            review_status=Application.ReviewStatus.APPROVED,
            metadata={"existing": True},
        )
        scan = self.create_started_scan()
        self.mark_step_succeeded(
            scan,
            "django_apps_discovery",
            {
                "applications": [
                    {
                        "path": "/opt/approved",
                        "name": "New Name",
                        "framework": "django",
                        "project_package": "config",
                    }
                ]
            },
        )

        ingest_completed_tool_runs(scan)

        app.refresh_from_db()
        self.assertEqual(app.baseline_scan, scan)
        self.assertEqual(app.name, "Approved")
        self.assertEqual(app.framework, "python")
        self.assertEqual(app.review_status, Application.ReviewStatus.APPROVED)
        self.assertEqual(app.metadata["project_package"], "config")

    def test_phase2_summary_is_scan_scoped_and_counts_applications(self):
        old_scan = BaselineScan.objects.create(account=self.account, server=self.server, requested_by=self.admin)
        DiscoveredService.objects.create(account=self.account, server=self.server, baseline_scan=old_scan, name="old.service")
        DiscoveredDomain.objects.create(account=self.account, server=self.server, baseline_scan=old_scan, domain="old.example.com")
        LogSource.objects.create(account=self.account, server=self.server, baseline_scan=old_scan, path="/var/log/old")
        Application.objects.create(account=self.account, server=self.server, baseline_scan=old_scan, name="Old App", path="/opt/old")

        scan = self.create_started_scan()
        self.mark_step_succeeded(scan, "system_identity", {})
        self.mark_step_succeeded(scan, "systemd_services_discovery", {"services": [{"service_name": "nginx.service"}]})
        self.mark_step_succeeded(
            scan,
            "nginx_sites_discovery",
            {"domains": [{"domain": "example.com", "document_root": "/opt/example/public"}]},
        )
        self.mark_step_succeeded(
            scan,
            "log_sources_discovery_v2",
            {"log_sources": [{"path": "/var/log/nginx", "type": "nginx_log_dir", "exists": True}]},
        )
        self.mark_step_succeeded(
            scan,
            "opt_apps_discovery",
            {"applications": [{"path": "/opt/example", "name": "Example", "framework": "python"}]},
        )
        self.complete_remaining_steps(scan)

        ingest_completed_tool_runs(scan)

        scan.refresh_from_db()
        self.assertEqual(scan.status, BaselineScan.Status.SUCCEEDED)
        self.assertEqual(scan.summary["services"], 1)
        self.assertEqual(scan.summary["domains"], 1)
        self.assertEqual(scan.summary["log_sources"], 1)
        self.assertEqual(scan.summary["applications"], 1)
        self.assertEqual(scan.summary["findings"], 0)
        self.assertEqual(DiscoveredService.objects.filter(baseline_scan=scan).count(), 1)
        self.assertEqual(DiscoveredDomain.objects.filter(baseline_scan=scan).count(), 1)
        self.assertEqual(LogSource.objects.filter(baseline_scan=scan).count(), 1)
        self.assertEqual(Application.objects.filter(baseline_scan=scan).count(), 1)
        self.assertEqual(Finding.objects.count(), 0)

    def test_phase2_outputs_do_not_create_findings(self):
        scan = self.create_started_scan()
        self.mark_step_succeeded(
            scan,
            "systemd_services_discovery",
            {"services": [{"service_name": "failed.service", "active_state": "failed"}]},
        )

        ingest_completed_tool_runs(scan)

        self.assertEqual(Finding.objects.count(), 0)
