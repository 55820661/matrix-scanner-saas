import json

from asgiref.sync import async_to_sync
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch

from apps.accounts.models import Account, User
from apps.ai_chat.chatkit_store import AdminChatKitContext, AdminChatKitStore
from apps.ai_chat.models import AdminChatMessage, AdminLiveAIRequestLog
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


class HydrationProvider:
    async def stream(self, *, instructions, input_text, state):
        state.provider_request_id = "response-hydration-123"
        state.usage = {"input_units": 7, "output_units": 3}
        yield "Stored assistant reply."


class LiveAIHistoryHydrationTests(TestCase):
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
            title="History hydration",
            server_id=self.server.id,
        )
        self.client.force_login(self.staff)

    def live_url(self, session=None):
        return reverse("admin_chat:session_live", args=[(session or self.session).id])

    def live_payload(self, text="Store this"):
        return {
            "type": "threads.add_user_message",
            "params": {
                "thread_id": str(self.session.id),
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

    def create_stored_messages(self):
        user_message = AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.USER,
            body_redacted="Stored user message",
            metadata_redacted={"source": "admin_live_chatkit", "chatkit_item_id": "ck_user_1"},
        )
        assistant_message = AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            body_redacted="Stored assistant message",
            metadata_redacted={"source": "admin_live_chatkit", "chatkit_item_id": "ck_assistant_1"},
        )
        fallback_id_message = AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            body_redacted="Stored assistant without chatkit id",
            metadata_redacted={"source": "admin_live_chatkit"},
        )
        return user_message, assistant_message, fallback_id_message

    def test_store_load_thread_items_hydrates_saved_messages_in_order(self):
        user_message, assistant_message, fallback_id_message = self.create_stored_messages()

        page = async_to_sync(AdminChatKitStore().load_thread_items)(
            str(self.session.id),
            after=None,
            limit=20,
            order="asc",
            context=AdminChatKitContext(user=self.staff, session=self.session),
        )

        self.assertEqual([item.id for item in page.data], ["ck_user_1", "ck_assistant_1", f"admin_msg_{fallback_id_message.id}"])
        self.assertEqual(page.data[0].type, "user_message")
        self.assertEqual(page.data[1].type, "assistant_message")
        self.assertEqual(page.data[0].content[0].text, user_message.body_redacted)
        self.assertEqual(page.data[1].content[0].text, assistant_message.body_redacted)
        self.assertEqual(page.data[2].content[0].text, fallback_id_message.body_redacted)
        self.assertFalse(AdminLiveAIRequestLog.objects.exists())

    def test_delete_thread_item_missing_item_is_idempotent_noop(self):
        async_to_sync(AdminChatKitStore().delete_thread_item)(
            str(self.session.id),
            "missing-chatkit-item",
            context=AdminChatKitContext(user=self.staff, session=self.session),
        )

        self.assertEqual(self.session.messages.count(), 0)

    def test_delete_thread_item_removes_empty_suppressed_placeholder_only(self):
        placeholder = AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            body_redacted="",
            metadata_redacted={
                "source": "admin_live_chatkit",
                "chatkit_item_id": "ck_hidden_placeholder",
                "suppress_from_history": True,
                "tool_request_handled": True,
            },
        )
        visible = AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            body_redacted="Visible bundle summary",
            metadata_redacted={
                "source": "diagnostic_bundle_result",
                "chatkit_item_id": "ck_visible_bundle_summary",
            },
        )

        async_to_sync(AdminChatKitStore().delete_thread_item)(
            str(self.session.id),
            "ck_hidden_placeholder",
            context=AdminChatKitContext(user=self.staff, session=self.session),
        )

        self.assertFalse(AdminChatMessage.objects.filter(id=placeholder.id).exists())
        self.assertTrue(AdminChatMessage.objects.filter(id=visible.id).exists())
        page = async_to_sync(AdminChatKitStore().load_thread_items)(
            str(self.session.id),
            after=None,
            limit=20,
            order="asc",
            context=AdminChatKitContext(user=self.staff, session=self.session),
        )
        history_text = "\n".join("".join(part.text for part in item.content) for item in page.data)
        self.assertNotIn("ck_hidden_placeholder", [item.id for item in page.data])
        self.assertIn("Visible bundle summary", history_text)

    def test_delete_thread_item_keeps_visible_user_message_without_exception(self):
        user_message = AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.USER,
            body_redacted="Keep visible user text",
            metadata_redacted={"source": "admin_live_chatkit", "chatkit_item_id": "ck_visible_user"},
        )

        async_to_sync(AdminChatKitStore().delete_thread_item)(
            str(self.session.id),
            "ck_visible_user",
            context=AdminChatKitContext(user=self.staff, session=self.session),
        )

        user_message.refresh_from_db()
        self.assertEqual(user_message.body_redacted, "Keep visible user text")

    def test_delete_thread_item_keeps_visible_tool_result_summary_without_exception(self):
        summary = AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            body_redacted="اكتمل فحص حالة السيرفر بنجاح.",
            metadata_redacted={
                "source": "tool_result_summary",
                "chatkit_item_id": "tool_result_summary_123",
                "tool_key": "log_sources_discovery_v2",
            },
        )

        async_to_sync(AdminChatKitStore().delete_thread_item)(
            str(self.session.id),
            "tool_result_summary_123",
            context=AdminChatKitContext(user=self.staff, session=self.session),
        )

        summary.refresh_from_db()
        self.assertEqual(summary.body_redacted, "اكتمل فحص حالة السيرفر بنجاح.")

    @override_settings(**LIVE_SETTINGS)
    def test_items_list_history_request_returns_stored_messages_without_audit(self):
        self.create_stored_messages()
        response = self.client.post(
            self.live_url(),
            data=json.dumps(
                {
                    "type": "items.list",
                    "params": {
                        "thread_id": str(self.session.id),
                        "limit": 20,
                        "order": "asc",
                    },
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Stored user message", content)
        self.assertIn("Stored assistant message", content)
        self.assertIn("Stored assistant without chatkit id", content)
        self.assertFalse(AdminLiveAIRequestLog.objects.exists())
        self.assertFalse(AdminLiveAIRequestLog.objects.filter(status=AdminLiveAIRequestLog.Status.PENDING).exists())

    @override_settings(**LIVE_SETTINGS)
    def test_generation_request_creates_single_finalized_audit_and_persists_messages(self):
        before = (ToolRun.objects.count(), AgentJob.objects.count())
        with patch("apps.ai_chat.live_ai.get_live_ai_provider", return_value=HydrationProvider()):
            response = self.client.post(
                self.live_url(),
                data=json.dumps(self.live_payload("Store sk-test-canary-secret")),
                content_type="application/json",
            )
            self.consume_stream(response)

        self.assertEqual(AdminLiveAIRequestLog.objects.count(), 1)
        log = AdminLiveAIRequestLog.objects.get()
        self.assertEqual(log.status, AdminLiveAIRequestLog.Status.SUCCEEDED)
        self.assertFalse(AdminLiveAIRequestLog.objects.filter(status=AdminLiveAIRequestLog.Status.PENDING).exists())
        messages = list(self.session.messages.order_by("created_at"))
        self.assertEqual([message.sender_type for message in messages], ["user", "assistant"])
        self.assertIn("Store [REDACTED]", messages[0].body_redacted)
        self.assertEqual(messages[1].body_redacted, "Stored assistant reply.")
        self.assertNotIn("sk-test-canary-secret", "\n".join(message.body_redacted for message in messages))
        self.assertNotIn("SAFE_CONTEXT_DATA", "\n".join(message.body_redacted for message in messages))
        self.assertEqual(before, (ToolRun.objects.count(), AgentJob.objects.count()))

    @override_settings(**LIVE_SETTINGS)
    def test_thread_load_request_does_not_create_audit(self):
        self.create_stored_messages()
        response = self.client.post(
            self.live_url(),
            data=json.dumps({"type": "threads.get_by_id", "params": {"thread_id": str(self.session.id)}}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Stored user message", response.content.decode())
        self.assertFalse(AdminLiveAIRequestLog.objects.exists())

    @override_settings(**LIVE_SETTINGS)
    def test_portal_customer_deterministic_chat_unchanged(self):
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
