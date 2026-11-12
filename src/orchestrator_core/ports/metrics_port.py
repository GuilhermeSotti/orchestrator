from __future__ import annotations

from typing import Protocol


class MetricsPort(Protocol):
    """Contract for collecting execution metrics."""

    def increment_counter(self, name: str, amount: int = 1) -> None:
        ...

    def record_timing(self, name: str, value: float) -> None:
        ...
