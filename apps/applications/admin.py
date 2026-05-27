from django.contrib import admin

from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("name", "account", "server", "domain", "framework", "review_status")
    list_filter = ("review_status", "framework", "account")
    search_fields = ("name", "domain", "path", "server__name", "account__name")
    readonly_fields = ("created_at", "updated_at")
