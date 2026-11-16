"""Events and metrics published by the notifications Capability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from orchestrator_core import ErrorInfo, Event

NOTIFICATIONS_FAILED: Final = "orchestrator.notifications.failed"
"""Counter of failed deliveries; tags ``channel`` and ``kind``."""


@dataclass(frozen=True, slots=True, kw_only=True)
class NotificationFailed(Event):
    """A notification could not be delivered to a channel.

    Attributes:
        channel: Channel name.
        kind: Kind of the notification.
        error: Masked description of the last error.
    """

    channel: str
    kind: str
    error: ErrorInfo
