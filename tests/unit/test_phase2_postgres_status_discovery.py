import subprocess
from unittest.mock import patch

from django.test import SimpleTestCase

from scanner_runtime.postgres_discovery import collect_postgres_status
from scanner_runtime.prototype import execute_job
from scanner_runtime.safe_exec import SafeExecError


class Phase2PostgresStatusDiscoveryTests(SimpleTestCase):
    def test_params_rejected(self):
        with self.assertRaisesMessage(ValueError, "does not accept parameters"):
            collect_postgres_status({"x": 1})

    def test_active_postgres_service_parsed(self):
        list_result = subprocess.CompletedProcess(
            args=["systemctl"],
            returncode=0,
            stdout="postgresql.service loaded active running PostgreSQL\n",
            stderr="",
        )
        pg_ready = subprocess.CompletedProcess(args=["pg_isready"], returncode=0, stdout="accepting connections", stderr="")
        show_result = subprocess.CompletedProcess(
            args=["systemctl"],
            returncode=0,
            stdout=(
                "Id=postgresql.service\nDescription=PostgreSQL Server\nLoadState=loaded\nActiveState=active\n"
                "SubState=running\nUnitFileState=enabled\nMainPID=123\nFragmentPath=/lib/systemd/system/postgresql.service\n\n"
            ),
            stderr="",
        )
        with patch("scanner_runtime.postgres_discovery.run_fixed_command", side_effect=[list_result, pg_ready, show_result]):
            result = collect_postgres_status({})

        self.assertEqual(result["summary"]["postgres_detected"], True)
        self.assertEqual(result["summary"]["pg_isready_ok"], True)
        service = result["services"][0]
        self.assertEqual(service["service_name"], "postgresql.service")
        self.assertEqual(service["active_state"], "active")
        self.assertEqual(service["health_check"], "ok")

    def test_no_postgres_units_returns_safe_not_detected(self):
        list_result = subprocess.CompletedProcess(args=["systemctl"], returncode=0, stdout="nginx.service loaded active running Nginx\n", stderr="")
        pg_ready = subprocess.CompletedProcess(args=["pg_isready"], returncode=1, stdout="", stderr="reject")
        with patch("scanner_runtime.postgres_discovery.run_fixed_command", side_effect=[list_result, pg_ready]):
            result = collect_postgres_status({})

        self.assertEqual(result["services"], [])
        self.assertEqual(result["summary"]["postgres_detected"], False)
        self.assertIn("no_postgres_units_found", result["summary"]["notes"])

    def test_pg_isready_failure(self):
        list_result = subprocess.CompletedProcess(
            args=["systemctl"],
            returncode=0,
            stdout="postgresql.service loaded active running PostgreSQL\n",
            stderr="",
        )
        pg_ready = subprocess.CompletedProcess(args=["pg_isready"], returncode=1, stdout="", stderr="could not connect")
        show_result = subprocess.CompletedProcess(
            args=["systemctl"],
            returncode=0,
            stdout=(
                "Id=postgresql.service\nDescription=PostgreSQL Server\nLoadState=loaded\nActiveState=active\n"
                "SubState=running\nUnitFileState=enabled\nMainPID=123\nFragmentPath=/lib/systemd/system/postgresql.service\n\n"
            ),
            stderr="",
        )
        with patch("scanner_runtime.postgres_discovery.run_fixed_command", side_effect=[list_result, pg_ready, show_result]):
            result = collect_postgres_status({})

        self.assertEqual(result["summary"]["pg_isready_ok"], False)
        self.assertEqual(result["services"][0]["health_check"], "failed")

    def test_missing_pg_isready_handled_safely(self):
        list_result = subprocess.CompletedProcess(
            args=["systemctl"],
            returncode=0,
            stdout="postgresql.service loaded active running PostgreSQL\n",
            stderr="",
        )
        show_result = subprocess.CompletedProcess(
            args=["systemctl"],
            returncode=0,
            stdout=(
                "Id=postgresql.service\nDescription=PostgreSQL Server\nLoadState=loaded\nActiveState=active\n"
                "SubState=running\nUnitFileState=enabled\nMainPID=123\nFragmentPath=/lib/systemd/system/postgresql.service\n\n"
            ),
            stderr="",
        )
        with patch(
            "scanner_runtime.postgres_discovery.run_fixed_command",
            side_effect=[list_result, FileNotFoundError("pg_isready not found password=secret"), show_result],
        ):
            result = collect_postgres_status({})

        self.assertEqual(result["summary"]["pg_isready_available"], False)
        self.assertEqual(result["services"][0]["health_check"], "not_available")
        self.assertNotIn("password=secret", str(result))

    def test_forbidden_fields_not_in_output(self):
        list_result = subprocess.CompletedProcess(
            args=["systemctl"],
            returncode=0,
            stdout="postgresql.service loaded active running PostgreSQL\n",
            stderr="",
        )
        pg_ready = subprocess.CompletedProcess(args=["pg_isready"], returncode=1, stdout="", stderr="password=secret dsn=postgres://x")
        show_result = subprocess.CompletedProcess(
            args=["systemctl"],
            returncode=0,
            stdout=(
                "Id=postgresql.service\nDescription=PostgreSQL Server\nLoadState=loaded\nActiveState=active\n"
                "SubState=running\nUnitFileState=enabled\nMainPID=123\nFragmentPath=/lib/systemd/system/postgresql.service\n\n"
            ),
            stderr="",
        )
        with patch("scanner_runtime.postgres_discovery.run_fixed_command", side_effect=[list_result, pg_ready, show_result]):
            result = collect_postgres_status({})

        serialized = str(result).lower()
        self.assertNotIn("password", serialized)
        self.assertNotIn("dsn", serialized)
        self.assertNotIn("connection_string", serialized)
        self.assertNotIn("query", serialized)
        self.assertNotIn("pg_hba", serialized)
        self.assertNotIn("postgresql.conf", serialized)

    def test_output_cap_enforced(self):
        list_result = subprocess.CompletedProcess(
            args=["systemctl"],
            returncode=0,
            stdout="postgresql.service loaded active running PostgreSQL\n",
            stderr="",
        )
        pg_ready = subprocess.CompletedProcess(args=["pg_isready"], returncode=0, stdout="ok", stderr="")
        show_result = subprocess.CompletedProcess(
            args=["systemctl"],
            returncode=0,
            stdout=(
                "Id=postgresql.service\nDescription=PostgreSQL Server\nLoadState=loaded\nActiveState=active\n"
                "SubState=running\nUnitFileState=enabled\nMainPID=123\nFragmentPath=/lib/systemd/system/postgresql.service\n\n"
            ),
            stderr="",
        )
        with patch("scanner_runtime.postgres_discovery.MAX_OUTPUT_BYTES", 10):
            with patch("scanner_runtime.postgres_discovery.run_fixed_command", side_effect=[list_result, pg_ready, show_result]):
                with self.assertRaises(SafeExecError):
                    collect_postgres_status({})

    def test_execute_job_supported_tool(self):
        with patch("scanner_runtime.prototype.collect_postgres_status", return_value={"services": [], "summary": {}}):
            result = execute_job({"tool_key": "postgres_status_discovery", "params": {}})
        self.assertEqual(result["status"], "succeeded")

    def test_unsupported_tool_behavior_unchanged(self):
        result = execute_job({"tool_key": "still_not_supported", "params": {}})
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["error"], "Tool is not allowlisted by this runtime.")
