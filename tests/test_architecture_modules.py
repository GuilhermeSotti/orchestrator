from __future__ import annotations

from orchestrator_core.bootstrap import build_runtime
from orchestrator_core.context import ExecutionContext
from orchestrator_core.execution_engine import ExecutionEngine
from orchestrator_core.specification import ExecutionSpecification
from orchestrator_core.stage.base_stage import BaseStage


class DummyStage(BaseStage):
    def execute(self, context: ExecutionContext) -> None:
        context.add_log("dummy")


def test_bootstrap_builds_runtime_with_registry_and_pipeline() -> None:
    runtime = build_runtime()

    assert isinstance(runtime, ExecutionEngine)
    assert runtime.pipeline is not None
    assert runtime.registry is not None


def test_execution_engine_runs_a_specification() -> None:
    engine = ExecutionEngine()
    spec = ExecutionSpecification.from_mapping({"name": "demo", "tasks": ["task-a"]})

    result = engine.run(spec)

    assert result.status == "success"
    assert result.context.spec.name == "demo"


def test_base_stage_can_be_extended_for_custom_pipeline_steps() -> None:
    context = ExecutionContext.from_spec(ExecutionSpecification.from_mapping({"name": "demo", "tasks": ["task-a"]}))

    DummyStage().execute(context)

    assert context.logs == ["dummy"]
