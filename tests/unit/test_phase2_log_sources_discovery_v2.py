from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from scanner_runtime.log_sources_discovery_v2 import collect_log_sources_v2
from scanner_runtime.prototype import execute_job


class _FakeStat:
    def __init__(self, size_bytes=0, mtime=0):
        self.st_size = size_bytes
        self.st_mtime = mtime


class Phase2LogSourcesDiscoveryV2Tests(SimpleTestCase):
    def test_params_rejected(self):
        with self.assertRaisesMessage(ValueError, "does not accept parameters"):
            collect_log_sources_v2({"path": "/var/log/nginx"})

    def test_discovers_nginx_log_dir_metadata(self):
        with patch("scanner_runtime.log_sources_discovery_v2.SYSTEM_CANDIDATES", [("/var/log/nginx", "nginx_log_dir")]):
            with patch("scanner_runtime.log_sources_discovery_v2.Path.stat", return_value=_FakeStat(size_bytes=4096, mtime=1710000000)):
                with patch("scanner_runtime.log_sources_discovery_v2.Path.is_dir", return_value=True):
                    with patch("scanner_runtime.log_sources_discovery_v2._discover_opt_logs_candidates", return_value=[]):
                        result = collect_log_sources_v2({})
        item = result["log_sources"][0]
        self.assertEqual(item["path"], "/var/log/nginx")
        self.assertEqual(item["type"], "nginx_log_dir")
        self.assertEqual(item["exists"], True)
        self.assertEqual(item["is_dir"], True)

    def test_discovers_postgresql_log_dir_metadata(self):
        with patch("scanner_runtime.log_sources_discovery_v2.SYSTEM_CANDIDATES", [("/var/log/postgresql", "postgresql_log_dir")]):
            with patch("scanner_runtime.log_sources_discovery_v2.Path.stat", return_value=_FakeStat(size_bytes=2048, mtime=1710000001)):
                with patch("scanner_runtime.log_sources_discovery_v2.Path.is_dir", return_value=True):
                    with patch("scanner_runtime.log_sources_discovery_v2._discover_opt_logs_candidates", return_value=[]):
                        result = collect_log_sources_v2({})
        item = result["log_sources"][0]
        self.assertEqual(item["path"], "/var/log/postgresql")
        self.assertEqual(item["type"], "postgresql_log_dir")

    def test_discovers_system_log_file_metadata(self):
        with patch("scanner_runtime.log_sources_discovery_v2.SYSTEM_CANDIDATES", [("/var/log/syslog", "system_log_file")]):
            with patch("scanner_runtime.log_sources_discovery_v2.Path.stat", return_value=_FakeStat(size_bytes=1024, mtime=1710000002)):
                with patch("scanner_runtime.log_sources_discovery_v2.Path.is_dir", return_value=False):
                    with patch("scanner_runtime.log_sources_discovery_v2._discover_opt_logs_candidates", return_value=[]):
                        result = collect_log_sources_v2({})
        item = result["log_sources"][0]
        self.assertEqual(item["path"], "/var/log/syslog")
        self.assertEqual(item["type"], "system_log_file")
        self.assertEqual(item["is_dir"], False)

    def test_discovers_safe_opt_app_logs(self):
        with patch("scanner_runtime.log_sources_discovery_v2._discover_opt_logs_candidates", return_value=["/opt/myapp/logs"]):
            with patch("scanner_runtime.log_sources_discovery_v2._opt_realpath_within_root", return_value=True):
                with patch("scanner_runtime.log_sources_discovery_v2.Path.stat", return_value=_FakeStat(size_bytes=300, mtime=1710000003)):
                    with patch("scanner_runtime.log_sources_discovery_v2.Path.is_dir", return_value=True):
                        result = collect_log_sources_v2({})

        item = next(source for source in result["log_sources"] if source["path"] == "/opt/myapp/logs")
        self.assertEqual(item["type"], "app_logs_dir")
        self.assertTrue(item["exists"])

    def test_discovers_safe_opt_suite_app_logs(self):
        with patch("scanner_runtime.log_sources_discovery_v2._discover_opt_logs_candidates", return_value=["/opt/suite/app/logs"]):
            with patch("scanner_runtime.log_sources_discovery_v2._opt_realpath_within_root", return_value=True):
                with patch("scanner_runtime.log_sources_discovery_v2.Path.stat", return_value=_FakeStat(size_bytes=301, mtime=1710000004)):
                    with patch("scanner_runtime.log_sources_discovery_v2.Path.is_dir", return_value=True):
                        result = collect_log_sources_v2({})

        item = next(source for source in result["log_sources"] if source["path"] == "/opt/suite/app/logs")
        self.assertEqual(item["type"], "app_logs_dir")
        self.assertTrue(item["exists"])

    def test_ignores_unsafe_outside_paths(self):
        with patch(
            "scanner_runtime.log_sources_discovery_v2._discover_opt_logs_candidates",
            return_value=["/root/secret/logs", "/opt/../etc/logs", "/opt/valid/logs"],
        ):
            with patch("scanner_runtime.log_sources_discovery_v2._opt_realpath_within_root", side_effect=lambda path: path == "/opt/valid/logs"):
                with patch("scanner_runtime.log_sources_discovery_v2.Path.stat", return_value=_FakeStat(size_bytes=111, mtime=1710000005)):
                    with patch("scanner_runtime.log_sources_discovery_v2.Path.is_dir", return_value=True):
                        result = collect_log_sources_v2({})

        paths = {item["path"] for item in result["log_sources"]}
        self.assertIn("/opt/valid/logs", paths)
        self.assertNotIn("/root/secret/logs", paths)
        self.assertNotIn("/etc/logs", paths)

    def test_rejects_opt_logs_symlink_realpath_escape(self):
        with patch("scanner_runtime.log_sources_discovery_v2.SYSTEM_CANDIDATES", []):
            with patch("scanner_runtime.log_sources_discovery_v2._discover_opt_logs_candidates", return_value=["/opt/myapp/logs"]):
                with patch("scanner_runtime.log_sources_discovery_v2._opt_realpath_within_root", return_value=False):
                    with patch("scanner_runtime.log_sources_discovery_v2.Path.stat", return_value=_FakeStat(size_bytes=1, mtime=1710000006)):
                        with patch("scanner_runtime.log_sources_discovery_v2.Path.is_dir", return_value=True):
                            result = collect_log_sources_v2({})

        self.assertEqual(result["log_sources"], [])
        self.assertNotIn("/root/secret", str(result))

    def test_does_not_read_log_contents(self):
        with patch("pathlib.Path.read_text", side_effect=AssertionError("must not read log contents")):
            with patch("scanner_runtime.log_sources_discovery_v2._discover_opt_logs_candidates", return_value=[]):
                collect_log_sources_v2({})

    def test_no_raw_log_line_appears_in_output(self):
        with patch("scanner_runtime.log_sources_discovery_v2._discover_opt_logs_candidates", return_value=[]):
            result = collect_log_sources_v2({})
        serialized = str(result)
        self.assertNotIn("Exception:", serialized)
        self.assertNotIn("Traceback", serialized)
        self.assertNotIn("ERROR", serialized)

    def test_permission_error_handled_safely(self):
        with patch("scanner_runtime.log_sources_discovery_v2._discover_opt_logs_candidates", return_value=["/opt/myapp/logs"]):
            with patch("scanner_runtime.log_sources_discovery_v2.Path.stat", side_effect=PermissionError):
                with patch("scanner_runtime.log_sources_discovery_v2.Path.is_dir", return_value=True):
                    result = collect_log_sources_v2({})
        self.assertGreaterEqual(result["summary"]["permission_denied"], 1)

    def test_output_cap_enforced(self):
        with patch("scanner_runtime.log_sources_discovery_v2.MAX_OUTPUT_BYTES", 10):
            with self.assertRaises(ValueError):
                collect_log_sources_v2({})

    def test_unsupported_tool_behavior_unchanged(self):
        result = execute_job({"tool_key": "unsupported_tool_key_v2", "params": {}})
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["error"], "Tool is not allowlisted by this runtime.")
