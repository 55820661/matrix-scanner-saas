import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import Account, User
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


class FakeStreamingResult:
    async def __aiter__(self):
        yield b'data: {"type":"stream_options","stream_options":{"allow_cancel":true}}\n\n'
        raise RuntimeError("stream failed with sk-test-should-not-leak")


class SuccessProvider:
    async def stream(self, *, instructions, input_text, state):
        state.provider_request_id = "response-after-failure"
        state.usage = {"input_units": 8, "output_units": 3}
        yield "Recovered response."


class LiveAIFailureFinalizationTests(TestCase):
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
            title="Failure finalization",
            server_id=self.server.id,
        )
        self.client.force_login(self.staff)

    def live_url(self, session=None):
        return reverse("admin_chat:session_live", args=[(session or self.session).id])

    def live_payload(self, text="Check status", thread_id=None):
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
    def test_exception_before_streaming_finalizes_audit_failed(self):
        before = (ToolRun.objects.count(), AgentJob.objects.count())
        with patch(
            "apps.ai_chat.views.live_admin_chatkit_server.process",
            new=AsyncMock(side_effect=RuntimeError("pre-stream failed with sk-test-should-not-leak")),
        ):
            response = self.client.post(
                self.live_url(),
                data=json.dumps(self.live_payload("status sk-test-should-not-leak")),
                content_type="application/json",
            )

        log = AdminLiveAIRequestLog.objects.get()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Live AI is temporarily unavailable. Please try again.")
        self.assertNotIn("deterministic fallback", response.content.decode().lower())
        self.assertNotIn("sk-test-should-not-leak", response.content.decode())
        self.assertEqual(log.status, AdminLiveAIRequestLog.Status.FAILED)
        self.assertNotEqual(log.status, AdminLiveAIRequestLog.Status.PENDING)
        self.assertEqual(log.error_class, AdminLiveAIRequestLog.ErrorClass.UPSTREAM_ERROR)
        self.assertGreater(log.latency_ms, 0)
        self.assertTrue(log.fallback_used)
        self.assertEqual(before, (ToolRun.objects.count(), AgentJob.objects.count()))

    @override_settings(**LIVE_SETTINGS)
    def test_exception_inside_streaming_generator_finalizes_audit_failed(self):
        before = (ToolRun.objects.count(), AgentJob.objects.count())
        with (
            patch("apps.ai_chat.views.StreamingResult", FakeStreamingResult),
            patch(
                "apps.ai_chat.views.live_admin_chatkit_server.process",
                new=AsyncMock(return_value=FakeStreamingResult()),
            ),
        ):
            response = self.client.post(
                self.live_url(),
                data=json.dumps(self.live_payload("stream failure")),
                content_type="application/json",
            )
            body = self.consume_stream(response)

        log = AdminLiveAIRequestLog.objects.get()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"temporarily unavailable", body)
        self.assertNotIn(b"sk-test-should-not-leak", body)
        self.assertEqual(log.status, AdminLiveAIRequestLog.Status.FAILED)
        self.assertNotEqual(log.status, AdminLiveAIRequestLog.Status.PENDING)
        self.assertEqual(log.error_class, AdminLiveAIRequestLog.ErrorClass.UPSTREAM_ERROR)
        self.assertGreater(log.latency_ms, 0)
        self.assertTrue(log.fallback_used)
        self.assertEqual(log.response_size_bytes, 0)
        self.assertEqual(before, (ToolRun.objects.count(), AgentJob.objects.count()))

    @override_settings(**LIVE_SETTINGS)
    def test_success_after_stream_failure_creates_success_audit(self):
        with (
            patch("apps.ai_chat.views.StreamingResult", FakeStreamingResult),
            patch(
                "apps.ai_chat.views.live_admin_chatkit_server.process",
                new=AsyncMock(return_value=FakeStreamingResult()),
            ),
        ):
            failed = self.client.post(
                self.live_url(),
                data=json.dumps(self.live_payload("first")),
                content_type="application/json",
            )
            self.consume_stream(failed)

        with patch("apps.ai_chat.live_ai.get_live_ai_provider", return_value=SuccessProvider()):
            succeeded = self.client.post(
                self.live_url(),
                data=json.dumps(self.live_payload("second")),
                content_type="application/json",
            )
            body = self.consume_stream(succeeded)

        self.assertIn(b"Recovered response", body)
        self.assertEqual(AdminLiveAIRequestLog.objects.filter(status=AdminLiveAIRequestLog.Status.FAILED).count(), 1)
        self.assertEqual(AdminLiveAIRequestLog.objects.filter(status=AdminLiveAIRequestLog.Status.SUCCEEDED).count(), 1)
        self.assertFalse(AdminLiveAIRequestLog.objects.filter(status=AdminLiveAIRequestLog.Status.PENDING).exists())

    def test_frontend_has_no_custom_status_error_strip_and_loads_history(self):
        asset_path = finders.find("admin_chat/live_chatkit.js")
        self.assertTrue(asset_path)
        self.assertEqual(
            Path(asset_path).resolve(),
            (settings.BASE_DIR / "apps" / "ai_chat" / "static" / "admin_chat" / "live_chatkit.js").resolve(),
        )
        source = Path(asset_path).read_text(encoding="utf-8")
        self.assertIn("history: { enabled: true }", source)
        self.assertNotIn("function clearError()", source)
        self.assertNotIn("clearError()", source)
        self.assertNotIn("showError", source)
        self.assertNotIn("chatkit.error", source)
        self.assertNotIn("matrix-live-ai-status", source)
        self.assertNotIn("matrix-live-ai-error", source)
        self.assertNotIn("Live AI ready", source)
        self.assertNotIn("Live AI is temporarily unavailable", source)
        self.assertNotIn("showFallback", source)
        self.assertNotIn("deterministic fallback remains available", source)

    @override_settings(**LIVE_SETTINGS)
    def test_portal_deterministic_chat_is_unchanged(self):
        portal_session = create_chat_session(user=self.owner, title="Portal deterministic", server_id=self.server.id)
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("portal:chat_session_detail", args=[portal_session.id]),
            data={"body": "server status"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(AdminLiveAIRequestLog.objects.exists())
        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)
