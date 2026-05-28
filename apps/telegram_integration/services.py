from datetime import timedelta
import json
from urllib import parse, request
from urllib.error import URLError

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.models import Account
from apps.applications.models import Application
from apps.audit.models import AuditLog
from apps.core.redaction import redact_json, redact_secrets
from apps.core.tokens import hash_token
from apps.diagnostics.models import DiagnosticSession, DiagnosticStep
from apps.diagnostics.services import (
    DiagnosticError,
    approve_diagnostic_step,
    start_diagnostic_session,
    sync_completed_tool_runs,
)
from apps.servers.models import BaselineScan, Finding, Server

from .models import TelegramChatLink, TelegramDiagnosticState, TelegramLinkToken, TelegramNotification


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
    "/diagnose",
    "/cancel",
    "/approve",
    "/session",
    "/report",
}

PRIVATE_COMMANDS = ALLOWED_COMMANDS
GROUP_COMMANDS = {"/start", "/unlink", "/help", "/menu", "/status"}
DIAGNOSTIC_ROLES = {User.CustomerRole.OWNER, User.CustomerRole.OPERATOR}
DIAGNOSTIC_STATE_TTL_MINUTES = 30
PROBLEM_TYPES = {
    DiagnosticSession.ProblemType.SLOWNESS,
    DiagnosticSession.ProblemType.HTTP_500,
    DiagnosticSession.ProblemType.SECURITY_SCAN,
    DiagnosticSession.ProblemType.LARAVEL_PRODUCTION_AUDIT,
    DiagnosticSession.ProblemType.CUSTOM,
}
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


def parse_callback(update):
    callback = update.get("callback_query") or {}
    message = callback.get("message") or {}
    chat = message.get("chat") or {}
    sender = callback.get("from") or {}
    return {
        "data": str(callback.get("data") or ""),
        "chat_id": chat.get("id"),
        "chat_type": chat.get("type") or "",
        "title": chat.get("title") or chat.get("username") or "",
        "telegram_user_id": sender.get("id"),
    }


def command_name(text):
    if not text.startswith("/"):
        return ""
    return text.split()[0].split("@")[0].lower()


def telegram_response(text, keyboard=None):
    return {"text": redact_secrets(text), "reply_markup": keyboard}


def inline_keyboard(rows):
    return {"inline_keyboard": rows}


def button(text, data):
    return {"text": text, "callback_data": data[:64]}


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


def active_chat_link_for_callback(update):
    parsed = parse_callback(update)
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


def handle_update_response(update):
    if update.get("callback_query"):
        return handle_callback_query(update)

    parsed = parse_message(update)
    text = parsed["text"]
    command = command_name(text)
    if not command:
        chat_link = active_chat_link_for_update(update)
        if chat_link:
            state = active_diagnostic_state(chat_link)
            if state and state.state == TelegramDiagnosticState.State.AWAITING_DESCRIPTION:
                return set_problem_description(state, text)
        return telegram_response("Use /help to see available Matrix Scanner commands.")
    if command not in ALLOWED_COMMANDS:
        return telegram_response("This Telegram command is not available in the read-only MVP.")
    if command == "/link":
        parts = text.split(maxsplit=1)
        if len(parts) != 2:
            return telegram_response("Send /link followed by your one-time link code.")
        try:
            link_chat_with_code(update, parts[1].strip())
        except TelegramCommandError as exc:
            return telegram_response(str(exc))
        return telegram_response("This Telegram chat is now linked to Matrix Scanner.")

    chat_link = active_chat_link_for_update(update)
    if not chat_link or not chat_link.is_active:
        if command in {"/start", "/help"}:
            return telegram_response(help_text(linked=False))
        return telegram_response("This chat is not linked. Use /link with a one-time code from the Portal.")

    if chat_link.chat_type != TelegramChatLink.ChatType.PRIVATE and command not in GROUP_COMMANDS:
        return telegram_response("Group chats support alerts plus /help and /status in this MVP.")
    if command == "/start" or command == "/help":
        return telegram_response(help_text(linked=True, chat_type=chat_link.chat_type))
    if command == "/menu":
        return telegram_response(menu_text(chat_link))
    if command == "/unlink":
        unlink_chat(chat_link)
        return telegram_response("This Telegram chat has been unlinked.")
    if command == "/servers":
        return telegram_response(servers_summary(chat_link))
    if command == "/apps":
        return telegram_response(applications_summary(chat_link))
    if command == "/findings":
        return telegram_response(findings_summary(chat_link))
    if command == "/status":
        return telegram_response(account_status_summary(chat_link))
    if command == "/baseline":
        return telegram_response(baseline_summary(chat_link))
    if command == "/diagnose":
        return handle_diagnose_command(chat_link, text)
    if command == "/cancel":
        return cancel_diagnostic_state(chat_link)
    if command == "/approve":
        return approve_active_diagnostic_step(chat_link)
    if command == "/session":
        return session_status_response(chat_link)
    if command == "/report":
        return report_response(chat_link)
    return telegram_response("This Telegram command is not available in the read-only MVP.")


def handle_update(update):
    return handle_update_response(update)["text"]


def help_text(*, linked, chat_type=TelegramChatLink.ChatType.PRIVATE):
    if not linked:
        return "Matrix Scanner Telegram is read-only. Link this chat with /link <code> from the Portal."
    if chat_type == TelegramChatLink.ChatType.PRIVATE:
        return "Read-only commands: /servers, /apps, /findings, /status, /baseline, /diagnose, /session, /approve, /report, /cancel, /unlink."
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


def diagnostic_access_error(chat_link):
    if not chat_link.is_active:
        return "This Telegram chat is not active."
    if chat_link.chat_type != TelegramChatLink.ChatType.PRIVATE:
        return "Diagnostics are only available in private Telegram chats."
    if not chat_link.user_id:
        return "This private chat is not linked to a Portal user."
    if chat_link.user.role not in DIAGNOSTIC_ROLES:
        return "Your Portal role cannot start or approve diagnostic sessions."
    return ""


def diagnostic_expiry():
    return timezone.now() + timedelta(minutes=DIAGNOSTIC_STATE_TTL_MINUTES)


def active_diagnostic_state(chat_link, *, lock=False):
    qs = TelegramDiagnosticState.objects.filter(chat_link=chat_link, state__in=TelegramDiagnosticState.ACTIVE_STATES)
    if lock:
        qs = qs.select_for_update()
    else:
        qs = qs.select_related(
            "account",
            "user",
            "chat_link",
            "selected_server",
            "selected_application",
            "diagnostic_session",
        )
    state = qs.order_by("-updated_at").first()
    if state and state.is_expired:
        state.state = TelegramDiagnosticState.State.EXPIRED
        state.save(update_fields=["state", "updated_at"])
        audit_telegram_action(
            action="telegram.diagnostic.expired",
            account=state.account,
            user=state.user,
            target_type="TelegramDiagnosticState",
            target_id=state.id,
            result=AuditLog.Result.DENIED,
            metadata={"state_id": str(state.id)},
        )
        return None
    return state


def audit_diagnostic_telegram(*, action, state=None, chat_link=None, result=AuditLog.Result.SUCCESS, metadata=None):
    account = state.account if state else chat_link.account
    user = state.user if state else chat_link.user
    target_id = state.id if state else chat_link.id
    safe_metadata = metadata or {}
    if state:
        safe_metadata = {"state_id": str(state.id), **safe_metadata}
    audit_telegram_action(
        action=action,
        account=account,
        user=user,
        target_type="TelegramDiagnosticState",
        target_id=target_id,
        result=result,
        metadata=safe_metadata,
    )


def handle_diagnose_command(chat_link, text):
    parts = text.split(maxsplit=2)
    if len(parts) >= 2:
        subcommand = parts[1].lower()
        value = parts[2].strip() if len(parts) > 2 else ""
        if subcommand == "server":
            return select_server_from_text(chat_link, value)
        if subcommand == "app":
            return select_application_from_text(chat_link, value)
        if subcommand == "problem":
            return select_problem_type_from_text(chat_link, value)
        if subcommand == "describe":
            return set_description_from_text(chat_link, value)
        if subcommand == "confirm":
            return confirm_diagnostic_state(chat_link)

    error = diagnostic_access_error(chat_link)
    if error:
        return telegram_response(error)
    state = active_diagnostic_state(chat_link)
    if state:
        return telegram_response("A diagnostic session is already active for this chat. Use /session, /approve, /report, or /cancel.")
    state = TelegramDiagnosticState.objects.create(
        chat_link=chat_link,
        account=chat_link.account,
        user=chat_link.user,
        state=TelegramDiagnosticState.State.SELECTING_SERVER,
        expires_at=diagnostic_expiry(),
        last_message_at=timezone.now(),
    )
    audit_diagnostic_telegram(action="telegram.diagnostic.start_requested", state=state)
    return server_selection_response(state)


def server_selection_response(state):
    servers = scoped_servers(state.chat_link)[:10]
    if not servers:
        return telegram_response("No servers are available for diagnostics.")
    rows = [[button(server.name[:40], f"dg:sv:{server.id}")] for server in servers]
    text_lines = ["Select a server for diagnostics:"]
    for server in servers:
        text_lines.append(f"- {server.id}: {redact_secrets(server.name)}")
    text_lines.append("Text fallback: /diagnose server <id>")
    return telegram_response("\n".join(text_lines), inline_keyboard(rows))


def select_server_from_text(chat_link, value):
    state = active_diagnostic_state(chat_link)
    if not state:
        return telegram_response("Start with /diagnose first.")
    return select_server(state, value)


def select_server(state, server_id):
    error = diagnostic_access_error(state.chat_link)
    if error:
        return telegram_response(error)
    if state.state != TelegramDiagnosticState.State.SELECTING_SERVER:
        return telegram_response("This diagnostic flow is not waiting for server selection.")
    server = Server.objects.filter(account=state.account, id=server_id).first()
    if not server:
        audit_diagnostic_telegram(
            action="telegram.diagnostic.server_denied",
            state=state,
            result=AuditLog.Result.DENIED,
            metadata={"server_id": str(server_id)},
        )
        return telegram_response("That server is not available for this account.")
    state.selected_server = server
    state.state = TelegramDiagnosticState.State.SELECTING_APPLICATION
    state.expires_at = diagnostic_expiry()
    state.last_message_at = timezone.now()
    state.save(update_fields=["selected_server", "state", "expires_at", "last_message_at", "updated_at"])
    audit_diagnostic_telegram(action="telegram.diagnostic.server_selected", state=state, metadata={"server_id": str(server.id)})
    return application_selection_response(state)


def application_selection_response(state):
    applications = Application.objects.filter(account=state.account, server=state.selected_server).order_by("name")[:10]
    rows = [[button("No application", "dg:app:none")]]
    rows.extend([[button(application.name[:40], f"dg:app:{application.id}")] for application in applications])
    lines = [f"Server selected: {redact_secrets(state.selected_server.name)}", "Select an application or choose No application:"]
    for application in applications:
        lines.append(f"- {application.id}: {redact_secrets(application.name)}")
    lines.append("Text fallback: /diagnose app <id|none>")
    return telegram_response("\n".join(lines), inline_keyboard(rows))


def select_application_from_text(chat_link, value):
    state = active_diagnostic_state(chat_link)
    if not state:
        return telegram_response("Start with /diagnose first.")
    return select_application(state, value)


def select_application(state, application_id):
    error = diagnostic_access_error(state.chat_link)
    if error:
        return telegram_response(error)
    if state.state != TelegramDiagnosticState.State.SELECTING_APPLICATION:
        return telegram_response("This diagnostic flow is not waiting for application selection.")
    application = None
    if str(application_id).lower() not in {"", "none", "0"}:
        application = Application.objects.filter(account=state.account, server=state.selected_server, id=application_id).first()
        if not application:
            audit_diagnostic_telegram(
                action="telegram.diagnostic.application_denied",
                state=state,
                result=AuditLog.Result.DENIED,
                metadata={"application_id": str(application_id)},
            )
            return telegram_response("That application is not available for the selected server.")
    state.selected_application = application
    state.state = TelegramDiagnosticState.State.SELECTING_PROBLEM_TYPE
    state.expires_at = diagnostic_expiry()
    state.last_message_at = timezone.now()
    state.save(update_fields=["selected_application", "state", "expires_at", "last_message_at", "updated_at"])
    audit_diagnostic_telegram(
        action="telegram.diagnostic.application_selected",
        state=state,
        metadata={"application_id": str(application.id) if application else ""},
    )
    return problem_type_response(state)


def problem_type_response(state):
    labels = {
        DiagnosticSession.ProblemType.SLOWNESS: "Slowness",
        DiagnosticSession.ProblemType.HTTP_500: "HTTP 500",
        DiagnosticSession.ProblemType.SECURITY_SCAN: "Security scan",
        DiagnosticSession.ProblemType.LARAVEL_PRODUCTION_AUDIT: "Laravel audit",
        DiagnosticSession.ProblemType.CUSTOM: "Custom",
    }
    rows = [[button(label, f"dg:pt:{value}")] for value, label in labels.items()]
    lines = ["Select problem type:"]
    for value, label in labels.items():
        lines.append(f"- {value}: {label}")
    lines.append("Text fallback: /diagnose problem <type>")
    return telegram_response("\n".join(lines), inline_keyboard(rows))


def select_problem_type_from_text(chat_link, value):
    state = active_diagnostic_state(chat_link)
    if not state:
        return telegram_response("Start with /diagnose first.")
    return select_problem_type(state, value)


def select_problem_type(state, problem_type):
    error = diagnostic_access_error(state.chat_link)
    if error:
        return telegram_response(error)
    if state.state != TelegramDiagnosticState.State.SELECTING_PROBLEM_TYPE:
        return telegram_response("This diagnostic flow is not waiting for problem type selection.")
    if problem_type not in PROBLEM_TYPES:
        return telegram_response("Unsupported problem type.")
    state.problem_type = problem_type
    state.state = TelegramDiagnosticState.State.AWAITING_DESCRIPTION
    state.expires_at = diagnostic_expiry()
    state.last_message_at = timezone.now()
    state.save(update_fields=["problem_type", "state", "expires_at", "last_message_at", "updated_at"])
    audit_diagnostic_telegram(action="telegram.diagnostic.problem_selected", state=state, metadata={"problem_type": problem_type})
    return telegram_response(
        "Send a short problem description, or choose Skip. Text fallback: /diagnose describe <text>",
        inline_keyboard([[button("Skip description", "dg:desc:skip")]]),
    )


def set_description_from_text(chat_link, value):
    state = active_diagnostic_state(chat_link)
    if not state:
        return telegram_response("Start with /diagnose first.")
    return set_problem_description(state, value)


def set_problem_description(state, description):
    error = diagnostic_access_error(state.chat_link)
    if error:
        return telegram_response(error)
    if state.state != TelegramDiagnosticState.State.AWAITING_DESCRIPTION:
        return telegram_response("This diagnostic flow is not waiting for a description.")
    bounded = (description or "")[:500]
    state.problem_description_redacted = redact_secrets(bounded)
    state.state = TelegramDiagnosticState.State.AWAITING_CONFIRMATION
    state.expires_at = diagnostic_expiry()
    state.last_message_at = timezone.now()
    state.save(update_fields=["problem_description_redacted", "state", "expires_at", "last_message_at", "updated_at"])
    return confirmation_response(state)


def confirmation_response(state):
    application_name = state.selected_application.name if state.selected_application else "No application"
    text = (
        "Confirm diagnostic session:\n"
        f"- Server: {redact_secrets(state.selected_server.name)}\n"
        f"- Application: {redact_secrets(application_name)}\n"
        f"- Problem: {state.problem_type}\n"
        f"- Description: {state.problem_description_redacted or 'No description'}"
    )
    return telegram_response(text, inline_keyboard([[button("Confirm", "dg:confirm"), button("Cancel", "dg:cancel")]]))


def confirm_diagnostic_state(chat_link):
    with transaction.atomic():
        state = active_diagnostic_state(chat_link, lock=True)
        if not state:
            return telegram_response("No active diagnostic flow. Start with /diagnose.")
        return create_session_from_state(state)


def create_session_from_state(state):
    error = diagnostic_access_error(state.chat_link)
    if error:
        return telegram_response(error)
    if state.state != TelegramDiagnosticState.State.AWAITING_CONFIRMATION:
        return telegram_response("This diagnostic flow is not ready for confirmation.")
    session = start_diagnostic_session(
        user=state.user,
        server=state.selected_server,
        application=state.selected_application,
        problem_type=state.problem_type,
        user_prompt=state.problem_description_redacted,
        source=DiagnosticSession.Source.TELEGRAM,
        source_chat_link=state.chat_link,
    )
    state.diagnostic_session = session
    state.state = TelegramDiagnosticState.State.ACTIVE
    state.expires_at = diagnostic_expiry()
    state.last_message_at = timezone.now()
    state.save(update_fields=["diagnostic_session", "state", "expires_at", "last_message_at", "updated_at"])
    audit_diagnostic_telegram(
        action="telegram.diagnostic.session_created",
        state=state,
        metadata={"session_id": str(session.id), "server_id": str(session.server_id)},
    )
    step = next_awaiting_step(session)
    if step:
        audit_diagnostic_telegram(
            action="telegram.diagnostic.approval_requested",
            state=state,
            metadata={"session_id": str(session.id), "step_id": str(step.id), "tool_key": step.tool_key},
        )
    return telegram_response(
        f"Diagnostic session started. Next read-only tool step: {step.tool_key if step else 'none'}.\nUse /approve to approve the next step.",
        inline_keyboard([[button("Approve next step", "dg:approve"), button("Cancel", "dg:cancel")]]),
    )


def next_awaiting_step(session):
    return (
        session.steps.filter(status=DiagnosticStep.Status.AWAITING_APPROVAL, requires_approval=True)
        .order_by("created_at")
        .first()
    )


def approve_active_diagnostic_step(chat_link):
    with transaction.atomic():
        state = active_diagnostic_state(chat_link, lock=True)
        if not state:
            return telegram_response("No active diagnostic session for this chat.")
        error = diagnostic_access_error(state.chat_link)
        if error:
            return telegram_response(error)
        if not state.diagnostic_session_id:
            return telegram_response("No diagnostic session has been confirmed yet.")
        session = DiagnosticSession.objects.select_for_update().get(id=state.diagnostic_session_id, account=state.account)
        step = next_awaiting_step(session)
        if not step:
            audit_diagnostic_telegram(
                action="telegram.diagnostic.approval_denied",
                state=state,
                result=AuditLog.Result.DENIED,
                metadata={"session_id": str(session.id)},
            )
            return telegram_response("No diagnostic step is waiting for approval.")
        step = DiagnosticStep.objects.select_for_update().get(id=step.id, session=session)
        before_jobs = session.server.agent_jobs.count()
        try:
            approve_diagnostic_step(user=state.user, session=session, step=step)
        except (PermissionDenied, DiagnosticError) as exc:
            audit_diagnostic_telegram(
                action="telegram.diagnostic.approval_denied",
                state=state,
                result=AuditLog.Result.DENIED,
                metadata={"session_id": str(session.id), "step_id": str(step.id)},
            )
            return telegram_response(str(exc))
        state.expires_at = diagnostic_expiry()
        state.last_message_at = timezone.now()
        state.save(update_fields=["expires_at", "last_message_at", "updated_at"])
        audit_diagnostic_telegram(
            action="telegram.diagnostic.approval_accepted",
            state=state,
            metadata={"session_id": str(session.id), "step_id": str(step.id), "job_count_before": str(before_jobs)},
        )
    return session_status_response(chat_link, prefix="Step approved through Diagnostic service.")


def session_status_response(chat_link, prefix=""):
    state = active_diagnostic_state(chat_link)
    if not state or not state.diagnostic_session_id:
        return telegram_response("No active diagnostic session for this chat.")
    session = state.diagnostic_session
    sync_completed_tool_runs(session)
    session.refresh_from_db()
    step = next_awaiting_step(session)
    text = (
        f"{prefix}\n" if prefix else ""
    ) + (
        f"Diagnostic session status: {session.status}\n"
        f"- Server: {redact_secrets(session.server.name)}\n"
        f"- Problem: {session.problem_type}\n"
        f"- Tool runs: {session.tool_run_count}/{session.max_tool_runs}"
    )
    keyboard = None
    if step:
        text += f"\nNext step awaiting approval: {step.tool_key}"
        keyboard = inline_keyboard([[button("Approve next step", "dg:approve"), button("Cancel", "dg:cancel")]])
    elif session.final_report_redacted:
        keyboard = inline_keyboard([[button("Show short report", "dg:report")]])
    return telegram_response(text, keyboard)


def short_report_text(session):
    findings = Finding.objects.filter(account=session.account, server=session.server).order_by("-created_at")[:3]
    application = session.application.name if session.application else "No application"
    lines = [
        f"Diagnostic report: {session.status}",
        f"- Server: {redact_secrets(session.server.name)}",
        f"- Application: {redact_secrets(application)}",
        f"- Problem: {session.problem_type}",
        f"- Tool count: {session.tool_run_count}/{session.max_tool_runs}",
    ]
    if session.final_report_redacted:
        report = redact_secrets(session.final_report_redacted)
        lines.append(f"- Summary: {report[:500]}")
    if findings:
        lines.append("Top findings:")
        for finding in findings:
            lines.append(f"- {finding.severity}/{finding.status}: {redact_secrets(finding.title)}")
    lines.append("View the full redacted report in the Portal.")
    return "\n".join(lines)


def report_response(chat_link):
    state = active_diagnostic_state(chat_link)
    if not state or not state.diagnostic_session_id:
        return telegram_response("No active diagnostic session for this chat.")
    session = state.diagnostic_session
    sync_completed_tool_runs(session)
    session.refresh_from_db()
    audit_diagnostic_telegram(
        action="telegram.diagnostic.report_viewed",
        state=state,
        metadata={"session_id": str(session.id)},
    )
    return telegram_response(short_report_text(session))


def cancel_diagnostic_state(chat_link):
    with transaction.atomic():
        state = active_diagnostic_state(chat_link, lock=True)
        if not state:
            return telegram_response("No active diagnostic session for this chat.")
        session = state.diagnostic_session
        if session and session.status in {DiagnosticSession.Status.DRAFT, DiagnosticSession.Status.WAITING_FOR_APPROVAL}:
            session.status = DiagnosticSession.Status.CANCELLED
            session.finished_at = timezone.now()
            session.save(update_fields=["status", "finished_at", "updated_at"])
            session.steps.filter(status=DiagnosticStep.Status.AWAITING_APPROVAL).update(status=DiagnosticStep.Status.CANCELLED)
        state.state = TelegramDiagnosticState.State.CANCELLED
        state.expires_at = timezone.now()
        state.last_message_at = timezone.now()
        state.save(update_fields=["state", "expires_at", "last_message_at", "updated_at"])
        audit_diagnostic_telegram(
            action="telegram.diagnostic.cancelled",
            state=state,
            metadata={"session_id": str(session.id) if session else ""},
        )
    return telegram_response("Telegram diagnostic flow cancelled. Already queued or running agent jobs are not cancelled.")


def handle_callback_query(update):
    chat_link = active_chat_link_for_callback(update)
    if not chat_link or not chat_link.is_active:
        return telegram_response("This chat is not linked. Use /link with a one-time code from the Portal.")
    parsed = parse_callback(update)
    data = parsed["data"]
    if not data.startswith("dg:"):
        return telegram_response("Unsupported callback.")
    if chat_link.chat_type != TelegramChatLink.ChatType.PRIVATE:
        return telegram_response("Diagnostics are only available in private Telegram chats.")
    if data == "dg:cancel":
        return cancel_diagnostic_state(chat_link)
    if data == "dg:confirm":
        return confirm_diagnostic_state(chat_link)
    if data == "dg:approve":
        return approve_active_diagnostic_step(chat_link)
    if data == "dg:session":
        return session_status_response(chat_link)
    if data == "dg:report":
        return report_response(chat_link)

    state = active_diagnostic_state(chat_link)
    if not state:
        return telegram_response("No active diagnostic flow. Start with /diagnose.")
    if data.startswith("dg:sv:"):
        return select_server(state, data.removeprefix("dg:sv:"))
    if data.startswith("dg:app:"):
        return select_application(state, data.removeprefix("dg:app:"))
    if data.startswith("dg:pt:"):
        return select_problem_type(state, data.removeprefix("dg:pt:"))
    if data == "dg:desc:skip":
        return set_problem_description(state, "")
    return telegram_response("Unsupported diagnostic callback.")


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
