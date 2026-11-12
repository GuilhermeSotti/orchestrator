from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from ..context import ExecutionContext


class StageResult(str, Enum):
    """Explicit outcome produced by a pipeline stage."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"
    RETRY = "RETRY"


class BaseStage(ABC):
    """Base contract for pipeline stages in the clean architecture layout."""

    @abstractmethod
    def execute(self, context: ExecutionContext) -> StageResult:
        raise NotImplementedError

    def run(self, context: ExecutionContext) -> StageResult:
        result = self.execute(context)
        if result is None:
            return StageResult.SUCCESS
        return result


class Stage(BaseStage):
    """Backward-compatible stage base class that supports both execute() and run()."""

    def run(self, context: ExecutionContext) -> StageResult:
        return self.execute(context)

    def execute(self, context: ExecutionContext) -> StageResult:
        if type(self).run is not Stage.run:
            return self.run(context)
        raise NotImplementedError("Stage subclasses must implement execute() or run().")
