"""The eight built-in stages of the documented lifecycle (RFC-0001)."""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Final

from orchestrator_core._context import internal_state
from orchestrator_core._events import ExecutionStarted
from orchestrator_core._pipeline import PipelineDefinition, Stage
from orchestrator_core._results import Phase

if TYPE_CHECKING:
    from orchestrator_core._context import ExecutionContext

_logger = logging.getLogger("orchestrator_core.stages")

INITIALIZE: Final = "initialize"
PROVISION_DEPENDENCIES: Final = "provision_dependencies"
PREPARE_ENVIRONMENT: Final = "prepare_environment"
PREPARE_EXECUTION: Final = "prepare_execution"
EXECUTE_AUTOMATION: Final = "execute_automation"
FINALIZE: Final = "finalize"
PERSIST_LOGS: Final = "persist_logs"
SHUTDOWN: Final = "shutdown"


def raise_collected(errors: list[BaseException], stage: str) -> None:
    """Raise nothing, the single error, or a group with every error."""
    if not errors:
        return
    if len(errors) == 1:
        raise errors[0]
    if all(isinstance(error, Exception) for error in errors):
        raise ExceptionGroup(f"{len(errors)} errors in stage {stage!r}", errors)  # type: ignore[type-var]
    raise BaseExceptionGroup(f"{len(errors)} errors in stage {stage!r}", errors)


class InitializeStage(Stage):
    """Opens the execution: logs the start and publishes :class:`ExecutionStarted`."""

    name = INITIALIZE
    phase = Phase.PREPARE

    def run(self, ctx: ExecutionContext) -> None:
        """Announce the execution."""
        _logger.info("execution started: automation=%s runtime=%s", ctx.automation, ctx.runtime)
        ctx.publish(
            ExecutionStarted(
                execution_id=ctx.execution_id,
                timestamp=ctx.now(),
                automation=ctx.automation,
                runtime=ctx.runtime,
            )
        )


class ProvisionDependenciesStage(Stage):
    """Verifies and opens every registered Capability, in registration order.

    It never installs packages: dependencies belong to the environment build.
    """

    name = PROVISION_DEPENDENCIES
    phase = Phase.PREPARE

    def run(self, ctx: ExecutionContext) -> None:
        """Open one handle per Capability for this execution."""
        state = internal_state(ctx)
        for registration in state.registry.registrations:
            try:
                registration.capability.verify()
                handle = registration.capability.open(ctx)
            except Exception as exc:
                exc.add_note(f"while provisioning capability {registration.name!r}")
                raise
            state.handles[registration.name] = handle
            _logger.debug("capability %r provisioned", registration.name)


class PrepareEnvironmentStage(Stage):
    """Creates the private workspace of the execution when ``runtime.workspace`` is on."""

    name = PREPARE_ENVIRONMENT
    phase = Phase.PREPARE

    def run(self, ctx: ExecutionContext) -> None:
        """Create the workspace and schedule its removal."""
        settings = ctx.config.runtime
        if not settings.workspace:
            return
        state = internal_state(ctx)
        path = Path(
            tempfile.mkdtemp(
                prefix=f"orchestrator-{ctx.execution_id[:12]}-",
                dir=settings.workspace_root,
            )
        )
        state.workspace = path
        if settings.keep_workspace:
            _logger.info("workspace kept after the execution: %s", path)
        else:
            ctx.resources.callback(shutil.rmtree, path)
        _logger.debug("workspace created: %s", path)


class PrepareExecutionStage(Stage):
    """Validates the parameters and makes them available as ``ctx.parameters``."""

    name = PREPARE_EXECUTION
    phase = Phase.PREPARE

    def run(self, ctx: ExecutionContext) -> None:
        """Apply the parameters validator, if any."""
        state = internal_state(ctx)
        if state.parameters_validator is None:
            return
        try:
            state.parameters = state.parameters_validator(state.raw_parameters)
        except Exception as exc:
            exc.add_note("while validating the parameters of the execution")
            raise


class ExecuteAutomationStage(Stage):
    """Calls the automation with the context and keeps its return value."""

    name = EXECUTE_AUTOMATION
    phase = Phase.EXECUTE

    def run(self, ctx: ExecutionContext) -> None:
        """Run the business logic of the consumer project."""
        state = internal_state(ctx)
        state.output = state.automation(ctx)


class FinalizeStage(Stage):
    """Runs finalizers (reverse order), then releases resources (reverse order)."""

    name = FINALIZE
    phase = Phase.TEARDOWN

    def run(self, ctx: ExecutionContext) -> None:
        """Wrap up the execution; every finalizer and cleanup runs even if others fail."""
        state = internal_state(ctx)
        errors: list[BaseException] = []
        outcome = state.outcome
        for finalizer in reversed(state.finalizers):
            try:
                finalizer(outcome)  # type: ignore[arg-type]
            except BaseException as exc:  # noqa: BLE001 - collected and re-raised below
                errors.append(exc)
        errors.extend(state.resources.close())
        raise_collected(errors, self.name)


class PersistLogsStage(Stage):
    """Delivers the execution record to the record sinks and flushes log handlers."""

    name = PERSIST_LOGS
    phase = Phase.TEARDOWN

    def run(self, ctx: ExecutionContext) -> None:
        """Persist the record of the execution."""
        state = internal_state(ctx)
        errors: list[BaseException] = []
        if state.record_sinks and state.record_builder is not None:
            record = state.record_builder()
            for sink in state.record_sinks:
                try:
                    sink.write(record)
                except Exception as exc:  # noqa: BLE001 - collected and re-raised below
                    errors.append(exc)
        _flush_handlers(ctx.logger.logger)
        _flush_handlers(_logger)
        raise_collected(errors, self.name)


class ShutdownStage(Stage):
    """Closes the context: Capability handles can no longer be obtained."""

    name = SHUTDOWN
    phase = Phase.TEARDOWN

    def run(self, ctx: ExecutionContext) -> None:
        """Close the execution context."""
        internal_state(ctx).closed = True


def _flush_handlers(logger: logging.Logger) -> None:
    """Flush the handlers reachable from ``logger``."""
    current: logging.Logger | None = logger
    while current is not None:
        for handler in current.handlers:
            handler.flush()
        current = current.parent if current.propagate else None


def default_pipeline() -> PipelineDefinition:
    """Return the eight documented stages, in order."""
    return PipelineDefinition(
        (
            InitializeStage(),
            ProvisionDependenciesStage(),
            PrepareEnvironmentStage(),
            PrepareExecutionStage(),
            ExecuteAutomationStage(),
            FinalizeStage(),
            PersistLogsStage(),
            ShutdownStage(),
        )
    )
