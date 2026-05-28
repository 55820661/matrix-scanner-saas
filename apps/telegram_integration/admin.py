from django.contrib import admin

from .models import TelegramChatLink, TelegramLinkToken, TelegramNotification


@admin.register(TelegramChatLink)
class TelegramChatLinkAdmin(admin.ModelAdmin):
    list_display = ("telegram_chat_id", "chat_type", "account", "server", "status", "linked_at", "revoked_at")
    list_filter = ("chat_type", "status", "account")
    search_fields = ("telegram_chat_id", "title", "account__name", "server__name")
    readonly_fields = ("created_at", "updated_at", "linked_at", "revoked_at")


@admin.register(TelegramLinkToken)
class TelegramLinkTokenAdmin(admin.ModelAdmin):
    list_display = ("account", "created_by", "chat_scope", "server", "expires_at", "used_at", "revoked_at", "created_at")
    list_filter = ("chat_scope", "account", "expires_at", "used_at", "revoked_at")
    search_fields = ("account__name", "server__name", "created_by__username")
    readonly_fields = ("token_hash", "created_at", "used_at", "revoked_at")


@admin.register(TelegramNotification)
class TelegramNotificationAdmin(admin.ModelAdmin):
    list_display = ("notification_type", "account", "server", "chat_link", "status", "dedupe_key", "sent_at", "created_at")
    list_filter = ("notification_type", "status", "account")
    search_fields = ("account__name", "server__name", "dedupe_key", "error_message")
    readonly_fields = ("payload_redacted", "created_at", "updated_at", "sent_at")
