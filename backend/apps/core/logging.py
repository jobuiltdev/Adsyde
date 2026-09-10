import json
import logging
from datetime import UTC, datetime

from .request_context import request_id_context


class RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        return True


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exception_type"] = record.exc_info[0].__name__
        for field in (
            "http_method",
            "http_path",
            "status_code",
            "outcome",
            "account_id",
            "project_id",
            "asset_id",
            "generation_id",
            "provider",
            "error_code",
            "prompt_length",
        ):
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        return json.dumps(payload, separators=(",", ":"))
