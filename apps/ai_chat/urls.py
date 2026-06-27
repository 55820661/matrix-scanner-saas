from django.urls import path

from . import views


app_name = "admin_chat"


urlpatterns = [
    path("", views.internal_chat_sessions, name="sessions"),
    path("start/", views.internal_chat_session_start, name="session_start"),
    path("<int:session_id>/", views.internal_chat_session_detail, name="session_detail"),
    path("<int:session_id>/live/", views.internal_chat_live, name="session_live"),
    path("<int:session_id>/live/bundle-status/", views.internal_chat_bundle_status, name="bundle_status"),
    path("<int:session_id>/tools/request/", views.internal_chat_tool_request_create, name="tool_request_create"),
    path("<int:session_id>/tools/<int:request_id>/approve/", views.internal_chat_tool_request_approve, name="tool_request_approve"),
    path("<int:session_id>/tools/<int:request_id>/reject/", views.internal_chat_tool_request_reject, name="tool_request_reject"),
    path("<int:session_id>/tool-builder/create/", views.internal_chat_tool_build_create, name="tool_build_create"),
    path("<int:session_id>/reports/create/", views.internal_chat_report_create, name="report_create"),
    path("<int:session_id>/reports/draft/", views.internal_chat_report_draft_create, name="report_draft_create"),
]
