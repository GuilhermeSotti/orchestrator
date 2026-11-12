from __future__ import annotations

from typing import Protocol

from .pipeline import ExecutionResult
from .spec import ExecutionSpecification


class RunnerPort(Protocol):
    """Core execution contract that concrete runners implement."""

    def run(self, spec: ExecutionSpecification) -> ExecutionResult:
        ...
