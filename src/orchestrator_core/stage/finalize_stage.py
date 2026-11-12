from __future__ import annotations

from ..context import ExecutionContext
from .base_stage import BaseStage, StageResult


class FinalizeStage(BaseStage):
    """Marks the execution as completed and records finalization."""

    def execute(self, context: ExecutionContext) -> StageResult:
        context.mark_finished()
        context.set_status("completed")
        context.add_log("finalization complete")
        return StageResult.SUCCESS
