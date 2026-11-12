from __future__ import annotations

from .base_stage import BaseStage, Stage, StageResult
from .execute_stage import ExecuteStage
from .finalize_stage import FinalizeStage
from .initialize_stage import InitializeStage
from .logging_stage import LoggingStage
from .shutdown_stage import ShutdownStage


class StageFailure(RuntimeError):
    """Raised when a stage fails and the pipeline should stop."""


__all__ = [
    "BaseStage",
    "ExecuteStage",
    "FinalizeStage",
    "InitializeStage",
    "LoggingStage",
    "ShutdownStage",
    "Stage",
    "StageFailure",
    "StageResult",
]
