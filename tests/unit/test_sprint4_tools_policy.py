import json

from django.test import Client, TestCase
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.audit.models import AuditLog
from apps.bootstrap.policy import render_command
from apps.plans.models import Plan
from apps.servers.models import AgentJob, ScannerAgent, Server
from apps.subscriptions.models import Subscription
from apps.tools.models import PlanTool, ToolDefinition, ToolRun
from apps.tools.services import ToolPolicyDenied, create_tool_run_job
from apps.tools.setup import ensure_system_identity_tool


class Sprint4ToolPolicyTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.account = Account.objects.create(name="Acme")
        self.plan = Plan.objects.create(name="Starter")
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
        self.user = User.objects.create_user(
            username="operator",
            email="operator@example.com",
            password="password",
            account=self.account,
            role=User.CustomerRole.OPERATOR,
        )
        _template, self.tool = ensure_system_identity_tool()

    def _raw_agent_token(self):
        raw_token = self.agent.issue_token()
        self.agent.save(update_fields=["token_hash", "updated_at"])
        return raw_token

    def test_system_identity_registered_and_enabled(self):
        _template, tool = ensure_system_identity_tool()

        self.assertEqual(tool.key, "system_identity")
        self.assertEqual(tool.status, ToolDefinition.Status.ENABLED)
        self.assertEqual(tool.risk_level, ToolDefinition.RiskLevel.READ_ONLY)
        self.assertTrue(tool.policy.is_active)
        self.assertTrue(PlanTool.objects.filter(plan=self.plan, tool_definition=tool, is_enabled=True).exists())

    def test_disabled_tool_rejected(self):
        self.tool.status = ToolDefinition.Status.DISABLED
        self.tool.save(update_fields=["status", "updated_at"])

        with self.assertRaises(ToolPolicyDenied):
            create_tool_run_job(account=self.account, server=self.server, tool_key=self.tool.key, requested_by=self.user)

        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertTrue(AuditLog.objects.filter(action="tool_policy.denied").exists())

    def test_draft_unapproved_tool_rejected(self):
        self.tool.status = ToolDefinition.Status.DRAFT
        self.tool.save(update_fields=["status", "updated_at"])

        with self.assertRaises(ToolPolicyDenied):
            create_tool_run_job(account=self.account, server=self.server, tool_key=self.tool.key, requested_by=self.user)

        self.assertEqual(ToolRun.objects.count(), 0)

    def test_non_read_only_tool_rejected(self):
        self.tool.risk_level = ToolDefinition.RiskLevel.SENSITIVE_READ
        self.tool.save(update_fields=["risk_level", "updated_at"])

        with self.assertRaises(ToolPolicyDenied):
            create_tool_run_job(account=self.account, server=self.server, tool_key=self.tool.key, requested_by=self.user)

    def test_tool_not_in_plan_rejected(self):
        PlanTool.objects.filter(plan=self.plan, tool_definition=self.tool).delete()

        with self.assertRaises(ToolPolicyDenied):
            create_tool_run_job(account=self.account, server=self.server, tool_key=self.tool.key, requested_by=self.user)

    def test_active_plan_and_enabled_read_only_tool_allowed(self):
        tool_run, job = create_tool_run_job(
            account=self.account,
            server=self.server,
            tool_key="system_identity",
            requested_by=self.user,
            requested_by_type=ToolRun.RequestedByType.USER,
        )

        self.assertEqual(tool_run.status, ToolRun.Status.QUEUED)
        self.assertEqual(tool_run.agent_job, job)
        self.assertEqual(job.tool_key, "system_identity")
        self.assertEqual(job.max_output_bytes, self.tool.max_output_bytes)

    def test_cross_account_mismatch_rejected(self):
        other_account = Account.objects.create(name="Other")
        other_server = Server.objects.create(account=other_account, name="Other Server", status=Server.Status.ACTIVE)

        with self.assertRaises(ToolPolicyDenied):
            create_tool_run_job(account=self.account, server=other_server, tool_key=self.tool.key, requested_by=self.user)

    def test_invalid_params_rejected(self):
        self.tool.input_schema = {"fields": {"count": {"type": "integer"}}, "required": ["count"]}
        self.tool.save(update_fields=["input_schema", "updated_at"])

        with self.assertRaises(ToolPolicyDenied):
            create_tool_run_job(
                account=self.account,
                server=self.server,
                tool_key=self.tool.key,
                params={"count": "not-an-integer"},
                requested_by=self.user,
            )

    def test_unknown_params_rejected(self):
        with self.assertRaises(ToolPolicyDenied):
            create_tool_run_job(
                account=self.account,
                server=self.server,
                tool_key=self.tool.key,
                params={"unexpected": True},
                requested_by=self.user,
            )

    def test_blocked_paths_rejected_before_allowed_paths(self):
        self.tool.input_schema = {"fields": {"target_path": {"type": "path"}}, "required": ["target_path"]}
        self.tool.requires_path_policy = True
        self.tool.allowed_path_prefixes = ["/"]
        self.tool.blocked_path_prefixes = ["/etc"]
        self.tool.save(
            update_fields=[
                "input_schema",
                "requires_path_policy",
                "allowed_path_prefixes",
                "blocked_path_prefixes",
                "updated_at",
            ]
        )

        with self.assertRaises(ToolPolicyDenied):
            create_tool_run_job(
                account=self.account,
                server=self.server,
                tool_key=self.tool.key,
                params={"target_path": "/etc/../etc/shadow"},
                requested_by=self.user,
            )

    def test_redaction_removes_secrets_from_tool_run_result(self):
        tool_run, job = create_tool_run_job(account=self.account, server=self.server, tool_key=self.tool.key)
        raw_token = self._raw_agent_token()
        self.client.get("/api/agent/jobs/next/", HTTP_AUTHORIZATION=f"Bearer {raw_token}")

        response = self.client.post(
            f"/api/agent/jobs/{job.id}/result/",
            data=json.dumps({"status": "succeeded", "output": {"DB_PASSWORD": "secret", "safe": "ok"}}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200, response.content)
        tool_run.refresh_from_db()
        self.assertEqual(tool_run.status, ToolRun.Status.SUCCEEDED)
        self.assertEqual(tool_run.result_redacted["DB_PASSWORD"], "[REDACTED]")
        self.assertEqual(tool_run.result_redacted["safe"], "ok")

    def test_agent_job_created_only_after_policy_approval(self):
        self.tool.status = ToolDefinition.Status.DISABLED
        self.tool.save(update_fields=["status", "updated_at"])

        with self.assertRaises(ToolPolicyDenied):
            create_tool_run_job(account=self.account, server=self.server, tool_key=self.tool.key)

        self.assertEqual(AgentJob.objects.count(), 0)
        self.assertEqual(ToolRun.objects.count(), 0)

    def test_agent_result_endpoint_updates_tool_run(self):
        tool_run, job = create_tool_run_job(account=self.account, server=self.server, tool_key=self.tool.key)
        raw_token = self._raw_agent_token()
        self.client.get("/api/agent/jobs/next/", HTTP_AUTHORIZATION=f"Bearer {raw_token}")

        response = self.client.post(
            f"/api/agent/jobs/{job.id}/result/",
            data=json.dumps({"status": "succeeded", "output": {"hostname": "web-01"}}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200, response.content)
        tool_run.refresh_from_db()
        self.assertEqual(tool_run.status, ToolRun.Status.SUCCEEDED)
        self.assertEqual(tool_run.result_redacted, {"hostname": "web-01"})

    def test_sprint2_polling_still_works_for_system_identity(self):
        _tool_run, job = create_tool_run_job(account=self.account, server=self.server, tool_key=self.tool.key)
        raw_token = self._raw_agent_token()

        response = self.client.get("/api/agent/jobs/next/", HTTP_AUTHORIZATION=f"Bearer {raw_token}")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["job"]["job_id"], str(job.id))
        self.assertEqual(response.json()["job"]["tool_key"], "system_identity")

    def test_bootstrap_policy_remains_unaffected(self):
        command = render_command("remote_os_probe")

        self.assertEqual(command, "cat /etc/os-release")
