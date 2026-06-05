from django.urls import path

from apps.diagnostics import views as diagnostic_views

from . import views


app_name = "portal"

urlpatterns = [
    path("login/", views.PortalLoginView.as_view(), name="login"),
    path("logout/", views.PortalLogoutView.as_view(), name="logout"),
    path("access-denied/", views.access_denied, name="access_denied"),
    path("", views.dashboard, name="dashboard"),
    path("servers/", views.servers_list, name="servers"),
    path("servers/add/", views.server_add, name="server_add"),
    path("servers/<int:server_id>/", views.server_detail, name="server_detail"),
    path("servers/<int:server_id>/registration-token/", views.registration_token, name="registration_token"),
    path("applications/", views.applications_list, name="applications"),
    path("applications/pending/", views.pending_applications, name="pending_applications"),
    path("applications/<int:application_id>/", views.application_detail, name="application_detail"),
    path("applications/<int:application_id>/<str:action>/", views.application_action, name="application_action"),
    path("findings/", views.findings_list, name="findings"),
    path("findings/<int:finding_id>/", views.finding_detail, name="finding_detail"),
    path("findings/<int:finding_id>/<str:action>/", views.finding_action, name="finding_action"),
    path("baseline-scans/", views.baseline_scans, name="baseline_scans"),
    path("subscription/", views.subscription_usage, name="subscription"),
    path("telegram/", views.telegram_settings, name="telegram"),
    path("diagnostics/", diagnostic_views.diagnostics_list, name="diagnostics"),
    path("diagnostics/start/", diagnostic_views.diagnostics_start, name="diagnostic_start"),
    path("diagnostics/<int:session_id>/", diagnostic_views.diagnostic_detail, name="diagnostic_detail"),
    path(
        "diagnostics/<int:session_id>/steps/<int:step_id>/approve/",
        diagnostic_views.diagnostic_step_approve,
        name="diagnostic_step_approve",
    ),
    path("reports/", views.reports_list, name="reports"),
    path("chat/", views.chat_sessions, name="chat_sessions"),
    path("chat/start/", views.chat_session_start, name="chat_session_start"),
    path("chat/<int:session_id>/", views.chat_session_detail, name="chat_session_detail"),
    path("reports/generate/", views.report_generate, name="report_generate"),
    path("reports/<int:report_id>/", views.report_detail, name="report_detail"),
    path("finding-groups/", views.finding_groups_list, name="finding_groups"),
    path("finding-groups/<int:group_id>/", views.finding_group_detail, name="finding_group_detail"),
]
