import logging

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc: Exception, context: dict) -> Response:
    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled API exception", extra={"event": "api.unhandled_exception"})
        return Response(
            {"error": {"code": "internal_error", "detail": "An unexpected error occurred."}},
            status=500,
        )
    code = (
        "validation_error"
        if isinstance(exc, ValidationError)
        else getattr(exc, "default_code", "api_error")
    )
    return Response({"error": {"code": code, "detail": response.data}}, status=response.status_code)
