"""Cooperative cancellation."""

from __future__ import annotations

import threading

from orchestrator_core._errors import ExecutionCancelledError


class CancellationToken:
    """Thread-safe, one-way cancellation signal shared by a caller and an execution.

    Cancellation is cooperative: the Runtime checks the token before every
    preparation and execution stage, and automations or Capabilities check it
    through :meth:`ExecutionContext.check`. Teardown stages always run.

    Example:
        >>> token = CancellationToken()
        >>> token.cancel("operator request")
        >>> token.is_cancelled
        True
    """

    __slots__ = ("_event", "_lock", "_reason")

    def __init__(self) -> None:
        """Create a token that is not cancelled."""
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._reason: str | None = None

    @property
    def is_cancelled(self) -> bool:
        """Whether :meth:`cancel` was called."""
        return self._event.is_set()

    @property
    def reason(self) -> str | None:
        """Reason given to the first :meth:`cancel` call, if any."""
        return self._reason

    @property
    def event(self) -> threading.Event:
        """Event set on cancellation, for interruptible waits."""
        return self._event

    def cancel(self, reason: str = "cancellation requested") -> None:
        """Request cancellation. Later calls keep the first reason.

        Args:
            reason: Human-readable reason, logged and reported. No secrets.
        """
        with self._lock:
            if not self._event.is_set():
                self._reason = reason
                self._event.set()

    def raise_if_cancelled(self) -> None:
        """Raise :class:`ExecutionCancelledError` if cancellation was requested."""
        if self._event.is_set():
            raise ExecutionCancelledError(self._reason or "cancellation requested")

    def wait(self, timeout: float | None = None) -> bool:
        """Block until cancellation is requested or ``timeout`` elapses.

        Returns:
            Whether cancellation was requested.
        """
        return self._event.wait(timeout)

    def __repr__(self) -> str:
        """Return a concise representation."""
        state = f"cancelled, reason={self._reason!r}" if self.is_cancelled else "active"
        return f"CancellationToken({state})"
