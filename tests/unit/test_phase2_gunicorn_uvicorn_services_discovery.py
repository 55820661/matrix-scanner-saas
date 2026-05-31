import subprocess
from unittest.mock import patch

from django.test import SimpleTestCase

from scanner_runtime.gunicorn_uvicorn_discovery import collect_gunicorn_uvicorn_services
from scanner_runtime.prototype import execute_job
from scanner_runtime.safe_exec import SafeExecError


class Phase2GunicornUvicornDiscoveryTests(SimpleTestCase):
    def _mock_collect(self, list_stdout, show_stdout):
        list_result = subprocess.CompletedProcess(args=["systemctl"], returncode=0, stdout=list_stdout, stderr="")
        show_result = subprocess.CompletedProcess(args=["systemctl"], returncode=0, stdout=show_stdout, stderr="")
        with patch("scanner_runtime.gunicorn_uvicorn_discovery.run_fixed_command", side_effect=[list_result, show_result]):
            return collect_gunicorn_uvicorn_services({})

    def test_params_rejected(self):
        with self.assertRaisesMessage(ValueError, "does not accept parameters"):
            collect_gunicorn_uvicorn_services({"service": "x"})

    def test_parses_gunicorn_service(self):
        result = self._mock_collect(
            "my-gunicorn.service loaded active running Gunicorn app\n",
            (
                "Id=my-gunicorn.service\nDescription=Gunicorn API service\nLoadState=loaded\nActiveState=active\n"
                "SubState=running\nUnitFileState=enabled\nMainPID=123\nFragmentPath=/etc/systemd/system/my-gunicorn.service\n"
                "User=www-data\nWorkingDirectory=/opt/myapp/current\n\n"
            ),
        )

        service = result["services"][0]
        self.assertEqual(service["process_type"], "gunicorn")
        self.assertEqual(service["service_name"], "my-gunicorn.service")
        self.assertEqual(service["active_state"], "active")

    def test_parses_uvicorn_service(self):
        result = self._mock_collect(
            "my-uvicorn.service loaded active running Uvicorn app\n",
            (
                "Id=my-uvicorn.service\nDescription=Uvicorn ASGI service\nLoadState=loaded\nActiveState=active\n"
                "SubState=running\nUnitFileState=enabled\nMainPID=321\nFragmentPath=/lib/systemd/system/my-uvicorn.service\n"
                "User=svc\nWorkingDirectory=/opt/suite/app/current\n\n"
            ),
        )

        self.assertEqual(result["services"][0]["process_type"], "uvicorn")

    def test_parses_daphne_service(self):
        result = self._mock_collect(
            "my-daphne.service loaded active running Daphne app\n",
            (
                "Id=my-daphne.service\nDescription=Daphne websocket service\nLoadState=loaded\nActiveState=active\n"
                "SubState=running\nUnitFileState=enabled\nMainPID=222\nFragmentPath=/etc/systemd/system/my-daphne.service\n"
                "User=svc\nWorkingDirectory=/opt/webapp\n\n"
            ),
        )
        self.assertEqual(result["services"][0]["process_type"], "daphne")

    def test_redacts_secret_like_description(self):
        result = self._mock_collect(
            "secret.service loaded active running secret\n",
            (
                "Id=secret.service\nDescription=password=secret token=abc\nLoadState=loaded\nActiveState=active\n"
                "SubState=running\nUnitFileState=enabled\nMainPID=11\nFragmentPath=/etc/systemd/system/secret.service\n"
                "User=svc\nWorkingDirectory=/opt/secret\n\n"
            ),
        )
        serialized = str(result)
        self.assertNotIn("token=abc", serialized)
        self.assertNotIn("password=secret", serialized)

    def test_never_returns_execstart_or_environment(self):
        result = self._mock_collect(
            "x.service loaded active running X\n",
            (
                "Id=x.service\nDescription=Service\nLoadState=loaded\nActiveState=active\n"
                "SubState=running\nUnitFileState=enabled\nMainPID=1\nFragmentPath=/etc/systemd/system/x.service\n"
                "User=svc\nWorkingDirectory=/opt/x\nExecStart=/usr/bin/python app.py\nEnvironment=TOKEN=abc\n\n"
            ),
        )
        service = result["services"][0]
        self.assertNotIn("ExecStart", service)
        self.assertNotIn("Environment", service)

    def test_working_directory_under_opt_maps_related_app_path(self):
        result = self._mock_collect(
            "app.service loaded active running App\n",
            (
                "Id=app.service\nDescription=App\nLoadState=loaded\nActiveState=active\n"
                "SubState=running\nUnitFileState=enabled\nMainPID=9\nFragmentPath=/etc/systemd/system/app.service\n"
                "User=svc\nWorkingDirectory=/opt/suite/app/current\n\n"
            ),
        )
        self.assertEqual(result["services"][0]["related_app_path"], "/opt/suite/app")
        self.assertEqual(result["summary"]["applications_total"], 1)

    def test_working_directory_myapp_current_maps_to_app_root(self):
        result = self._mock_collect(
            "app.service loaded active running App\n",
            (
                "Id=app.service\nDescription=App\nLoadState=loaded\nActiveState=active\n"
                "SubState=running\nUnitFileState=enabled\nMainPID=9\nFragmentPath=/etc/systemd/system/app.service\n"
                "User=svc\nWorkingDirectory=/opt/myapp/current\n\n"
            ),
        )
        self.assertEqual(result["services"][0]["related_app_path"], "/opt/myapp")

    def test_working_directory_myapp_releases_maps_to_app_root(self):
        result = self._mock_collect(
            "app.service loaded active running App\n",
            (
                "Id=app.service\nDescription=App\nLoadState=loaded\nActiveState=active\n"
                "SubState=running\nUnitFileState=enabled\nMainPID=9\nFragmentPath=/etc/systemd/system/app.service\n"
                "User=svc\nWorkingDirectory=/opt/myapp/releases/20260531\n\n"
            ),
        )
        self.assertEqual(result["services"][0]["related_app_path"], "/opt/myapp")

    def test_working_directory_outside_opt_omitted(self):
        result = self._mock_collect(
            "other.service loaded active running Other\n",
            (
                "Id=other.service\nDescription=Other\nLoadState=loaded\nActiveState=active\n"
                "SubState=running\nUnitFileState=enabled\nMainPID=7\nFragmentPath=/etc/systemd/system/other.service\n"
                "User=svc\nWorkingDirectory=/srv/other\n\n"
            ),
        )
        service = result["services"][0]
        self.assertEqual(service["working_directory"], "")
        self.assertEqual(service["related_app_path"], "")

    def test_output_cap_enforced(self):
        list_result = subprocess.CompletedProcess(args=["systemctl"], returncode=0, stdout="a.service loaded active running A\n", stderr="")
        show_result = subprocess.CompletedProcess(
            args=["systemctl"],
            returncode=0,
            stdout=(
                "Id=a.service\nDescription=VeryLongDescription\nLoadState=loaded\nActiveState=active\n"
                "SubState=running\nUnitFileState=enabled\nMainPID=1\nFragmentPath=/etc/systemd/system/a.service\n"
                "User=svc\nWorkingDirectory=/opt/a\n\n"
            ),
            stderr="",
        )
        with patch("scanner_runtime.gunicorn_uvicorn_discovery.MAX_OUTPUT_BYTES", 10):
            with patch("scanner_runtime.gunicorn_uvicorn_discovery.run_fixed_command", side_effect=[list_result, show_result]):
                with self.assertRaises(SafeExecError):
                    collect_gunicorn_uvicorn_services({})

    def test_execute_job_supported_tool(self):
        with patch("scanner_runtime.prototype.collect_gunicorn_uvicorn_services", return_value={"services": [], "applications": [], "summary": {}}):
            result = execute_job({"tool_key": "gunicorn_uvicorn_services_discovery", "params": {}})
        self.assertEqual(result["status"], "succeeded")

    def test_unsupported_tool_behavior_unchanged(self):
        result = execute_job({"tool_key": "still_unknown", "params": {}})
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["error"], "Tool is not allowlisted by this runtime.")
