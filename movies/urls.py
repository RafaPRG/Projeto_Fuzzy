from django.urls import path

from .views import home

app_name = "movies"

urlpatterns = [
    path("", home, name="home"),
]
