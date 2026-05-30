import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from scanner_runtime.django_discovery import collect_django_apps
from scanner_runtime.prototype import execute_job


class Phase2DjangoAppsDiscoveryTests(SimpleTestCase):
    def with_opt_root(self):
        return tempfile.TemporaryDirectory(prefix="matrix-django-discovery-")

    def touch(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    def write_text(self, path: Path, content: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_params_rejected(self):
        with self.assertRaisesMessage(ValueError, "does not accept parameters"):
            collect_django_apps({"path": "/opt/app"})

    def test_detects_django_by_manage_py(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            app = root / "app"
            self.touch(app / "manage.py")

            with patch("scanner_runtime.django_discovery.OPT_ROOT", root):
                result = collect_django_apps({})

        self.assertIn("applications", result)
        self.assertNotIn("apps", result)
        self.assertEqual(result["summary"]["apps_total"], 1)
        self.assertEqual(result["applications"][0]["framework"], "django")
        self.assertTrue(result["applications"][0]["has_manage_py"])

    def test_detects_django_with_manage_py_and_project_wsgi(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            app = root / "app"
            self.touch(app / "manage.py")
            self.touch(app / "config" / "wsgi.py")

            with patch("scanner_runtime.django_discovery.OPT_ROOT", root):
                result = collect_django_apps({})

        application = result["applications"][0]
        self.assertEqual(application["project_package"], "config")
        self.assertTrue(application["has_wsgi"])
        self.assertIn("config/wsgi.py", application["detection"])

    def test_child_package_with_wsgi_not_counted_separately_when_parent_has_manage_py(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            app = root / "app"
            self.touch(app / "manage.py")
            self.touch(app / "config" / "wsgi.py")
            self.touch(app / "config" / "urls.py")

            with patch("scanner_runtime.django_discovery.OPT_ROOT", root):
                result = collect_django_apps({})

        self.assertEqual(result["summary"]["apps_total"], 1)
        self.assertEqual(result["applications"][0]["path"], str(app))
        self.assertGreaterEqual(result["summary"]["nested_candidates_skipped"], 0)

    def test_directory_with_only_wsgi_is_not_counted(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            self.touch(root / "package" / "wsgi.py")

            with patch("scanner_runtime.django_discovery.OPT_ROOT", root):
                result = collect_django_apps({})

        self.assertEqual(result["summary"]["apps_total"], 0)

    def test_directory_with_only_settings_is_not_read_or_counted(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            self.write_text(root / "settings_only" / "settings.py", "SECRET_KEY='raw-secret'")

            with patch("scanner_runtime.django_discovery.OPT_ROOT", root):
                result = collect_django_apps({})

        serialized = json.dumps(result)
        self.assertEqual(result["summary"]["apps_total"], 0)
        self.assertNotIn("raw-secret", serialized)
        self.assertNotIn("SECRET_KEY", serialized)

    def test_env_ignored(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            app = root / "app"
            self.touch(app / "manage.py")
            self.write_text(app / ".env", "DATABASE_URL=postgres://secret")

            with patch("scanner_runtime.django_discovery.OPT_ROOT", root):
                result = collect_django_apps({})

        serialized = json.dumps(result)
        self.assertEqual(result["summary"]["apps_total"], 1)
        self.assertNotIn("DATABASE_URL", serialized)
        self.assertNotIn("postgres://secret", serialized)

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

            with patch("scanner_runtime.django_discovery.OPT_ROOT", root):
                result = collect_django_apps({})

        self.assertEqual(result["summary"]["apps_total"], 1)
        self.assertEqual(result["applications"][0]["name"], "realapp")

    def test_symlink_outside_opt_is_rejected_when_supported(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            outside = Path(tmp) / "outside"
            self.touch(outside / "manage.py")
            link = root / "badlink"
            root.mkdir(parents=True, exist_ok=True)

            try:
                os.symlink(str(outside), str(link), target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks are not supported in this environment.")

            with patch("scanner_runtime.django_discovery.OPT_ROOT", root):
                result = collect_django_apps({})

        self.assertEqual(result["summary"]["apps_total"], 0)

    def test_depth_two_behavior_works(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            app = root / "suite" / "app"
            self.touch(app / "manage.py")

            with patch("scanner_runtime.django_discovery.OPT_ROOT", root):
                result = collect_django_apps({})

        self.assertEqual(result["summary"]["apps_total"], 1)
        self.assertEqual(result["applications"][0]["metadata"]["depth"], 2)

    def test_heavy_dirs_skipped(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            self.touch(root / "node_modules" / "manage.py")

            with patch("scanner_runtime.django_discovery.OPT_ROOT", root):
                result = collect_django_apps({})

        self.assertEqual(result["summary"]["apps_total"], 0)
        self.assertGreaterEqual(result["summary"]["dirs_skipped"], 1)

    def test_strong_marker_plus_django_indicator_detected(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            app = root / "pyproject_app"
            self.write_text(app / "pyproject.toml", '[project]\nname = "safe-django-name"\n')
            self.touch(app / "config" / "asgi.py")

            with patch("scanner_runtime.django_discovery.OPT_ROOT", root):
                result = collect_django_apps({})

        application = result["applications"][0]
        self.assertEqual(application["name"], "safe-django-name")
        self.assertEqual(application["framework"], "django")
        self.assertTrue(application["has_asgi"])

    def test_execute_job_routes_django_apps_discovery(self):
        with self.with_opt_root() as tmp:
            root = Path(tmp) / "opt"
            self.touch(root / "app" / "manage.py")

            with patch("scanner_runtime.django_discovery.OPT_ROOT", root):
                result = execute_job({"tool_key": "django_apps_discovery", "params": {}})

        self.assertEqual(result["status"], "succeeded")
        self.assertIn("applications", result["output"])

    def test_execute_job_rejects_non_empty_params(self):
        result = execute_job({"tool_key": "django_apps_discovery", "params": {"path": "/opt/app"}})
        self.assertEqual(result["status"], "rejected")

    def test_unsupported_tool_behavior_unchanged(self):
        result = execute_job({"tool_key": "unknown_phase2_tool", "params": {}})
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["output"], {})

