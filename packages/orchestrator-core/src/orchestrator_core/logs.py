"""Logging helpers: correlation, masking of secrets and structured output.

The Core logs through the standard :mod:`logging` module and never configures
logging by itself. Applications call :func:`configure_logging` in their entry
point, or add :class:`ExecutionContextFilter` and :class:`RedactingFilter` to
their own handlers.

Example:
    >>> import io, logging
    >>> stream = io.StringIO()
    >>> handler = configure_logging("INFO", stream=stream, logger="doctest")
    >>> logging.getLogger("doctest").info("hello")
    >>> "hello" in stream.getvalue()
    True
    >>> logging.getLogger("doctest").removeHandler(handler)
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Final, TextIO

from orchestrator_core import _correlation
from orchestrator_core._redaction import Redactor, default_redactor

__all__ = [
    "TEXT_FORMAT",
    "ExecutionContextFilter",
    "JsonFormatter",
    "RedactingFilter",
    "configure_logging",
]

TEXT_FORMAT: Final = (
    "%(asctime)s %(levelname)-8s [%(execution_id)s|%(stage)s] %(name)s: %(message)s"
)
"""Format used by :func:`configure_logging` for text output."""

_FIELDS: Final = ("execution_id", "automation", "stage")
_MARKER: Final = "_orchestrator_handler"


class ExecutionContextFilter(logging.Filter):
    """Adds ``execution_id``, ``automation`` and ``stage`` to every record.

    Values come from the execution running in the current thread or task, and
    are ``"-"`` outside executions. Attributes already set are kept.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Annotate ``record``; never drops it."""
        correlation = _correlation.current()
        for name, value in zip(_FIELDS, correlation, strict=True):
            if not hasattr(record, name):
                setattr(record, name, value or "-")
        return True


class RedactingFilter(logging.Filter):
    """Masks registered secret values in messages, tracebacks and stack traces.

    Secrets resolved through the Runtime are registered automatically.
    """

    def __init__(self, redactor: Redactor | None = None) -> None:
        """Create the filter.

        Args:
            redactor: Registry of sensitive values (default: process-wide registry).
        """
        super().__init__()
        self._redactor = redactor or default_redactor

    def filter(self, record: logging.LogRecord) -> bool:
        """Mask ``record`` in place; never drops it."""
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 - malformed records are left to the handler
            return True
        masked = self._redactor.redact(message)
        if masked != message:
            record.msg = masked
            record.args = None
        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(record.exc_info)
        if record.exc_text:
            record.exc_text = self._redactor.redact(record.exc_text)
        if record.stack_info:
            record.stack_info = self._redactor.redact(record.stack_info)
        return True


class JsonFormatter(logging.Formatter):
    """Formats records as one JSON object per line.

    Keys: ``timestamp`` (UTC, ISO 8601), ``level``, ``logger``, ``message``,
    ``execution_id``, ``automation``, ``stage`` and, when present, ``exception``.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Return the JSON line for ``record``."""
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for name in _FIELDS:
            payload[name] = getattr(record, name, "-")
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            payload["exception"] = record.exc_text
        if record.stack_info:
            payload["stack"] = record.stack_info
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(
    level: int | str = "INFO",
    *,
    json_output: bool = False,
    stream: TextIO | None = None,
    logger: str | None = None,
) -> logging.Handler:
    """Install a stream handler with correlation and masking. Idempotent.

    A handler previously installed by this function on the same logger is
    replaced.

    Args:
        level: Level of the configured logger.
        json_output: Emit JSON lines instead of text.
        stream: Destination stream (default: ``sys.stderr``).
        logger: Logger to configure (default: the root logger).

    Returns:
        The installed handler.
    """
    target = logging.getLogger(logger)
    for existing in list(target.handlers):
        if getattr(existing, _MARKER, False):
            target.removeHandler(existing)
            existing.close()
    handler = logging.StreamHandler(stream)
    setattr(handler, _MARKER, True)
    handler.addFilter(ExecutionContextFilter())
    handler.addFilter(RedactingFilter())
    handler.setFormatter(JsonFormatter() if json_output else logging.Formatter(TEXT_FORMAT))
    target.addHandler(handler)
    target.setLevel(level)
    return handler
