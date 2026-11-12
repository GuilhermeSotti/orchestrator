from __future__ import annotations

from typing import Protocol


class SecretsPort(Protocol):
    """Contract for retrieving secrets securely."""

    def get_secret(self, key: str) -> str | None:
        ...
