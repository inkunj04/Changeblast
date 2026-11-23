"""Unit tests for ChangeBlast structured logging."""

from __future__ import annotations

import io
import json
import logging

from changeblast.logging import (
    ConsoleLogFormatter,
    JsonLogFormatter,
    get_logger,
    setup_logging,
)


class TestLogging:
    """Validate log formatting, log levels, and structured output."""

    def test_console_log_formatter(self) -> None:
        formatter = ConsoleLogFormatter()
        record = logging.LogRecord(
            name="changeblast.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Analysis completed successfully",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert "[INFO]" in formatted
        assert "Analysis completed successfully" in formatted

    def test_json_log_formatter(self) -> None:
        formatter = JsonLogFormatter()
        record = logging.LogRecord(
            name="changeblast.test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=25,
            msg="Unresolved symbol encountered",
            args=(),
            exc_info=None,
        )
        record.__dict__["context"] = {"symbol_id": "com.example.Unknown"}

        formatted = formatter.format(record)
        data = json.loads(formatted)
        assert data["level"] == "WARNING"
        assert data["message"] == "Unresolved symbol encountered"
        assert data["context"]["symbol_id"] == "com.example.Unknown"
        assert "timestamp" in data

    def test_setup_logging_and_get_logger(self) -> None:
        stream = io.StringIO()
        logger = setup_logging(level=logging.DEBUG, json_format=True, stream=stream)
        assert logger.level == logging.DEBUG

        child = get_logger("unit_test")
        assert child.name == "changeblast.unit_test"

        child.info("Hello structured log")
        output = stream.getvalue().strip()
        assert output != ""
        parsed = json.loads(output)
        assert parsed["message"] == "Hello structured log"
