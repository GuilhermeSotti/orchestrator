"""Retry (D-12), cancellation and timeout (D-06), with a fake clock: no real waiting."""

from __future__ import annotations

import random
import threading
import time

import pytest

from orchestrator_core import (
    CancellationToken,
    ExecutionCancelledError,
    ExecutionContext,
    ExecutionStatus,
    ExecutionTimeoutError,
    FunctionStage,
    Phase,
    ProviderError,
    RetryPolicy,
    RuntimeBuilder,
    StageStatus,
    is_retryable,
    retry,
)
from orchestrator_core.testing import FakeClock, InMemoryMetrics


class Flaky:
    def __init__(self, failures: int, error: Exception | None = None) -> None:
        self.failures = failures
        self.calls = 0
        self.error = error or ProviderError("temporarily unavailable", retryable=True)

    def __call__(self) -> str:
        self.calls += 1
        if self.calls <= self.failures:
            raise self.error
        return "ok"


def test_policy_validation_and_schedule() -> None:
    for kwargs in (
        {"max_attempts": 0},
        {"initial_delay": -1},
        {"multiplier": 0.5},
        {"jitter": 2},
        {"max_elapsed": 0},
    ):
        with pytest.raises(ValueError):
            RetryPolicy(**kwargs)  # type: ignore[arg-type]
    policy = RetryPolicy.exponential(5, initial_delay=1, max_delay=5, jitter=0)
    assert [policy.delay_before(n, random.Random(1)) for n in range(1, 6)] == [
        1,
        2,
        4,
        5,
        5,
    ]
    jittered = RetryPolicy.exponential(3, initial_delay=10, jitter=0.2)
    for seed in range(20):
        assert 8 <= jittered.delay_before(1, random.Random(seed)) <= 12
    assert RetryPolicy.fixed(3, 2.0).delay_before(3, random.Random()) == 2.0
    assert RetryPolicy.no_retry().max_attempts == 1


def test_retry_until_success(clock: FakeClock) -> None:
    operation = Flaky(failures=2)
    seen: list[int] = []
    result = retry(
        operation,
        RetryPolicy.fixed(3, 1.5),
        clock=clock,
        on_retry=lambda attempt: seen.append(attempt.attempt),
    )
    assert result == "ok"
    assert operation.calls == 3
    assert clock.sleeps == [1.5, 1.5]
    assert seen == [1, 2]


def test_retry_gives_up_and_keeps_the_original_error(clock: FakeClock) -> None:
    operation = Flaky(failures=5)
    with pytest.raises(ProviderError) as info:
        retry(operation, RetryPolicy.fixed(3, 1), clock=clock)
    assert info.value is operation.error
    assert "orchestrator: gave up after 3 attempts" in info.value.__notes__
    assert operation.calls == 3


def test_retry_never_retries_by_default_or_non_retryable_errors(
    clock: FakeClock,
) -> None:
    with pytest.raises(ProviderError):
        retry(Flaky(1), RetryPolicy(), clock=clock)
    not_flagged = Flaky(1, ValueError("bad"))
    with pytest.raises(ValueError):
        retry(not_flagged, RetryPolicy.fixed(5, 1), clock=clock)
    assert not_flagged.calls == 1
    by_type = Flaky(1, TimeoutError("slow"))
    assert retry(by_type, RetryPolicy.fixed(2, 1, retry_on=(TimeoutError,)), clock=clock) == "ok"
    assert not is_retryable(KeyboardInterrupt())
    assert not RetryPolicy(retry_on=(BaseException,)).should_retry(KeyboardInterrupt())


def test_retry_respects_max_elapsed(clock: FakeClock) -> None:
    operation = Flaky(failures=10)
    with pytest.raises(ProviderError) as info:
        retry(operation, RetryPolicy.fixed(10, 4, max_elapsed=10), clock=clock)
    assert operation.calls == 3  # 0s, 4s, 8s; the next attempt would start at 12s
    assert any("max_elapsed=10" in note for note in info.value.__notes__)


def test_context_retry_logs_and_counts(
    builder: RuntimeBuilder, metrics: InMemoryMetrics, caplog: pytest.LogCaptureFixture
) -> None:
    operation = Flaky(failures=2)
    runtime = builder.build()
    result = runtime.run(
        lambda ctx: ctx.retry(operation, RetryPolicy.fixed(3, 1), name="fetch-invoices")
    )
    assert result.output == "ok"
    assert metrics.counter("orchestrator.retry.attempts", operation="fetch-invoices") == 2
    assert caplog.text.count("fetch-invoices failed on attempt") == 2


def test_cancellation_before_start(builder: RuntimeBuilder) -> None:
    token = CancellationToken()
    token.cancel("operator request")
    token.cancel("ignored second reason")
    result = builder.build().run(lambda ctx: None, cancellation=token)
    assert result.status is ExecutionStatus.CANCELLED
    assert isinstance(result.error, ExecutionCancelledError)
    assert str(result.error) == "operator request"
    assert result.stage("initialize").status is StageStatus.CANCELLED
    assert result.stage("execute_automation").status is StageStatus.SKIPPED
    assert result.stage("shutdown").status is StageStatus.SUCCEEDED
    assert "cancelled" in repr(token)


def test_cancellation_from_another_thread_wakes_up_sleeping_automations() -> None:
    token = CancellationToken()
    runtime = RuntimeBuilder().with_environment({}, prefix=None).build()

    def automation(ctx: ExecutionContext) -> None:
        threading.Timer(0.05, token.cancel, args=("stop",)).start()
        ctx.sleep(30)

    started = time.monotonic()
    result = runtime.run(automation, cancellation=token)
    assert time.monotonic() - started < 5
    assert result.status is ExecutionStatus.CANCELLED
    assert result.stage("execute_automation").status is StageStatus.CANCELLED


def test_timeout_interrupts_cooperative_waits(builder: RuntimeBuilder, clock: FakeClock) -> None:
    runtime = builder.with_settings({"runtime": {"timeout": 2}}).build()
    seen: list[float | None] = []

    def automation(ctx: ExecutionContext) -> None:
        seen.append(ctx.remaining())
        ctx.sleep(5)

    result = runtime.run(automation)
    assert result.status is ExecutionStatus.TIMED_OUT
    assert isinstance(result.error, ExecutionTimeoutError)
    assert seen == [2.0]
    assert clock.sleeps == [2.0]
    assert result.stage("finalize").status is StageStatus.SUCCEEDED


def test_deadline_is_checked_before_each_stage(builder: RuntimeBuilder, clock: FakeClock) -> None:
    slow = FunctionStage("slow_setup", Phase.PREPARE, lambda ctx: clock.advance(10))
    runtime = builder.with_stage(slow, after="prepare_environment").build()
    result = runtime.run(lambda ctx: None, timeout=5)
    assert result.status is ExecutionStatus.TIMED_OUT
    assert result.stage("slow_setup").status is StageStatus.SUCCEEDED
    assert result.stage("prepare_execution").status is StageStatus.TIMED_OUT
    assert result.stage("execute_automation").status is StageStatus.SKIPPED


def test_retry_stops_at_the_deadline(builder: RuntimeBuilder) -> None:
    operation = Flaky(failures=10)
    runtime = builder.build()
    result = runtime.run(lambda ctx: ctx.retry(operation, RetryPolicy.fixed(10, 3)), timeout=7)
    assert result.status is ExecutionStatus.TIMED_OUT
    assert operation.calls == 3
    assert isinstance(result.error, ExecutionTimeoutError)
    assert isinstance(result.error.__context__, ProviderError)


def test_overrunning_automation_succeeds_with_a_warning(
    builder: RuntimeBuilder, clock: FakeClock, caplog: pytest.LogCaptureFixture
) -> None:
    result = builder.build().run(lambda ctx: clock.advance(3), timeout=1)
    assert result.succeeded
    assert "finished after its timeout of 1s" in caplog.text


def test_context_time_helpers(builder: RuntimeBuilder, clock: FakeClock) -> None:
    def automation(ctx: ExecutionContext) -> tuple[object, ...]:
        before = ctx.remaining()
        ctx.sleep(0)
        return before, ctx.timeout, ctx.deadline_exceeded(), ctx.now() == clock.now()

    assert builder.build().run(automation).output == (None, None, False, True)
