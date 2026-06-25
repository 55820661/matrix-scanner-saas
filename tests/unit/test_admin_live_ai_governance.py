import asyncio
import json
from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.contrib import admin
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import Account, User
from apps.ai_chat.admin import AdminLiveAIRequestLogAdmin
from apps.ai_chat.models import AdminChatMessage, AdminLiveAIRequestLog
from apps.ai_chat.services import create_admin_chat_session, create_chat_session
from apps.servers.models import Server


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


class GovernanceProvider:
    async def stream(self, *, instructions, input_text, state):
        state.provider_request_id = "response-governance-123"
        state.usage = {"input_units": 11, "output_units": 5}
        yield "Safe governance response."


class FailingProvider:
    async def stream(self, *, instructions, input_text, state):
        raise RuntimeError("upstream exploded with sk-test-should-not-leak")
        yield ""


class SlowProvider:
    async def stream(self, *, instructions, input_text, state):
        await asyncio.sleep(2)
        yield "late"


class AdminLiveAIGovernanceTests(TestCase):
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
            title="Live governance",
            server_id=self.server.id,
        )
        self.client.force_login(self.staff)

    def live_url(self, session=None):
        return reverse("admin_chat:session_live", args=[(session or self.session).id])

    def live_payload(self, text="Summarize status", thread_id=None):
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
    def test_successful_live_request_creates_audit_log(self):
        with patch("apps.ai_chat.live_ai.get_live_ai_provider", return_value=GovernanceProvider()):
            response = self.client.post(
                self.live_url(),
                data=json.dumps(self.live_payload()),
                content_type="application/json",
            )
            self.consume_stream(response)

        log = AdminLiveAIRequestLog.objects.get()
        self.assertEqual(log.status, AdminLiveAIRequestLog.Status.SUCCEEDED)
        self.assertEqual(log.user, self.staff)
        self.assertEqual(log.user_identifier, "matrix-admin <admin@example.com>")
        self.assertEqual(log.session, self.session)
        self.assertEqual(log.account, self.account)
        self.assertEqual(log.server, self.server)
        self.assertEqual(log.model, "test-model")
        self.assertEqual(log.error_class, "")
        self.assertFalse(log.fallback_used)
        self.assertGreater(log.safe_context_size_bytes, 0)
        self.assertGreater(log.response_size_bytes, 0)

    @override_settings(**LIVE_SETTINGS)
    def test_failed_live_request_creates_safe_audit_log(self):
        with patch("apps.ai_chat.live_ai.get_live_ai_provider", return_value=FailingProvider()):
            response = self.client.post(
                self.live_url(),
                data=json.dumps(self.live_payload("status sk-test-should-not-leak")),
                content_type="application/json",
            )
            body = self.consume_stream(response)

        log = AdminLiveAIRequestLog.objects.get()
        serialized = json.dumps(
            {
                "user_identifier": log.user_identifier,
                "model": log.model,
                "status": log.status,
                "error_class": log.error_class,
                "fallback_used": log.fallback_used,
            }
        )
        self.assertIn(b"Live AI is temporarily unavailable. Please try again.", body)
        self.assertNotIn(b"deterministic fallback", body.lower())
        self.assertNotIn(b"sk-test-should-not-leak", body)
        self.assertEqual(log.status, AdminLiveAIRequestLog.Status.FAILED)
        self.assertEqual(log.error_class, AdminLiveAIRequestLog.ErrorClass.UPSTREAM_ERROR)
        self.assertTrue(log.fallback_used)
        self.assertNotIn("server-only-test-key", serialized)
        self.assertNotIn("domain-test-key", serialized)
        self.assertNotIn("sk-test-should-not-leak", serialized)

    @override_settings(**{**LIVE_SETTINGS, "OPENAI_API_KEY": ""})
    def test_missing_config_is_classified_without_secret_details(self):
        response = self.client.post(
            self.live_url(),
            data=json.dumps(self.live_payload()),
            content_type="application/json",
        )

        log = AdminLiveAIRequestLog.objects.get()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"], "Live AI is temporarily unavailable. Please try again.")
        self.assertNotIn("deterministic fallback", response.content.decode().lower())
        self.assertEqual(log.status, AdminLiveAIRequestLog.Status.FAILED)
        self.assertEqual(log.error_class, AdminLiveAIRequestLog.ErrorClass.MISSING_CONFIG)
        self.assertTrue(log.fallback_used)
        self.assertNotIn("OPENAI_API_KEY", response.content.decode())

    @override_settings(**{**LIVE_SETTINGS, "OPENAI_TIMEOUT_SECONDS": 1})
    def test_timeout_is_classified(self):
        with patch("apps.ai_chat.live_ai.get_live_ai_provider", return_value=SlowProvider()):
            response = self.client.post(
                self.live_url(),
                data=json.dumps(self.live_payload()),
                content_type="application/json",
            )
            self.consume_stream(response)

        log = AdminLiveAIRequestLog.objects.get()
        self.assertEqual(log.status, AdminLiveAIRequestLog.Status.FAILED)
        self.assertEqual(log.error_class, AdminLiveAIRequestLog.ErrorClass.TIMEOUT)
        self.assertTrue(log.fallback_used)

    @override_settings(**{**LIVE_SETTINGS, "ADMIN_LIVE_AI_ENABLED": False})
    def test_feature_flag_off_denies_live_ai_and_records_audit(self):
        response = self.client.post(
            self.live_url(),
            data=json.dumps(self.live_payload()),
            content_type="application/json",
        )

        log = AdminLiveAIRequestLog.objects.get()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(log.status, AdminLiveAIRequestLog.Status.DENIED)
        self.assertEqual(log.error_class, AdminLiveAIRequestLog.ErrorClass.DISABLED)

    def test_admin_audit_view_is_readonly(self):
        model_admin = AdminLiveAIRequestLogAdmin(AdminLiveAIRequestLog, admin.site)

        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_change_permission(None))
        self.assertFalse(model_admin.has_delete_permission(None))
        self.assertIn("status", model_admin.list_filter)
        self.assertIn("model", model_admin.list_filter)
        self.assertIn("user", model_admin.list_filter)
        self.assertIn("account", model_admin.list_filter)
        self.assertIn("created_at", model_admin.list_filter)
        self.assertIn("user__email", model_admin.search_fields)
        self.assertIn("session__id", model_admin.search_fields)
        self.assertIn("error_class", model_admin.search_fields)

    @override_settings(**LIVE_SETTINGS)
    def test_admin_chat_displays_governance_status_without_secrets(self):
        response = self.client.get(reverse("admin_chat:session_detail", args=[self.session.id]))

        self.assertContains(response, "Live AI: Enabled")
        self.assertContains(response, "Model: test-model")
        self.assertContains(response, "Rate limit: 30/hour")
        self.assertContains(response, "Safe Context max:")
        self.assertNotContains(response, LIVE_SETTINGS["OPENAI_API_KEY"])

    @override_settings(**LIVE_SETTINGS)
    def test_portal_deterministic_chat_does_not_create_live_audit(self):
        portal_session = create_chat_session(user=self.owner, title="Portal deterministic", server_id=self.server.id)
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("portal:chat_session_detail", args=[portal_session.id]),
            data={"body": "server status"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(AdminLiveAIRequestLog.objects.exists())
        assistant = portal_session.messages.filter(sender_type=AdminChatMessage.SenderType.ASSISTANT).latest("created_at")
        self.assertEqual(assistant.metadata_redacted["source"], "deterministic_responder")
