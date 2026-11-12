from __future__ import annotations

from typing import Any, Protocol


class WorkQueuePort(Protocol):
    """Contract for pulling work items from a queue."""

    def pull_item(self) -> Any:
        ...

    def ack_item(self, item_id: str) -> None:
        ...
