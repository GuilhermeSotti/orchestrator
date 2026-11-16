"""Lifecycle semantics of RFC-0001: failure matrix, teardown guarantees and extension points."""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import Mapping
from pathlib import Path

import pytest

from orchestrator_core import (
    Capability,
    ConfigurationError,
    ExecutionContext,
    ExecutionFailedError,
    ExecutionFinished,
    ExecutionOutcome,
    ExecutionStatus,
    FunctionStage,
    Phase,
    PipelineDefinitionError,
    RuntimeBuilder,
    Stage,
    StageStatus,
    _stages,
)
from orchestrator_core.testing import EventRecorder, InMemoryMetrics, InMemoryRecordSink

STAGES = (
    "initialize",
    "provision_dependencies",
    "prepare_environment",
    "prepare_execution",
    "execute_automation",
    "finalize",
    "persist_logs",
    "shutdown",
)
TEARDOWN = {"finalize", "persist_logs", "shutdown"}
STAGE_CLASSES = {
    "initialize": _stages.InitializeStage,
    "provision_dependencies": _stages.ProvisionDependenciesStage,
    "prepare_environment": _stages.PrepareEnvironmentStage,
    "prepare_execution": _stages.PrepareExecutionStage,
    "execute_automation": _stages.ExecuteAutomationStage,
    "finalize": _stages.FinalizeStage,
    "persist_logs": _stages.PersistLogsStage,
    "shutdown": _stages.ShutdownStage,
}


class Boom(Exception):
    pass


def test_default_pipeline_has_the_eight_documented_stages(
    builder: RuntimeBuilder,
) -> None:
    runtime = builder.build()
    assert runtime.stages == STAGES
    result = runtime.run(lambda ctx: "ok", name="noop")
    assert [s.name for s in result.stages] == list(STAGES)
    assert all(s.status is StageStatus.SUCCEEDED for s in result.stages)
    assert result.output == "ok"
    assert result.automation == "noop"


@pytest.mark.parametrize("failing", STAGES)
def test_failure_matrix(
    failing: str, builder: RuntimeBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failure in any stage: later prepare/execute stages are skipped, teardown always runs."""
    error = Boom(f"failure injected in {failing}")
    original = STAGE_CLASSES[failing].run

    def failing_run(self: Stage, ctx: ExecutionContext) -> None:
        original(self, ctx)
        raise error

    monkeypatch.setattr(STAGE_CLASSES[failing], "run", failing_run)
    released: list[str] = []

    def automation(ctx: ExecutionContext) -> str:
        ctx.resources.callback(released.append, "resource")
        return "done"

    result = builder.build().run(automation)

    assert result.status is ExecutionStatus.FAILED
    assert result.error is error
    statuses = {s.name: s.status for s in result.stages}
    position = STAGES.index(failing)
    for index, name in enumerate(STAGES):
        if name == failing:
            expected = StageStatus.FAILED
        elif name in TEARDOWN or index < position:
            expected = StageStatus.SUCCEEDED
        else:
            expected = StageStatus.SKIPPED
        assert statuses[name] is expected, name
    if failing in TEARDOWN:
        assert result.teardown_errors == (error,)
    else:
        assert result.teardown_errors == ()
    automation_ran = (
        position > STAGES.index("execute_automation") or failing == "execute_automation"
    )
    if automation_ran:
        assert released == ["resource"] or failing == "finalize"
    else:
        assert released == []


def test_teardown_errors_are_aggregated_and_do_not_mask_the_primary_error(
    builder: RuntimeBuilder,
) -> None:
    primary = Boom("primary")
    order: list[str] = []

    def automation(ctx: ExecutionContext) -> None:
        def first(outcome: ExecutionOutcome) -> None:
            order.append("finalizer-1")
            raise Boom("finalizer-1")

        def second(outcome: ExecutionOutcome) -> None:
            order.append(f"finalizer-2:{outcome.status.value}")

        ctx.add_finalizer(first)
        ctx.add_finalizer(second)
        ctx.resources.callback(order.append, "resource-1")
        ctx.resources.callback(_raise, Boom("resource-2"))
        raise primary

    result = builder.build().run(automation)

    assert result.status is ExecutionStatus.FAILED
    assert result.error is primary
    assert order == ["finalizer-2:failed", "finalizer-1", "resource-1"]
    (group,) = result.teardown_errors
    assert isinstance(group, ExceptionGroup)
    assert [str(e) for e in group.exceptions] == ["finalizer-1", "resource-2"]
    assert result.stage("finalize").status is StageStatus.FAILED
    assert result.stage("persist_logs").status is StageStatus.SUCCEEDED
    assert result.record.error is not None
    assert result.record.error.message == "primary"


def test_successful_execution_with_failing_teardown_is_failed(
    builder: RuntimeBuilder,
) -> None:
    def automation(ctx: ExecutionContext) -> int:
        ctx.resources.callback(_raise, Boom("cleanup failed"))
        return 7

    result = builder.build().run(automation)
    assert result.status is ExecutionStatus.FAILED
    assert str(result.error) == "cleanup failed"
    assert result.output == 7
    with pytest.raises(ExecutionFailedError, match="cleanup failed") as info:
        result.raise_for_status()
    assert info.value.__cause__ is result.error
    assert info.value.result is result


def test_finalizers_see_the_success_outcome_and_run_before_resources(
    builder: RuntimeBuilder,
) -> None:
    seen: list[str] = []

    def automation(ctx: ExecutionContext) -> None:
        ctx.resources.callback(seen.append, "resource")
        ctx.add_finalizer(lambda outcome: seen.append(f"finalizer:{outcome.succeeded}"))

    assert builder.build().run(automation).succeeded
    assert seen == ["finalizer:True", "resource"]


def test_custom_stages_can_be_inserted_without_changing_the_builtin_ones(
    builder: RuntimeBuilder,
) -> None:
    calls: list[str] = []
    runtime = (
        builder.with_stage(
            FunctionStage("load_secrets", Phase.PREPARE, lambda ctx: calls.append("prepare")),
            before="prepare_execution",
        )
        .with_stage(
            FunctionStage("post_process", Phase.EXECUTE, lambda ctx: calls.append("post")),
            after="execute_automation",
        )
        .with_stage(
            FunctionStage("notify", Phase.TEARDOWN, lambda ctx: calls.append("notify")),
            after="finalize",
        )
        .build()
    )
    assert runtime.stages == (
        "initialize",
        "provision_dependencies",
        "prepare_environment",
        "load_secrets",
        "prepare_execution",
        "execute_automation",
        "post_process",
        "finalize",
        "notify",
        "persist_logs",
        "shutdown",
    )
    assert runtime.run(lambda ctx: calls.append("automation")).succeeded
    assert calls == ["prepare", "automation", "post", "notify"]


@pytest.mark.parametrize(
    ("stage", "where", "message"),
    [
        (
            FunctionStage("x", Phase.PREPARE, print),
            {"before": "nope"},
            "unknown stage 'nope'",
        ),
        (FunctionStage("x", Phase.PREPARE, print), {}, "exactly one"),
        (
            FunctionStage("x", Phase.PREPARE, print),
            {"before": "a", "after": "b"},
            "exactly one",
        ),
        (
            FunctionStage("x", Phase.TEARDOWN, print),
            {"before": "execute_automation"},
            "cannot run after",
        ),
        (
            FunctionStage("x", Phase.PREPARE, print),
            {"after": "finalize"},
            "cannot run after",
        ),
        (
            FunctionStage("x", Phase.PREPARE, print),
            {"before": "initialize"},
            "must be 'initialize'",
        ),
        (
            FunctionStage("finalize", Phase.TEARDOWN, print),
            {"after": "shutdown"},
            "duplicate",
        ),
        (
            FunctionStage("Bad Name", Phase.TEARDOWN, print),
            {"after": "shutdown"},
            "invalid stage name",
        ),
    ],
)
def test_invalid_pipelines_are_rejected(
    builder: RuntimeBuilder, stage: Stage, where: dict[str, str], message: str
) -> None:
    with pytest.raises(PipelineDefinitionError, match=message):
        builder.with_stage(stage, **where).build()


def test_parameters_are_read_only_and_can_be_validated(builder: RuntimeBuilder) -> None:
    @dataclasses.dataclass(frozen=True)
    class Params:
        day: str
        limit: int

    def validate(raw: Mapping[str, object]) -> Params:
        return Params(day=str(raw["day"]), limit=int(str(raw["limit"])))

    runtime = builder.build()

    def raw_automation(ctx: ExecutionContext) -> object:
        params = ctx.parameters
        assert isinstance(params, Mapping)
        with pytest.raises(TypeError):
            params["day"] = "x"  # type: ignore[index]
        return params["day"]

    assert runtime.run(raw_automation, parameters={"day": "2026-11-12"}).output == "2026-11-12"

    result = runtime.run(
        lambda ctx: ctx.parameters_as(Params).limit * 2,
        parameters={"day": "2026-11-12", "limit": "21"},
        parameters_validator=validate,
    )
    assert result.output == 42

    failed = runtime.run(lambda ctx: None, parameters={"day": "x"}, parameters_validator=validate)
    assert failed.stage("prepare_execution").status is StageStatus.FAILED
    assert failed.stage("execute_automation").status is StageStatus.SKIPPED
    assert isinstance(failed.error, KeyError)
    assert "while validating the parameters of the execution" in failed.error.__notes__

    wrong_type = runtime.run(lambda ctx: ctx.parameters_as(Params))
    assert isinstance(wrong_type.error, TypeError)


def test_pydantic_models_work_as_parameter_validators(builder: RuntimeBuilder) -> None:
    pydantic = pytest.importorskip("pydantic")

    class Params(pydantic.BaseModel):  # type: ignore[misc,name-defined]
        day: str
        limit: int

    result = builder.build().run(
        lambda ctx: ctx.parameters_as(Params).limit + 1,
        parameters={"day": "2026-11-12", "limit": "41"},
        parameters_validator=Params.model_validate,
    )
    assert result.output == 42


def test_workspace_lifecycle(builder: RuntimeBuilder, tmp_path: Path) -> None:
    seen: list[Path] = []

    def automation(ctx: ExecutionContext) -> None:
        (ctx.workspace / "out.txt").write_text("data", encoding="utf-8")
        seen.append(ctx.workspace)

    removed = builder.with_settings(
        {"runtime": {"workspace": True, "workspace_root": str(tmp_path)}}
    ).build()
    assert removed.run(automation).succeeded
    assert seen[-1].parent == tmp_path
    assert not seen[-1].exists()

    kept = (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_settings(
            {
                "runtime": {
                    "workspace": True,
                    "workspace_root": str(tmp_path),
                    "keep_workspace": True,
                }
            }
        )
        .build()
    )
    assert kept.run(automation).succeeded
    assert (seen[-1] / "out.txt").read_text(encoding="utf-8") == "data"


def test_workspace_is_unavailable_unless_enabled(builder: RuntimeBuilder) -> None:
    result = builder.build().run(lambda ctx: ctx.workspace)
    assert result.status is ExecutionStatus.FAILED
    assert "runtime.workspace" in str(result.error)


def test_record_sink_failures_never_change_the_execution(
    builder: RuntimeBuilder,
    sink: InMemoryRecordSink,
    metrics: InMemoryMetrics,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """RFC-0009, answer 6: a failing sink is reported, never turned into a failure."""

    class BrokenSink:
        def write(self, record: object) -> None:
            raise OSError("disk full")

    after = InMemoryRecordSink()
    runtime = builder.with_record_sink(BrokenSink()).with_record_sink(after).build()
    with caplog.at_level(logging.WARNING, logger="orchestrator_core.stages"):
        result = runtime.run(lambda ctx: None, name="report")
    (record,) = sink.records
    assert record.automation == "report"
    assert record.status is ExecutionStatus.SUCCEEDED
    assert [s.name for s in record.stages] == list(STAGES[:6])
    assert after.records == [record]  # the sinks after the broken one still run
    assert result.status is ExecutionStatus.SUCCEEDED
    assert result.error is None
    assert result.teardown_errors == ()
    assert result.stage("persist_logs").status is StageStatus.SUCCEEDED
    assert metrics.counter("orchestrator.record_sink.errors", sink="BrokenSink") == 1.0
    (warning,) = [r for r in caplog.records if "record sink" in r.getMessage()]
    assert "BrokenSink" in warning.getMessage()
    assert warning.exc_info is not None


def test_record_sink_failure_does_not_mask_a_failed_execution(builder: RuntimeBuilder) -> None:
    class BrokenSink:
        def write(self, record: object) -> None:
            raise OSError("disk full")

    def automation(ctx: ExecutionContext) -> None:
        raise Boom("primary")

    result = builder.with_record_sink(BrokenSink()).build().run(automation)
    assert result.status is ExecutionStatus.FAILED
    assert isinstance(result.error, Boom)
    assert result.teardown_errors == ()


def test_context_lists_the_configured_stages(builder: RuntimeBuilder) -> None:
    """RFC-0007, answer 6: a Capability can see which stages are installed."""
    seen: list[tuple[str, ...]] = []

    class Inspect(Capability[None]):
        default_name = "inspect"

        def open(self, ctx: ExecutionContext) -> None:
            seen.append(ctx.stages)

    stage = FunctionStage("notify_outcome", Phase.TEARDOWN, lambda ctx: None)
    runtime = builder.with_capability(Inspect()).with_stage(stage, after="finalize").build()
    result = runtime.run(lambda ctx: seen.append(ctx.stages))
    assert result.succeeded
    expected = (*STAGES[:6], "notify_outcome", *STAGES[6:])
    assert seen == [expected, expected]
    assert runtime.stages == expected


def test_capability_can_refuse_a_missing_stage_before_the_automation_runs(
    builder: RuntimeBuilder,
) -> None:
    ran: list[str] = []

    class NeedsStage(Capability[None]):
        default_name = "needs_stage"

        def open(self, ctx: ExecutionContext) -> None:
            if "notify_outcome" not in ctx.stages:
                msg = "lifecycle notifications are configured but NotifyOutcome is not installed"
                raise ConfigurationError(msg)

    result = builder.with_capability(NeedsStage()).build().run(lambda ctx: ran.append("x"))
    assert result.status is ExecutionStatus.FAILED
    assert isinstance(result.error, ConfigurationError)
    assert result.stage("execute_automation").status is StageStatus.SKIPPED
    assert ran == []


def test_finalizers_receive_a_masked_error_description(builder: RuntimeBuilder) -> None:
    infos: list[ExecutionOutcome] = []

    def automation(ctx: ExecutionContext) -> None:
        ctx.add_finalizer(infos.append)
        raise Boom("broken")

    result = builder.build().run(automation)
    (outcome,) = infos
    assert outcome.status is ExecutionStatus.FAILED
    assert outcome.error is result.error
    assert outcome.error_info is not None
    assert outcome.error_info.message == "broken"
    assert outcome.error_info.type.endswith("Boom")
    succeeded: list[ExecutionOutcome] = []
    assert builder.build().run(lambda ctx: ctx.add_finalizer(succeeded.append)).succeeded
    assert succeeded[0].error_info is None


def test_keyboard_interrupt_runs_teardown_then_propagates(
    builder: RuntimeBuilder, events: EventRecorder
) -> None:
    released: list[str] = []

    def automation(ctx: ExecutionContext) -> None:
        ctx.resources.callback(released.append, "resource")
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        builder.build().run(automation)
    assert released == ["resource"]
    (finished,) = events.of_type(ExecutionFinished)
    assert finished.status is ExecutionStatus.CANCELLED


def test_context_is_closed_after_shutdown(builder: RuntimeBuilder) -> None:
    contexts: list[ExecutionContext] = []
    assert builder.build().run(contexts.append).succeeded
    ctx = contexts[0]
    with pytest.raises(Exception, match="closed"):
        ctx.add_finalizer(lambda outcome: None)
    with pytest.raises(RuntimeError, match="already closed"):
        ctx.resources.callback(print)
    assert ctx.outcome is not None
    assert "execution_id" in repr(ctx)


def test_run_argument_validation(builder: RuntimeBuilder) -> None:
    runtime = builder.build()
    with pytest.raises(TypeError, match="callable"):
        runtime.run("not callable")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="timeout"):
        runtime.run(lambda ctx: None, timeout=0)
    with pytest.raises(ValueError, match="execution_id"):
        runtime.run(lambda ctx: None, execution_id="has spaces")
    result = runtime.run(lambda ctx: ctx.execution_id, execution_id="job-42:attempt.1")
    assert result.execution_id == result.output == "job-42:attempt.1"


def _raise(error: BaseException) -> None:
    raise error


def test_an_exception_whose_str_fails_does_not_break_the_pipeline(
    builder: RuntimeBuilder, events: EventRecorder
) -> None:
    """Regression (audit of 2026-11-15): in 0.1.0, run() raised and skipped teardown."""
    released: list[str] = []

    class Unprintable(Exception):
        def __str__(self) -> str:
            raise RuntimeError("str() is broken")

    def automation(ctx: ExecutionContext) -> None:
        ctx.resources.callback(released.append, "resource")
        with ctx.step("call_driver"):
            raise Unprintable

    result = builder.build().run(automation)
    assert result.status is ExecutionStatus.FAILED
    assert isinstance(result.error, Unprintable)
    assert released == ["resource"]  # teardown ran
    assert result.record.error is not None
    assert result.record.error.message == "<exception str() failed>"
    assert result.record.steps[0].error is not None
    assert result.record.steps[0].error.message == "<exception str() failed>"
    (finished,) = events.of_type(ExecutionFinished)
    assert finished.status is ExecutionStatus.FAILED
