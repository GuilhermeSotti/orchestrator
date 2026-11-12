from __future__ import annotations

from .pipeline import ExecutionPipeline, ExecutionResult
from .registry import CapabilityRegistry
from .spec import ExecutionSpecification


class ExecutionEngine:
    """High-level orchestration facade for running execution specifications."""

    def __init__(self, registry: CapabilityRegistry | None = None, pipeline: ExecutionPipeline | None = None) -> None:
        self.registry = registry or CapabilityRegistry()
        self.pipeline = pipeline or ExecutionPipeline()

    def run(self, spec: ExecutionSpecification) -> ExecutionResult:
        """Execute a specification through the configured pipeline."""
        return self.pipeline.run(spec)
