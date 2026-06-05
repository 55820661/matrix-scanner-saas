from datetime import timedelta
from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.plans.models import Plan
from apps.servers.models import AgentJob, ScannerAgent, Server
from apps.subscriptions.models import Subscription
from apps.tools.models import PlanTool, ToolDefinition, ToolPolicy, ToolRun, ToolTemplate
from apps.tools.services import ToolPolicyDenied, create_tool_run_job
from scanner_runtime.prototype import execute_job
from scanner_runtime.safe_exec import SafeExecError, SafeExecResult, run_fixed_command


class SprintC6CommandTemplateTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create(name="Acme")
        self.plan = Plan.objects.create(name="Pilot", max_servers=5, max_applications=20, max_users=5)
        self.subscription = Subscription.objects.create(
            account=self.account,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            current_period_start=timezone.now() - timedelta(days=1),
            current_period_end=timezone.now() + timedelta(days=30),
        )
        self.user = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="password",
            account=self.account,
            role=User.CustomerRole.OWNER,
        )
        self.server = Server.objects.create(account=self.account, name="Production", status=Server.Status.ACTIVE)
        self.agent = ScannerAgent.objects.create(
            account=self.account,
            server=self.server,
            token_hash="agent-token-hash",
            status=ScannerAgent.Status.ACTIVE,
            registered_at=timezone.now(),
        )

    def create_command_tool(
        self,
        *,
        key="command_template_tool",
        argv=None,
        allowed_binaries=None,
        execution_type=ToolTemplate.ExecutionType.COMMAND_TEMPLATE,
        blocked_tokens=None,
    ):
        argv = argv or ["echo", "ok"]
        template = ToolTemplate.objects.create(
            key=f"{key}_template",
            name=f"{key} template",
            runtime_handler_key="",
            execution_type=execution_type,
            command_argv_template=argv,
            allowed_binaries=allowed_binaries if allowed_binaries is not None else ["echo"],
            blocked_tokens=blocked_tokens or [],
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            output_schema={"command": "object"},
            is_active=True,
        )
        definition = ToolDefinition.objects.create(
            template=template,
            key=key,
            name=key,
            status=ToolDefinition.Status.ENABLED,
            risk_level=ToolDefinition.RiskLevel.READ_ONLY,
            execution_type=execution_type,
            command_argv_template=argv,
            allowed_binaries=allowed_binaries if allowed_binaries is not None else ["echo"],
            blocked_tokens=blocked_tokens or [],
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            default_params={},
            timeout_seconds=5,
            max_output_bytes=128,
        )
        ToolPolicy.objects.create(
            tool_definition=definition,
            allow_customer_run=True,
            allow_admin_run=True,
            allow_agent_run=True,
            allowed_roles=[User.CustomerRole.OWNER],
            allowed_server_statuses=[Server.Status.ACTIVE],
            is_active=True,
        )
        PlanTool.objects.create(plan=self.plan, tool_definition=definition, is_enabled=True)
        return definition

    def test_command_template_creates_safe_agent_job_payload(self):
        definition = self.create_command_tool()

        tool_run, job = create_tool_run_job(
            account=self.account,
            server=self.server,
            tool_key=definition.key,
            requested_by=self.user,
            requested_by_type=ToolRun.RequestedByType.USER,
        )

        self.assertEqual(tool_run.agent_job, job)
        self.assertEqual(job.execution_payload["execution_type"], "command_template")
        self.assertEqual(job.execution_payload["argv"], ["echo", "ok"])
        self.assertEqual(job.execution_payload["timeout_seconds"], 5)
        self.assertEqual(job.execution_payload["max_output_bytes"], 128)

    def test_blocked_token_denied_before_toolrun_or_agentjob(self):
        definition = self.create_command_tool(key="blocked_token_tool", argv=["echo", "bad;token"])

        with self.assertRaises(ToolPolicyDenied):
            create_tool_run_job(account=self.account, server=self.server, tool_key=definition.key, requested_by=self.user)

        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    def test_disallowed_binary_denied_before_toolrun_or_agentjob(self):
        definition = self.create_command_tool(key="bad_binary_tool", argv=["cat", "/etc/passwd"], allowed_binaries=["echo"])

        with self.assertRaises(ToolPolicyDenied):
            create_tool_run_job(account=self.account, server=self.server, tool_key=definition.key, requested_by=self.user)

        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    def test_script_template_denied_before_toolrun_or_agentjob(self):
        definition = self.create_command_tool(
            key="script_tool",
            argv=["echo", "ok"],
            execution_type=ToolTemplate.ExecutionType.SCRIPT_TEMPLATE,
        )

        with self.assertRaises(ToolPolicyDenied):
            create_tool_run_job(account=self.account, server=self.server, tool_key=definition.key, requested_by=self.user)

        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    def test_runtime_executes_command_template_payload_with_redaction(self):
        payload = {
            "execution_type": "command_template",
            "argv": ["echo", "ok"],
            "timeout_seconds": 5,
            "max_output_bytes": 128,
        }
        with patch(
            "scanner_runtime.command_templates.run_fixed_command",
            return_value=SafeExecResult(
                returncode=0,
                stdout="token=raw-secret",
                stderr="password=stderr-secret",
                execution_time_seconds=0.12345,
                truncated=False,
            ),
        ) as run_command:
            result = execute_job({"tool_key": "not_in_runtime_allowlist", "params": {}, "execution_payload": payload})

        run_command.assert_called_once_with(["echo", "ok"], timeout_seconds=5, max_output_bytes=128, truncate_output=True)
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["output"]["command"]["exit_code"], 0)
        self.assertIn("[REDACTED]", result["output"]["command"]["stdout_redacted"])
        self.assertIn("[REDACTED]", result["output"]["command"]["stderr_redacted"])
        self.assertNotIn("raw-secret", str(result))
        self.assertNotIn("stderr-secret", str(result))

    def test_runtime_rejects_bad_command_template_payload(self):
        result = execute_job({"tool_key": "not_in_runtime_allowlist", "params": {}, "execution_payload": {"execution_type": "command_template", "argv": "echo ok"}})

        self.assertEqual(result["status"], "rejected")
        self.assertIn("fixed argv list", result["error"])

    def test_safe_exec_rejects_string_command(self):
        with self.assertRaises(SafeExecError):
            run_fixed_command("echo ok")

    def test_safe_exec_truncates_when_requested(self):
        completed = Mock(returncode=0, stdout="abcdef", stderr="")
        with patch("scanner_runtime.safe_exec.subprocess.run", return_value=completed):
            result = run_fixed_command(["echo", "abcdef"], timeout_seconds=1, max_output_bytes=3, truncate_output=True)

        self.assertEqual(result.stdout, "abc")
        self.assertTrue(result.truncated)
