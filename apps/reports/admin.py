from django.contrib import admin, messages

from .models import FindingGroup, KnowledgeEntry, KnowledgeSource, Recommendation, Report, ReportSection
from .services import rebuild_finding_groups


class ReportSectionInline(admin.TabularInline):
    model = ReportSection
    extra = 0
    fields = ("order", "section_type", "title", "body_redacted")
    readonly_fields = ("body_redacted",)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("title", "account", "server", "report_type", "status", "generated_at", "generated_by")
    list_filter = ("report_type", "status", "account", "generated_at")
    search_fields = ("title", "account__name", "server__name", "summary_redacted")
    readonly_fields = ("summary_redacted", "source_snapshot_redacted", "generated_at", "created_at", "updated_at")
    inlines = [ReportSectionInline]
    actions = ("archive_reports",)

    @admin.action(description="Archive selected reports")
    def archive_reports(self, request, queryset):
        updated = queryset.update(status=Report.Status.ARCHIVED)
        self.message_user(request, f"Archived {updated} report(s).")


@admin.register(ReportSection)
class ReportSectionAdmin(admin.ModelAdmin):
    list_display = ("report", "section_type", "title", "order", "created_at")
    list_filter = ("section_type", "created_at")
    search_fields = ("report__title", "title", "body_redacted")
    readonly_fields = ("body_redacted", "data_redacted", "created_at", "updated_at")


@admin.register(FindingGroup)
class FindingGroupAdmin(admin.ModelAdmin):
    list_display = ("title", "server", "account", "severity", "status", "occurrence_count", "last_seen_at")
    list_filter = ("severity", "status", "account", "server")
    search_fields = ("title", "fingerprint", "normalized_fingerprint", "server__name", "account__name")
    readonly_fields = ("summary_redacted", "created_at", "updated_at")
    actions = ("rebuild_groups_for_selected_accounts",)

    @admin.action(description="Rebuild finding groups for selected accounts")
    def rebuild_groups_for_selected_accounts(self, request, queryset):
        account_ids = set(queryset.values_list("account_id", flat=True))
        rebuilt = 0
        for account_id in account_ids:
            sample = queryset.filter(account_id=account_id).first()
            rebuilt += len(rebuild_finding_groups(account=sample.account))
        self.message_user(request, f"Rebuilt {rebuilt} finding group(s).", level=messages.SUCCESS)


class KnowledgeSourceInline(admin.TabularInline):
    model = KnowledgeSource
    extra = 0
    fields = ("source_type", "source_id", "title_redacted", "summary_redacted")


@admin.register(KnowledgeEntry)
class KnowledgeEntryAdmin(admin.ModelAdmin):
    list_display = ("title", "scope", "account", "server", "application", "status", "visibility", "updated_at")
    list_filter = ("scope", "status", "visibility", "account")
    search_fields = ("title", "body_redacted", "account__name", "server__name", "application__name")
    readonly_fields = ("created_at", "updated_at")
    inlines = [KnowledgeSourceInline]


@admin.register(KnowledgeSource)
class KnowledgeSourceAdmin(admin.ModelAdmin):
    list_display = ("entry", "source_type", "source_id", "created_at")
    list_filter = ("source_type", "created_at")
    search_fields = ("entry__title", "title_redacted", "summary_redacted")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ("title", "account", "server", "application", "priority", "status", "created_at")
    list_filter = ("priority", "status", "account", "created_at")
    search_fields = ("title", "body_redacted", "account__name", "server__name", "application__name")
    readonly_fields = ("body_redacted", "created_at", "updated_at")
