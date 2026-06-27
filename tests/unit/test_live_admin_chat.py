import asyncio
import json
from pathlib import Path
from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.ai_chat.chatkit_store import AdminChatKitContext, AdminChatKitStore
from apps.accounts.models import Account, User
from apps.ai_chat.models import AdminChatMessage, AdminChatSession, AdminChatToolRequest
from apps.ai_chat.services import create_admin_chat_session
from apps.servers.models import AgentJob, Finding, Server
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


class FakeProvider:
    def __init__(self, chunks=None):
        self.chunks = chunks or ["Server ", "is healthy."]
        self.calls = []

    async def stream(self, *, instructions, input_text, state):
        self.calls.append({"instructions": instructions, "input_text": input_text})
        state.provider_request_id = "response-safe-123"
        state.usage = {"input_units": 25, "output_units": 7}
        for chunk in self.chunks:
            yield chunk


class FailingProvider:
    async def stream(self, *, instructions, input_text, state):
        raise RuntimeError("provider failed")
        yield ""


class SlowProvider:
    async def stream(self, *, instructions, input_text, state):
        await asyncio.sleep(2)
        yield "late"


class LiveAdminChatTests(TestCase):
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
            title="Live review",
            server_id=self.server.id,
        )
        self.client.force_login(self.staff)

    def live_url(self, session=None):
        return reverse("admin_chat:session_live", args=[(session or self.session).id])

    def live_payload(self, text="What is the server status?", thread_id=None):
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

    @override_settings(**{**LIVE_SETTINGS, "ADMIN_LIVE_AI_ENABLED": False})
    def test_feature_flag_off_hides_chatkit_and_never_calls_provider(self):
        with patch("apps.ai_chat.live_ai.get_live_ai_provider") as provider:
            page = self.client.get(reverse("admin_chat:session_detail", args=[self.session.id]))
            response = self.client.post(
                self.live_url(),
                data=json.dumps(self.live_payload()),
                content_type="application/json",
            )

        self.assertNotContains(page, '<openai-chatkit id="matrix-admin-chatkit"', html=False)
        self.assertNotContains(page, "cdn.platform.openai.com")
        self.assertContains(page, "Send deterministic message")
        self.assertEqual(response.status_code, 404)
        provider.assert_not_called()

    @override_settings(**{**LIVE_SETTINGS, "OPENAI_API_KEY": ""})
    def test_missing_api_key_fails_closed_without_exposing_a_secret(self):
        page = self.client.get(reverse("admin_chat:session_detail", args=[self.session.id]))
        response = self.client.post(
            self.live_url(),
            data=json.dumps(self.live_payload()),
            content_type="application/json",
        )

        self.assertContains(page, "OPENAI_API_KEY is not configured")
        self.assertNotContains(page, '<openai-chatkit id="matrix-admin-chatkit"', html=False)
        self.assertNotContains(page, "cdn.platform.openai.com")
        self.assertEqual(response.status_code, 503)

    @override_settings(**LIVE_SETTINGS)
    def test_live_ui_is_embedded_staff_only_and_never_exposes_api_key(self):
        page = self.client.get(reverse("admin_chat:session_detail", args=[self.session.id]))

        self.assertContains(page, '<openai-chatkit id="matrix-admin-chatkit"', html=False)
        self.assertContains(page, self.live_url())
        self.assertNotContains(page, "Deterministic fallback")
        self.assertNotContains(page, 'id="deterministic-fallback"', html=False)
        self.assertNotContains(page, 'id="matrix-live-ai-status"', html=False)
        self.assertNotContains(page, 'id="matrix-live-ai-error"', html=False)
        self.assertNotContains(page, "Live AI ready")
        self.assertNotContains(page, "Live AI is temporarily unavailable")
        self.assertNotContains(page, "Send deterministic message")
        self.assertNotContains(page, LIVE_SETTINGS["OPENAI_API_KEY"])
        self.assertNotContains(page, "getClientSecret")
        self.assertNotContains(page, "chat-launcher")

    @override_settings(**LIVE_SETTINGS)
    def test_chatkit_static_asset_is_discoverable_and_uses_custom_server_options(self):
        asset_path = finders.find("admin_chat/live_chatkit.js")

        self.assertTrue(asset_path)
        self.assertEqual(
            Path(asset_path).resolve(),
            (settings.BASE_DIR / "apps" / "ai_chat" / "static" / "admin_chat" / "live_chatkit.js").resolve(),
        )
        source = Path(asset_path).read_text(encoding="utf-8")
        self.assertIn("api: {", source)
        self.assertIn("url: livePanel.dataset.apiUrl", source)
        self.assertIn("domainKey: livePanel.dataset.domainKey", source)
        self.assertIn("fetch: (input, init = {})", source)
        self.assertIn("header: { enabled: false }", source)
        self.assertIn("history: { enabled: true }", source)
        self.assertIn("pollBundleUntilComplete", source)
        self.assertIn("livePanel.dataset.bundleStatusUrl", source)
        self.assertIn("const POLL_INTERVAL_MS = 3000", source)
        self.assertIn("const MAX_POLL_ATTEMPTS = 40", source)
        self.assertIn("const refreshChatHistory = async () => {", source)
        self.assertIn("chatkitBody.replaceChildren(nextChatkit)", source)
        self.assertIn("matrix-live-ai-bundle-indicator", source)
        self.assertIn("setBundleIndicator(Boolean(status.running))", source)
        self.assertNotIn("apiURL:", source)
        self.assertNotIn("header: false", source)
        self.assertNotIn("matrix-live-ai-status", source)
        self.assertNotIn("matrix-live-ai-error", source)
        self.assertNotIn("window.location.reload()", source)
        self.assertNotIn("Live AI ready", source)
        self.assertNotIn("Live AI is temporarily unavailable", source)
        self.assertNotIn("Live AI could not load", source)
        self.assertNotIn("history: { enabled: false }", source)
        self.assertNotIn("showFallback", source)
        self.assertNotIn("show-deterministic-fallback", source)
        self.assertNotIn("deterministic fallback remains available", source)
        self.assertNotIn("Live AI UI failed. The deterministic fallback remains available below.", source)
        self.assertNotIn("ChatKit could not load. The deterministic fallback remains available below.", source)

    @override_settings(**LIVE_SETTINGS)
    def test_live_ui_contains_bundle_indicator_and_status_endpoint(self):
        page = self.client.get(reverse("admin_chat:session_detail", args=[self.session.id]))

        self.assertContains(page, 'id="matrix-live-ai-bundle-indicator"', html=False)
        self.assertContains(page, "جاري تنفيذ الفحوصات")
        self.assertContains(page, reverse("admin_chat:bundle_status", args=[self.session.id]))

    @override_settings(**{**LIVE_SETTINGS, "OPENAI_CHATKIT_DOMAIN_KEY": ""})
    def test_missing_chatkit_domain_key_fails_closed(self):
        page = self.client.get(reverse("admin_chat:session_detail", args=[self.session.id]))

        self.assertContains(page, "OPENAI_CHATKIT_DOMAIN_KEY is not configured")
        self.assertNotContains(page, '<openai-chatkit id="matrix-admin-chatkit"', html=False)

    @override_settings(**LIVE_SETTINGS)
    def test_non_staff_and_portal_sessions_are_rejected(self):
        non_staff_client = Client()
        non_staff_client.force_login(self.owner)
        non_staff_response = non_staff_client.post(
            self.live_url(),
            data=json.dumps(self.live_payload()),
            content_type="application/json",
        )
        portal_session = AdminChatSession.objects.create(
            account=self.account,
            user=self.owner,
            server=self.server,
            channel=AdminChatSession.Channel.PORTAL_CUSTOMER,
            title_redacted="Portal",
        )
        portal_response = self.client.post(
            self.live_url(portal_session),
            data=json.dumps(self.live_payload(thread_id=portal_session.id)),
            content_type="application/json",
        )

        self.assertEqual(non_staff_response.status_code, 302)
        self.assertEqual(portal_response.status_code, 404)

    @override_settings(**LIVE_SETTINGS)
    def test_cross_session_thread_id_is_rejected(self):
        other_session = create_admin_chat_session(
            user=self.staff,
            account_id=self.account.id,
            title="Other",
        )
        response = self.client.post(
            self.live_url(),
            data=json.dumps(self.live_payload(thread_id=other_session.id)),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    @override_settings(**LIVE_SETTINGS)
    def test_live_endpoint_keeps_csrf_protection(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.staff)
        response = csrf_client.post(
            self.live_url(),
            data=json.dumps(self.live_payload()),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    @override_settings(**LIVE_SETTINGS)
    def test_success_streams_and_persists_only_safe_completed_response(self):
        Finding.objects.create(
            account=self.account,
            server=self.server,
            title="Key sk-test-canary-secret",
            severity="critical",
            evidence_summary="password=canary-password",
            fingerprint="live-canary",
        )
        provider = FakeProvider(chunks=["Healthy ", "without sk-test-canary-secret exposure."])
        before = (
            AdminChatToolRequest.objects.count(),
            ToolRun.objects.count(),
            AgentJob.objects.count(),
        )
        with patch("apps.ai_chat.live_ai.get_live_ai_provider", return_value=provider):
            response = self.client.post(
                self.live_url(),
                data=json.dumps(self.live_payload("Status sk-test-canary-secret")),
                content_type="application/json",
            )
            body = self.consume_stream(response)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/event-stream")
        self.assertEqual(response["X-Accel-Buffering"], "no")
        self.assertIn(b"thread.item.updated", body)
        self.assertEqual(len(provider.calls), 1)
        self.assertNotIn("sk-test-canary-secret", provider.calls[0]["input_text"])
        self.assertNotIn("canary-password", provider.calls[0]["input_text"])
        self.assertIn("[REDACTED]", provider.calls[0]["input_text"])
        self.assertIn("Do not execute commands, tools, functions", provider.calls[0]["instructions"])
        assistant = self.session.messages.filter(sender_type=AdminChatMessage.SenderType.ASSISTANT).latest("created_at")
        user_message = self.session.messages.filter(sender_type=AdminChatMessage.SenderType.USER).latest("created_at")
        self.assertEqual(assistant.metadata_redacted["stream_status"], "completed")
        self.assertEqual(assistant.metadata_redacted["model"], "test-model")
        self.assertEqual(assistant.metadata_redacted["usage"], {"input_units": 25, "output_units": 7})
        self.assertIn("final_size_bytes", assistant.metadata_redacted["context"])
        self.assertNotIn("sk-test-canary-secret", assistant.body_redacted)
        self.assertNotIn("sk-test-canary-secret", user_message.body_redacted)
        self.assertNotIn("SAFE_CONTEXT_DATA", assistant.body_redacted)
        self.assertNotIn("SAFE_CONTEXT_DATA", user_message.body_redacted)
        history = async_to_sync(AdminChatKitStore().load_thread_items)(
            str(self.session.id),
            after=None,
            limit=20,
            order="asc",
            context=AdminChatKitContext(user=self.staff, session=self.session),
        )
        history_text = "\n".join("".join(part.text for part in item.content) for item in history.data)
        self.assertIn("Status [REDACTED]", history_text)
        self.assertIn("Healthy without [REDACTED] exposure.", history_text)
        self.assertEqual(
            before,
            (
                AdminChatToolRequest.objects.count(),
                ToolRun.objects.count(),
                AgentJob.objects.count(),
            ),
        )

    @override_settings(**LIVE_SETTINGS)
    def test_provider_failure_returns_safe_failed_fallback(self):
        with patch("apps.ai_chat.live_ai.get_live_ai_provider", return_value=FailingProvider()):
            response = self.client.post(
                self.live_url(),
                data=json.dumps(self.live_payload()),
                content_type="application/json",
            )
            body = self.consume_stream(response)

        self.assertIn(b"temporarily unavailable", body)
        assistant = self.session.messages.filter(sender_type=AdminChatMessage.SenderType.ASSISTANT).latest("created_at")
        self.assertEqual(assistant.metadata_redacted["stream_status"], "failed")
        self.assertEqual(assistant.metadata_redacted["error_code"], "upstream_error")

    @override_settings(**{**LIVE_SETTINGS, "OPENAI_TIMEOUT_SECONDS": 1})
    def test_provider_timeout_returns_failed_fallback(self):
        with patch("apps.ai_chat.live_ai.get_live_ai_provider", return_value=SlowProvider()):
            response = self.client.post(
                self.live_url(),
                data=json.dumps(self.live_payload()),
                content_type="application/json",
            )
            self.consume_stream(response)

        assistant = self.session.messages.filter(sender_type=AdminChatMessage.SenderType.ASSISTANT).latest("created_at")
        self.assertEqual(assistant.metadata_redacted["stream_status"], "failed")
        self.assertEqual(assistant.metadata_redacted["error_code"], "timeout")

    @override_settings(**{**LIVE_SETTINGS, "ADMIN_LIVE_AI_RATE_LIMIT_PER_HOUR": 1})
    def test_rate_limit_blocks_second_provider_call(self):
        provider = FakeProvider()
        with patch("apps.ai_chat.live_ai.get_live_ai_provider", return_value=provider):
            first = self.client.post(
                self.live_url(), data=json.dumps(self.live_payload("First")), content_type="application/json"
            )
            self.consume_stream(first)
            second = self.client.post(
                self.live_url(), data=json.dumps(self.live_payload("Second")), content_type="application/json"
            )
            body = self.consume_stream(second)

        self.assertEqual(len(provider.calls), 1)
        self.assertIn(b"temporarily unavailable", body)
        latest = self.session.messages.filter(sender_type=AdminChatMessage.SenderType.ASSISTANT).latest("created_at")
        self.assertEqual(latest.metadata_redacted["error_code"], "rate_limited")

    @override_settings(**LIVE_SETTINGS)
    def test_deterministic_post_remains_available_without_provider_call(self):
        with patch("apps.ai_chat.live_ai.get_live_ai_provider") as provider:
            response = self.client.post(
                reverse("admin_chat:session_detail", args=[self.session.id]),
                data={"body": "server status"},
            )

        self.assertEqual(response.status_code, 302)
        provider.assert_not_called()
        assistant = self.session.messages.filter(sender_type=AdminChatMessage.SenderType.ASSISTANT).latest("created_at")
        self.assertEqual(assistant.metadata_redacted["source"], "deterministic_responder")
