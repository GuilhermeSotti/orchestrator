from __future__ import annotations

from ..context import ExecutionContext
from .base_stage import BaseStage, StageResult


class LoggingStage(BaseStage):
    """A simple stage that records a logging marker in the runtime context."""

    def execute(self, context: ExecutionContext) -> StageResult:
        context.add_log("logging stage executed")
        return StageResult.SUCCESS
