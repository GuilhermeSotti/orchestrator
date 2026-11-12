"""Metrics port. The Core records a few metrics and ships no backend."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Final, Protocol, runtime_checkable

EXECUTIONS: Final = "orchestrator.executions"
"""Counter of finished executions. Tags: ``runtime``, ``automation``, ``status``."""

EXECUTION_DURATION: Final = "orchestrator.execution.duration_seconds"
"""Duration of executions. Tags: ``runtime``, ``automation``, ``status``."""

STAGE_DURATION: Final = "orchestrator.stage.duration_seconds"
"""Duration of stages. Tags: ``runtime``, ``stage``, ``status``."""

EVENT_HANDLER_ERRORS: Final = "orchestrator.event_handler.errors"
"""Counter of event handlers that raised. Tags: ``event``."""

RETRY_ATTEMPTS: Final = "orchestrator.retry.attempts"
"""Counter of retried attempts made through ``ExecutionContext.retry``. Tags: ``operation``."""

_logger = logging.getLogger("orchestrator_core.metrics")


@runtime_checkable
class MetricsRecorder(Protocol):
    """Port for metric backends (Prometheus, OpenTelemetry, StatsD...).

    Implementations live outside the Core, must be thread-safe and should not
    block. Errors they raise are logged and never interrupt an execution.
    """

    def increment(
        self, name: str, value: float = 1.0, *, tags: Mapping[str, str] | None = None
    ) -> None:
        """Add ``value`` to the counter ``name``."""
        ...

    def observe(self, name: str, value: float, *, tags: Mapping[str, str] | None = None) -> None:
        """Record one observation of ``value`` (for example, a duration in seconds)."""
        ...


class NoopMetrics:
    """Recorder that discards everything. Default of the Runtime."""

    def increment(
        self, name: str, value: float = 1.0, *, tags: Mapping[str, str] | None = None
    ) -> None:
        """Discard the increment."""

    def observe(self, name: str, value: float, *, tags: Mapping[str, str] | None = None) -> None:
        """Discard the observation."""


class SafeMetrics:
    """Wrapper that keeps metric failures from interrupting executions."""

    def __init__(self, recorder: MetricsRecorder) -> None:
        """Wrap ``recorder``."""
        self._recorder = recorder

    @property
    def wrapped(self) -> MetricsRecorder:
        """The wrapped recorder."""
        return self._recorder

    def increment(
        self, name: str, value: float = 1.0, *, tags: Mapping[str, str] | None = None
    ) -> None:
        """Forward to the recorder, logging failures."""
        try:
            self._recorder.increment(name, value, tags=tags)
        except Exception:
            _logger.warning("metrics recorder failed to increment %s", name, exc_info=True)

    def observe(self, name: str, value: float, *, tags: Mapping[str, str] | None = None) -> None:
        """Forward to the recorder, logging failures."""
        try:
            self._recorder.observe(name, value, tags=tags)
        except Exception:
            _logger.warning("metrics recorder failed to observe %s", name, exc_info=True)
