import subprocess
from unittest.mock import patch

from django.test import SimpleTestCase

from scanner_runtime.baseline_tools import (
    collect_systemd_services,
    parse_systemd_unit_files_output,
    parse_systemd_units_output,
)
from scanner_runtime.prototype import execute_job
from scanner_runtime.safe_exec import SafeExecError, SafeExecOutputTooLarge, SafeExecTimeout, run_fixed_command


class Phase2SystemdDiscoveryTests(SimpleTestCase):
    def test_safe_exec_uses_argv_shell_false_and_redacts_stderr(self):
        completed = subprocess.CompletedProcess(
            args=["systemctl", "list-units"],
            returncode=1,
            stdout="ok",
            stderr="password=secret token=abc",
        )
        with patch("scanner_runtime.safe_exec.subprocess.run", return_value=completed) as run:
            result = run_fixed_command(["systemctl", "list-units"], timeout_seconds=5, max_output_bytes=1024)

        self.assertEqual(result.stdout, "ok")
        self.assertIn("[REDACTED]", result.stderr)
        self.assertNotIn("secret", result.stderr)
        run.assert_called_once()
        self.assertEqual(run.call_args.kwargs["shell"], False)
        self.assertEqual(run.call_args.args[0], ["systemctl", "list-units"])

    def test_safe_exec_rejects_string_command(self):
        with self.assertRaises(SafeExecError):
            run_fixed_command("systemctl list-units")

    def test_safe_exec_timeout_behavior(self):
        timeout = subprocess.TimeoutExpired(cmd=["systemctl"], timeout=1, stderr="token=abc")
        with patch("scanner_runtime.safe_exec.subprocess.run", side_effect=timeout):
            with self.assertRaises(SafeExecTimeout) as error:
                run_fixed_command(["systemctl"], timeout_seconds=1)

        self.assertIn("[REDACTED]", str(error.exception))

    def test_safe_exec_output_cap_behavior(self):
        completed = subprocess.CompletedProcess(args=["systemctl"], returncode=0, stdout="x" * 20, stderr="")
        with patch("scanner_runtime.safe_exec.subprocess.run", return_value=completed):
            with self.assertRaises(SafeExecOutputTooLarge):
                run_fixed_command(["systemctl"], max_output_bytes=10)

    def test_parser_handles_active_service(self):
        output = "nginx.service loaded active running A high performance web server\n"

        services = parse_systemd_units_output(output)

        self.assertEqual(len(services), 1)
        self.assertEqual(services[0]["name"], "nginx.service")
        self.assertEqual(services[0]["status"], "active")
        self.assertEqual(services[0]["load_state"], "loaded")
        self.assertEqual(services[0]["active_state"], "active")
        self.assertEqual(services[0]["sub_state"], "running")
        self.assertEqual(services[0]["description"], "A high performance web server")
        self.assertEqual(services[0]["unit_type"], "service")
        self.assertEqual(services[0]["metadata"], {"source": "systemctl"})

    def test_parser_handles_failed_service(self):
        output = "broken.service loaded failed failed Broken service\n"

        services = parse_systemd_units_output(output)

        self.assertEqual(services[0]["name"], "broken.service")
        self.assertEqual(services[0]["status"], "failed")
        self.assertEqual(services[0]["active_state"], "failed")
        self.assertEqual(services[0]["sub_state"], "failed")

    def test_parser_handles_missing_description(self):
        output = "minimal.service loaded inactive dead\n"

        services = parse_systemd_units_output(output)

        self.assertEqual(services[0]["name"], "minimal.service")
        self.assertEqual(services[0]["description"], "")

    def test_parser_redacts_secret_like_description(self):
        output = "leaky.service loaded active running password=secret token=abc\n"

        services = parse_systemd_units_output(output)

        self.assertIn("[REDACTED]", services[0]["description"])
        self.assertNotIn("secret", services[0]["description"])
        self.assertNotIn("abc", services[0]["description"])

    def test_enabled_state_merge(self):
        units = subprocess.CompletedProcess(
            args=["systemctl"],
            returncode=0,
            stdout="nginx.service loaded active running Nginx\nbroken.service loaded failed failed Broken\n",
            stderr="",
        )
        unit_files = subprocess.CompletedProcess(
            args=["systemctl"],
            returncode=0,
            stdout="nginx.service enabled\nbroken.service disabled\nother.timer enabled\n",
            stderr="",
        )
        with patch("scanner_runtime.baseline_tools.run_fixed_command", side_effect=[units, unit_files]):
            result = collect_systemd_services({})

        by_name = {service["name"]: service for service in result["services"]}
        self.assertEqual(by_name["nginx.service"]["enabled_state"], "enabled")
        self.assertEqual(by_name["broken.service"]["enabled_state"], "disabled")
        self.assertEqual(result["summary"], {"total": 2, "active": 1, "failed": 1})

    def test_non_zero_list_units_result_fails_safely(self):
        failed_units = subprocess.CompletedProcess(
            args=["systemctl"],
            returncode=1,
            stdout="",
            stderr="password=secret",
        )
        with patch("scanner_runtime.baseline_tools.run_fixed_command", return_value=failed_units):
            with self.assertRaises(SafeExecError) as error:
                collect_systemd_services({})

        self.assertIn("[REDACTED]", str(error.exception))
        self.assertNotIn("secret", str(error.exception))

    def test_unit_files_parser_ignores_non_services(self):
        states = parse_systemd_unit_files_output("nginx.service enabled\napt-daily.timer enabled\n")

        self.assertEqual(states, {"nginx.service": "enabled"})

    def test_execute_job_systemd_discovery_succeeds_with_mocked_collector(self):
        with patch("scanner_runtime.prototype.collect_systemd_services", return_value={"services": [], "summary": {"total": 0}}):
            result = execute_job({"tool_key": "systemd_services_discovery", "params": {}})

        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["output"], {"services": [], "summary": {"total": 0}})

    def test_non_empty_params_rejected(self):
        result = execute_job({"tool_key": "systemd_services_discovery", "params": {"service": "nginx"}})

        self.assertEqual(result["status"], "rejected")
        self.assertIn("does not accept parameters", result["error"])

    def test_unsupported_tools_still_rejected(self):
        result = execute_job({"tool_key": "arbitrary_tool", "params": {}})

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["error"], "Tool is not allowlisted by this runtime.")
