"""Pipeline stages that send the lifecycle notices (RFC-0007, section 3)."""

from __future__ import annotations

from orchestrator_core import (
    CapabilityError,
    CapabilityNotFoundError,
    ExecutionContext,
    Phase,
    Stage,
)
from orchestrator_notifications._capability import NotificationCapability
from orchestrator_notifications._model import NOTIFY_OUTCOME, NOTIFY_STARTED, LifecycleNotice
from orchestrator_notifications._notifier import notify_lifecycle


class NotifyStarted(Stage):
    """Preparation stage that sends the ``started`` notice.

    Install it after ``prepare_execution``::

        builder.with_stage(NotifyStarted(), after="prepare_execution")

    A failure on a ``required`` channel fails the preparation: the automation
    does not run.
    """

    name = NOTIFY_STARTED
    phase = Phase.PREPARE

    def __init__(self, *, capability: str | None = None) -> None:
        """Create the stage for the Capability registered as ``capability``."""
        self._capability = capability

    def run(self, ctx: ExecutionContext) -> None:
        """Send the notice to the channels configured for ``started``."""
        notifier = ctx.capability(NotificationCapability, self._capability)
        notify_lifecycle(
            notifier,
            LifecycleNotice(
                status="started",
                automation=ctx.automation,
                runtime=ctx.runtime,
                execution_id=ctx.execution_id,
                started_at=ctx.started_at,
            ),
        )


class NotifyOutcome(Stage):
    """Teardown stage that sends the outcome notice.

    Install it after ``finalize``, so that errors of finalizers and of
    resource release are already part of the outcome::

        builder.with_stage(NotifyOutcome(), after="finalize")

    A failure on a ``required`` channel becomes a teardown error: a successful
    execution ends ``failed``. If the Capability was never opened (an earlier
    preparation stage failed first), the notice cannot be sent and a warning
    is logged.
    """

    name = NOTIFY_OUTCOME
    phase = Phase.TEARDOWN

    def __init__(self, *, capability: str | None = None) -> None:
        """Create the stage for the Capability registered as ``capability``."""
        self._capability = capability

    def run(self, ctx: ExecutionContext) -> None:
        """Send the notice to the channels configured for the current status."""
        outcome = ctx.outcome
        if outcome is None:  # pragma: no cover - teardown stages always see an outcome
            return
        try:
            notifier = ctx.capability(NotificationCapability, self._capability)
        except CapabilityNotFoundError:
            raise
        except CapabilityError:
            ctx.logger.warning(
                "the notifications capability was not opened; no %s notice was sent",
                outcome.status.value,
            )
            return
        notify_lifecycle(
            notifier,
            LifecycleNotice(
                status=outcome.status.value,
                automation=ctx.automation,
                runtime=ctx.runtime,
                execution_id=ctx.execution_id,
                started_at=ctx.started_at,
                duration=(ctx.now() - ctx.started_at).total_seconds(),
                error=outcome.error_info,
            ),
        )
