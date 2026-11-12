from __future__ import annotations

from typing import Any, Protocol


class CachePort(Protocol):
    """Contract for temporary data caching."""

    def get(self, key: str) -> Any:
        ...

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ...
