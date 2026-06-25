from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from asgiref.sync import sync_to_async
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from chatkit.store import Store
from chatkit.types import (
    AssistantMessageContent,
    AssistantMessageItem,
    Attachment,
    InferenceOptions,
    Page,
    ThreadItem,
    ThreadMetadata,
    UserMessageItem,
    UserMessageTextContent,
)

from apps.ai_chat.models import AdminChatDecision, AdminChatMessage, AdminChatSession
from apps.ai_chat.services import (
    MAX_RESPONSE_LENGTH,
    add_user_message,
    create_ai_tool_requests_from_proposals,
    extract_tool_request_proposal,
    strip_tool_request_proposals,
)
from apps.audit.models import AuditLog
from apps.core.redaction import redact_json, redact_secrets


@dataclass
class AdminChatKitContext:
    user: Any
    session: AdminChatSession
    item_metadata: dict[str, dict] = field(default_factory=dict)
    audit_log_id: int | None = None


class AdminChatKitStore(Store[AdminChatKitContext]):
    def generate_thread_id(self, context: AdminChatKitContext) -> str:
        return str(context.session.id)

    async def load_thread(self, thread_id: str, context: AdminChatKitContext) -> ThreadMetadata:
        self._require_thread(thread_id, context)
        return self._to_thread(context.session)

    async def save_thread(self, thread: ThreadMetadata, context: AdminChatKitContext) -> None:
        self._require_thread(thread.id, context)
        if thread.title and thread.title != context.session.title_redacted:
            await sync_to_async(self._update_thread_title, thread_sensitive=True)(context.session, thread.title)

    async def load_thread_items(
        self,
        thread_id: str,
        after: str | None,
        limit: int,
        order: str,
        context: AdminChatKitContext,
    ) -> Page[ThreadItem]:
        self._require_thread(thread_id, context)
        messages = await sync_to_async(self._load_messages, thread_sensitive=True)(context.session)
        items = [self._to_item(message, thread_id) for message in messages]
        items = [item for item in items if item is not None]
        if order == "desc":
            items.reverse()
        if after:
            cursor_index = next((index for index, item in enumerate(items) if item.id == after), None)
            items = items[cursor_index + 1 :] if cursor_index is not None else []
        page_items = items[:limit]
        has_more = len(items) > limit
        return Page(data=page_items, has_more=has_more, after=page_items[-1].id if has_more and page_items else None)

    async def load_threads(
        self,
        limit: int,
        after: str | None,
        order: str,
        context: AdminChatKitContext,
    ) -> Page[ThreadMetadata]:
        thread = self._to_thread(context.session)
        if after == thread.id or limit < 1:
            return Page()
        return Page(data=[thread], has_more=False, after=None)

    async def add_thread_item(self, thread_id: str, item: ThreadItem, context: AdminChatKitContext) -> None:
        self._require_thread(thread_id, context)
        if isinstance(item, UserMessageItem):
            await sync_to_async(self._add_user_item, thread_sensitive=True)(item, context)
        elif isinstance(item, AssistantMessageItem):
            metadata = context.item_metadata.pop(item.id, {})
            await sync_to_async(self._add_assistant_item, thread_sensitive=True)(item, context, metadata)

    async def save_item(self, thread_id: str, item: ThreadItem, context: AdminChatKitContext) -> None:
        self._require_thread(thread_id, context)
        if isinstance(item, (UserMessageItem, AssistantMessageItem)):
            await sync_to_async(self._replace_item, thread_sensitive=True)(item, context)

    async def load_item(self, thread_id: str, item_id: str, context: AdminChatKitContext) -> ThreadItem:
        self._require_thread(thread_id, context)
        message = await sync_to_async(self._find_message, thread_sensitive=True)(context.session, item_id)
        item = self._to_item(message, thread_id) if message else None
        if item is None:
            raise ValueError("Chat item was not found.")
        return item

    async def delete_thread(self, thread_id: str, context: AdminChatKitContext) -> None:
        self._require_thread(thread_id, context)
        raise PermissionDenied("Thread deletion is not available in Live Admin Chat.")

    async def delete_thread_item(self, thread_id: str, item_id: str, context: AdminChatKitContext) -> None:
        self._require_thread(thread_id, context)
        raise PermissionDenied("Message deletion is not available in Live Admin Chat.")

    async def save_attachment(self, attachment: Attachment, context: AdminChatKitContext) -> None:
        raise PermissionDenied("Attachments are disabled.")

    async def load_attachment(self, attachment_id: str, context: AdminChatKitContext) -> Attachment:
        raise PermissionDenied("Attachments are disabled.")

    async def delete_attachment(self, attachment_id: str, context: AdminChatKitContext) -> None:
        raise PermissionDenied("Attachments are disabled.")

    def _require_thread(self, thread_id: str, context: AdminChatKitContext) -> None:
        if str(context.session.id) != str(thread_id):
            raise PermissionDenied("Cross-session ChatKit access denied.")
        if context.session.channel != AdminChatSession.Channel.ADMIN_INTERNAL:
            raise PermissionDenied("Live AI is restricted to internal admin chat sessions.")
        if not context.user.is_authenticated or not context.user.is_staff:
            raise PermissionDenied("Live AI requires a staff user.")

    @staticmethod
    def _to_thread(session: AdminChatSession) -> ThreadMetadata:
        return ThreadMetadata(id=str(session.id), title=session.title_redacted, created_at=session.created_at)

    @staticmethod
    def _load_messages(session: AdminChatSession):
        return list(session.messages.order_by("created_at"))

    @staticmethod
    def _item_id(message: AdminChatMessage) -> str:
        return str((message.metadata_redacted or {}).get("chatkit_item_id") or f"admin_msg_{message.id}")

    def _to_item(self, message: AdminChatMessage, thread_id: str) -> ThreadItem | None:
        item_id = self._item_id(message)
        if message.sender_type == AdminChatMessage.SenderType.USER:
            return UserMessageItem(
                id=item_id,
                thread_id=thread_id,
                created_at=message.created_at,
                content=[UserMessageTextContent(text=message.body_redacted)],
                attachments=[],
                inference_options=InferenceOptions(),
            )
        if message.sender_type in {AdminChatMessage.SenderType.ASSISTANT, AdminChatMessage.SenderType.SYSTEM}:
            return AssistantMessageItem(
                id=item_id,
                thread_id=thread_id,
                created_at=message.created_at,
                content=[AssistantMessageContent(text=message.body_redacted)],
            )
        return None

    @staticmethod
    def _update_thread_title(session: AdminChatSession, title: str) -> None:
        session.title_redacted = redact_secrets(title)[:255]
        session.save(update_fields=["title_redacted", "updated_at"])

    @staticmethod
    def _find_message(session: AdminChatSession, item_id: str):
        for message in session.messages.order_by("created_at"):
            if AdminChatKitStore._item_id(message) == item_id:
                return message
        return None

    @staticmethod
    def _user_text(item: UserMessageItem) -> str:
        return "".join(part.text for part in item.content if isinstance(part, UserMessageTextContent))

    @staticmethod
    def _assistant_text(item: AssistantMessageItem) -> str:
        return "".join(part.text for part in item.content)

    def _add_user_item(self, item: UserMessageItem, context: AdminChatKitContext) -> None:
        if item.attachments:
            raise PermissionDenied("Attachments are disabled.")
        if self._find_message(context.session, item.id):
            return
        add_user_message(
            user=context.user,
            session=context.session,
            body=self._user_text(item),
            metadata={"source": "admin_live_chatkit", "chatkit_item_id": item.id},
        )

    def _add_assistant_item(
        self,
        item: AssistantMessageItem,
        context: AdminChatKitContext,
        metadata: dict,
    ) -> None:
        if self._find_message(context.session, item.id):
            return
        raw_body = redact_secrets(self._assistant_text(item)).strip()[:MAX_RESPONSE_LENGTH]
        proposal = metadata.pop("tool_request_proposal", None) or extract_tool_request_proposal(raw_body)
        body = strip_tool_request_proposals(raw_body)
        safe_metadata = redact_json(
            {
                "source": "admin_live_chatkit",
                "chatkit_item_id": item.id,
                **metadata,
            }
        )
        message = AdminChatMessage.objects.create(
            session=context.session,
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            body_redacted=body,
            metadata_redacted=safe_metadata,
        )
        context.session.last_message_at = message.created_at
        context.session.save(update_fields=["last_message_at", "updated_at"])
        stream_status = safe_metadata.get("stream_status", "completed")
        AdminChatDecision.objects.create(
            session=context.session,
            decision_type=AdminChatDecision.DecisionType.ANSWER,
            input_context_redacted={
                "source": "admin_live_chatkit",
                "context": safe_metadata.get("context", {}),
            },
            output_json_redacted={
                "message_id": str(message.id),
                "model": safe_metadata.get("model", ""),
                "stream_status": stream_status,
            },
            reasoning_summary="Live AI context-only response." if stream_status == "completed" else "Live AI failed; safe fallback response returned.",
        )
        if stream_status == "completed" and proposal and not safe_metadata.get("tool_request_handled"):
            try:
                create_ai_tool_requests_from_proposals(
                    user=context.user,
                    session=context.session,
                    message=message,
                    proposals=[proposal],
                )
            except (PermissionDenied, ValidationError, ValueError):
                pass
        AuditLog.objects.create(
            actor_user=context.user,
            actor_type=AuditLog.ActorType.ADMIN,
            account=context.session.account,
            action="admin_live_ai.response",
            target_type="AdminChatSession",
            target_id=str(context.session.id),
            result=AuditLog.Result.SUCCESS if stream_status == "completed" else AuditLog.Result.FAILURE,
            metadata={
                "model": safe_metadata.get("model", ""),
                "provider_request_id": safe_metadata.get("provider_request_id", ""),
                "latency_ms": safe_metadata.get("latency_ms", 0),
                "stream_status": stream_status,
                "usage": safe_metadata.get("usage", {}),
            },
        )

    def _replace_item(self, item: UserMessageItem | AssistantMessageItem, context: AdminChatKitContext) -> None:
        message = self._find_message(context.session, item.id)
        if message is None:
            return
        body = self._user_text(item) if isinstance(item, UserMessageItem) else self._assistant_text(item)
        message.body_redacted = redact_secrets(body)[:MAX_RESPONSE_LENGTH]
        message.save(update_fields=["body_redacted", "updated_at"])
