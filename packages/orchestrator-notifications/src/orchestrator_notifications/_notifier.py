"""Notifier: the per-execution handle of the notifications Capability."""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace

from orchestrator_core import (
    CapabilityError,
    ErrorInfo,
    ExecutionContext,
    ExecutionInterruptedError,
    RetryPolicy,
)
from orchestrator_notifications._channel import NotificationChannel
from orchestrator_notifications._errors import NotificationError
from orchestrator_notifications._events import NOTIFICATIONS_FAILED, NotificationFailed
from orchestrator_notifications._model import (
    DeliveryReport,
    DeliveryStatus,
    LifecycleNotice,
    Notification,
)

Formatter = Callable[[LifecycleNotice], Notification]
"""Builds the notification of a lifecycle notice (text and language of the consumer)."""

_MAX_MESSAGE = 2000
_UNPRINTABLE = "<exception str() failed>"


@dataclass(frozen=True, slots=True)
class ChannelSettings:
    """A channel Provider together with its delivery policy.

    Attributes:
        provider: The channel Provider.
        required: Whether a failure raises :class:`NotificationError`, which
            changes the outcome of the execution (default: no).
        attempts: Delivery attempts for ``retryable`` errors (default: 1).
        delay: Seconds between attempts.
    """

    provider: NotificationChannel
    required: bool = False
    attempts: int = 1
    delay: float = 0.0

    def __post_init__(self) -> None:
        if self.attempts < 1:
            msg = "attempts must be at least 1"
            raise ValueError(msg)
        if self.delay < 0:
            msg = "delay must be zero or greater"
            raise ValueError(msg)


class Notifier:
    """Sends notifications for one execution and keeps what happened to each one.

    Obtained with ``ctx.capability(NotificationCapability)``. Every text is
    masked with ``ctx.redact`` before it leaves the process. There is no limit
    on the number of notifications and no grouping (RFC-0007, answer 4).
    """

    def __init__(
        self,
        ctx: ExecutionContext,
        channels: Mapping[str, ChannelSettings],
        default_channels: tuple[str, ...],
        lifecycle: Mapping[str, tuple[str, ...]],
        formatter: Formatter,
    ) -> None:
        """Create the handle (done by :meth:`NotificationCapability.open`)."""
        self._ctx = ctx
        self._channels = channels
        self._default = default_channels
        self._lifecycle = lifecycle
        self._formatter = formatter
        self._reports: list[DeliveryReport] = []
        self._lifecycle_done: set[tuple[str, str]] = set()
        self._lock = threading.Lock()

    @property
    def channels(self) -> tuple[str, ...]:
        """Names of the configured channels."""
        return tuple(self._channels)

    @property
    def default_channels(self) -> tuple[str, ...]:
        """Channels used by :meth:`send` when no channel is given."""
        return self._default

    @property
    def reports(self) -> tuple[DeliveryReport, ...]:
        """Delivery reports of this execution, in order."""
        with self._lock:
            return tuple(self._reports)

    def send(
        self,
        notification: Notification,
        *,
        channel: str | None = None,
        required: bool | None = None,
    ) -> tuple[DeliveryReport, ...]:
        """Send ``notification`` to ``channel``, or to every default channel.

        Every channel is tried, even after a failure.

        Args:
            notification: The message.
            channel: Channel name; ``None`` uses ``default_channels``.
            required: Overrides the ``required`` policy of the channels for
                this notification (RFC-0007, answer 5).

        Returns:
            One report per channel, in order.

        Raises:
            CapabilityError: If the channel is unknown or no channel applies.
            NotificationError: If a delivery that is required failed.
        """
        names = (channel,) if channel is not None else self._default
        if not names:
            msg = "no channel was given and no default_channels are configured"
            raise CapabilityError(msg)
        for name in names:
            if name not in self._channels:
                msg = f"unknown notification channel {name!r}"
                raise CapabilityError(msg)
        return self._deliver_all(names, notification, required)

    def _send_lifecycle(self, notice: LifecycleNotice) -> tuple[DeliveryReport, ...]:
        names = self._lifecycle.get(notice.status, ())
        if not names:
            return ()
        notification = self._formatter(notice)
        pending: list[str] = []
        skipped: list[DeliveryReport] = []
        with self._lock:
            for name in names:
                if (notice.status, name) in self._lifecycle_done:  # at most one per status
                    report = DeliveryReport(
                        name, notification.kind, DeliveryStatus.SKIPPED, 0, None
                    )
                    self._reports.append(report)
                    skipped.append(report)
                else:
                    self._lifecycle_done.add((notice.status, name))
                    pending.append(name)
        return (*skipped, *self._deliver_all(tuple(pending), notification, None))

    def _deliver_all(
        self, names: tuple[str, ...], notification: Notification, required: bool | None
    ) -> tuple[DeliveryReport, ...]:
        reports: list[DeliveryReport] = []
        failed_required: DeliveryReport | None = None
        for name in names:
            report = self._deliver(name, notification)
            reports.append(report)
            policy = self._channels[name].required if required is None else required
            if report.status is DeliveryStatus.FAILED and policy and failed_required is None:
                failed_required = report
        if failed_required is not None:
            error = failed_required.error
            assert error is not None  # noqa: S101 - a failed report has an error
            msg = (
                f"required notification channel {failed_required.channel!r} failed: "
                f"{error.type}: {error.message}"
            )
            raise NotificationError(msg)
        return tuple(reports)

    def _deliver(self, name: str, notification: Notification) -> DeliveryReport:
        settings = self._channels[name]
        masked = _masked(self._ctx, notification)
        attempts = 0

        def attempt() -> None:
            nonlocal attempts
            attempts += 1
            settings.provider.send(masked, self._ctx.secrets)

        try:
            if settings.attempts > 1:
                policy = RetryPolicy(
                    max_attempts=settings.attempts,
                    initial_delay=settings.delay,
                    multiplier=1.0,
                    max_delay=settings.delay,
                    jitter=0.0,
                )
                self._ctx.retry(attempt, policy, name=f"notification.{name}")
            else:
                attempt()
        except ExecutionInterruptedError:
            raise  # cancellation or deadline is not a channel failure
        except Exception as exc:  # noqa: BLE001 - a failing channel is reported, not raised
            report = DeliveryReport(
                name,
                notification.kind,
                DeliveryStatus.FAILED,
                attempts,
                _error_info(self._ctx, exc),
            )
            self._failed(report)
            return report
        report = DeliveryReport(name, notification.kind, DeliveryStatus.SENT, attempts)
        with self._lock:
            self._reports.append(report)
        self._ctx.logger.debug("notification %r sent to channel %r", notification.kind, name)
        return report

    def _failed(self, report: DeliveryReport) -> None:
        error = report.error
        assert error is not None  # noqa: S101 - a failed report has an error
        with self._lock:
            self._reports.append(report)
        self._ctx.logger.warning(
            "notification %r to channel %r failed after %d attempt(s): %s: %s",
            report.kind,
            report.channel,
            report.attempts,
            error.type,
            error.message,
        )
        self._ctx.metrics.increment(
            NOTIFICATIONS_FAILED, tags={"channel": report.channel, "kind": report.kind}
        )
        self._ctx.publish(
            NotificationFailed(
                execution_id=self._ctx.execution_id,
                timestamp=self._ctx.now(),
                channel=report.channel,
                kind=report.kind,
                error=error,
            )
        )


def notify_lifecycle(notifier: Notifier, notice: LifecycleNotice) -> tuple[DeliveryReport, ...]:
    """Send the lifecycle notice to its configured channels, at most once per channel."""
    return notifier._send_lifecycle(notice)  # noqa: SLF001 - same package


def _masked(ctx: ExecutionContext, notification: Notification) -> Notification:
    return replace(
        notification,
        subject=ctx.redact(notification.subject),
        body=ctx.redact(notification.body),
        facts=tuple((ctx.redact(name), ctx.redact(value)) for name, value in notification.facts),
    )


def _error_info(ctx: ExecutionContext, error: BaseException) -> ErrorInfo:
    kind = type(error)
    module = kind.__module__
    name = kind.__qualname__ if module == "builtins" else f"{module}.{kind.__qualname__}"
    try:
        text = str(error)
    except Exception:  # noqa: BLE001 - a broken __str__ must not break the delivery report
        text = _UNPRINTABLE
    message = ctx.redact(text)
    if len(message) > _MAX_MESSAGE:
        message = message[:_MAX_MESSAGE] + "…"
    return ErrorInfo(type=name, message=message)
