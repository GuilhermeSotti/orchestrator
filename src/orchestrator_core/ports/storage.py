from __future__ import annotations

from typing import Protocol

from ..context import ExecutionContext


class StoragePort(Protocol):
    """Contract for persisting execution outcomes."""

    def save_result(self, context: ExecutionContext) -> None:
        ...
