"""Structured logging system for ChangeBlast.

Provides deterministic, machine-readable JSON logging and standard console
logging with contextual fields.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class JsonLogFormatter(logging.Formatter):
    """Formatter that outputs structured JSON log records."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include custom extra attributes if present
        if hasattr(record, "context") and isinstance(record.context, dict):
            log_payload["context"] = record.context

        if record.exc_info and record.exc_text:
            log_payload["exception"] = record.exc_text

        return json.dumps(log_payload)


class ConsoleLogFormatter(logging.Formatter):
    """Formatter that outputs clean, human-readable terminal log lines."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).strftime("%H:%M:%S")
        prefix = f"[{timestamp}] [{record.levelname}]"
        context_str = ""
        if hasattr(record, "context") and isinstance(record.context, dict):
            context_str = f" | {record.context}"
        return f"{prefix} {record.getMessage()}{context_str}"


def setup_logging(
    level: int = logging.INFO,
    json_format: bool = False,
    stream: Any = None,
) -> logging.Logger:
    """Configure and return the root ChangeBlast logger.

    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO).
        json_format: Whether to output logs formatted as structured JSON lines.
        stream: Target output stream (defaults to sys.stderr).

    Returns:
        Configured ChangeBlast Logger instance.
    """
    logger = logging.getLogger("changeblast")
    logger.setLevel(level)
    logger.handlers.clear()

    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setLevel(level)

    if json_format:
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(ConsoleLogFormatter())

    logger.addHandler(handler)
    logger.propagate = False
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Retrieve a child logger under the ChangeBlast namespace."""
    if not name:
        return logging.getLogger("changeblast")
    return logging.getLogger(f"changeblast.{name}")
