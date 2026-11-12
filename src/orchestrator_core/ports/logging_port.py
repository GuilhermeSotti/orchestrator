from __future__ import annotations

from typing import Any, Protocol


class LoggingPort(Protocol):
    """Contract for structured logging implementations."""

    def log(self, level: str, message: str, **metadata: Any) -> None:
        ...
