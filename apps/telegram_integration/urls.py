from django.urls import path

from . import views


app_name = "telegram_integration"

urlpatterns = [
    path("webhook/<str:secret>/", views.telegram_webhook, name="webhook"),
]
