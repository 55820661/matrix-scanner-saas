import json
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.ai_chat.models import AdminChatToolRequest
from apps.ai_context.services import apply_safe_context_hard_cap, prepare_safe_context_for_ai
from apps.servers.models import AgentJob
from apps.tools.models import ToolRun


class AIContextSafetyTests(SimpleTestCase):
    @override_settings(AI_SAFE_CONTEXT_MAX_BYTES=2048)
    def test_configured_hard_cap_is_structured_and_deterministic(self):
        context = {
            "context_version": "1.0",
            "account_summary": {"id": "account-1", "name": "Acme"},
            "server_summary": {"id": "server-1", "name": "Production"},
            "applications_summary": [
                {"id": str(index), "name": "a" * 450, "metadata": {"verbose": "m" * 450}}
                for index in range(10)
            ],
            "reports_summary": [{"id": str(index), "summary": "r" * 450} for index in range(10)],
            "knowledge_summary": [{"id": str(index), "body_summary": "k" * 450} for index in range(10)],
        }

        first = apply_safe_context_hard_cap(context)
        second = apply_safe_context_hard_cap(context)
        serialized = json.dumps(first, sort_keys=True)

        self.assertEqual(first, second)
        self.assertLessEqual(len(serialized.encode("utf-8")), 2048)
        self.assertTrue(first["metadata"]["truncated"])
        self.assertGreater(first["metadata"]["original_size_bytes"], 2048)
        self.assertEqual(first["metadata"]["final_size_bytes"], len(serialized.encode("utf-8")))
        self.assertEqual(first["metadata"]["max_size_bytes"], 2048)
        self.assertEqual(json.loads(serialized), first)
        self.assertEqual(first["account_summary"]["id"], "account-1")
        self.assertEqual(first["server_summary"]["id"], "server-1")

    def test_second_redaction_removes_canaries_and_forbidden_payload_sections(self):
        canaries = (
            "sk-test-canary-secret",
            "password=canary-password",
            "PRIVATE_KEY_CANARY",
            "TOKEN_CANARY_123",
            "AWS_SECRET_ACCESS_KEY_CANARY",
        )
        context = {
            "context_version": "1.0",
            "account_summary": {"id": "1", "name": canaries[0], "raw_dump": canaries[1]},
            "server_summary": {"id": "2", "name": canaries[2], "raw_env": canaries[3]},
            "findings_summary": [
                {
                    "id": "3",
                    "title": canaries[3],
                    "severity": "critical",
                    "evidence_summary": canaries[1],
                    "raw_logs": canaries[4],
                }
            ],
            "reports_summary": [{"id": "4", "title": canaries[4], "summary": canaries[0]}],
            "recent_tool_runs": [{"result_redacted": canaries[0], "raw_output": canaries[1]}],
            "agent_jobs": [{"result": canaries[4]}],
            "environment": {"SECRET": canaries[0]},
        }

        with self.assertNoLogs(level="INFO"):
            capped = apply_safe_context_hard_cap(context)
            payload = prepare_safe_context_for_ai(capped)

        capped_json = json.dumps(capped, sort_keys=True)
        payload_json = json.dumps(payload, sort_keys=True)
        for canary in canaries:
            self.assertNotIn(canary, capped_json)
            self.assertNotIn(canary, payload_json)
        self.assertIn("[REDACTED]", payload_json)
        for forbidden_key in (
            "raw_logs",
            "raw_env",
            "raw_output",
            "result_redacted",
            "agent_jobs",
            "environment",
        ):
            self.assertNotIn(forbidden_key, payload_json)

    def test_truncation_keeps_critical_findings_ahead_of_verbose_sections(self):
        context = {
            "context_version": "1.0",
            "account_summary": {"id": "account-1", "name": "Acme"},
            "server_summary": {"id": "server-1", "name": "Production"},
            "findings_summary": [
                {"id": "info", "severity": "info", "title": "i" * 450},
                {"id": "critical", "severity": "critical", "title": "Critical issue"},
            ],
            "diagnostics_summary": [{"id": str(index), "summary": "d" * 450} for index in range(10)],
            "reports_summary": [{"id": str(index), "summary": "r" * 450} for index in range(10)],
        }

        payload = prepare_safe_context_for_ai(context, max_bytes=2048)
        serialized = json.dumps(payload, sort_keys=True)

        self.assertLessEqual(len(serialized.encode("utf-8")), 2048)
        self.assertTrue(payload["metadata"]["truncated"])
        self.assertEqual(payload["findings_summary"][0]["id"], "critical")
        self.assertEqual(json.loads(serialized), payload)

    def test_payload_preparation_cannot_create_execution_objects(self):
        context = {
            "context_version": "1.0",
            "account_summary": {"id": "account-1", "name": "Acme"},
            "server_summary": {"id": "server-1", "name": "Production"},
            "available_tools": [{"key": "status", "name": "Status"}],
        }

        with (
            patch.object(AdminChatToolRequest.objects, "create") as create_request,
            patch.object(ToolRun.objects, "create") as create_run,
            patch.object(AgentJob.objects, "create") as create_job,
        ):
            payload = prepare_safe_context_for_ai(context)

        create_request.assert_not_called()
        create_run.assert_not_called()
        create_job.assert_not_called()
        self.assertFalse(payload["metadata"]["tools_enabled"])
        self.assertIn("Do not execute tools", " ".join(payload["safety_guidance"]["instructions"]))

    def test_minimal_fallback_keeps_non_execution_safety_guidance(self):
        payload = prepare_safe_context_for_ai(
            {
                "context_version": "1.0",
                "account_summary": {"id": "account-1", "name": "a" * 10000},
                "server_summary": {"id": "server-1", "name": "s" * 10000},
            },
            max_bytes=2048,
        )

        serialized = json.dumps(payload, sort_keys=True)
        self.assertLessEqual(len(serialized.encode("utf-8")), 2048)
        self.assertTrue(payload["metadata"]["truncated"])
        self.assertEqual(payload["safety_guidance"]["context_trust"], "untrusted_reference_data")
        self.assertIn("Do not execute tools", " ".join(payload["safety_guidance"]["instructions"]))
