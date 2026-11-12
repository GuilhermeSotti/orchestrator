from __future__ import annotations

from typing import Protocol

from ..spec import ExecutionSpecification


class ConfigurationPort(Protocol):
    """Contract for loading specifications from external configuration sources."""

    def load_spec(self, file_path: str) -> ExecutionSpecification:
        ...
