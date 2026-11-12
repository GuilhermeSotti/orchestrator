"""Execution-scoped resources, released in reverse order during ``finalize``."""

from __future__ import annotations

import threading
from collections.abc import Callable
from contextlib import AbstractContextManager


class ResourceScope:
    """Stack of cleanups owned by one execution.

    Capabilities and automations register what they acquire; the ``finalize``
    stage releases everything in reverse order of registration. A failing
    cleanup does not prevent the others from running. Thread-safe.

    Example:
        >>> scope = ResourceScope()
        >>> released = []
        >>> scope.callback(released.append, "first")
        >>> scope.callback(released.append, "second")
        >>> scope.close()
        []
        >>> released
        ['second', 'first']
    """

    def __init__(self) -> None:
        """Create an open, empty scope."""
        self._lock = threading.Lock()
        self._cleanups: list[Callable[[], object]] = []
        self._closed = False

    @property
    def closed(self) -> bool:
        """Whether :meth:`close` was called."""
        return self._closed

    def __len__(self) -> int:
        """Return the number of pending cleanups."""
        return len(self._cleanups)

    def enter[T](self, manager: AbstractContextManager[T]) -> T:
        """Enter ``manager`` now and exit it when the scope closes.

        Returns:
            The value returned by ``manager.__enter__``.

        Raises:
            RuntimeError: If the scope is already closed.
        """
        self._ensure_open()
        value = manager.__enter__()
        self._push(lambda: manager.__exit__(None, None, None))
        return value

    def callback[**P](
        self, function: Callable[P, object], /, *args: P.args, **kwargs: P.kwargs
    ) -> None:
        """Call ``function(*args, **kwargs)`` when the scope closes.

        Raises:
            RuntimeError: If the scope is already closed.
        """
        self._push(lambda: function(*args, **kwargs))

    def close(self) -> list[BaseException]:
        """Run every cleanup in reverse order. Idempotent.

        Returns:
            The exceptions raised by cleanups, in the order they occurred.
        """
        with self._lock:
            cleanups, self._cleanups = self._cleanups, []
            self._closed = True
        errors: list[BaseException] = []
        for cleanup in reversed(cleanups):
            try:
                cleanup()
            except BaseException as exc:  # noqa: BLE001 - every cleanup must run
                errors.append(exc)
        return errors

    def _push(self, cleanup: Callable[[], object]) -> None:
        with self._lock:
            self._ensure_open()
            self._cleanups.append(cleanup)

    def _ensure_open(self) -> None:
        if self._closed:
            msg = "the resource scope of this execution is already closed"
            raise RuntimeError(msg)
