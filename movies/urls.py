from django.urls import path

from .views import analysis_status, home, start_analysis

app_name = "movies"

urlpatterns = [
    path("", home, name="home"),
    path("analysis/start/", start_analysis, name="start-analysis"),
    path("analysis/status/<slug:job_id>/", analysis_status, name="analysis-status"),
]
