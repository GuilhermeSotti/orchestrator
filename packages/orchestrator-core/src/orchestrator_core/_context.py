"""Execution Context: what an execution can see and use."""

from __future__ import annotations

import logging
import random
from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from orchestrator_core import _correlation
from orchestrator_core._errors import (
    CapabilityError,
    ConfigurationError,
    ExecutionTimeoutError,
)
from orchestrator_core._metrics import RETRY_ATTEMPTS
from orchestrator_core._retry import RetryAttempt, RetryPolicy, retry

if TYPE_CHECKING:
    from orchestrator_core._cancellation import CancellationToken
    from orchestrator_core._capabilities import Capability, CapabilityRegistry
    from orchestrator_core._clock import Clock
    from orchestrator_core._config import Configuration
    from orchestrator_core._events import Event, EventBus
    from orchestrator_core._metrics import MetricsRecorder
    from orchestrator_core._redaction import Redactor
    from orchestrator_core._resources import ResourceScope
    from orchestrator_core._results import (
        ExecutionOutcome,
        ExecutionRecord,
        ExecutionRecordSink,
    )
    from orchestrator_core._secrets import SecretStore

AUTOMATION_LOGGER = "orchestrator.automation"
"""Name of the logger returned by :attr:`ExecutionContext.logger`."""

type Automation = Callable[[ExecutionContext], object]
"""An automation: business logic of the consumer project, called with the context."""

type Finalizer = Callable[[ExecutionOutcome], object]
"""Callback run by the ``finalize`` stage with the provisional outcome."""


class _ExecutionLogger(logging.LoggerAdapter[logging.Logger]):
    """Adds the correlation fields to records, even without the logging filters."""

    def __init__(self, logger: logging.Logger, execution_id: str, automation: str) -> None:
        super().__init__(logger, {"execution_id": execution_id, "automation": automation})

    def process(
        self, msg: object, kwargs: MutableMapping[str, Any]
    ) -> tuple[object, MutableMapping[str, Any]]:
        extra = dict(self.extra or {})
        extra["stage"] = _correlation.current().stage or "-"
        extra.update(kwargs.get("extra") or {})
        kwargs["extra"] = extra
        return msg, kwargs


@dataclass(slots=True)
class ExecutionState:
    """Mutable, internal state of one execution. Not part of the public API."""

    automation: Automation
    raw_parameters: Mapping[str, object]
    parameters_validator: Callable[[Mapping[str, object]], object] | None
    registry: CapabilityRegistry
    record_sinks: tuple[ExecutionRecordSink, ...]
    redactor: Redactor
    resources: ResourceScope
    parameters: object = None
    output: object = None
    workspace: Path | None = None
    outcome: ExecutionOutcome | None = None
    closed: bool = False
    record_builder: Callable[[], ExecutionRecord] | None = None
    handles: dict[str, object] = field(default_factory=dict)
    finalizers: list[Finalizer] = field(default_factory=list)


class ExecutionContext:
    """Context of one execution, passed to stages, Capabilities and the automation.

    Identity and services are read-only. The only mutable space is
    :attr:`state`, which belongs to the consumer project. A context is created
    for every execution and never shared between executions.

    Example:
        >>> def automation(ctx: ExecutionContext) -> int:  # doctest: +SKIP
        ...     ctx.logger.info("processing %s", ctx.parameters["day"])
        ...     ctx.check()  # cooperate with cancellation and timeout
        ...     return 42
    """

    __slots__ = (
        "_automation_name",
        "_cancellation",
        "_clock",
        "_config",
        "_deadline",
        "_events",
        "_execution_id",
        "_internal",
        "_logger",
        "_metrics",
        "_rng",
        "_runtime_name",
        "_secrets",
        "_started_at",
        "_timeout",
        "_user_state",
    )

    def __init__(
        self,
        *,
        execution_id: str,
        automation_name: str,
        runtime_name: str,
        started_at: datetime,
        config: Configuration,
        events: EventBus,
        metrics: MetricsRecorder,
        secrets: SecretStore,
        cancellation: CancellationToken,
        clock: Clock,
        timeout: float | None,
        deadline: float | None,
        internal: ExecutionState,
    ) -> None:
        """Create a context. Only the Runtime creates contexts."""
        self._execution_id = execution_id
        self._automation_name = automation_name
        self._runtime_name = runtime_name
        self._started_at = started_at
        self._config = config
        self._events = events
        self._metrics = metrics
        self._secrets = secrets
        self._cancellation = cancellation
        self._clock = clock
        self._timeout = timeout
        self._deadline = deadline
        self._internal = internal
        self._logger = _ExecutionLogger(
            logging.getLogger(AUTOMATION_LOGGER), execution_id, automation_name
        )
        self._user_state: dict[str, object] = {}
        self._rng = random.Random()  # noqa: S311 - retry jitter, not cryptography

    # Identity ---------------------------------------------------------------

    @property
    def execution_id(self) -> str:
        """Unique identifier of the execution."""
        return self._execution_id

    @property
    def automation(self) -> str:
        """Name of the automation being executed."""
        return self._automation_name

    @property
    def runtime(self) -> str:
        """Name of the Runtime."""
        return self._runtime_name

    @property
    def started_at(self) -> datetime:
        """Start time of the execution (UTC)."""
        return self._started_at

    # Services ---------------------------------------------------------------

    @property
    def config(self) -> Configuration:
        """Read-only configuration of the Runtime."""
        return self._config

    @property
    def logger(self) -> logging.LoggerAdapter[logging.Logger]:
        """Logger whose records carry ``execution_id``, ``automation`` and ``stage``."""
        return self._logger

    @property
    def metrics(self) -> MetricsRecorder:
        """Metrics recorder of the Runtime."""
        return self._metrics

    @property
    def secrets(self) -> SecretStore:
        """Resolves secret references, e.g. ``ctx.secrets.resolve("env:API_TOKEN")``."""
        return self._secrets

    @property
    def cancellation(self) -> CancellationToken:
        """Cancellation token of the execution."""
        return self._cancellation

    @property
    def resources(self) -> ResourceScope:
        """Cleanups released in reverse order by the ``finalize`` stage."""
        return self._internal.resources

    @property
    def state(self) -> dict[str, object]:
        """Mutable space owned by the consumer project (not thread-safe)."""
        return self._user_state

    @property
    def parameters(self) -> object:
        """Parameters of the execution.

        A read-only mapping, or the value returned by the parameters validator
        after the ``prepare_execution`` stage.
        """
        return self._internal.parameters

    def parameters_as[T](self, kind: type[T]) -> T:
        """Return :attr:`parameters`, checked to be an instance of ``kind``.

        Raises:
            TypeError: If the parameters are of another type.
        """
        value = self._internal.parameters
        if not isinstance(value, kind):
            msg = f"parameters are {type(value).__name__}, not {kind.__name__}"
            raise TypeError(msg)
        return value

    @property
    def workspace(self) -> Path:
        """Private temporary directory of the execution.

        Raises:
            ConfigurationError: If ``runtime.workspace`` is not enabled or the
                ``prepare_environment`` stage has not run yet.
        """
        if self._internal.workspace is None:
            msg = "the execution workspace is not available; set runtime.workspace = true"
            raise ConfigurationError(msg, key="runtime.workspace")
        return self._internal.workspace

    @property
    def outcome(self) -> ExecutionOutcome | None:
        """Provisional outcome, available to teardown stages; ``None`` before."""
        return self._internal.outcome

    @property
    def timeout(self) -> float | None:
        """Timeout of the execution in seconds, if any."""
        return self._timeout

    # Capabilities -------------------------------------------------------------

    def capability[H](self, key: type[Capability[H]], name: str | None = None) -> H:
        """Return the handle of a registered Capability for this execution.

        Args:
            key: Capability class (or base class) to look for.
            name: Registration name, required when several match ``key``.

        Raises:
            CapabilityNotFoundError: If no matching Capability is registered.
            CapabilityError: If the handle is not available (before the
                ``provision_dependencies`` stage, or after ``shutdown``).
        """
        if self._internal.closed:
            msg = "the execution context is closed"
            raise CapabilityError(msg)
        registration = self._internal.registry.find(key, name)
        try:
            handle = self._internal.handles[registration.name]
        except KeyError:
            msg = f"capability {registration.name!r} has not been provisioned yet"
            raise CapabilityError(msg) from None
        return handle  # type: ignore[return-value]

    # Time, cancellation and retry ---------------------------------------------

    def remaining(self) -> float | None:
        """Seconds left before the deadline, or ``None`` without timeout."""
        if self._deadline is None:
            return None
        return max(0.0, self._deadline - self._clock.monotonic())

    def deadline_exceeded(self) -> bool:
        """Whether the deadline has passed."""
        return self._deadline is not None and self._clock.monotonic() >= self._deadline

    def check(self) -> None:
        """Raise if the execution was cancelled or its deadline has passed.

        Raises:
            ExecutionCancelledError: If cancellation was requested.
            ExecutionTimeoutError: If the deadline has passed.
        """
        self._cancellation.raise_if_cancelled()
        if self.deadline_exceeded():
            msg = f"execution exceeded its timeout of {self._timeout}s"
            raise ExecutionTimeoutError(msg)

    def sleep(self, seconds: float) -> None:
        """Wait ``seconds``, waking up early on cancellation.

        Raises:
            ExecutionCancelledError: If cancelled before or while waiting.
            ExecutionTimeoutError: If the deadline passes before or while waiting.
        """
        self.check()
        remaining = self.remaining()
        duration = seconds if remaining is None else min(seconds, remaining)
        self._clock.wait(self._cancellation.event, max(0.0, duration))
        self.check()

    def retry[T](
        self,
        operation: Callable[[], T],
        policy: RetryPolicy,
        *,
        name: str = "operation",
    ) -> T:
        """Run ``operation`` with ``policy``, honoring cancellation and the deadline.

        Each retry is logged as a warning and counted in the
        ``orchestrator.retry.attempts`` metric.

        Args:
            operation: Callable without arguments.
            policy: Retry policy; nothing is retried by default.
            name: Name of the operation, used in logs and metric tags.
        """

        def on_retry(attempt: RetryAttempt) -> None:
            self._logger.warning(
                "%s failed on attempt %d (%s); retrying in %.2fs",
                name,
                attempt.attempt,
                type(attempt.error).__name__,
                attempt.delay,
            )
            self._metrics.increment(RETRY_ATTEMPTS, tags={"operation": name})

        return retry(
            operation,
            policy,
            clock=self._clock,
            sleep=self.sleep,
            rng=self._rng,
            before_attempt=self.check,
            on_retry=on_retry,
        )

    # Events and finalization ---------------------------------------------------

    def publish(self, event: Event) -> None:
        """Publish ``event`` to the handlers registered in the Runtime."""
        self._events.publish(event)

    def now(self) -> datetime:
        """Return the current UTC time from the Runtime clock."""
        return self._clock.now()

    def add_finalizer(self, finalizer: Finalizer) -> None:
        """Run ``finalizer(outcome)`` in the ``finalize`` stage, before resources are released.

        Finalizers run in reverse order of registration and receive the
        provisional :class:`ExecutionOutcome` (for example, to commit or roll back).

        Raises:
            CapabilityError: If the context is already closed.
        """
        if self._internal.closed:
            msg = "the execution context is closed"
            raise CapabilityError(msg)
        self._internal.finalizers.append(finalizer)

    def __repr__(self) -> str:
        """Return the identity of the execution."""
        return (
            f"ExecutionContext(execution_id={self._execution_id!r}, "
            f"automation={self._automation_name!r}, runtime={self._runtime_name!r})"
        )


def internal_state(ctx: ExecutionContext) -> ExecutionState:
    """Return the internal state of ``ctx`` (for the Runtime and built-in stages)."""
    return ctx._internal  # noqa: SLF001 - single sanctioned access to internals
