import logging
import re
import uuid
from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse

from .request_context import request_id_context

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
logger = logging.getLogger(__name__)


class RequestSizeLimitMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        raw_length = request.META.get("CONTENT_LENGTH")
        try:
            content_length = int(raw_length) if raw_length else 0
        except (TypeError, ValueError):
            content_length = 0
        if content_length > settings.REQUEST_MAX_BODY_SIZE:
            return JsonResponse(
                {
                    "error": {
                        "code": "request_too_large",
                        "detail": "The request body exceeds the configured limit.",
                    }
                },
                status=413,
            )
        return self.get_response(request)


class RequestIDMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        candidate = request.headers.get("X-Request-ID", "")
        request_id = candidate if REQUEST_ID_PATTERN.fullmatch(candidate) else uuid.uuid4().hex
        request.request_id = request_id
        token = request_id_context.set(request_id)
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = request_id
            logger.info(
                "Request completed",
                extra={
                    "event": "http.request_completed",
                    "http_method": request.method,
                    "http_path": request.path,
                    "status_code": response.status_code,
                },
            )
            return response
        finally:
            request_id_context.reset(token)
