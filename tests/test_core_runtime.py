from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from orchestrator_core.context import ExecutionContext
from orchestrator_core.pipeline import ExecutionPipeline, PipelineBuilder, StageResult
from orchestrator_core.registry import CapabilityRegistry
from orchestrator_core.runner.base import LocalRunner, ProcessRunner, ThreadRunner
from orchestrator_core.spec import ExecutionSpecification
from orchestrator_core.stage import Stage


class EchoStage(Stage):
    def execute(self, context: ExecutionContext) -> StageResult:
        context.add_log("echo")
        context.status = "completed"
        return StageResult.SUCCESS


class FailingStage(Stage):
    def execute(self, context: ExecutionContext) -> StageResult:
        context.add_log("failing")
        return StageResult.FAILURE


class ExtraStage(Stage):
    def execute(self, context: ExecutionContext) -> StageResult:
        context.add_log("extra")
        return StageResult.SUCCESS


def test_execution_specification_parses_required_fields() -> None:
    spec = ExecutionSpecification.from_mapping(
        {
            "name": "demo",
            "tasks": ["task-a"],
            "parameters": {"mode": "fast"},
        }
    )

    assert spec.name == "demo"
    assert spec.tasks == ["task-a"]
    assert spec.parameters["mode"] == "fast"


def test_execution_specification_rejects_missing_tasks() -> None:
    with pytest.raises(ValueError, match="tasks"):
        ExecutionSpecification.from_mapping({"name": "demo"})


def test_pipeline_runs_registered_stages() -> None:
    pipeline = ExecutionPipeline(stages=[EchoStage()])
    spec = ExecutionSpecification.from_mapping({"name": "demo", "tasks": ["task-a"]})

    result = pipeline.run(spec)

    assert result.status == "success"
    assert result.context.logs == ["echo"]


def test_local_runner_executes_specification() -> None:
    runner = LocalRunner()
    spec = ExecutionSpecification.from_mapping({"name": "demo", "tasks": ["task-a"]})

    result = runner.run(spec)

    assert result.status == "success"
    assert result.context.spec.name == "demo"


def test_thread_runner_executes_specification() -> None:
    runner = ThreadRunner()
    spec = ExecutionSpecification.from_mapping({"name": "demo", "tasks": ["task-a"]})

    result = runner.run(spec)

    assert result.status == "success"
    assert result.details["runner"]["strategy"] == "thread"


def test_process_runner_executes_specification() -> None:
    runner = ProcessRunner()
    spec = ExecutionSpecification.from_mapping({"name": "demo", "tasks": ["task-a"]})

    result = runner.run(spec)

    assert result.status == "success"
    assert result.details["runner"]["strategy"] == "process"


def test_execution_context_tracks_runtime_metadata_and_helpers() -> None:
    spec = ExecutionSpecification.from_mapping({"name": "demo", "tasks": ["task-a"]})
    context = ExecutionContext.from_spec(spec)

    context.add_log("started")
    context.set_variable("work_item", {"id": 1})
    context.add_metric("latency_ms", 12.5)
    context.add_artifact("result", {"ok": True})

    assert context.status == "pending"
    assert context.variables["work_item"]["id"] == 1
    assert context.metrics["latency_ms"] == 12.5
    assert context.artifacts["result"]["ok"] is True
    assert context.logs == ["started"]


def test_pipeline_stops_on_stage_failure() -> None:
    pipeline = ExecutionPipeline(stages=[EchoStage(), FailingStage()])
    spec = ExecutionSpecification.from_mapping({"name": "demo", "tasks": ["task-a"]})

    result = pipeline.run(spec)

    assert result.status == "failure"
    assert result.context.status == "failed"
    assert result.context.logs[:2] == ["echo", "failing"]
    assert any(log.startswith("stage failed") for log in result.context.logs)


def test_pipeline_builder_uses_registry_capabilities() -> None:
    registry = CapabilityRegistry()

    class DemoCapability:
        def is_applicable(self, spec: ExecutionSpecification) -> bool:
            return spec.name == "demo"

        def provide_stages(self, spec: ExecutionSpecification) -> list[Stage]:
            return [ExtraStage()]

    registry.register("demo", DemoCapability())
    builder = PipelineBuilder(capability_registry=registry)
    spec = ExecutionSpecification.from_mapping({"name": "demo", "tasks": ["task-a"]})

    pipeline = builder.build(spec)
    result = pipeline.run(spec)

    assert result.status == "success"
    assert "extra" in result.context.logs


def test_registry_can_register_and_resolve_provider() -> None:
    registry = CapabilityRegistry()

    class DemoProvider:
        name = "demo"

    registry.register("demo", DemoProvider())

    resolved = registry.resolve("demo")

    assert resolved is not None
    assert getattr(resolved, "name", None) == "demo"
