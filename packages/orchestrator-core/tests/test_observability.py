"""Events, metrics and logging (D-13, D-14)."""

from __future__ import annotations

import io
import json
import logging
from collections.abc import Iterator, Mapping

import pytest

from orchestrator_core import (
    Event,
    ExecutionContext,
    ExecutionFinished,
    ExecutionStarted,
    ExecutionStatus,
    RuntimeBuilder,
    StageFinished,
    StageStatus,
)
from orchestrator_core.logs import (
    ExecutionContextFilter,
    JsonFormatter,
    RedactingFilter,
    configure_logging,
)
from orchestrator_core.testing import EventRecorder, InMemoryMetrics


def test_lifecycle_events_are_published_in_order(
    builder: RuntimeBuilder, events: EventRecorder
) -> None:
    result = builder.build().run(lambda ctx: None, name="job")
    kinds = [type(e).__name__ for e in events.events]
    assert kinds[0] == "StageStarted"  # initialize starts before announcing the execution
    assert kinds[1] == "ExecutionStarted"
    assert kinds[-1] == "ExecutionFinished"
    assert kinds.count("StageStarted") == kinds.count("StageFinished") == 8
    assert {e.execution_id for e in events.events} == {result.execution_id}
    (started,) = events.of_type(ExecutionStarted)
    assert (started.automation, started.runtime) == ("job", "orchestrator")
    finished = events.of_type(StageFinished)
    assert [e.stage for e in finished] == [stage.name for stage in result.stages]
    (done,) = events.of_type(ExecutionFinished)
    assert done.status is ExecutionStatus.SUCCEEDED
    assert done.duration == result.duration


def test_failed_stage_event_carries_masked_error_info(
    builder: RuntimeBuilder, events: EventRecorder
) -> None:
    def automation(ctx: ExecutionContext) -> None:
        raise ValueError("bad input")

    builder.build().run(automation)
    failed = [e for e in events.of_type(StageFinished) if e.status is StageStatus.FAILED]
    assert [(e.stage, e.error.type if e.error else None) for e in failed] == [
        ("execute_automation", "ValueError")
    ]


def test_failing_handlers_are_isolated(builder: RuntimeBuilder, metrics: InMemoryMetrics) -> None:
    received: list[str] = []

    def broken(event: Event) -> None:
        raise RuntimeError("handler bug")

    runtime = (
        builder.on_event(ExecutionStarted, broken)
        .on_event(ExecutionStarted, lambda e: received.append(e.automation))
        .build()
    )
    result = runtime.run(lambda ctx: None, name="resilient")
    assert result.succeeded
    assert received == ["resilient"]
    assert metrics.counter("orchestrator.event_handler.errors", event="ExecutionStarted") == 1


def test_custom_events_can_be_published(builder: RuntimeBuilder) -> None:
    from dataclasses import dataclass

    @dataclass(frozen=True, slots=True, kw_only=True)
    class InvoiceProcessed(Event):
        invoice: str

    seen: list[str] = []
    runtime = builder.on_event(InvoiceProcessed, lambda e: seen.append(e.invoice)).build()

    def automation(ctx: ExecutionContext) -> None:
        ctx.publish(
            InvoiceProcessed(execution_id=ctx.execution_id, timestamp=ctx.now(), invoice="A-1")
        )

    assert runtime.run(automation).succeeded
    assert seen == ["A-1"]


def test_subscription_validation() -> None:
    with pytest.raises(TypeError, match="subclass of Event"):
        RuntimeBuilder().with_environment({}, prefix=None).on_event(int, print).build()  # type: ignore[arg-type,type-var]
    with pytest.raises(TypeError, match="callable"):
        RuntimeBuilder().with_environment({}, prefix=None).on_event(Event, "x").build()  # type: ignore[arg-type]


def test_metrics(builder: RuntimeBuilder, metrics: InMemoryMetrics) -> None:
    runtime = builder.build()
    runtime.run(lambda ctx: None, name="ok")
    runtime.run(_fail, name="ko")
    assert metrics.counter("orchestrator.executions") == 2
    assert metrics.counter("orchestrator.executions", automation="ok", status="succeeded") == 1
    assert metrics.counter("orchestrator.executions", automation="ko", status="failed") == 1
    assert len(metrics.values("orchestrator.execution.duration_seconds")) == 2
    assert len(metrics.values("orchestrator.stage.duration_seconds")) == 16
    assert len(metrics.values("orchestrator.stage.duration_seconds", status="failed")) == 1


def test_failing_metrics_backend_never_breaks_executions(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class Broken:
        def increment(
            self,
            name: str,
            value: float = 1.0,
            *,
            tags: Mapping[str, str] | None = None,
        ) -> None:
            raise ConnectionError("statsd down")

        def observe(
            self, name: str, value: float, *, tags: Mapping[str, str] | None = None
        ) -> None:
            raise ConnectionError("statsd down")

    runtime = RuntimeBuilder().with_environment({}, prefix=None).with_metrics(Broken()).build()
    with caplog.at_level(logging.WARNING, logger="orchestrator_core.metrics"):
        assert runtime.run(lambda ctx: None).succeeded
    assert "metrics recorder failed" in caplog.text


@pytest.fixture
def captured_json() -> Iterator[io.StringIO]:
    stream = io.StringIO()
    handler = configure_logging("DEBUG", stream=stream, json_output=True)
    try:
        yield stream
    finally:
        logging.getLogger().removeHandler(handler)


def test_every_log_line_of_an_execution_carries_its_id(
    builder: RuntimeBuilder, captured_json: io.StringIO
) -> None:
    """M6 acceptance: correlation also covers loggers of the consumer and of Capabilities."""
    logging.getLogger("outside").info("before the execution")

    def automation(ctx: ExecutionContext) -> None:
        ctx.logger.info("from the context logger")
        logging.getLogger("acme.billing").warning("from a consumer module logger")

    result = builder.build().run(automation, name="billing")
    logging.getLogger("outside").info("after the execution")

    lines = [json.loads(line) for line in captured_json.getvalue().splitlines()]
    inside = [line for line in lines if line["logger"] != "outside"]
    outside = [line for line in lines if line["logger"] == "outside"]
    assert len(outside) == 2
    assert all(line["execution_id"] == "-" for line in outside)
    assert len(inside) >= 4
    assert all(line["execution_id"] == result.execution_id for line in inside)
    assert all(line["automation"] == "billing" for line in inside)
    by_message = {line["message"]: line for line in inside}
    assert by_message["from the context logger"]["stage"] == "execute_automation"
    assert by_message["from a consumer module logger"]["stage"] == "execute_automation"


def test_failure_is_logged_once_with_traceback(
    builder: RuntimeBuilder, captured_json: io.StringIO
) -> None:
    builder.build().run(_fail)
    errors = [
        json.loads(line)
        for line in captured_json.getvalue().splitlines()
        if json.loads(line)["level"] == "ERROR"
    ]
    assert len(errors) == 1
    assert errors[0]["message"] == "stage 'execute_automation' failed"
    assert "ValueError: kaput" in errors[0]["exception"]


def test_configure_logging_is_idempotent_and_supports_text() -> None:
    stream = io.StringIO()
    first = configure_logging("INFO", stream=stream, logger="idempotent")
    second = configure_logging("INFO", stream=stream, logger="idempotent")
    target = logging.getLogger("idempotent")
    try:
        assert target.handlers == [second]
        assert first not in target.handlers
        target.info("hello %s", "world")
        assert "[-|-] idempotent: hello world" in stream.getvalue()
    finally:
        target.removeHandler(second)


def test_filters_and_formatter_handle_edge_cases() -> None:
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "%s %s", ("only-one",), None)
    assert RedactingFilter().filter(record)  # malformed records are left untouched
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "msg", None, None)
    record.execution_id = "preset"
    ExecutionContextFilter().filter(record)
    assert record.execution_id == "preset"
    record.stack_info = "Stack (most recent call last)"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["stack"] == "Stack (most recent call last)"
    assert payload["stage"] == "-"


def _fail(ctx: ExecutionContext) -> None:
    raise ValueError("kaput")


def test_broken_log_handlers_never_fail_an_execution(builder: RuntimeBuilder) -> None:
    class Broken(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            pass

        def flush(self) -> None:
            raise ValueError("I/O operation on closed file.")

    handler = Broken()
    logging.getLogger("orchestrator").addHandler(handler)
    try:
        result = builder.build().run(lambda ctx: ctx.logger.info("hello"))
    finally:
        logging.getLogger("orchestrator").removeHandler(handler)
    assert result.succeeded
