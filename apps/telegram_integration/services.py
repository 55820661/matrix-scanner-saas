from datetime import timedelta
import json
from urllib import parse, request
from urllib.error import URLError

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Account
from apps.applications.models import Application
from apps.audit.models import AuditLog
from apps.core.redaction import redact_json, redact_secrets
from apps.core.tokens import hash_token
from apps.servers.models import BaselineScan, Finding, Server

from .models import TelegramChatLink, TelegramLinkToken, TelegramNotification


ALLOWED_COMMANDS = {
    "/start",
    "/link",
    "/unlink",
    "/help",
    "/menu",
    "/servers",
    "/apps",
    "/findings",
    "/status",
    "/baseline",
}

PRIVATE_COMMANDS = ALLOWED_COMMANDS
GROUP_COMMANDS = {"/start", "/unlink", "/help", "/menu", "/status"}
DEFAULT_NOTIFICATION_TYPES = [
    TelegramNotification.NotificationType.BASELINE_COMPLETED,
    TelegramNotification.NotificationType.FINDING_CREATED,
    TelegramNotification.NotificationType.AGENT_OFFLINE,
    TelegramNotification.NotificationType.AGENT_RECOVERED,
    TelegramNotification.NotificationType.BOOTSTRAP_COMPLETED,
    TelegramNotification.NotificationType.BOOTSTRAP_FAILED,
]


class TelegramCommandError(ValueError):
    pass


def parse_message(update):
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    text = str(message.get("text") or "").strip()
    return {
        "text": text,
        "chat_id": chat.get("id"),
        "chat_type": chat.get("type") or "",
        "title": chat.get("title") or chat.get("username") or "",
        "telegram_user_id": sender.get("id"),
    }


def command_name(text):
    if not text.startswith("/"):
        return ""
    return text.split()[0].split("@")[0].lower()


def audit_telegram_action(*, action, account, user=None, target_type="", target_id="", result=AuditLog.Result.SUCCESS, metadata=None):
    AuditLog.objects.create(
        actor_user=user,
        actor_type=AuditLog.ActorType.USER if user else AuditLog.ActorType.SYSTEM,
        account=account,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else "",
        result=result,
        metadata=metadata or {},
    )


def create_link_token_for_portal(*, user, chat_scope, server=None, ttl_minutes=30):
    if user.account.status != Account.Status.ACTIVE:
        raise PermissionDenied("Telegram linking is only available for active accounts.")
    if chat_scope == TelegramLinkToken.ChatScope.GROUP and user.role != "owner":
        raise PermissionDenied("Only account owners can create group Telegram link codes.")
    if chat_scope == TelegramLinkToken.ChatScope.PRIVATE and user.role not in {"owner", "operator"}:
        raise PermissionDenied("Only owners and operators can create private Telegram link codes.")
    if chat_scope not in {TelegramLinkToken.ChatScope.PRIVATE, TelegramLinkToken.ChatScope.GROUP}:
        raise ValueError("Unsupported Telegram chat scope.")
    if server and server.account_id != user.account_id:
        raise PermissionDenied("Server does not belong to this account.")
    token, raw_token = TelegramLinkToken.create_for_account(
        account=user.account,
        created_by=user,
        chat_scope=chat_scope,
        server=server,
        ttl_minutes=ttl_minutes,
    )
    audit_telegram_action(
        action="portal.telegram_link_issued",
        account=user.account,
        user=user,
        target_type="TelegramLinkToken",
        target_id=token.id,
        metadata={
            "link_id": str(token.id),
            "chat_scope": chat_scope,
            "server_id": str(server.id) if server else "",
            "expires_at": token.expires_at.isoformat(),
        },
    )
    return token, raw_token


def active_chat_link_for_update(update):
    parsed = parse_message(update)
    if parsed["chat_id"] is None:
        return None
    return (
        TelegramChatLink.objects.select_related("account", "user", "server")
        .filter(telegram_chat_id=parsed["chat_id"], status=TelegramChatLink.Status.ACTIVE)
        .first()
    )


@transaction.atomic
def link_chat_with_code(update, raw_code):
    parsed = parse_message(update)
    if not parsed["chat_id"]:
        raise TelegramCommandError("Telegram chat id is missing.")
    token = TelegramLinkToken.objects.select_for_update().filter(token_hash=hash_token(raw_code)).first()
    if not token or not token.is_usable:
        raise TelegramCommandError("This link code is invalid, expired, revoked, or already used.")
    if token.account.status != Account.Status.ACTIVE:
        raise TelegramCommandError("This account is not active.")
    if token.chat_scope == TelegramLinkToken.ChatScope.PRIVATE and parsed["chat_type"] != TelegramChatLink.ChatType.PRIVATE:
        raise TelegramCommandError("This code can only link a private chat.")
    if token.chat_scope == TelegramLinkToken.ChatScope.GROUP and parsed["chat_type"] not in {
        TelegramChatLink.ChatType.GROUP,
        TelegramChatLink.ChatType.SUPERGROUP,
    }:
        raise TelegramCommandError("This code can only link a group or supergroup chat.")

    existing = TelegramChatLink.objects.select_for_update().filter(telegram_chat_id=parsed["chat_id"]).first()
    if existing and existing.status == TelegramChatLink.Status.ACTIVE and existing.account_id != token.account_id:
        raise TelegramCommandError("This Telegram chat is already linked to another account.")

    chat_link, _created = TelegramChatLink.objects.update_or_create(
        telegram_chat_id=parsed["chat_id"],
        defaults={
            "account": token.account,
            "user": token.created_by if token.chat_scope == TelegramLinkToken.ChatScope.PRIVATE else None,
            "server": token.server,
            "telegram_user_id": parsed["telegram_user_id"] if token.chat_scope == TelegramLinkToken.ChatScope.PRIVATE else None,
            "chat_type": parsed["chat_type"],
            "title": parsed["title"],
            "status": TelegramChatLink.Status.ACTIVE,
            "allowed_notifications": DEFAULT_NOTIFICATION_TYPES,
            "linked_at": timezone.now(),
            "revoked_at": None,
        },
    )
    token.mark_used()
    audit_telegram_action(
        action="telegram.chat_linked",
        account=token.account,
        user=token.created_by,
        target_type="TelegramChatLink",
        target_id=chat_link.id,
        metadata={"chat_id": str(chat_link.telegram_chat_id), "chat_scope": token.chat_scope, "link_id": str(chat_link.id)},
    )
    return chat_link


def unlink_chat(chat_link):
    chat_link.status = TelegramChatLink.Status.REVOKED
    chat_link.revoked_at = timezone.now()
    chat_link.save(update_fields=["status", "revoked_at", "updated_at"])
    audit_telegram_action(
        action="telegram.chat_unlinked",
        account=chat_link.account,
        user=chat_link.user,
        target_type="TelegramChatLink",
        target_id=chat_link.id,
        metadata={"chat_id": str(chat_link.telegram_chat_id), "link_id": str(chat_link.id)},
    )


def handle_update(update):
    parsed = parse_message(update)
    text = parsed["text"]
    command = command_name(text)
    if not command:
        return "Use /help to see available Matrix Scanner commands."
    if command not in ALLOWED_COMMANDS:
        return "This Telegram command is not available in the read-only MVP."
    if command == "/link":
        parts = text.split(maxsplit=1)
        if len(parts) != 2:
            return "Send /link followed by your one-time link code."
        try:
            link_chat_with_code(update, parts[1].strip())
        except TelegramCommandError as exc:
            return str(exc)
        return "This Telegram chat is now linked to Matrix Scanner."

    chat_link = active_chat_link_for_update(update)
    if not chat_link or not chat_link.is_active:
        if command in {"/start", "/help"}:
            return help_text(linked=False)
        return "This chat is not linked. Use /link with a one-time code from the Portal."

    if chat_link.chat_type != TelegramChatLink.ChatType.PRIVATE and command not in GROUP_COMMANDS:
        return "Group chats support alerts plus /help and /status in this MVP."
    if command == "/start" or command == "/help":
        return help_text(linked=True, chat_type=chat_link.chat_type)
    if command == "/menu":
        return menu_text(chat_link)
    if command == "/unlink":
        unlink_chat(chat_link)
        return "This Telegram chat has been unlinked."
    if command == "/servers":
        return servers_summary(chat_link)
    if command == "/apps":
        return applications_summary(chat_link)
    if command == "/findings":
        return findings_summary(chat_link)
    if command == "/status":
        return account_status_summary(chat_link)
    if command == "/baseline":
        return baseline_summary(chat_link)
    return "This Telegram command is not available in the read-only MVP."


def help_text(*, linked, chat_type=TelegramChatLink.ChatType.PRIVATE):
    if not linked:
        return "Matrix Scanner Telegram is read-only. Link this chat with /link <code> from the Portal."
    if chat_type == TelegramChatLink.ChatType.PRIVATE:
        return "Read-only commands: /servers, /apps, /findings, /status, /baseline, /unlink."
    return "Group commands: /status, /help, /unlink. Alerts are delivered when enabled."


def menu_text(chat_link):
    if chat_link.chat_type == TelegramChatLink.ChatType.PRIVATE:
        return "/servers\n/apps\n/findings\n/status\n/baseline\n/unlink"
    return "/status\n/help\n/unlink"


def scoped_servers(chat_link):
    qs = Server.objects.filter(account=chat_link.account).order_by("name")
    if chat_link.server_id:
        qs = qs.filter(id=chat_link.server_id)
    return qs


def servers_summary(chat_link):
    servers = scoped_servers(chat_link).select_related("scanner_agent")[:10]
    if not servers:
        return "No servers are available for this account."
    lines = ["Servers:"]
    for server in servers:
        try:
            agent_status = server.scanner_agent.status
        except Server.scanner_agent.RelatedObjectDoesNotExist:
            agent_status = server.agent_status or "unknown"
        lines.append(redact_secrets(f"- {server.name}: server={server.status}, agent={agent_status}"))
    return "\n".join(lines)


def applications_summary(chat_link):
    qs = Application.objects.select_related("server").filter(account=chat_link.account).order_by("name")
    if chat_link.server_id:
        qs = qs.filter(server_id=chat_link.server_id)
    applications = qs[:10]
    if not applications:
        return "No applications are available for this account."
    lines = ["Applications:"]
    for application in applications:
        value = f"- {application.name}: {application.domain or 'no domain'} {application.path} ({application.review_status})"
        lines.append(redact_secrets(value))
    return "\n".join(lines)


def findings_summary(chat_link):
    qs = Finding.objects.select_related("server", "application").filter(account=chat_link.account).order_by("-created_at")
    if chat_link.server_id:
        qs = qs.filter(server_id=chat_link.server_id)
    findings = qs[:10]
    if not findings:
        return "No findings are available for this account."
    lines = ["Findings:"]
    for finding in findings:
        evidence = redact_secrets(finding.evidence_summary or "")
        if len(evidence) > 160:
            evidence = f"{evidence[:157]}..."
        lines.append(redact_secrets(f"- {finding.title}: {finding.severity}/{finding.status}. {evidence}"))
    return "\n".join(lines)


def account_status_summary(chat_link):
    servers = scoped_servers(chat_link)
    findings = Finding.objects.filter(account=chat_link.account)
    if chat_link.server_id:
        findings = findings.filter(server_id=chat_link.server_id)
    active_servers = servers.filter(status=Server.Status.ACTIVE).count()
    open_findings = findings.filter(status=Finding.Status.OPEN).count()
    critical_findings = findings.filter(status=Finding.Status.OPEN, severity__iexact="critical").count()
    return (
        f"Status for {redact_secrets(chat_link.account.name)}:\n"
        f"- Servers: {servers.count()} ({active_servers} active)\n"
        f"- Open findings: {open_findings}\n"
        f"- Critical findings: {critical_findings}"
    )


def baseline_summary(chat_link):
    qs = BaselineScan.objects.filter(account=chat_link.account).select_related("server").order_by("-created_at")
    if chat_link.server_id:
        qs = qs.filter(server_id=chat_link.server_id)
    scan = qs.first()
    if not scan:
        return "No baseline scans are available for this account."
    summary = redact_json(scan.summary if isinstance(scan.summary, dict) else {})
    safe_counts = {
        "services": summary.get("services", 0),
        "domains": summary.get("domains", 0),
        "applications": summary.get("applications", 0),
        "findings": summary.get("findings", 0),
    }
    return (
        f"Latest baseline: {scan.status}\n"
        f"- Server: {redact_secrets(scan.server.name)}\n"
        f"- Started: {scan.started_at or 'not started'}\n"
        f"- Finished: {scan.finished_at or 'not finished'}\n"
        f"- Summary: {safe_counts}"
    )


def create_notification(
    *,
    chat_link,
    notification_type,
    server=None,
    finding=None,
    payload=None,
    dedupe_key="",
    suppression_minutes=60,
):
    account = chat_link.account
    payload_redacted = redact_json(payload or {})
    cutoff = timezone.now() - timedelta(minutes=suppression_minutes)
    status = TelegramNotification.Status.PENDING
    if dedupe_key and TelegramNotification.objects.filter(
        chat_link=chat_link,
        dedupe_key=dedupe_key,
        created_at__gte=cutoff,
        status__in=[TelegramNotification.Status.PENDING, TelegramNotification.Status.SENT, TelegramNotification.Status.SUPPRESSED],
    ).exists():
        status = TelegramNotification.Status.SUPPRESSED
    return TelegramNotification.objects.create(
        account=account,
        server=server,
        finding=finding,
        chat_link=chat_link,
        notification_type=notification_type,
        status=status,
        dedupe_key=dedupe_key,
        payload_redacted=payload_redacted,
    )


def render_notification(notification):
    payload = notification.payload_redacted or {}
    message = payload.get("message") or notification.notification_type.replace("_", " ").title()
    if notification.server:
        message = f"{message}\nServer: {notification.server.name}"
    if notification.finding:
        message = f"{message}\nFinding: {notification.finding.title} ({notification.finding.severity})"
    return redact_secrets(message)


def send_notification(notification):
    if notification.status == TelegramNotification.Status.SUPPRESSED:
        return notification
    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        notification.status = TelegramNotification.Status.FAILED
        notification.error_message = "Telegram bot token is not configured."
        notification.save(update_fields=["status", "error_message", "updated_at"])
        return notification

    payload = {
        "chat_id": notification.chat_link.telegram_chat_id,
        "text": render_notification(notification),
        "disable_web_page_preview": True,
    }
    encoded = parse.urlencode(payload).encode("utf-8")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        req = request.Request(url, data=encoded, method="POST")
        with request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8") or "{}")
        if not result.get("ok"):
            raise TelegramCommandError("Telegram API rejected the message.")
        notification.status = TelegramNotification.Status.SENT
        notification.sent_at = timezone.now()
        notification.error_message = ""
        notification.save(update_fields=["status", "sent_at", "error_message", "updated_at"])
    except (OSError, URLError, ValueError, TelegramCommandError) as exc:
        notification.status = TelegramNotification.Status.FAILED
        notification.error_message = redact_secrets(str(exc))
        notification.save(update_fields=["status", "error_message", "updated_at"])
    return notification


def notifications_for_account(account, notification_type, *, server=None, finding=None, payload=None, dedupe_key=""):
    links = TelegramChatLink.objects.filter(account=account, status=TelegramChatLink.Status.ACTIVE)
    created = []
    for link in links:
        if link.allowed_notifications and notification_type not in link.allowed_notifications:
            continue
        if server and link.server_id and link.server_id != server.id:
            continue
        created.append(
            create_notification(
                chat_link=link,
                notification_type=notification_type,
                server=server,
                finding=finding,
                payload=payload,
                dedupe_key=dedupe_key,
            )
        )
    return created
