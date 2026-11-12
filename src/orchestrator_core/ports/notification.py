from __future__ import annotations

from typing import Protocol

from ..context import ExecutionContext


class NotificationPort(Protocol):
    """Contract for sending notifications about execution status."""

    def notify(self, status: str, context: ExecutionContext) -> None:
        ...
