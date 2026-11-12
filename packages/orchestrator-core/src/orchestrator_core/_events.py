"""Lifecycle events and the in-process, synchronous event bus.

Guarantees of :class:`EventBus`:

* handlers run synchronously, in the thread that publishes, in subscription order;
* a handler receives every event that is an instance of the type it subscribed to;
* each event is delivered at most once per subscription and is never persisted;
* a handler that raises is logged and counted, and never interrupts the
  execution or the other handlers.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from orchestrator_core._metrics import EVENT_HANDLER_ERRORS, MetricsRecorder
from orchestrator_core._results import ErrorInfo, ExecutionStatus, Phase, StageStatus

_logger = logging.getLogger("orchestrator_core.events")


@dataclass(frozen=True, slots=True, kw_only=True)
class Event:
    """Base class of events. Subclass it to publish custom events.

    Attributes:
        execution_id: Execution that produced the event.
        timestamp: When the event was produced (UTC).
    """

    execution_id: str
    timestamp: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionStarted(Event):
    """Published by the ``initialize`` stage."""

    automation: str
    runtime: str


@dataclass(frozen=True, slots=True, kw_only=True)
class StageStarted(Event):
    """Published before each stage runs."""

    stage: str
    phase: Phase


@dataclass(frozen=True, slots=True, kw_only=True)
class StageFinished(Event):
    """Published after each stage runs, successfully or not."""

    stage: str
    phase: Phase
    status: StageStatus
    duration: float
    error: ErrorInfo | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionFinished(Event):
    """Published once the whole pipeline, teardown included, has finished."""

    automation: str
    runtime: str
    status: ExecutionStatus
    duration: float
    error: ErrorInfo | None = None


type EventHandler[E: Event] = Callable[[E], object]
"""Callable that receives events of type ``E``."""


class EventBus:
    """In-process, synchronous publisher of events. Thread-safe."""

    def __init__(self, metrics: MetricsRecorder) -> None:
        """Create a bus that counts handler failures in ``metrics``."""
        self._metrics = metrics
        self._lock = threading.Lock()
        self._subscriptions: tuple[tuple[type[Event], Callable[[Event], object]], ...] = ()

    def subscribe[E: Event](self, event_type: type[E], handler: EventHandler[E]) -> None:
        """Deliver every event that is an instance of ``event_type`` to ``handler``."""
        candidate: object = event_type
        if not (isinstance(candidate, type) and issubclass(candidate, Event)):
            msg = "event_type must be a subclass of Event"
            raise TypeError(msg)
        function: object = handler
        if not callable(function):
            msg = "handler must be callable"
            raise TypeError(msg)

        def deliver(event: Event) -> object:
            return handler(event)  # type: ignore[arg-type]

        deliver.__qualname__ = getattr(handler, "__qualname__", type(handler).__qualname__)
        with self._lock:
            self._subscriptions = (*self._subscriptions, (event_type, deliver))

    def publish(self, event: Event) -> None:
        """Deliver ``event`` to the matching handlers, isolating their failures."""
        for event_type, handler in self._subscriptions:
            if not isinstance(event, event_type):
                continue
            try:
                handler(event)
            except Exception:
                _logger.warning(
                    "event handler %s failed for %s",
                    handler.__qualname__,
                    type(event).__name__,
                    exc_info=True,
                )
                self._metrics.increment(EVENT_HANDLER_ERRORS, tags={"event": type(event).__name__})
