from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class DomainEvent:
    """Simple event payload used for runtime hooks."""

    name: str
    payload: dict[str, Any] = field(default_factory=dict)


class ExecutionStarted(DomainEvent):
    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        super().__init__(name="execution.started", payload=payload or {})


class ExecutionFinished(DomainEvent):
    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        super().__init__(name="execution.finished", payload=payload or {})


class EventBus:
    """Minimal in-process event bus for runtime subscribers."""

    def __init__(self) -> None:
        self._subscribers: list[Callable[[DomainEvent], None]] = []

    def subscribe(self, callback: Callable[[DomainEvent], None]) -> None:
        self._subscribers.append(callback)

    def publish(self, event: DomainEvent) -> None:
        for subscriber in self._subscribers:
            subscriber(event)
