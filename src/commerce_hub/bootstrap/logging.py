"""Allowlisted structured events: raw messages, arguments and tracebacks are never formatted."""
from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import re
import sys

trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
EVENTS = {"application_started", "application_stopped", "request_completed", "request_failed", "database_unavailable"}


class SafeJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = getattr(record, "event", None)
        data = {"time": datetime.now(timezone.utc).isoformat(), "level": record.levelname,
                "moduleId": "BOOTSTRAP", "event": event if event in EVENTS else "redacted_event"}
        current = trace_id.get()
        if current and re.fullmatch(r"[a-f0-9]{32}", current):
            data["traceId"] = current
        status = getattr(record, "status_code", None)
        if isinstance(status, int) and 100 <= status <= 599:
            data["status"] = status
        return json.dumps(data, separators=(",", ":"))


def configure_logger(level: str) -> logging.Logger:
    logger = logging.getLogger("commerce_hub")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(SafeJsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger
