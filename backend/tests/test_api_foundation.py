from unittest.mock import patch

import pytest
from django.db import DatabaseError
from django.test import override_settings
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView


@pytest.mark.django_db
def test_health_is_minimal_and_public():
    response = APIClient().get("/api/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-ID" in response


@pytest.mark.django_db
def test_readiness_uses_database():
    response = APIClient().get("/api/readiness/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_readiness_failure_is_safe():
    with patch("apps.core.views.connection.cursor", side_effect=DatabaseError("secret-host")):
        response = APIClient().get("/api/readiness/")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert b"secret-host" not in response.content


def test_invalid_request_id_is_replaced():
    response = APIClient().get("/api/health/", HTTP_X_REQUEST_ID="x" * 1000)
    assert response["X-Request-ID"] != "x" * 1000
    assert len(response["X-Request-ID"]) == 32


@pytest.mark.urls("tests.urls")
def test_validation_errors_have_consistent_shape():
    response = APIClient().get("/test/error/")
    assert response.status_code == 400
    assert response.json() == {
        "error": {"code": "validation_error", "detail": {"field": ["Invalid value."]}}
    }


@pytest.mark.urls("tests.urls")
@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_THROTTLE_RATES": {"test": "2/min"},
        "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    }
)
def test_representative_scoped_throttle():
    client = APIClient()
    assert client.get("/test/throttled/").status_code == 200
    assert client.get("/test/throttled/").status_code == 200
    response = client.get("/test/throttled/")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "throttled"


class ErrorView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        raise ValidationError({"field": ["Invalid value."]})


class ThrottledView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "test"

    def get(self, request):
        return Response({"status": "ok"})
