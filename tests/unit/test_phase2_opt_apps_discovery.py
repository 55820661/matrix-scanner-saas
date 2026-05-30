import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from scanner_runtime.opt_discovery import OptDiscoveryError, collect_opt_apps
from scanner_runtime.prototype import execute_job


class Phase2OptAppsDiscoveryTests(SimpleTestCase):
    def with_opt_root(self):
        return tempfile.TemporaryDirectory(prefix="matrix-opt-discovery-")

    def write_text(self, path: Path, content: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def touch(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    def test_params_rejected(self):
        with self.assertRaisesMessage(ValueError, "does not accept parameters"):
            collect_opt_apps({"x": 1})

    def test_detects_django_by_manage_py(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            app_dir = root / "app1"
            self.touch(app_dir / "manage.py")
            self.touch(app_dir / "requirements.txt")

            with patch("scanner_runtime.opt_discovery.OPT_ROOT", root):
                result = collect_opt_apps({})

        self.assertIn("applications", result)
        self.assertNotIn("apps", result)
        self.assertEqual(result["summary"]["apps_total"], 1)
        self.assertEqual(result["applications"][0]["framework"], "django")
        self.assertIn("manage.py", result["applications"][0]["detection"])

    def test_django_with_public_supporting_marker_stays_django(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            app_dir = root / "django_public"
            self.touch(app_dir / "manage.py")
            (app_dir / "public").mkdir(parents=True, exist_ok=True)

            with patch("scanner_runtime.opt_discovery.OPT_ROOT", root):
                result = collect_opt_apps({})

        self.assertEqual(result["summary"]["apps_total"], 1)
        self.assertEqual(result["applications"][0]["framework"], "django")
        self.assertIn("public/", result["applications"][0]["detection"])

    def test_detects_laravel_by_artisan(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            app_dir = root / "laravel_app"
            self.touch(app_dir / "artisan")
            self.touch(app_dir / "composer.json")

            with patch("scanner_runtime.opt_discovery.OPT_ROOT", root):
                result = collect_opt_apps({})

        self.assertEqual(result["applications"][0]["framework"], "laravel")

    def test_detects_node_and_extracts_safe_name_from_package_json(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            app_dir = root / "node_app"
            self.write_text(app_dir / "package.json", json.dumps({"name": "safe-node-name", "scripts": {"start": "rm -rf /"}}))

            # Presence-based node detection + safe name extraction only.
            with patch("scanner_runtime.opt_discovery.OPT_ROOT", root):
                result = collect_opt_apps({})

        self.assertEqual(result["applications"][0]["framework"], "node")
        self.assertEqual(result["applications"][0]["name"], "safe-node-name")

    def test_node_with_public_supporting_marker_stays_node(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            app_dir = root / "node_public"
            self.write_text(app_dir / "package.json", json.dumps({"name": "node-public"}))
            (app_dir / "public").mkdir(parents=True, exist_ok=True)

            with patch("scanner_runtime.opt_discovery.OPT_ROOT", root):
                result = collect_opt_apps({})

        self.assertEqual(result["summary"]["apps_total"], 1)
        self.assertEqual(result["applications"][0]["framework"], "node")
        self.assertIn("public/", result["applications"][0]["detection"])

    def test_directory_with_only_public_is_not_counted(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            app_dir = root / "public_only"
            (app_dir / "public").mkdir(parents=True, exist_ok=True)

            with patch("scanner_runtime.opt_discovery.OPT_ROOT", root):
                result = collect_opt_apps({})

        self.assertEqual(result["summary"]["apps_total"], 0)

    def test_env_and_settings_are_not_required_and_do_not_break_scan(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            app_dir = root / "app_env"
            self.touch(app_dir / "manage.py")
            self.write_text(app_dir / ".env", "DB_PASSWORD=supersecret")
            self.write_text(app_dir / "settings.py", "SECRET_KEY='x'")

            with patch("scanner_runtime.opt_discovery.OPT_ROOT", root):
                result = collect_opt_apps({})

        self.assertEqual(result["summary"]["apps_total"], 1)

    def test_depth_two_candidate_dirs_scanned(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            app_dir = root / "suite" / "app2"
            self.touch(app_dir / "manage.py")

            with patch("scanner_runtime.opt_discovery.OPT_ROOT", root):
                result = collect_opt_apps({})

        self.assertEqual(result["summary"]["apps_total"], 1)
        self.assertEqual(result["applications"][0]["metadata"]["depth"], 2)

    def test_symlink_inside_opt_is_accepted_when_supported(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            target = root / "realapp"
            link = root / "linkapp"
            self.touch(target / "manage.py")

            try:
                os.symlink(str(target), str(link), target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks are not supported in this environment.")

            with patch("scanner_runtime.opt_discovery.OPT_ROOT", root):
                result = collect_opt_apps({})

        names = {item["name"] for item in result["applications"]}
        self.assertIn("realapp", names)

    def test_symlink_outside_opt_is_rejected_when_supported(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            outside = Path(tmp) / "outside"
            outside.mkdir(parents=True, exist_ok=True)
            (outside / "manage.py").write_text("", encoding="utf-8")

            link = root / "badlink"
            try:
                root.mkdir(parents=True, exist_ok=True)
                os.symlink(str(outside), str(link), target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks are not supported in this environment.")

            with patch("scanner_runtime.opt_discovery.OPT_ROOT", root):
                result = collect_opt_apps({})

        self.assertEqual(result["summary"]["apps_total"], 0)

    def test_heavy_dirs_skipped(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            heavy = root / "node_modules"
            self.touch(heavy / "manage.py")

            with patch("scanner_runtime.opt_discovery.OPT_ROOT", root):
                result = collect_opt_apps({})

        self.assertEqual(result["summary"]["apps_total"], 0)
        self.assertGreaterEqual(result["summary"]["dirs_skipped"], 1)

    def test_missing_root_is_handled_safely(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "missing-opt"

            with patch("scanner_runtime.opt_discovery.OPT_ROOT", root):
                result = collect_opt_apps({})

        self.assertEqual(result["summary"]["apps_total"], 0)
        self.assertEqual(result["summary"]["permission_denied"], 1)

    def test_execute_job_routes_opt_apps_discovery(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            app_dir = root / "app1"
            self.touch(app_dir / "manage.py")

            with patch("scanner_runtime.opt_discovery.OPT_ROOT", root):
                result = execute_job({"tool_key": "opt_apps_discovery", "params": {}})

        self.assertEqual(result["status"], "succeeded")
        self.assertIn("applications", result["output"])

    def test_execute_job_rejects_non_empty_params(self):
        with patch("scanner_runtime.opt_discovery.collect_opt_apps", side_effect=ValueError("opt_apps_discovery does not accept parameters.")):
            result = execute_job({"tool_key": "opt_apps_discovery", "params": {"x": 1}})
        self.assertEqual(result["status"], "rejected")

    def test_output_is_json_serializable_and_does_not_include_raw_file_contents(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            app_dir = root / "node_app"
            self.write_text(app_dir / "package.json", json.dumps({"name": "n", "private": True, "scripts": {"start": "echo SECRET=1"}}))
            with patch("scanner_runtime.opt_discovery.OPT_ROOT", root):
                result = collect_opt_apps({})

        serialized = json.dumps(result)
        self.assertNotIn("echo SECRET", serialized)
        self.assertNotIn("scripts", serialized)

    def test_opt_discovery_output_cap_error_surfaces_as_failed(self):
        with patch("scanner_runtime.prototype.collect_opt_apps", side_effect=OptDiscoveryError("opt_apps_discovery output exceeded the configured cap.")):
            result = execute_job({"tool_key": "opt_apps_discovery", "params": {}})
        self.assertEqual(result["status"], "failed")
