from __future__ import annotations

from typing import Protocol


class MetricsPort(Protocol):
    """Contract for recording runtime metrics."""

    def record(self, metric_name: str, value: float) -> None:
        ...
