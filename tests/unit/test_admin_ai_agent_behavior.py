import json
from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import Account, User
from apps.ai_chat.live_ai import LIVE_AI_INSTRUCTIONS, _build_provider_input
from apps.ai_chat.models import AdminLiveAIRequestLog
from apps.ai_chat.services import create_admin_chat_session, create_chat_session
from apps.servers.models import AgentJob, Server
from apps.tools.models import ToolRun


LIVE_SETTINGS = {
    "ADMIN_LIVE_AI_ENABLED": True,
    "OPENAI_API_KEY": "server-only-test-key",
    "OPENAI_MODEL": "test-model",
    "OPENAI_CHATKIT_DOMAIN_KEY": "domain-test-key",
    "OPENAI_TIMEOUT_SECONDS": 3,
    "OPENAI_MAX_INPUT_TOKENS": 4000,
    "OPENAI_MAX_OUTPUT_TOKENS": 500,
    "ADMIN_LIVE_AI_RATE_LIMIT_PER_HOUR": 30,
}


class BehaviorProvider:
    def __init__(self):
        self.calls = []

    async def stream(self, *, instructions, input_text, state):
        self.calls.append({"instructions": instructions, "input_text": input_text})
        state.provider_request_id = "response-behavior-123"
        state.usage = {"input_units": 18, "output_units": 9}
        if '"diagnostic_intent":true' in input_text:
            yield (
                "Executive Summary\n"
                "Known State\n"
                "Potential Issues\n"
                "Limitations\n"
                "Suggested Read-Only Checks"
            )
        else:
            yield "Short answer from Safe Context."


class AdminAIAgentBehaviorTests(TestCase):
    def setUp(self):
        cache.clear()
        self.account = Account.objects.create(name="Acme")
        self.staff = User.objects.create_superuser(
            username="matrix-admin",
            email="admin@example.com",
            password="password",
        )
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="password",
            account=self.account,
            role=User.CustomerRole.OWNER,
        )
        self.server = Server.objects.create(
            account=self.account,
            name="Production",
            hostname="prod.example.test",
            status=Server.Status.ACTIVE,
        )
        self.session = create_admin_chat_session(
            user=self.staff,
            account_id=self.account.id,
            title="Behavior review",
            server_id=self.server.id,
        )
        self.client.force_login(self.staff)

    def live_url(self, session=None):
        return reverse("admin_chat:session_live", args=[(session or self.session).id])

    def live_payload(self, text, thread_id=None):
        return {
            "type": "threads.add_user_message",
            "params": {
                "thread_id": str(thread_id or self.session.id),
                "input": {
                    "content": [{"type": "input_text", "text": text}],
                    "attachments": [],
                    "inference_options": {},
                },
            },
        }

    @staticmethod
    async def _consume_async(stream):
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
        return b"".join(chunks)

    def consume_stream(self, response):
        if hasattr(response.streaming_content, "__aiter__"):
            return async_to_sync(self._consume_async)(response.streaming_content)
        return b"".join(response.streaming_content)

    @override_settings(**LIVE_SETTINGS)
    def test_diagnostic_question_gets_structured_contextual_mode(self):
        provider = BehaviorProvider()

        with patch("apps.ai_chat.live_ai.get_live_ai_provider", return_value=provider):
            response = self.client.post(
                self.live_url(),
                data=json.dumps(self.live_payload("شايف فين المشكلة وإيه المخاطر؟")),
                content_type="application/json",
            )
            body = self.consume_stream(response).decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn("Executive Summary", body)
        self.assertIn("Known State", body)
        self.assertIn("Potential Issues", body)
        self.assertIn("Suggested Read-Only Checks", body)
        self.assertEqual(len(provider.calls), 1)
        self.assertIn('"diagnostic_intent":true', provider.calls[0]["input_text"])
        self.assertIn('"response_mode":"contextual_diagnostic"', provider.calls[0]["input_text"])
        self.assertIn("observed facts", provider.calls[0]["instructions"])
        self.assertIn("inferred risks", provider.calls[0]["instructions"])
        self.assertTrue(AdminLiveAIRequestLog.objects.filter(status=AdminLiveAIRequestLog.Status.SUCCEEDED).exists())

    @override_settings(**LIVE_SETTINGS)
    def test_ordinary_question_stays_concise_mode(self):
        provider = BehaviorProvider()

        with patch("apps.ai_chat.live_ai.get_live_ai_provider", return_value=provider):
            response = self.client.post(
                self.live_url(),
                data=json.dumps(self.live_payload("What is the server hostname?")),
                content_type="application/json",
            )
            body = self.consume_stream(response).decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn("Short answer from Safe Context.", body)
        self.assertNotIn("Executive Summary", body)
        self.assertIn('"diagnostic_intent":false', provider.calls[0]["input_text"])
        self.assertIn('"response_mode":"concise_assistant"', provider.calls[0]["input_text"])

    def test_provider_input_uses_safe_context_and_redacted_conversation_only(self):
        provider_input = _build_provider_input(
            {
                "server": {"hostname": "prod.example.test"},
                "metadata": {"final_size_bytes": 123, "truncated": False},
            },
            [{"role": "user", "content": "diagnose sk-test-canary-secret"}],
        )

        self.assertIn("<SAFE_CONTEXT_DATA>", provider_input)
        self.assertIn("<REQUEST_ANALYSIS>", provider_input)
        self.assertIn("<REDACTED_CONVERSATION>", provider_input)
        self.assertIn('"diagnostic_intent":true', provider_input)
        self.assertNotIn("sk-test-canary-secret", provider_input)
        self.assertIn("[REDACTED]", provider_input)

    def test_base_instructions_are_hardcoded_internal_advisory_rules(self):
        self.assertIn("internal operational AI assistant", LIVE_AI_INSTRUCTIONS)
        self.assertIn("Use only the supplied Safe Context", LIVE_AI_INSTRUCTIONS)
        self.assertIn("You are advisory only.", LIVE_AI_INSTRUCTIONS)
        self.assertIn("You do not execute tools.", LIVE_AI_INSTRUCTIONS)
        self.assertIn("You do not run commands.", LIVE_AI_INSTRUCTIONS)
        self.assertIn("You do not create ToolRequest, ToolRun, AgentJob", LIVE_AI_INSTRUCTIONS)
        self.assertIn("Suggested checks must be read-only", LIVE_AI_INSTRUCTIONS)
        self.assertIn("Do not claim you performed live checks", LIVE_AI_INSTRUCTIONS)
        self.assertIn("Limitations", LIVE_AI_INSTRUCTIONS)

    @override_settings(**LIVE_SETTINGS)
    def test_live_ai_does_not_create_tools_or_agent_jobs(self):
        provider = BehaviorProvider()
        before = (ToolRun.objects.count(), AgentJob.objects.count())

        with patch("apps.ai_chat.live_ai.get_live_ai_provider", return_value=provider):
            response = self.client.post(
                self.live_url(),
                data=json.dumps(self.live_payload("diagnose this and run checks")),
                content_type="application/json",
            )
            body = self.consume_stream(response).decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn("Suggested Read-Only Checks", body)
        self.assertEqual(before, (ToolRun.objects.count(), AgentJob.objects.count()))

    @override_settings(**LIVE_SETTINGS)
    def test_feature_flag_off_preserves_previous_denial_behavior(self):
        with override_settings(ADMIN_LIVE_AI_ENABLED=False):
            response = self.client.post(
                self.live_url(),
                data=json.dumps(self.live_payload("diagnose this")),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 404)
        log = AdminLiveAIRequestLog.objects.get()
        self.assertEqual(log.status, AdminLiveAIRequestLog.Status.DENIED)
        self.assertEqual(log.error_class, AdminLiveAIRequestLog.ErrorClass.DISABLED)

    @override_settings(**LIVE_SETTINGS)
    def test_portal_customer_deterministic_chat_is_unchanged(self):
        portal_session = create_chat_session(user=self.owner, title="Portal chat", server_id=self.server.id)
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("portal:chat_session_detail", args=[portal_session.id]),
            data={"body": "شايف فين المشكلة؟"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(AdminLiveAIRequestLog.objects.exists())
        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    @override_settings(**LIVE_SETTINGS)
    def test_secret_like_input_is_not_echoed_in_response_or_error(self):
        provider = BehaviorProvider()

        with patch("apps.ai_chat.live_ai.get_live_ai_provider", return_value=provider):
            response = self.client.post(
                self.live_url(),
                data=json.dumps(self.live_payload("diagnose sk-test-canary-secret")),
                content_type="application/json",
            )
            body = self.consume_stream(response).decode()

        self.assertNotIn("sk-test-canary-secret", body)
        self.assertNotIn("sk-test-canary-secret", provider.calls[0]["input_text"])
        self.assertIn("[REDACTED]", provider.calls[0]["input_text"])
