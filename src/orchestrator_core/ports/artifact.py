from __future__ import annotations

from typing import Any, Protocol


class ArtifactPort(Protocol):
    """Contract for persisting artifacts produced by execution."""

    def save_artifact(self, name: str, data: Any) -> None:
        ...
