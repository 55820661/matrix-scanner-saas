from django.urls import path

from . import views

app_name = "agent"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("heartbeat/", views.heartbeat, name="heartbeat"),
    path("jobs/next/", views.next_job, name="next-job"),
    path("jobs/<int:job_id>/result/", views.job_result, name="job-result"),
]
