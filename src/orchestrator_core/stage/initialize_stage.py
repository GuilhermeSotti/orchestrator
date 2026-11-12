from __future__ import annotations

from ..context import ExecutionContext
from .base_stage import BaseStage, StageResult


class InitializeStage(BaseStage):
    """Marks the execution as initializing and records the start of the run."""

    def execute(self, context: ExecutionContext) -> StageResult:
        context.set_status("initializing")
        context.mark_started()
        context.add_log("initialization complete")
        return StageResult.SUCCESS
