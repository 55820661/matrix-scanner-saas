"""URL configuration for Matrix Scanner SaaS."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/agent/", include("apps.servers.urls")),
]
