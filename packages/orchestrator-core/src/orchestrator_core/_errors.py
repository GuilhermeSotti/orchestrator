"""Exception hierarchy of the Orchestrator platform.

Every error raised by the platform derives from :class:`OrchestratorError`.
Errors that may succeed when the operation is repeated carry
``retryable = True``; the default retry predicate relies on that flag.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orchestrator_core._results import ExecutionResult


class OrchestratorError(Exception):
    """Base class of every error raised by the Orchestrator platform.

    Attributes:
        retryable: Whether repeating the failed operation may succeed.
    """

    retryable: bool = False


class ConfigurationError(OrchestratorError):
    """Invalid or missing configuration.

    Attributes:
        key: Dotted path of the offending configuration key, when known.
    """

    def __init__(self, message: str, *, key: str | None = None) -> None:
        """Create the error.

        Args:
            message: Description of the problem. Must not contain secret values.
            key: Dotted path of the offending key, such as ``runtime.timeout``.
        """
        super().__init__(f"{key}: {message}" if key else message)
        self.key = key


class PipelineDefinitionError(OrchestratorError):
    """The execution pipeline definition is invalid (names, order or phases)."""


class CapabilityError(OrchestratorError):
    """Base class of errors related to Capabilities."""


class CapabilityNotFoundError(CapabilityError):
    """The requested Capability is not registered in the Runtime."""


class DuplicateCapabilityError(CapabilityError):
    """A Capability with the same name is already registered."""


class IncompatibleCapabilityError(CapabilityError):
    """The Capability was built against an incompatible Core API version."""


class CapabilityUnavailableError(CapabilityError):
    """The Capability cannot be used: a dependency or setting is missing."""


class ProviderError(OrchestratorError):
    """Base class of errors that Providers translate from infrastructure errors.

    Providers must raise subclasses of this error instead of letting driver or
    SDK exceptions escape, and must not include secret values or sensitive data
    in the message.
    """

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        """Create the error.

        Args:
            message: Description of the failure, without sensitive data.
            retryable: Whether the operation may succeed if repeated.
        """
        super().__init__(message)
        self.retryable = retryable


class SecretResolutionError(OrchestratorError):
    """A secret reference could not be resolved. Never carries the secret value."""


class ExecutionInterruptedError(OrchestratorError):
    """Base class of cooperative interruptions of an execution."""


class ExecutionCancelledError(ExecutionInterruptedError):
    """The execution was cancelled through its cancellation token."""


class ExecutionTimeoutError(ExecutionInterruptedError):
    """The execution exceeded its deadline."""


class ExecutionFailedError(OrchestratorError):
    """Raised by :meth:`ExecutionResult.raise_for_status` for unsuccessful executions.

    Attributes:
        result: The unsuccessful execution result.
    """

    def __init__(self, result: ExecutionResult) -> None:
        """Create the error from an unsuccessful result.

        Args:
            result: The execution result whose status is not ``succeeded``.
        """
        error = result.record.error
        detail = f": {error.type}: {error.message}" if error is not None else ""
        super().__init__(
            f"execution {result.execution_id} of {result.automation!r} "
            f"finished with status {result.status.value}{detail}"
        )
        self.result = result
