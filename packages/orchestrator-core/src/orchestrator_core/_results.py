"""Statuses, outcomes, records and results of executions."""

from __future__ import annotations

import builtins
import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable

from orchestrator_core._errors import (
    ExecutionCancelledError,
    ExecutionFailedError,
    ExecutionTimeoutError,
)
from orchestrator_core._redaction import Redactor

_MAX_MESSAGE = 2000
_UNPRINTABLE = "<exception str() failed>"


class Phase(enum.StrEnum):
    """Phase of a pipeline stage.

    Preparation stages run in order until one fails; the execution phase runs
    only if every preparation stage succeeded; teardown stages always run.
    """

    PREPARE = "prepare"
    EXECUTE = "execute"
    TEARDOWN = "teardown"


class ExecutionStatus(enum.StrEnum):
    """Final status of an execution."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class StageStatus(enum.StrEnum):
    """Outcome of a single stage."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    SKIPPED = "skipped"


def status_for_error(error: BaseException | None) -> ExecutionStatus:
    """Map the primary error of an execution to its status."""
    if error is None:
        return ExecutionStatus.SUCCEEDED
    if isinstance(error, ExecutionCancelledError | KeyboardInterrupt):
        return ExecutionStatus.CANCELLED
    if isinstance(error, ExecutionTimeoutError):
        return ExecutionStatus.TIMED_OUT
    return ExecutionStatus.FAILED


def stage_status_for_error(error: BaseException) -> StageStatus:
    """Map the error raised by a stage to the stage status."""
    return StageStatus(status_for_error(error).value)


@dataclass(frozen=True, slots=True)
class ErrorInfo:
    """Serializable description of an error, with sensitive values masked.

    Attributes:
        type: Qualified name of the exception class.
        message: Exception message, masked and truncated to 2000 characters;
            ``<exception str() failed>`` when the exception cannot be converted
            to text.
    """

    type: str
    message: str

    @classmethod
    def from_exception(cls, error: BaseException, redactor: Redactor) -> ErrorInfo:
        """Describe ``error`` without exposing registered secrets."""
        kind = type(error)
        module = kind.__module__
        name = kind.__qualname__ if module == builtins.__name__ else f"{module}.{kind.__qualname__}"
        try:
            text = str(error)
        except Exception:  # noqa: BLE001 - a broken __str__ must never break the pipeline
            text = _UNPRINTABLE
        message = redactor.redact(text)
        if len(message) > _MAX_MESSAGE:
            message = message[:_MAX_MESSAGE] + "…"
        return cls(type=name, message=message)

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-compatible dictionary."""
        return {"type": self.type, "message": self.message}


@dataclass(frozen=True, slots=True)
class StageOutcome:
    """What happened to one stage of an execution.

    Attributes:
        name: Stage name.
        phase: Stage phase.
        status: Stage status.
        duration: Seconds spent in the stage (zero if it did not run).
        error: Exception raised by the stage, if any (not part of ``repr``).
    """

    name: str
    phase: Phase
    status: StageStatus
    duration: float = 0.0
    error: BaseException | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class StageRecord:
    """Serializable, masked counterpart of :class:`StageOutcome`."""

    name: str
    phase: Phase
    status: StageStatus
    duration: float
    error: ErrorInfo | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible dictionary."""
        return {
            "name": self.name,
            "phase": self.phase.value,
            "status": self.status.value,
            "duration": self.duration,
            "error": None if self.error is None else self.error.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class StepOutcome:
    """What happened to one step of an execution (see :meth:`ExecutionContext.step`).

    Attributes:
        index: Position of the step in start order within the execution (1-based).
            Names may repeat; indexes do not.
        name: Step name.
        parent: Index of the step that contains this one, or ``None`` at the top level.
        stage: Pipeline stage that was running when the step started.
        status: Step status, mapped from its error like the execution status.
        started_at: Start time (UTC).
        duration: Seconds spent in the step.
        error: Exception that left the step, if any (not part of ``repr``).
    """

    index: int
    name: str
    parent: int | None
    stage: str
    status: ExecutionStatus
    started_at: datetime
    duration: float
    error: BaseException | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class StepRecord:
    """Serializable, masked counterpart of :class:`StepOutcome`."""

    index: int
    name: str
    parent: int | None
    stage: str
    status: ExecutionStatus
    started_at: datetime
    duration: float
    error: ErrorInfo | None = None

    @classmethod
    def from_outcome(cls, outcome: StepOutcome, redactor: Redactor) -> StepRecord:
        """Describe ``outcome`` without exposing registered secrets."""
        return cls(
            index=outcome.index,
            name=outcome.name,
            parent=outcome.parent,
            stage=outcome.stage,
            status=outcome.status,
            started_at=outcome.started_at,
            duration=outcome.duration,
            error=None
            if outcome.error is None
            else ErrorInfo.from_exception(outcome.error, redactor),
        )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible dictionary."""
        return {
            "index": self.index,
            "name": self.name,
            "parent": self.parent,
            "stage": self.stage,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "duration": self.duration,
            "error": None if self.error is None else self.error.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class ExecutionOutcome:
    """Provisional outcome of an execution, visible to teardown stages and finalizers.

    Example::

        def notify(outcome: ExecutionOutcome) -> None:
            if outcome.error_info is not None:  # already masked
                send(f"{outcome.error_info.type}: {outcome.error_info.message}")

    Attributes:
        status: Status the execution has so far.
        error: Primary error (or first teardown error), if any. The raw
            exception may carry secret values: never send ``str(error)`` out
            of the process; use :attr:`error_info` or
            :meth:`ExecutionContext.redact`.
        error_info: Masked description of :attr:`error`, if any.
    """

    status: ExecutionStatus
    error: BaseException | None = field(default=None, repr=False)
    error_info: ErrorInfo | None = None

    @property
    def succeeded(self) -> bool:
        """Whether the status is ``succeeded``."""
        return self.status is ExecutionStatus.SUCCEEDED


@dataclass(frozen=True, slots=True)
class ExecutionRecord:
    """Serializable, masked summary of an execution, delivered to record sinks.

    Attributes:
        execution_id: Unique execution identifier.
        automation: Name of the automation.
        runtime: Name of the Runtime.
        status: Status at the time the record was produced.
        started_at: Start time (UTC).
        finished_at: Time the record was produced (UTC).
        duration: Seconds between start and the production of the record.
        stages: Stage records, in execution order.
        error: Primary error, if any.
        teardown_errors: Errors raised by teardown stages.
        steps: Records of the steps finished so far, in start order.
        steps_truncated: Whether steps were left out because the execution
            started more than ``runtime.max_steps`` steps.
    """

    execution_id: str
    automation: str
    runtime: str
    status: ExecutionStatus
    started_at: datetime
    finished_at: datetime
    duration: float
    stages: tuple[StageRecord, ...]
    error: ErrorInfo | None = None
    teardown_errors: tuple[ErrorInfo, ...] = ()
    steps: tuple[StepRecord, ...] = ()
    steps_truncated: bool = False

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible dictionary."""
        return {
            "execution_id": self.execution_id,
            "automation": self.automation,
            "runtime": self.runtime,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "duration": self.duration,
            "stages": [stage.to_dict() for stage in self.stages],
            "error": None if self.error is None else self.error.to_dict(),
            "teardown_errors": [error.to_dict() for error in self.teardown_errors],
            "steps": [step.to_dict() for step in self.steps],
            "steps_truncated": self.steps_truncated,
        }


@dataclass(frozen=True, slots=True, repr=False)
class ExecutionResult:
    """Result of :meth:`Runtime.run`.

    The raw exceptions are kept for programmatic inspection; ``repr`` and
    :attr:`record` only expose masked information.

    Attributes:
        execution_id: Unique execution identifier.
        automation: Name of the automation.
        runtime: Name of the Runtime.
        status: Final status.
        started_at: Start time (UTC).
        finished_at: End time (UTC).
        duration: Total duration in seconds.
        stages: Outcome of every stage, in order.
        output: Value returned by the automation (``None`` if it did not finish).
        error: Primary error, or the first teardown error if there is no primary error.
        teardown_errors: Every error raised by teardown stages.
        steps: Outcome of every recorded step, in start order (at most
            ``runtime.max_steps``; see :attr:`ExecutionRecord.steps_truncated`).
        record: Masked, serializable summary.
    """

    execution_id: str
    automation: str
    runtime: str
    status: ExecutionStatus
    started_at: datetime
    finished_at: datetime
    duration: float
    stages: tuple[StageOutcome, ...]
    record: ExecutionRecord
    output: object = None
    error: BaseException | None = None
    teardown_errors: tuple[BaseException, ...] = ()
    steps: tuple[StepOutcome, ...] = ()

    @property
    def succeeded(self) -> bool:
        """Whether the status is ``succeeded``."""
        return self.status is ExecutionStatus.SUCCEEDED

    def stage(self, name: str) -> StageOutcome:
        """Return the outcome of the stage called ``name``.

        Raises:
            KeyError: If no such stage exists.
        """
        for outcome in self.stages:
            if outcome.name == name:
                return outcome
        raise KeyError(name)

    def raise_for_status(self) -> None:
        """Raise :class:`ExecutionFailedError` unless the execution succeeded.

        The primary error is chained as ``__cause__``.
        """
        if not self.succeeded:
            raise ExecutionFailedError(self) from self.error

    def __repr__(self) -> str:
        """Return a masked, concise representation."""
        error = self.record.error.type if self.record.error is not None else None
        return (
            f"ExecutionResult(execution_id={self.execution_id!r}, automation={self.automation!r}, "
            f"status={self.status.value!r}, duration={self.duration:.3f}, error={error!r})"
        )


@runtime_checkable
class ExecutionRecordSink(Protocol):
    """Port that receives the record of every execution during ``persist_logs``.

    Implementations (files, databases, observability backends) live outside the
    Core. An exception raised by a sink never changes the status, the result or
    the flow of the execution (RFC-0009): it is logged as a warning and counted
    in the ``orchestrator.record_sink.errors`` metric. ``KeyboardInterrupt`` and
    other non-``Exception`` errors still interrupt, as anywhere in the pipeline.
    """

    def write(self, record: ExecutionRecord) -> None:
        """Persist or forward ``record``."""
        ...
