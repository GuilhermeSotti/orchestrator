"""Time source abstraction, so that time-dependent behavior is testable."""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """Source of time used by the Runtime.

    Implementations must be thread-safe. :class:`orchestrator_core.testing.FakeClock`
    is a deterministic implementation for tests.
    """

    def monotonic(self) -> float:
        """Return a monotonic time in seconds, used for durations and deadlines."""
        ...

    def now(self) -> datetime:
        """Return the current wall-clock time as a timezone-aware UTC datetime."""
        ...

    def sleep(self, seconds: float) -> None:
        """Block for ``seconds``."""
        ...

    def wait(self, event: threading.Event, timeout: float) -> bool:
        """Block until ``event`` is set or ``timeout`` seconds elapse.

        Returns:
            Whether the event is set.
        """
        ...


class SystemClock:
    """Clock backed by the operating system."""

    def monotonic(self) -> float:
        """Return :func:`time.monotonic`."""
        return time.monotonic()

    def now(self) -> datetime:
        """Return the current UTC time."""
        return datetime.now(UTC)

    def sleep(self, seconds: float) -> None:
        """Block for ``seconds`` using :func:`time.sleep`."""
        time.sleep(max(0.0, seconds))

    def wait(self, event: threading.Event, timeout: float) -> bool:
        """Wait on ``event`` for at most ``timeout`` seconds."""
        return event.wait(max(0.0, timeout))
