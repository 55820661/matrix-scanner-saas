from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied

from .crypto import encrypt_payload
from .models import AgentInstallation, BootstrapCredential, BootstrapSession, BootstrapStep
from .services import BootstrapError, is_matrix_admin, run_bootstrap_session


class MatrixAdminOnlyMixin:
    def has_module_permission(self, request):
        return is_matrix_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_matrix_admin(request.user)

    def has_add_permission(self, request):
        return is_matrix_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_matrix_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_matrix_admin(request.user)


class BootstrapStepInline(admin.TabularInline):
    model = BootstrapStep
    extra = 0
    fields = (
        "step_key",
        "status",
        "command_template_key",
        "requires_confirmation",
        "confirmed_at",
        "exit_code",
        "summary",
        "error_message",
    )
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class BootstrapSessionAdminForm(forms.ModelForm):
    credential_secret = forms.CharField(
        label="Temporary SSH credential",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "autocomplete": "off"}),
        help_text="Required when creating a session. This value is encrypted into BootstrapCredential and is not stored raw.",
    )

    class Meta:
        model = BootstrapSession
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        server = cleaned_data.get("server")
        target_host = cleaned_data.get("target_host")
        if server and not target_host:
            cleaned_data["target_host"] = server.hostname or str(server.public_ip or "")
        if not cleaned_data.get("target_host"):
            raise forms.ValidationError("Target host is required when the selected Server has no hostname or public IP.")
        if self.instance._state.adding and not cleaned_data.get("credential_secret"):
            raise forms.ValidationError("Temporary SSH credential is required when creating a bootstrap session.")
        return cleaned_data


@admin.register(BootstrapSession)
class BootstrapSessionAdmin(MatrixAdminOnlyMixin, admin.ModelAdmin):
    form = BootstrapSessionAdminForm
    list_display = (
        "server",
        "account",
        "status",
        "target_host",
        "ssh_user",
        "auth_method",
        "confirm_package_install",
        "started_at",
        "finished_at",
    )
    list_filter = ("status", "auth_method", "confirm_package_install", "account", "created_at")
    search_fields = ("server__name", "server__hostname", "target_host", "ssh_user", "account__name")
    readonly_fields = (
        "started_at",
        "finished_at",
        "failure_reason",
        "created_at",
        "updated_at",
    )
    inlines = [BootstrapStepInline]
    actions = ["run_selected_bootstrap_sessions"]

    def save_model(self, request, obj, form, change):
        if not is_matrix_admin(request.user):
            raise PermissionDenied("Remote bootstrap is restricted to Matrix Admin users.")
        if not obj.account_id and obj.server_id:
            obj.account = obj.server.account
        if not obj.target_host and obj.server_id:
            obj.target_host = obj.server.hostname or str(obj.server.public_ip or "")
        super().save_model(request, obj, form, change)
        raw_secret = form.cleaned_data.get("credential_secret")
        if raw_secret:
            credential_type = (
                BootstrapCredential.CredentialType.SSH_PASSWORD
                if obj.auth_method == BootstrapSession.AuthMethod.PASSWORD
                else BootstrapCredential.CredentialType.SSH_PRIVATE_KEY
            )
            BootstrapCredential.objects.create(
                session=obj,
                credential_type=credential_type,
                encrypted_payload=encrypt_payload(raw_secret),
                expires_at=BootstrapCredential.default_expiry(),
            )

    @admin.action(description="Run selected bootstrap sessions")
    def run_selected_bootstrap_sessions(self, request, queryset):
        if not is_matrix_admin(request.user):
            raise PermissionDenied("Remote bootstrap is restricted to Matrix Admin users.")
        for session in queryset:
            try:
                run_bootstrap_session(session)
                self.message_user(request, f"Bootstrap session {session.id} completed.", messages.SUCCESS)
            except BootstrapError as exc:
                self.message_user(request, f"Bootstrap session {session.id} failed: {exc}", messages.ERROR)


@admin.register(BootstrapStep)
class BootstrapStepAdmin(MatrixAdminOnlyMixin, admin.ModelAdmin):
    list_display = ("session", "step_key", "status", "command_template_key", "exit_code", "started_at", "finished_at")
    list_filter = ("status", "step_key", "command_template_key", "created_at")
    search_fields = ("session__server__name", "step_key", "summary", "error_message")
    readonly_fields = (
        "session",
        "step_key",
        "status",
        "started_at",
        "finished_at",
        "command_template_key",
        "requires_confirmation",
        "confirmed_at",
        "summary",
        "stdout_redacted",
        "stderr_redacted",
        "exit_code",
        "error_message",
        "structured_output",
        "created_at",
        "updated_at",
    )


@admin.register(BootstrapCredential)
class BootstrapCredentialAdmin(MatrixAdminOnlyMixin, admin.ModelAdmin):
    list_display = ("session", "credential_type", "expires_at", "destroyed_at", "created_at")
    list_filter = ("credential_type", "expires_at", "destroyed_at", "created_at")
    search_fields = ("session__server__name", "session__target_host")
    readonly_fields = ("session", "credential_type", "encrypted_payload", "expires_at", "destroyed_at", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False


@admin.register(AgentInstallation)
class AgentInstallationAdmin(MatrixAdminOnlyMixin, admin.ModelAdmin):
    list_display = (
        "server",
        "account",
        "agent",
        "status",
        "install_method",
        "install_path",
        "service_name",
        "installed_at",
        "last_verified_at",
    )
    list_filter = ("status", "install_method", "service_name", "account", "created_at")
    search_fields = ("server__name", "server__hostname", "account__name", "service_name", "agent_version")
    readonly_fields = ("created_at", "updated_at")
