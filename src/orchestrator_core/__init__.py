"""Hexagonal runtime core for orchestrating automation workflows."""

from .bootstrap import build_runtime
from .context import ExecutionContext
from .execution_engine import ExecutionEngine
from .pipeline import ExecutionPipeline, ExecutionResult, PipelineBuilder, StageResult
from .registry import CapabilityRegistry
from .spec import ExecutionSpecification
from .specification import ExecutionSpecification as Specification
from .stage import Stage

__all__ = [
    "CapabilityRegistry",
    "ExecutionContext",
    "ExecutionEngine",
    "ExecutionPipeline",
    "ExecutionResult",
    "ExecutionSpecification",
    "PipelineBuilder",
    "Specification",
    "Stage",
    "StageResult",
    "build_runtime",
]
