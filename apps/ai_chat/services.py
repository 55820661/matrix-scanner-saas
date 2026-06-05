from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.ai_context.services import build_safe_context
from apps.applications.models import Application
from apps.core.redaction import redact_json, redact_secrets
from apps.servers.models import Server

from .models import AdminChatMessage, AdminChatSession


MAX_MESSAGE_LENGTH = 4000
MAX_TITLE_LENGTH = 160


def _safe_text(value, *, limit):
    text = redact_secrets(value or "").strip()
    if len(text) > limit:
        return f"{text[:limit]}..."
    return text


def _require_portal_account_user(user):
    if not user or not user.is_authenticated:
        raise PermissionDenied
    if user.account_id is None:
        raise PermissionDenied
    if user.account.status != Account.Status.ACTIVE:
        raise PermissionDenied
    if user.role not in {User.CustomerRole.OWNER, User.CustomerRole.OPERATOR, User.CustomerRole.VIEWER}:
        raise PermissionDenied


def _require_chat_writer(user):
    _require_portal_account_user(user)
    if user.role not in {User.CustomerRole.OWNER, User.CustomerRole.OPERATOR}:
        raise PermissionDenied


def user_can_view_chat(user, session):
    if not user or not user.is_authenticated or user.account_id is None:
        return False
    return user.account_id == session.account_id and user.role in {
        User.CustomerRole.OWNER,
        User.CustomerRole.OPERATOR,
        User.CustomerRole.VIEWER,
    }


def user_can_write_chat(user, session):
    return user_can_view_chat(user, session) and user.role in {User.CustomerRole.OWNER, User.CustomerRole.OPERATOR}


def _resolve_server(user, server_id):
    if not server_id:
        return None
    return Server.objects.filter(account=user.account, id=server_id).first()


def _resolve_application(user, application_id, server=None):
    if not application_id:
        return None
    queryset = Application.objects.filter(account=user.account, id=application_id)
    if server:
        queryset = queryset.filter(server=server)
    return queryset.first()


def create_chat_session(*, user, title="", server_id=None, application_id=None):
    _require_chat_writer(user)
    server = _resolve_server(user, server_id)
    if server_id and server is None:
        raise ValidationError("Selected server is not available.")
    application = _resolve_application(user, application_id, server=server)
    if application_id and application is None:
        raise ValidationError("Selected application is not available.")
    if application and server is None:
        server = application.server

    title_redacted = _safe_text(title or "New chat", limit=MAX_TITLE_LENGTH)
    context_snapshot = build_safe_context(account=user.account, user=user, server=server)
    session = AdminChatSession(
        account=user.account,
        user=user,
        server=server,
        application=application,
        title_redacted=title_redacted,
        context_snapshot_redacted=redact_json(context_snapshot),
        last_message_at=timezone.now(),
    )
    session.full_clean()
    session.save()
    return session


def add_user_message(*, user, session, body, metadata=None):
    _require_chat_writer(user)
    if not user_can_write_chat(user, session):
        raise PermissionDenied
    if session.status != AdminChatSession.Status.OPEN:
        raise ValidationError("Chat session is archived.")
    body_redacted = _safe_text(body, limit=MAX_MESSAGE_LENGTH)
    message = AdminChatMessage.objects.create(
        session=session,
        sender_type=AdminChatMessage.SenderType.USER,
        body_redacted=body_redacted,
        metadata_redacted=redact_json(metadata or {}),
    )
    session.last_message_at = message.created_at
    session.save(update_fields=["last_message_at", "updated_at"])
    return message
