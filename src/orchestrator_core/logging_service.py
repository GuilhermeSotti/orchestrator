from __future__ import annotations

from typing import Any

from .ports.event import EventPort


class LoggingService:
    """Structured logging service that optionally publishes events."""

    def __init__(self, event_port: EventPort | None = None) -> None:
        self.event_port = event_port

    def info(self, message: str, **fields: Any) -> None:
        self._emit("info", message, fields)

    def error(self, message: str, **fields: Any) -> None:
        self._emit("error", message, fields)

    def _emit(self, level: str, message: str, fields: dict[str, Any]) -> None:
        if self.event_port is not None:
            self.event_port.publish("log", {"level": level, "message": message, **fields})
