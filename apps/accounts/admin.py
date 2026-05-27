from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Account, User


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "status", "created_at", "updated_at")
    list_filter = ("type", "status", "created_at")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(User)
class MatrixUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Matrix Scanner", {"fields": ("account", "role")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Matrix Scanner", {"fields": ("account", "role", "email")}),
    )
    list_display = ("username", "email", "account", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_superuser", "is_active", "account")
    search_fields = ("username", "email", "first_name", "last_name", "account__name")
