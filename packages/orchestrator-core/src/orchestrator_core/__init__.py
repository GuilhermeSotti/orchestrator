"""Orchestrator Core: runtime, execution pipeline and contracts for Capabilities and Providers.

The names exported here are the public API (RFC-0002). Modules whose names
start with an underscore are internal and may change without notice. The
public submodules are :mod:`orchestrator_core.logs` and
:mod:`orchestrator_core.testing`.

Example:
    >>> from orchestrator_core import ExecutionContext, RuntimeBuilder
    >>> def automation(ctx: ExecutionContext) -> str:
    ...     return f"processed {ctx.parameters['items']} items"
    >>> runtime = RuntimeBuilder().with_environment({}, prefix=None).build()
    >>> result = runtime.run(automation, parameters={"items": 3})
    >>> result.raise_for_status()
    >>> result.output
    'processed 3 items'
"""

import logging as _logging

from orchestrator_core._cancellation import CancellationToken
from orchestrator_core._capabilities import Capability
from orchestrator_core._clock import Clock
from orchestrator_core._config import ConfigSection, Configuration, RuntimeSettings
from orchestrator_core._context import Automation, ExecutionContext, Finalizer
from orchestrator_core._errors import (
    CapabilityError,
    CapabilityNotFoundError,
    CapabilityUnavailableError,
    ConfigurationError,
    DuplicateCapabilityError,
    ExecutionCancelledError,
    ExecutionFailedError,
    ExecutionInterruptedError,
    ExecutionTimeoutError,
    IncompatibleCapabilityError,
    OrchestratorError,
    PipelineDefinitionError,
    ProviderError,
    SecretResolutionError,
)
from orchestrator_core._events import (
    Event,
    EventHandler,
    ExecutionFinished,
    ExecutionStarted,
    StageFinished,
    StageStarted,
)
from orchestrator_core._metrics import MetricsRecorder
from orchestrator_core._pipeline import FunctionStage, Stage
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
)
from orchestrator_core._retry import RetryAttempt, RetryPolicy, is_retryable, retry
from orchestrator_core._runtime import Runtime, RuntimeBuilder
from orchestrator_core._secrets import Secret, SecretRef, SecretResolver, SecretStore
from orchestrator_core._version import CORE_API_VERSION, __version__

# Libraries must not emit logs unless the application configures logging.
for _name in ("orchestrator_core", "orchestrator"):
    _logging.getLogger(_name).addHandler(_logging.NullHandler())

__all__ = [
    "CORE_API_VERSION",
    "Automation",
    "CancellationToken",
    "Capability",
    "CapabilityError",
    "CapabilityNotFoundError",
    "CapabilityUnavailableError",
    "Clock",
    "ConfigSection",
    "Configuration",
    "ConfigurationError",
    "DuplicateCapabilityError",
    "ErrorInfo",
    "Event",
    "EventHandler",
    "ExecutionCancelledError",
    "ExecutionContext",
    "ExecutionFailedError",
    "ExecutionFinished",
    "ExecutionInterruptedError",
    "ExecutionOutcome",
    "ExecutionRecord",
    "ExecutionRecordSink",
    "ExecutionResult",
    "ExecutionStarted",
    "ExecutionStatus",
    "ExecutionTimeoutError",
    "Finalizer",
    "FunctionStage",
    "IncompatibleCapabilityError",
    "MetricsRecorder",
    "OrchestratorError",
    "Phase",
    "PipelineDefinitionError",
    "ProviderError",
    "ResourceScope",
    "RetryAttempt",
    "RetryPolicy",
    "Runtime",
    "RuntimeBuilder",
    "RuntimeSettings",
    "Secret",
    "SecretRef",
    "SecretResolutionError",
    "SecretResolver",
    "SecretStore",
    "Stage",
    "StageFinished",
    "StageOutcome",
    "StageRecord",
    "StageStarted",
    "StageStatus",
    "__version__",
    "is_retryable",
    "retry",
]
