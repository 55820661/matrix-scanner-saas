import json
from unittest.mock import patch

from django.test import SimpleTestCase

from scanner_runtime.nginx_discovery import collect_nginx_sites
from scanner_runtime.prototype import execute_job


def payload(content, source_path="/etc/nginx/sites-enabled/app.conf"):
    return {"source_path": source_path, "content": content, "bytes": len(content.encode("utf-8"))}


class Phase2NginxSitesDiscoveryTests(SimpleTestCase):
    def collect_payloads(self, *payload_results):
        candidates = [f"candidate-{index}" for index, _item in enumerate(payload_results)]
        with (
            patch("scanner_runtime.nginx_discovery.candidate_config_files", return_value=candidates),
            patch("scanner_runtime.nginx_discovery.read_config_file", side_effect=payload_results),
        ):
            return collect_nginx_sites({})

    def test_simple_server_block_parsing(self):
        result = self.collect_payloads(
            (
                payload(
                    """
                    server {
                        listen 80;
                        server_name example.com;
                        root /opt/example/current/public;
                    }
                    """
                ),
                "",
            )
        )

        self.assertEqual(result["summary"]["sites"], 1)
        self.assertEqual(result["domains"][0]["domain"], "example.com")
        self.assertEqual(result["domains"][0]["document_root"], "/opt/example/current/public")
        self.assertEqual(result["sites"][0]["listen_ports"], [80])

    def test_multiple_server_names_and_comments_ignored(self):
        result = self.collect_payloads(
            (
                payload(
                    """
                    # server_name ignored.example.com;
                    server {
                        listen 443 ssl; # comment after directive
                        server_name example.com www.example.com *.example.net; # three names
                        root /opt/example/public;
                    }
                    """
                ),
                "",
            )
        )

        domains = {item["domain"] for item in result["domains"]}
        self.assertEqual(domains, {"example.com", "www.example.com", "*.example.net"})
        self.assertTrue(result["sites"][0]["metadata"]["has_wildcard"])
        self.assertNotIn("ignored.example.com", domains)

    def test_multiple_server_blocks_summary_counts(self):
        result = self.collect_payloads(
            (
                payload(
                    """
                    server { listen 80 default_server; server_name _; }
                    server { listen 8080; server_name app.example.com; proxy_pass http://127.0.0.1:8020; }
                    """
                ),
                "",
            )
        )

        self.assertEqual(result["summary"]["sites"], 2)
        self.assertEqual(result["summary"]["domains"], 1)
        self.assertEqual(result["summary"]["default_sites"], 1)
        self.assertEqual(result["summary"]["proxied_sites"], 1)
        self.assertEqual(result["domains"][0]["proxy_pass"], "http://127.0.0.1:8020")

    def test_proxy_pass_credentials_and_variables_are_dropped(self):
        result = self.collect_payloads(
            (
                payload(
                    """
                    server {
                        server_name secret.example.com;
                        proxy_pass http://user:password@127.0.0.1:8020;
                    }
                    server {
                        server_name variable.example.com;
                        proxy_pass http://127.0.0.1:$port;
                    }
                    """
                ),
                "",
            )
        )

        self.assertEqual([site["proxy_pass"] for site in result["sites"]], ["", ""])

    def test_paths_are_canonicalized_and_unsafe_paths_ignored(self):
        result = self.collect_payloads(
            (
                payload(
                    """
                    server {
                        server_name app.example.com;
                        root /opt/app/../app/public;
                        access_log /var/log/nginx/app.access.log main;
                        error_log /var/log/nginx/app.error.log warn;
                    }
                    server {
                        server_name blocked.example.com;
                        root /root/app;
                        access_log /etc/ssl/private/access.log;
                        error_log /opt/app/.env;
                    }
                    server {
                        server_name variable-root.example.com;
                        root /opt/$host/public;
                    }
                    """
                ),
                "",
            )
        )

        by_name = {site["server_names"][0]: site for site in result["sites"]}
        self.assertEqual(by_name["app.example.com"]["root"], "/opt/app/public")
        self.assertEqual(by_name["app.example.com"]["access_log"], "/var/log/nginx/app.access.log")
        self.assertEqual(by_name["app.example.com"]["error_log"], "/var/log/nginx/app.error.log")
        self.assertEqual(by_name["blocked.example.com"]["root"], "")
        self.assertEqual(by_name["blocked.example.com"]["access_log"], "")
        self.assertEqual(by_name["blocked.example.com"]["error_log"], "")
        self.assertEqual(by_name["variable-root.example.com"]["root"], "")

    def test_cert_key_directives_ignored_and_no_raw_config_output(self):
        result = self.collect_payloads(
            (
                payload(
                    """
                    server {
                        listen 443 ssl;
                        server_name tls.example.com;
                        ssl_certificate /etc/letsencrypt/live/tls/fullchain.pem;
                        ssl_certificate_key /etc/ssl/private/tls.key;
                        auth_basic_user_file /etc/nginx/.htpasswd;
                    }
                    """
                ),
                "",
            )
        )

        serialized = json.dumps(result)
        self.assertNotIn("ssl_certificate", serialized)
        self.assertNotIn("tls.key", serialized)
        self.assertNotIn(".htpasswd", serialized)

    def test_symlink_inside_allowlist_accepted(self):
        result = self.collect_payloads(
            (
                payload("server { listen 80; server_name linked.example.com; }", source_path="/etc/nginx/sites-available/linked.conf"),
                "",
            )
        )

        self.assertEqual(result["domains"][0]["domain"], "linked.example.com")
        self.assertEqual(result["summary"]["rejected_files"], 0)

    def test_symlink_outside_allowlist_rejected(self):
        result = self.collect_payloads((None, "outside_allowlist"))

        self.assertEqual(result["domains"], [])
        self.assertEqual(result["summary"]["rejected_files"], 1)

    def test_include_directives_are_flagged_not_followed(self):
        result = self.collect_payloads(
            (
                payload(
                    """
                    server {
                        listen 80;
                        server_name include.example.com;
                        include /tmp/should-not-be-read.conf;
                    }
                    """
                ),
                "",
            )
        )

        self.assertTrue(result["sites"][0]["metadata"]["has_include"])
        self.assertEqual(result["summary"]["files_scanned"], 1)

    def test_params_rejected(self):
        result = execute_job({"tool_key": "nginx_sites_discovery", "params": {"path": "/etc/nginx/nginx.conf"}})

        self.assertEqual(result["status"], "rejected")
        self.assertIn("does not accept parameters", result["error"])

    def test_execute_job_nginx_discovery_succeeds_with_mocked_collector(self):
        with patch("scanner_runtime.prototype.collect_nginx_sites", return_value={"sites": [], "domains": [], "summary": {"sites": 0}}):
            result = execute_job({"tool_key": "nginx_sites_discovery", "params": {}})

        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["output"], {"sites": [], "domains": [], "summary": {"sites": 0}})

    def test_unsupported_tool_behavior_unchanged(self):
        result = execute_job({"tool_key": "not_supported", "params": {}})

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["error"], "Tool is not allowlisted by this runtime.")
