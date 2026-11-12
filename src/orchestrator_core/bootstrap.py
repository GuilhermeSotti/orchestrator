from __future__ import annotations

from .execution_engine import ExecutionEngine
from .pipeline import ExecutionPipeline
from .registry import CapabilityRegistry
from .stage import ExecuteStage, FinalizeStage, InitializeStage


def build_runtime() -> ExecutionEngine:
    """Create a default runtime with a standard stage pipeline and registry."""
    pipeline = ExecutionPipeline(stages=[InitializeStage(), ExecuteStage(), FinalizeStage()])
    registry = CapabilityRegistry()
    return ExecutionEngine(registry=registry, pipeline=pipeline)
