"""Notification model: the message, its severity and the delivery report."""

from __future__ import annotations

import enum
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

from orchestrator_core import ErrorInfo

_KIND_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
STATUSES = ("started", "succeeded", "failed", "cancelled", "timed_out")
"""Lifecycle statuses that can be configured in ``[capabilities.<name>.lifecycle]``."""
NOTIFY_STARTED = "notify_started"
"""Name of the stage that sends the ``started`` notice."""
NOTIFY_OUTCOME = "notify_outcome"
"""Name of the stage that sends the outcome notice."""


class Severity(enum.StrEnum):
    """How important a notification is. Channels may render it (color, prefix)."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True, kw_only=True)
class Notification:
    """A message for people. The recipients belong to the channel, not to the message.

    Example:
        >>> Notification(subject="Lote processado", body="120 itens", facts=(("Lote", "42"),)).facts
        (('Lote', '42'),)

    Attributes:
        subject: One-line title.
        body: Plain text.
        severity: Importance of the message.
        facts: Name and value pairs shown by the channel.
        kind: Identifier of the kind of message, such as ``execution.failed``.
        dedup_key: Optional key that lets channels avoid duplicates.
    """

    subject: str
    body: str
    severity: Severity = Severity.INFO
    facts: tuple[tuple[str, str], ...] = field(default=())
    kind: str = "custom"
    dedup_key: str | None = None

    def __post_init__(self) -> None:
        if not self.subject.strip():
            msg = "subject must not be empty"
            raise ValueError(msg)
        object.__setattr__(self, "severity", Severity(self.severity))
        object.__setattr__(self, "facts", _pairs(self.facts))
        if not _KIND_RE.match(self.kind):
            msg = "kind must use lowercase letters, digits, '.', '-' or '_' (max. 64)"
            raise ValueError(msg)
        if self.dedup_key is not None and not self.dedup_key:
            msg = "dedup_key must not be empty when given"
            raise ValueError(msg)


def _pairs(facts: Iterable[object]) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    for item in facts:
        if not (isinstance(item, tuple) and len(item) == 2):  # noqa: PLR2004 - a pair
            msg = "facts must be a sequence of (name, value) pairs"
            raise TypeError(msg)
        name, value = item
        if not isinstance(name, str) or not isinstance(value, str):
            msg = "fact names and values must be strings"
            raise TypeError(msg)
        pairs.append((name, value))
    return tuple(pairs)


class DeliveryStatus(enum.StrEnum):
    """Result of one delivery attempt to one channel."""

    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class DeliveryReport:
    """What happened to one notification on one channel.

    Attributes:
        channel: Channel name.
        kind: Kind of the notification.
        status: ``sent``, ``failed`` or ``skipped``.
        attempts: Number of delivery attempts made.
        error: Masked description of the last error, when failed.
    """

    channel: str
    kind: str
    status: DeliveryStatus
    attempts: int
    error: ErrorInfo | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class LifecycleNotice:
    """Data available to the formatter of lifecycle notifications.

    Attributes:
        status: One of :data:`STATUSES`.
        automation: Automation name.
        runtime: Runtime name.
        execution_id: Execution identifier.
        started_at: Start time of the execution (UTC).
        duration: Seconds since the start; ``None`` for ``started``.
        error: Masked error of the execution, if any.
    """

    status: str
    automation: str
    runtime: str
    execution_id: str
    started_at: datetime
    duration: float | None = None
    error: ErrorInfo | None = None
