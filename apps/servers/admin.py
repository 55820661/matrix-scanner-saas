from django.contrib import admin
from django.contrib import messages

from apps.reports.services import create_baseline_report, rebuild_finding_groups

from .baseline import BaselineScanError, start_baseline_scan
from .models import (
    AgentJob,
    AgentRegistrationToken,
    BaselineScan,
    BaselineScanStep,
    DiscoveredDomain,
    DiscoveredService,
    Finding,
    LogSource,
    ScannerAgent,
    Server,
)


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ("name", "account", "hostname", "public_ip", "status", "agent_status", "last_seen_at")
    list_filter = ("status", "agent_status", "account")
    search_fields = ("name", "hostname", "public_ip", "account__name")
    readonly_fields = ("created_at", "updated_at")
    actions = ("create_and_start_baseline_scans",)

    @admin.action(description="Create and start baseline scan")
    def create_and_start_baseline_scans(self, request, queryset):
        if not request.user.is_staff:
            self.message_user(request, "Only Matrix Admin staff users can start baseline scans.", level=messages.ERROR)
            return
        started = 0
        failed = 0
        for server in queryset:
            scan = BaselineScan.objects.create(account=server.account, server=server, requested_by=request.user)
            try:
                start_baseline_scan(scan)
                started += 1
            except BaselineScanError:
                failed += 1
        self.message_user(request, f"Created and started {started} baseline scan(s); failed {failed}.")


@admin.register(ScannerAgent)
class ScannerAgentAdmin(admin.ModelAdmin):
    list_display = ("server", "account", "status", "agent_version", "registered_at", "last_seen_at", "revoked_at")
    list_filter = ("status", "account", "registered_at", "last_seen_at")
    search_fields = ("server__name", "server__hostname", "account__name", "agent_version")
    readonly_fields = ("token_hash", "created_at", "updated_at")


@admin.register(AgentRegistrationToken)
class AgentRegistrationTokenAdmin(admin.ModelAdmin):
    list_display = ("server", "account", "expires_at", "used_at", "revoked_at", "created_by", "created_at")
    list_filter = ("expires_at", "used_at", "revoked_at", "account")
    search_fields = ("server__name", "server__hostname", "account__name", "created_by__username")
    readonly_fields = ("token_hash", "created_at", "updated_at")


@admin.register(AgentJob)
class AgentJobAdmin(admin.ModelAdmin):
    list_display = ("tool_key", "server", "agent", "account", "status", "claimed_at", "claim_expires_at", "finished_at")
    list_filter = ("status", "tool_key", "account", "created_at")
    search_fields = ("tool_key", "server__name", "server__hostname", "account__name")
    readonly_fields = ("raw_result_hidden", "created_at", "updated_at")
    exclude = ("result",)

    @admin.display(description="Result")
    def raw_result_hidden(self, obj):
        return "Raw AgentJob results are hidden. Use redacted ToolRun, report, or diagnostic summaries instead."


@admin.register(BaselineScan)
class BaselineScanAdmin(admin.ModelAdmin):
    list_display = ("server", "account", "status", "current_step", "started_at", "finished_at", "created_at")
    list_filter = ("status", "account", "created_at")
    search_fields = ("server__name", "server__hostname", "account__name")
    readonly_fields = ("summary", "error_message", "created_at", "updated_at")
    actions = ("start_selected_baseline_scans", "generate_baseline_reports")

    @admin.action(description="Start selected baseline scans")
    def start_selected_baseline_scans(self, request, queryset):
        if not request.user.is_staff:
            self.message_user(request, "Only Matrix Admin staff users can start baseline scans.", level=messages.ERROR)
            return
        started = 0
        failed = 0
        for scan in queryset:
            if scan.requested_by_id is None:
                scan.requested_by = request.user
                scan.save(update_fields=["requested_by", "updated_at"])
            try:
                start_baseline_scan(scan)
                started += 1
            except BaselineScanError:
                failed += 1
        self.message_user(request, f"Started {started} baseline scan(s); failed {failed}.")

    @admin.action(description="Generate redacted baseline reports")
    def generate_baseline_reports(self, request, queryset):
        generated = 0
        for scan in queryset:
            create_baseline_report(scan, user=request.user)
            generated += 1
        self.message_user(request, f"Generated {generated} baseline report(s).")


@admin.register(BaselineScanStep)
class BaselineScanStepAdmin(admin.ModelAdmin):
    list_display = ("baseline_scan", "step_key", "status", "tool_run", "started_at", "finished_at")
    list_filter = ("status", "step_key", "created_at")
    search_fields = ("step_key", "baseline_scan__server__name", "baseline_scan__account__name")
    readonly_fields = ("structured_output", "created_at", "updated_at")


@admin.register(DiscoveredService)
class DiscoveredServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "server", "account", "status", "version", "updated_at")
    list_filter = ("status", "account", "created_at")
    search_fields = ("name", "server__name", "account__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(DiscoveredDomain)
class DiscoveredDomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "server", "account", "document_root", "owner", "updated_at")
    list_filter = ("account", "created_at")
    search_fields = ("domain", "document_root", "owner", "server__name", "account__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(LogSource)
class LogSourceAdmin(admin.ModelAdmin):
    list_display = ("path", "server", "account", "source_type", "exists", "size_bytes", "updated_at")
    list_filter = ("source_type", "exists", "account", "created_at")
    search_fields = ("path", "server__name", "account__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    list_display = ("title", "server", "account", "severity", "status", "updated_at")
    list_filter = ("status", "severity", "account", "created_at")
    search_fields = ("title", "fingerprint", "server__name", "account__name")
    readonly_fields = ("created_at", "updated_at")
    actions = ("rebuild_finding_groups_for_selected",)

    @admin.action(description="Rebuild finding groups for selected findings")
    def rebuild_finding_groups_for_selected(self, request, queryset):
        pairs = {(finding.account_id, finding.server_id) for finding in queryset.select_related("account", "server")}
        rebuilt = 0
        for account_id, server_id in pairs:
            finding = queryset.filter(account_id=account_id, server_id=server_id).select_related("account", "server").first()
            rebuilt += len(rebuild_finding_groups(account=finding.account, server=finding.server))
        self.message_user(request, f"Rebuilt {rebuilt} finding group(s).")
