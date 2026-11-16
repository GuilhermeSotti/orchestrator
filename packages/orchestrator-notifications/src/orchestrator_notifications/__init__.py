"""Notifications Capability of the Orchestrator platform.

Automations send notifications to named channels; lifecycle notices
(started, succeeded, failed, cancelled, timed out) are sent by the stages
:class:`NotifyStarted` and :class:`NotifyOutcome` when configured. Channel
technologies are Providers of :class:`NotificationChannel`, such as
``orchestrator-notifications-smtp`` and ``orchestrator-notifications-teams``.
The public submodule :mod:`orchestrator_notifications.testing` holds an
in-memory channel and the conformance suite of the channel Providers.
"""

from orchestrator_notifications._capability import NotificationCapability
from orchestrator_notifications._channel import NotificationChannel
from orchestrator_notifications._errors import NotificationError
from orchestrator_notifications._events import NOTIFICATIONS_FAILED, NotificationFailed
from orchestrator_notifications._model import (
    NOTIFY_OUTCOME,
    NOTIFY_STARTED,
    STATUSES,
    DeliveryReport,
    DeliveryStatus,
    LifecycleNotice,
    Notification,
    Severity,
)
from orchestrator_notifications._notifier import ChannelSettings, Formatter, Notifier
from orchestrator_notifications._stages import NotifyOutcome, NotifyStarted
from orchestrator_notifications._texts import default_formatter
from orchestrator_notifications._version import __version__

__all__ = [
    "NOTIFICATIONS_FAILED",
    "NOTIFY_OUTCOME",
    "NOTIFY_STARTED",
    "STATUSES",
    "ChannelSettings",
    "DeliveryReport",
    "DeliveryStatus",
    "Formatter",
    "LifecycleNotice",
    "Notification",
    "NotificationCapability",
    "NotificationChannel",
    "NotificationError",
    "NotificationFailed",
    "Notifier",
    "NotifyOutcome",
    "NotifyStarted",
    "Severity",
    "__version__",
    "default_formatter",
]
