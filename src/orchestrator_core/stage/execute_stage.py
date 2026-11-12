from __future__ import annotations

from ..context import ExecutionContext
from .base_stage import BaseStage, StageResult


class ExecuteStage(BaseStage):
    """Executes the planned tasks declared in the specification."""

    def execute(self, context: ExecutionContext) -> StageResult:
        context.set_status("executing")
        context.add_log(f"executing tasks: {', '.join(context.spec.tasks)}")
        return StageResult.SUCCESS
