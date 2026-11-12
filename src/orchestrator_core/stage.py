from __future__ import annotations

from abc import ABC, abstractmethod

from .context import ExecutionContext


class Stage(ABC):
    """Interface for pipeline stages implementing the execution lifecycle."""

    @abstractmethod
    def run(self, context: ExecutionContext) -> None:
        raise NotImplementedError


class InitializeStage(Stage):
    def run(self, context: ExecutionContext) -> None:
        context.set_status("initializing")
        context.add_log("initialization complete")


class ExecuteStage(Stage):
    def run(self, context: ExecutionContext) -> None:
        context.set_status("executing")
        context.add_log(f"executing tasks: {', '.join(context.spec.tasks)}")


class FinalizeStage(Stage):
    def run(self, context: ExecutionContext) -> None:
        context.set_status("completed")
        context.add_log("finalization complete")


class StageFailure(RuntimeError):
    """Raised when a stage fails and the pipeline should stop."""
