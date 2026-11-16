"""Step tracking (RFC-0005, 2.3): results, records, events, metrics, logs, limits and threads."""

from __future__ import annotations

import contextvars
import io
import json
import logging
import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor

import pytest

from orchestrator_core import (
    CancellationToken,
    CapabilityError,
    ExecutionContext,
    ExecutionStatus,
    FunctionStage,
    Phase,
    RuntimeBuilder,
    StepFinished,
    StepStarted,
)
from orchestrator_core._secrets import EnvSecretResolver
from orchestrator_core.logs import configure_logging
from orchestrator_core.testing import EventRecorder, FakeClock, InMemoryMetrics

SENTINEL = "S3NT1NEL-step-error-91c2"


class Boom(Exception):
    pass


def test_nested_steps_are_kept_in_the_result_the_record_and_the_events(
    builder: RuntimeBuilder, clock: FakeClock, events: EventRecorder, metrics: InMemoryMetrics
) -> None:
    def automation(ctx: ExecutionContext) -> None:
        with ctx.step("download"):
            clock.advance(2)
            with ctx.step("unzip"):
                clock.advance(1)
        with ctx.step("download"):  # names may repeat
            pass

    result = builder.build().run(automation, name="statement")
    assert result.succeeded
    steps = [(s.index, s.name, s.parent, s.stage, s.status) for s in result.steps]
    assert steps == [
        (1, "download", None, "execute_automation", ExecutionStatus.SUCCEEDED),
        (2, "unzip", 1, "execute_automation", ExecutionStatus.SUCCEEDED),
        (3, "download", None, "execute_automation", ExecutionStatus.SUCCEEDED),
    ]
    assert [s.duration for s in result.steps] == [3.0, 1.0, 0.0]
    assert result.steps[0].started_at == result.started_at
    record = result.record.to_dict()
    assert record["steps_truncated"] is False
    assert [(s["index"], s["name"], s["parent"]) for s in record["steps"]] == [  # type: ignore[union-attr]
        (1, "download", None),
        (2, "unzip", 1),
        (3, "download", None),
    ]
    json.dumps(record)  # serializable
    started = events.of_type(StepStarted)
    finished = events.of_type(StepFinished)
    assert [(e.step, e.index, e.parent) for e in started] == [
        ("download", 1, None),
        ("unzip", 2, 1),
        ("download", 3, None),
    ]
    assert [(e.step, e.index, e.status) for e in finished] == [
        ("unzip", 2, ExecutionStatus.SUCCEEDED),
        ("download", 1, ExecutionStatus.SUCCEEDED),
        ("download", 3, ExecutionStatus.SUCCEEDED),
    ]
    assert all(e.execution_id == result.execution_id for e in started + finished)
    assert metrics.values("orchestrator.step.duration_seconds", step="download") == [3.0, 0.0]
    assert metrics.values("orchestrator.step.duration_seconds", status="succeeded") == [
        1.0,
        3.0,
        0.0,
    ]


def test_a_failing_step_records_a_masked_error_and_reraises_the_original() -> None:
    events = EventRecorder()
    runtime = (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_secret_resolver("env", EnvSecretResolver({"TOKEN": SENTINEL}))
        .on_event(StepFinished, events)
        .build()
    )
    raised: list[BaseException] = []

    def automation(ctx: ExecutionContext) -> None:
        token = ctx.secrets.resolve("env:TOKEN").reveal()
        try:
            with ctx.step("outer"), ctx.step("inner"):
                raise Boom(f"rejected {token}")
        except Boom as exc:
            raised.append(exc)
            raise

    result = runtime.run(automation)
    assert result.status is ExecutionStatus.FAILED
    (original,) = raised
    assert result.error is original  # unchanged
    inner, outer = sorted(result.steps, key=lambda s: s.index, reverse=True)
    assert inner.error is original
    assert outer.error is original  # the exception left both steps
    assert inner.status is outer.status is ExecutionStatus.FAILED
    texts = [json.dumps(result.record.to_dict()), repr(events.events), repr(result.steps)]
    for text in texts:
        assert SENTINEL not in text
    assert result.record.steps[0].error is not None
    assert result.record.steps[0].error.message == "rejected ***"
    assert [e.error.message for e in events.events if isinstance(e, StepFinished) and e.error] == [
        "rejected ***",
        "rejected ***",
    ]


def test_interruptions_inside_a_step_map_to_its_status(
    builder: RuntimeBuilder, clock: FakeClock
) -> None:
    token = CancellationToken()

    def cancelled(ctx: ExecutionContext) -> None:
        with ctx.step("wait_for_file"):
            token.cancel("operator")
            ctx.sleep(10)

    result = builder.build().run(cancelled, cancellation=token)
    assert result.status is ExecutionStatus.CANCELLED
    assert result.steps[0].status is ExecutionStatus.CANCELLED

    def slow(ctx: ExecutionContext) -> None:
        with ctx.step("poll"):
            ctx.sleep(10)

    result = builder.build().run(slow, timeout=3)
    assert result.status is ExecutionStatus.TIMED_OUT
    assert result.steps[0].status is ExecutionStatus.TIMED_OUT
    assert result.steps[0].duration == 3.0


def test_keyboard_interrupt_inside_a_step_counts_as_cancelled(builder: RuntimeBuilder) -> None:
    results: list[ExecutionContext] = []

    def automation(ctx: ExecutionContext) -> None:
        results.append(ctx)
        with ctx.step("interactive"):
            raise KeyboardInterrupt

    events = EventRecorder()
    with pytest.raises(KeyboardInterrupt):
        builder.on_event(StepFinished, events).build().run(automation)
    (finished,) = events.of_type(StepFinished)
    assert finished.status is ExecutionStatus.CANCELLED


def test_step_names_are_validated_and_closed_contexts_refuse_steps(
    builder: RuntimeBuilder,
) -> None:
    contexts: list[ExecutionContext] = []

    def automation(ctx: ExecutionContext) -> None:
        contexts.append(ctx)
        for name in ("", "Download", "1st", "with space", "x" * 65, 42):
            with pytest.raises(ValueError, match="invalid step name"):
                ctx.step(name)  # type: ignore[arg-type]
        with ctx.step("a" * 64):
            pass

    result = builder.build().run(automation)
    assert result.succeeded, result.error
    assert len(result.steps) == 1
    with pytest.raises(CapabilityError, match="closed"):
        contexts[0].step("late")


def test_the_step_limit_truncates_the_record_but_not_events_or_metrics(
    builder: RuntimeBuilder,
    events: EventRecorder,
    metrics: InMemoryMetrics,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def automation(ctx: ExecutionContext) -> None:
        for _ in range(5):
            with ctx.step("item"):
                pass

    runtime = builder.with_settings({"runtime": {"max_steps": 3}}).build()
    with caplog.at_level(logging.WARNING, logger="orchestrator_core.steps"):
        result = runtime.run(automation)
    assert result.succeeded
    assert [s.index for s in result.steps] == [1, 2, 3]
    assert result.record.steps_truncated is True
    assert len(result.record.steps) == 3
    assert len(events.of_type(StepFinished)) == 5
    assert len(metrics.values("orchestrator.step.duration_seconds")) == 5
    warnings = [r for r in caplog.records if "step limit of 3" in r.getMessage()]
    assert len(warnings) == 1


def test_the_default_step_limit_is_1000(builder: RuntimeBuilder) -> None:
    def automation(ctx: ExecutionContext) -> None:
        for _ in range(1001):
            with ctx.step("item"):
                pass

    result = builder.build().run(automation)
    assert len(result.steps) == 1000
    assert result.record.steps_truncated is True


@pytest.fixture
def captured_json() -> Iterator[io.StringIO]:
    stream = io.StringIO()
    handler = configure_logging("DEBUG", stream=stream, json_output=True)
    try:
        yield stream
    finally:
        logging.getLogger().removeHandler(handler)


def test_log_records_carry_the_current_step(
    builder: RuntimeBuilder, captured_json: io.StringIO
) -> None:
    def automation(ctx: ExecutionContext) -> None:
        ctx.logger.info("before")
        with ctx.step("outer"):
            logging.getLogger("acme").info("in outer")
            with ctx.step("inner"):
                ctx.logger.info("in inner")
            ctx.logger.info("back in outer")
        ctx.logger.info("after")

    assert builder.build().run(automation).succeeded
    lines = [json.loads(line) for line in captured_json.getvalue().splitlines()]
    by_message = {line["message"]: line["step"] for line in lines}
    assert by_message["before"] == "-"
    assert by_message["in outer"] == "outer"
    assert by_message["in inner"] == "inner"
    assert by_message["back in outer"] == "outer"
    assert by_message["after"] == "-"


def test_steps_run_in_teardown_stages_and_finalizers(builder: RuntimeBuilder) -> None:
    def close_systems(ctx: ExecutionContext) -> None:
        with ctx.step("close_systems"):
            pass

    stage = FunctionStage("wrap_up", Phase.TEARDOWN, close_systems)

    def automation(ctx: ExecutionContext) -> None:
        def finalizer(outcome: object) -> None:
            with ctx.step("logout"):
                pass

        ctx.add_finalizer(finalizer)

    result = builder.with_stage(stage, after="finalize").build().run(automation)
    assert result.succeeded
    assert [(s.name, s.stage) for s in result.steps] == [
        ("logout", "finalize"),
        ("close_systems", "wrap_up"),
    ]
    assert [s.name for s in result.record.steps] == ["logout", "close_systems"]


def test_threads_inherit_the_current_step_only_through_a_copied_context(
    builder: RuntimeBuilder,
) -> None:
    def automation(ctx: ExecutionContext) -> None:
        with ctx.step("parallel"):
            copied = contextvars.copy_context()

            def child() -> None:
                with ctx.step("child"):
                    pass

            worker = threading.Thread(target=copied.run, args=(child,))
            worker.start()
            worker.join()
            orphan = threading.Thread(target=child)
            orphan.start()
            orphan.join()

    result = builder.build().run(automation)
    assert result.succeeded
    parents = {(s.index, s.name): s.parent for s in result.steps}
    assert parents == {(1, "parallel"): None, (2, "child"): 1, (3, "child"): None}


def test_nested_executions_do_not_inherit_the_outer_step(builder: RuntimeBuilder) -> None:
    inner_runtime = RuntimeBuilder().with_environment({}, prefix=None).build()

    def inner(ctx: ExecutionContext) -> None:
        with ctx.step("inner_step"):
            pass

    def outer(ctx: ExecutionContext) -> object:
        with ctx.step("outer_step"):
            return inner_runtime.run(inner)

    result = builder.build().run(outer)
    inner_result = result.output
    assert [s.parent for s in inner_result.steps] == [None]  # type: ignore[attr-defined]
    assert [s.name for s in result.steps] == ["outer_step"]


def test_stress_concurrent_executions_with_nested_steps_do_not_mix() -> None:
    runtime = RuntimeBuilder().with_environment({}, prefix=None).build()

    def automation(ctx: ExecutionContext) -> str:
        label = f"run_{ctx.parameters['n']}"
        for _ in range(5):
            with ctx.step(label), ctx.step("nested"):
                ctx.check()
        return label

    def run(n: int) -> tuple[str, list[tuple[int, str, int | None]]]:
        result = runtime.run(automation, parameters={"n": n})
        assert result.succeeded, result.error
        return str(result.output), [(s.index, s.name, s.parent) for s in result.steps]

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(run, range(200)))
    for label, steps in outcomes:
        assert len(steps) == 10
        assert [name for _, name, _ in steps] == [label, "nested"] * 5
        for index, name, parent in steps:
            assert parent == (None if name == label else index - 1)


def test_an_interrupt_in_a_step_started_handler_does_not_leak_the_step() -> None:
    """Regression (audit of 2026-11-15): the step stayed current after the failed handler."""
    calls: list[str] = []

    def handler(event: StepStarted) -> None:
        calls.append(event.step)
        if event.step == "first":
            raise KeyboardInterrupt

    runtime = RuntimeBuilder().with_environment({}, prefix=None).on_event(StepStarted, handler)

    def automation(ctx: ExecutionContext) -> None:
        with pytest.raises(KeyboardInterrupt), ctx.step("first"):
            calls.append("body")  # never runs
        with ctx.step("second"):
            pass

    result = runtime.build().run(automation)
    assert result.succeeded, result.error
    assert calls == ["first", "second"]
    assert [(s.name, s.parent) for s in result.steps] == [("second", None)]
