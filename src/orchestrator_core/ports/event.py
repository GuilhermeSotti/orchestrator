from __future__ import annotations

from typing import Any, Protocol


class EventPort(Protocol):
    """Contract for publishing domain events."""

    def publish(self, event_name: str, payload: dict[str, Any]) -> None:
        ...
