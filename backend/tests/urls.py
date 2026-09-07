from django.urls import path

from .test_api_foundation import ErrorView, ThrottledView

urlpatterns = [
    path("test/error/", ErrorView.as_view()),
    path("test/throttled/", ThrottledView.as_view()),
]
