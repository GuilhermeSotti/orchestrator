from __future__ import annotations

from typing import Any, Protocol

from ..spec import ExecutionSpecification


class InfrastructurePort(Protocol):
    """Contract for provisioning execution environments."""

    def setup_environment(self, spec: ExecutionSpecification) -> Any:
        ...
