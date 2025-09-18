from django.urls import path
from .views import HomePageView, DocumentationView

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path("documentation/", DocumentationView.as_view(), name="documentation"),
]