"""Runtime (executes automations) and RuntimeBuilder (composition root)."""

from __future__ import annotations

import logging
import os
import re
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Self

from orchestrator_core import _correlation
from orchestrator_core._cancellation import CancellationToken
from orchestrator_core._capabilities import (
    Capability,
    CapabilityRegistration,
    CapabilityRegistry,
)
from orchestrator_core._clock import Clock, SystemClock
from orchestrator_core._config import Configuration
from orchestrator_core._context import Automation, ExecutionContext, ExecutionState
from orchestrator_core._errors import CapabilityError, ExecutionInterruptedError
from orchestrator_core._events import (
    Event,
    EventBus,
    EventHandler,
    ExecutionFinished,
    StageFinished,
    StageStarted,
)
from orchestrator_core._metrics import (
    EXECUTION_DURATION,
    EXECUTIONS,
    STAGE_DURATION,
    MetricsRecorder,
    NoopMetrics,
    SafeMetrics,
)
from orchestrator_core._pipeline import PipelineDefinition, Stage
from orchestrator_core._redaction import Redactor, default_redactor
from orchestrator_core._resources import ResourceScope
from orchestrator_core._results import (
    ErrorInfo,
    ExecutionOutcome,
    ExecutionRecord,
    ExecutionRecordSink,
    ExecutionResult,
    ExecutionStatus,
    Phase,
    StageOutcome,
    StageRecord,
    StageStatus,
    stage_status_for_error,
    status_for_error,
)
from orchestrator_core._secrets import (
    EnvSecretResolver,
    FileSecretResolver,
    SecretResolver,
    SecretStore,
)
from orchestrator_core._stages import EXECUTE_AUTOMATION, default_pipeline

_logger = logging.getLogger("orchestrator_core.runtime")
_EXECUTION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*$")


@dataclass(slots=True)
class _Run:
    """Mutable bookkeeping of one pipeline run."""

    outcomes: list[StageOutcome] = field(default_factory=list)
    primary: BaseException | None = None
    teardown_errors: list[BaseException] = field(default_factory=list)
    interrupt: BaseException | None = None

    @property
    def error(self) -> BaseException | None:
        if self.primary is not None:
            return self.primary
        return self.teardown_errors[0] if self.teardown_errors else None

    @property
    def status(self) -> ExecutionStatus:
        if self.primary is None and self.teardown_errors:
            return ExecutionStatus.FAILED
        return status_for_error(self.primary)


class Runtime:
    """Executes automations through the execution pipeline.

    Create it with :class:`RuntimeBuilder`. A Runtime is immutable and
    thread-safe: :meth:`run` may be called concurrently, and each call gets its
    own context, resources and Capability handles.

    Example:
        >>> runtime = RuntimeBuilder().with_environment(None, prefix=None).build()
        >>> result = runtime.run(lambda ctx: 21 * 2, name="answer")
        >>> result.status.value, result.output
        ('succeeded', 42)
    """

    def __init__(
        self,
        *,
        configuration: Configuration,
        registry: CapabilityRegistry,
        pipeline: PipelineDefinition,
        events: EventBus,
        metrics: MetricsRecorder,
        record_sinks: tuple[ExecutionRecordSink, ...],
        secret_resolvers: Mapping[str, SecretResolver],
        clock: Clock,
        redactor: Redactor,
    ) -> None:
        """Assemble a Runtime. Use :class:`RuntimeBuilder` instead."""
        self._configuration = configuration
        self._registry = registry
        self._pipeline = pipeline
        self._events = events
        self._metrics = metrics
        self._record_sinks = record_sinks
        self._secret_resolvers = dict(secret_resolvers)
        self._clock = clock
        self._redactor = redactor

    @property
    def name(self) -> str:
        """Name of the Runtime (``runtime.name``)."""
        return self._configuration.runtime.name

    @property
    def configuration(self) -> Configuration:
        """Validated configuration."""
        return self._configuration

    @property
    def stages(self) -> tuple[str, ...]:
        """Names of the pipeline stages, in order."""
        return self._pipeline.names

    @property
    def capabilities(self) -> tuple[str, ...]:
        """Names of the registered Capabilities, in registration order."""
        return self._registry.names

    def run(
        self,
        automation: Automation,
        /,
        *,
        name: str | None = None,
        parameters: Mapping[str, object] | None = None,
        parameters_validator: Callable[[Mapping[str, object]], object] | None = None,
        timeout: float | None = None,
        cancellation: CancellationToken | None = None,
        execution_id: str | None = None,
    ) -> ExecutionResult:
        """Execute ``automation`` through the whole pipeline.

        Failures of the automation or of any stage are reported in the result,
        never raised, so that teardown always runs. Only ``KeyboardInterrupt``,
        ``SystemExit`` and other non-``Exception`` errors are re-raised, after
        teardown.

        Args:
            automation: Callable that receives the :class:`ExecutionContext`.
            name: Name of the automation (default: the callable's qualified name).
            parameters: Parameters, exposed read-only as ``ctx.parameters``.
            parameters_validator: Converts and validates the parameters in the
                ``prepare_execution`` stage; for example, a Pydantic model's
                ``model_validate`` or a dataclass constructor wrapper.
            timeout: Seconds before the execution times out (overrides
                ``runtime.timeout``). Enforcement is cooperative.
            cancellation: Token to cancel the execution from another thread.
            execution_id: Identifier to use instead of a random one, for
                correlation with external systems.

        Raises:
            TypeError: If ``automation`` is not callable.
            ValueError: If ``timeout`` or ``execution_id`` is invalid.
        """
        candidate: object = automation
        if not callable(candidate):
            msg = "automation must be callable"
            raise TypeError(msg)
        effective_timeout = self._configuration.runtime.timeout if timeout is None else timeout
        if effective_timeout is not None and effective_timeout <= 0:
            msg = "timeout must be greater than zero"
            raise ValueError(msg)
        if execution_id is not None and not _EXECUTION_ID_RE.match(execution_id):
            msg = "execution_id must have 1-128 characters: letters, digits, '.', '_', ':' or '-'"
            raise ValueError(msg)
        automation_name = name or str(
            getattr(automation, "__qualname__", type(automation).__qualname__)
        )
        raw_parameters = MappingProxyType(dict(parameters or {}))
        started = self._clock.monotonic()
        state = ExecutionState(
            automation=automation,
            raw_parameters=raw_parameters,
            parameters_validator=parameters_validator,
            registry=self._registry,
            record_sinks=self._record_sinks,
            redactor=self._redactor,
            resources=ResourceScope(),
            parameters=raw_parameters,
        )
        ctx = ExecutionContext(
            execution_id=execution_id or uuid.uuid4().hex,
            automation_name=automation_name,
            runtime_name=self.name,
            started_at=self._clock.now(),
            config=self._configuration,
            events=self._events,
            metrics=self._metrics,
            secrets=SecretStore(self._secret_resolvers, self._redactor),
            cancellation=cancellation or CancellationToken(),
            clock=self._clock,
            timeout=effective_timeout,
            deadline=None if effective_timeout is None else started + effective_timeout,
            internal=state,
        )
        binding = _correlation.bind(ctx.execution_id, automation_name)
        try:
            run = self._execute(ctx, state, started)
            result = self._result(ctx, state, run, started)
            self._report(result)
        finally:
            _correlation.unbind(binding)
        if run.interrupt is not None:
            raise run.interrupt
        return result

    # Pipeline ---------------------------------------------------------------

    def _execute(self, ctx: ExecutionContext, state: ExecutionState, started: float) -> _Run:
        run = _Run()
        state.record_builder = lambda: self._record(ctx, run, started)
        for stage in self._pipeline.stages:
            if stage.phase is Phase.TEARDOWN:
                state.outcome = ExecutionOutcome(status=run.status, error=run.error)
                error = self._run_stage(ctx, stage, run)
                if error is not None:
                    run.teardown_errors.append(error)
                continue
            if run.primary is not None:
                run.outcomes.append(StageOutcome(stage.name, stage.phase, StageStatus.SKIPPED))
                continue
            try:
                ctx.check()
            except ExecutionInterruptedError as exc:
                _logger.warning("execution interrupted before stage %r: %s", stage.name, exc)
                run.outcomes.append(
                    StageOutcome(stage.name, stage.phase, stage_status_for_error(exc), 0.0, exc)
                )
                run.primary = exc
                continue
            run.primary = self._run_stage(ctx, stage, run)
            if stage.name == EXECUTE_AUTOMATION and run.primary is None and ctx.deadline_exceeded():
                _logger.warning("the automation finished after its timeout of %ss", ctx.timeout)
        return run

    def _run_stage(self, ctx: ExecutionContext, stage: Stage, run: _Run) -> BaseException | None:
        token = _correlation.enter_stage(stage.name)
        try:
            self._events.publish(
                StageStarted(
                    execution_id=ctx.execution_id,
                    timestamp=self._clock.now(),
                    stage=stage.name,
                    phase=stage.phase,
                )
            )
            begin = self._clock.monotonic()
            error: BaseException | None = None
            try:
                stage.run(ctx)
            except BaseException as exc:  # noqa: BLE001 - recorded; interrupts re-raised by run()
                error = exc
                self._log_stage_failure(stage, exc)
                if not isinstance(exc, Exception) and run.interrupt is None:
                    run.interrupt = exc
            duration = self._clock.monotonic() - begin
            status = StageStatus.SUCCEEDED if error is None else stage_status_for_error(error)
            run.outcomes.append(StageOutcome(stage.name, stage.phase, status, duration, error))
            info = None if error is None else ErrorInfo.from_exception(error, self._redactor)
            self._events.publish(
                StageFinished(
                    execution_id=ctx.execution_id,
                    timestamp=self._clock.now(),
                    stage=stage.name,
                    phase=stage.phase,
                    status=status,
                    duration=duration,
                    error=info,
                )
            )
            self._metrics.observe(
                STAGE_DURATION,
                duration,
                tags={
                    "runtime": self.name,
                    "stage": stage.name,
                    "status": status.value,
                },
            )
            return error
        finally:
            _correlation.exit_stage(token)

    @staticmethod
    def _log_stage_failure(stage: Stage, error: BaseException) -> None:
        if isinstance(error, ExecutionInterruptedError):
            _logger.warning("stage %r interrupted: %s", stage.name, error)
        elif not isinstance(error, Exception):
            _logger.warning("stage %r interrupted by %s", stage.name, type(error).__name__)
        else:
            _logger.error("stage %r failed", stage.name, exc_info=error)

    # Results ----------------------------------------------------------------

    def _record(self, ctx: ExecutionContext, run: _Run, started: float) -> ExecutionRecord:
        redact = self._redactor
        return ExecutionRecord(
            execution_id=ctx.execution_id,
            automation=ctx.automation,
            runtime=self.name,
            status=run.status,
            started_at=ctx.started_at,
            finished_at=self._clock.now(),
            duration=self._clock.monotonic() - started,
            stages=tuple(
                StageRecord(
                    name=outcome.name,
                    phase=outcome.phase,
                    status=outcome.status,
                    duration=outcome.duration,
                    error=None
                    if outcome.error is None
                    else ErrorInfo.from_exception(outcome.error, redact),
                )
                for outcome in run.outcomes
            ),
            error=None if run.error is None else ErrorInfo.from_exception(run.error, redact),
            teardown_errors=tuple(ErrorInfo.from_exception(e, redact) for e in run.teardown_errors),
        )

    def _result(
        self, ctx: ExecutionContext, state: ExecutionState, run: _Run, started: float
    ) -> ExecutionResult:
        record = self._record(ctx, run, started)
        return ExecutionResult(
            execution_id=ctx.execution_id,
            automation=ctx.automation,
            runtime=self.name,
            status=run.status,
            started_at=record.started_at,
            finished_at=record.finished_at,
            duration=record.duration,
            stages=tuple(run.outcomes),
            record=record,
            output=state.output,
            error=run.error,
            teardown_errors=tuple(run.teardown_errors),
        )

    def _report(self, result: ExecutionResult) -> None:
        tags = {
            "runtime": self.name,
            "automation": result.automation,
            "status": result.status.value,
        }
        self._metrics.increment(EXECUTIONS, tags=tags)
        self._metrics.observe(EXECUTION_DURATION, result.duration, tags=tags)
        if result.succeeded:
            _logger.info(
                "execution finished: status=%s duration=%.3fs",
                result.status.value,
                result.duration,
            )
        else:
            error = result.record.error
            _logger.warning(
                "execution finished: status=%s duration=%.3fs error=%s",
                result.status.value,
                result.duration,
                "-" if error is None else error.type,
            )
        self._events.publish(
            ExecutionFinished(
                execution_id=result.execution_id,
                timestamp=result.finished_at,
                automation=result.automation,
                runtime=self.name,
                status=result.status,
                duration=result.duration,
                error=result.record.error,
            )
        )


@dataclass(slots=True)
class _CapabilitySpec:
    capability: Capability[Any] | type[Capability[Any]]
    name: str | None
    options: dict[str, object]


@dataclass(slots=True)
class _StageSpec:
    stage: Stage
    before: str | None
    after: str | None


class RuntimeBuilder:
    """Composition root of a :class:`Runtime`.

    Every dependency is given explicitly; nothing is discovered or loaded
    implicitly. Environment variables with the ``ORCHESTRATOR`` prefix are read
    by default (see :meth:`with_environment`).

    Example:
        >>> runtime = (
        ...     RuntimeBuilder()
        ...     .with_environment(None, prefix=None)
        ...     .with_settings({"runtime": {"name": "billing", "timeout": 60}})
        ...     .build()
        ... )
        >>> runtime.name, runtime.stages[0], runtime.stages[-1]
        ('billing', 'initialize', 'shutdown')
    """

    def __init__(self) -> None:
        """Create a builder: no file, ``ORCHESTRATOR_*`` variables, no Capabilities."""
        self._config_file: str | os.PathLike[str] | None = None
        self._environ: Mapping[str, str] | None = None
        self._env_prefix: str | None = "ORCHESTRATOR"
        self._overrides: list[Mapping[str, object]] = []
        self._capabilities: list[_CapabilitySpec] = []
        self._stages: list[_StageSpec] = []
        self._handlers: list[tuple[type[Event], EventHandler[Any]]] = []
        self._metrics: MetricsRecorder = NoopMetrics()
        self._record_sinks: list[ExecutionRecordSink] = []
        self._secret_resolvers: dict[str, SecretResolver] = {
            "env": EnvSecretResolver(),
            "file": FileSecretResolver(),
        }
        self._clock: Clock = SystemClock()
        self._redactor: Redactor = default_redactor

    def with_config_file(self, path: str | os.PathLike[str]) -> Self:
        """Read configuration from the TOML file at ``path``."""
        self._config_file = path
        return self

    def with_environment(
        self,
        environ: Mapping[str, str] | None = None,
        *,
        prefix: str | None = "ORCHESTRATOR",
    ) -> Self:
        """Choose the environment variables to read.

        Args:
            environ: Variables to read; ``None`` means :data:`os.environ` at build time.
            prefix: Prefix of the variables; ``None`` disables this source.
        """
        self._environ = environ
        self._env_prefix = prefix
        return self

    def with_settings(self, settings: Mapping[str, object]) -> Self:
        """Apply explicit settings, with the highest precedence. Calls accumulate."""
        self._overrides.append(settings)
        return self

    def with_capability(
        self,
        capability: Capability[Any] | type[Capability[Any]],
        /,
        *,
        name: str | None = None,
        **options: object,
    ) -> Self:
        """Register a Capability.

        Args:
            capability: A ready instance, or a Capability class built at
                :meth:`build` time with ``cls.from_config(section, **options)``,
                where ``section`` is ``[capabilities.<name>]``.
            name: Registration name (default: the class ``default_name``).
            **options: Extra arguments for ``from_config`` (classes only).

        Raises:
            CapabilityError: If ``options`` are given with an instance.
        """
        if options and not isinstance(capability, type):
            msg = "options can only be given together with a Capability class"
            raise CapabilityError(msg)
        self._capabilities.append(_CapabilitySpec(capability, name, dict(options)))
        return self

    def with_stage(
        self, stage: Stage, *, before: str | None = None, after: str | None = None
    ) -> Self:
        """Insert a custom stage before or after an existing stage."""
        self._stages.append(_StageSpec(stage, before, after))
        return self

    def on_event[E: Event](self, event_type: type[E], handler: EventHandler[E]) -> Self:
        """Call ``handler`` for every published event that is an instance of ``event_type``."""
        self._handlers.append((event_type, handler))
        return self

    def with_metrics(self, recorder: MetricsRecorder) -> Self:
        """Use ``recorder`` for metrics (default: discard)."""
        self._metrics = recorder
        return self

    def with_record_sink(self, sink: ExecutionRecordSink) -> Self:
        """Deliver the record of every execution to ``sink``. Calls accumulate."""
        self._record_sinks.append(sink)
        return self

    def with_secret_resolver(self, scheme: str, resolver: SecretResolver) -> Self:
        """Resolve ``<scheme>:<target>`` references with ``resolver``.

        Raises:
            ValueError: If ``scheme`` is invalid.
        """
        if not _SCHEME_RE.match(scheme):
            msg = "secret schemes use lowercase letters, digits, '+', '.' or '-'"
            raise ValueError(msg)
        self._secret_resolvers[scheme] = resolver
        return self

    def with_clock(self, clock: Clock) -> Self:
        """Use ``clock`` as time source (tests use ``testing.FakeClock``)."""
        self._clock = clock
        return self

    def with_redactor(self, redactor: Redactor) -> Self:
        """Use ``redactor`` instead of the process-wide one (intended for tests)."""
        self._redactor = redactor
        return self

    def build(self) -> Runtime:
        """Validate everything and create the Runtime.

        Raises:
            ConfigurationError: If the configuration is invalid.
            CapabilityError: If a Capability cannot be registered.
            PipelineDefinitionError: If a custom stage cannot be inserted.
        """
        environ = os.environ if self._environ is None else self._environ
        configuration = Configuration.load(
            file=self._config_file,
            environ=environ,
            env_prefix=self._env_prefix,
            overrides=self._overrides,
        )
        registrations: list[CapabilityRegistration] = []
        for spec in self._capabilities:
            if isinstance(spec.capability, type):
                capability_name = spec.name or spec.capability.default_name
                instance = spec.capability.from_config(
                    configuration.capability(capability_name), **spec.options
                )
            else:
                capability_name = spec.name or type(spec.capability).default_name
                instance = spec.capability
            registrations.append(CapabilityRegistration(capability_name, instance))
        registry = CapabilityRegistry(registrations)
        pipeline = default_pipeline()
        for stage_spec in self._stages:
            pipeline = pipeline.insert(
                stage_spec.stage, before=stage_spec.before, after=stage_spec.after
            )
        metrics = SafeMetrics(self._metrics)
        events = EventBus(metrics)
        for event_type, handler in self._handlers:
            events.subscribe(event_type, handler)
        return Runtime(
            configuration=configuration,
            registry=registry,
            pipeline=pipeline,
            events=events,
            metrics=metrics,
            record_sinks=tuple(self._record_sinks),
            secret_resolvers=self._secret_resolvers,
            clock=self._clock,
            redactor=self._redactor,
        )
