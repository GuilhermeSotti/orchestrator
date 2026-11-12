from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from .context import ExecutionContext
from .registry import CapabilityRegistry
from .spec import ExecutionSpecification
from .stage import ExecuteStage, FinalizeStage, InitializeStage, Stage, StageFailure, StageResult


@dataclass
class ExecutionResult:
    """Outcome of a pipeline execution."""

    status: str
    context: ExecutionContext
    duration_seconds: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


class ExecutionPipeline:
    """Orchestrates a sequence of stages around an execution specification."""

    def __init__(self, stages: list[Stage] | None = None) -> None:
        self.stages = stages or [InitializeStage(), ExecuteStage(), FinalizeStage()]

    def run(self, spec: ExecutionSpecification) -> ExecutionResult:
        context = ExecutionContext.from_spec(spec)
        started_at = perf_counter()

        try:
            for stage in self.stages:
                if hasattr(stage, "should_run") and callable(stage.should_run) and not stage.should_run(context):
                    context.add_log(f"skipped stage: {stage.__class__.__name__}")
                    continue

                result = stage.run(context)
                if result is None:
                    result = StageResult.SUCCESS

                if result in {StageResult.FAILURE, StageResult.CANCELLED}:
                    context.set_status("failed")
                    context.add_log(f"stage failed: {stage.__class__.__name__}")
                    return ExecutionResult(
                        status="failure",
                        context=context,
                        duration_seconds=perf_counter() - started_at,
                        details={"stages": len(self.stages)},
                    )

                if result == StageResult.RETRY:
                    context.add_log(f"retry requested by: {stage.__class__.__name__}")

        except StageFailure as exc:
            context.set_status("failed")
            context.add_log(str(exc))
            return ExecutionResult(status="failure", context=context, duration_seconds=perf_counter() - started_at)
        except Exception as exc:  # pragma: no cover - defensive branch
            context.set_status("failed")
            context.add_log(f"pipeline error: {exc}")
            return ExecutionResult(status="failure", context=context, duration_seconds=perf_counter() - started_at)

        if context.status == "pending":
            context.set_status("completed")

        return ExecutionResult(
            status="success",
            context=context,
            duration_seconds=perf_counter() - started_at,
            details={"stages": len(self.stages)},
        )


class PipelineBuilder:
    """Builds a pipeline from common stages plus capability-provided stages."""

    def __init__(self, capability_registry: CapabilityRegistry | None = None) -> None:
        self.capability_registry = capability_registry or CapabilityRegistry()

    def build(self, spec: ExecutionSpecification) -> ExecutionPipeline:
        stages: list[Stage] = [InitializeStage()]
        stages.extend(self.capability_registry.get_stages_for(spec))
        stages.extend([ExecuteStage(), FinalizeStage()])
        return ExecutionPipeline(stages=stages)
