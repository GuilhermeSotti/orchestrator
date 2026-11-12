from __future__ import annotations

from ..context import ExecutionContext
from .base_stage import BaseStage, StageResult


class ShutdownStage(BaseStage):
    """Records the shutdown phase of the execution lifecycle."""

    def execute(self, context: ExecutionContext) -> StageResult:
        context.set_status("shutdown")
        context.add_log("shutdown complete")
        return StageResult.SUCCESS
