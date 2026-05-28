"""URL configuration for Matrix Scanner SaaS."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/agent/", include("apps.servers.urls")),
    path("telegram/", include("apps.telegram_integration.urls")),
    path("portal/", include("apps.portal.urls")),
]

admin.site.site_header = "Matrix Scanner Admin"
admin.site.site_title = "Matrix Scanner Admin"
admin.site.index_title = "Matrix Scanner Operations"
