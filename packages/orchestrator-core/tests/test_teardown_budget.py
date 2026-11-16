"""Teardown budget (RFC-0005, 2.2): own deadline for teardown, 60 s by default, 0 disables it."""

from __future__ import annotations

import pytest

from orchestrator_core import (
    CancellationToken,
    Configuration,
    ConfigurationError,
    ExecutionContext,
    ExecutionOutcome,
    ExecutionStatus,
    ExecutionTimeoutError,
    FunctionStage,
    Phase,
    RetryPolicy,
    RuntimeBuilder,
    StageStatus,
)
from orchestrator_core.testing import FakeClock


class Transient(Exception):
    retryable = True


class Flaky:
    """Fails ``failures`` times with a retryable error, then succeeds."""

    def __init__(self, failures: int) -> None:
        self.calls = 0
        self.failures = failures

    def __call__(self) -> str:
        self.calls += 1
        if self.calls <= self.failures:
            raise Transient(f"attempt {self.calls}")
        return "sent"


def test_default_and_validation_of_the_teardown_budget() -> None:
    def budget(value: object) -> float:
        return Configuration.from_mapping(
            {"runtime": {"teardown_timeout": value}}
        ).runtime.teardown_timeout

    assert Configuration.from_mapping({}).runtime.teardown_timeout == 60.0
    assert budget("0") == 0.0
    assert budget(5) == 5.0
    with pytest.raises(ConfigurationError, match=r"runtime\.teardown_timeout: must be zero"):
        Configuration.from_mapping({"runtime": {"teardown_timeout": -1}})
    with pytest.raises(ConfigurationError, match=r"runtime\.teardown_timeout: expected a number"):
        Configuration.from_mapping({"runtime": {"teardown_timeout": "soon"}})
    with pytest.raises(ConfigurationError, match=r"runtime\.teardown_timeout: expected a finite"):
        Configuration.from_mapping({"runtime": {"teardown_timeout": "inf"}})


@pytest.mark.parametrize("interruption", ["timeout", "cancellation"])
def test_after_an_interruption_teardown_can_retry_within_its_budget(
    builder: RuntimeBuilder, clock: FakeClock, interruption: str
) -> None:
    """E7.4: after timed_out and cancelled, a teardown operation with retry is attempted."""
    flaky = Flaky(failures=2)
    replies: list[str] = []
    token = CancellationToken()

    def automation(ctx: ExecutionContext) -> None:
        def notify(outcome: ExecutionOutcome) -> None:
            replies.append(ctx.retry(flaky, RetryPolicy.fixed(3, 1.0), name="notify"))

        ctx.add_finalizer(notify)
        if interruption == "cancellation":
            token.cancel("operator")
        ctx.sleep(10)

    result = builder.build().run(automation, timeout=5, cancellation=token)
    expected = ExecutionStatus.TIMED_OUT if interruption == "timeout" else ExecutionStatus.CANCELLED
    assert result.status is expected
    assert replies == ["sent"]
    assert flaky.calls == 3
    assert result.teardown_errors == ()
    assert result.stage("finalize").status is StageStatus.SUCCEEDED
    assert clock.sleeps[-2:] == [1.0, 1.0]  # the waits between attempts were not zeroed


def test_check_and_sleep_in_teardown_ignore_the_interruption_that_ended_the_execution(
    builder: RuntimeBuilder, clock: FakeClock
) -> None:
    token = CancellationToken()
    seen: list[tuple[float | None, bool]] = []

    def wrap_up(ctx: ExecutionContext) -> None:
        ctx.check()  # does not raise the cancellation again
        seen.append((ctx.remaining(), ctx.deadline_exceeded()))
        ctx.sleep(2)  # does not wake up on the cancelled token
        seen.append((ctx.remaining(), ctx.deadline_exceeded()))

    def automation(ctx: ExecutionContext) -> None:
        token.cancel("stop")
        ctx.check()

    stage = FunctionStage("wrap_up", Phase.TEARDOWN, wrap_up)
    result = builder.with_stage(stage, after="finalize").build().run(automation, cancellation=token)
    assert result.status is ExecutionStatus.CANCELLED
    assert result.teardown_errors == ()
    assert seen == [(60.0, False), (58.0, False)]
    assert clock.sleeps[-1] == 2.0


def test_an_exhausted_budget_raises_a_timeout_in_teardown(
    builder: RuntimeBuilder, clock: FakeClock
) -> None:
    attempts: list[float] = []

    def automation(ctx: ExecutionContext) -> None:
        def slow_cleanup(outcome: ExecutionOutcome) -> None:
            while True:
                attempts.append(clock.monotonic())
                ctx.sleep(2)

        ctx.add_finalizer(slow_cleanup)

    runtime = builder.with_settings({"runtime": {"teardown_timeout": 5}}).build()
    result = runtime.run(automation)
    assert result.status is ExecutionStatus.FAILED  # a teardown error fails a successful run
    (error,) = result.teardown_errors
    assert isinstance(error, ExecutionTimeoutError)
    assert "teardown exceeded its budget of 5.0s" in str(error)
    assert result.stage("finalize").status is StageStatus.TIMED_OUT
    assert attempts == [0.0, 2.0, 4.0]  # the last sleep was cut to the 1 s left
    assert clock.monotonic() == 5.0


def test_the_budget_starts_at_the_first_teardown_stage_and_is_independent_of_the_timeout(
    builder: RuntimeBuilder, clock: FakeClock
) -> None:
    remaining: list[float | None] = []

    def automation(ctx: ExecutionContext) -> None:
        clock.advance(9)
        remaining.append(ctx.remaining())  # 1 s left of the 10 s timeout

    def early(ctx: ExecutionContext) -> None:
        remaining.append(ctx.remaining())

    def late(ctx: ExecutionContext) -> None:
        clock.advance(4)
        remaining.append(ctx.remaining())

    runtime = (
        builder.with_settings({"runtime": {"teardown_timeout": 30}})
        .with_stage(FunctionStage("early", Phase.TEARDOWN, early), before="finalize")
        .with_stage(FunctionStage("late", Phase.TEARDOWN, late), after="shutdown")
        .build()
    )
    result = runtime.run(automation, timeout=10)
    assert result.succeeded
    assert remaining == [1.0, 30.0, 26.0]


def test_zero_disables_the_teardown_budget(builder: RuntimeBuilder, clock: FakeClock) -> None:
    seen: list[float | None] = []

    def automation(ctx: ExecutionContext) -> None:
        def cleanup(outcome: ExecutionOutcome) -> None:
            seen.append(ctx.remaining())
            ctx.sleep(10_000)
            ctx.check()
            seen.append(ctx.remaining())

        ctx.add_finalizer(cleanup)
        ctx.sleep(100)

    runtime = builder.with_settings({"runtime": {"teardown_timeout": 0}}).build()
    result = runtime.run(automation, timeout=1)
    assert result.status is ExecutionStatus.TIMED_OUT
    assert result.teardown_errors == ()
    assert seen == [None, None]
    assert clock.sleeps[-1] == 10_000


def test_cancelling_during_teardown_does_not_interrupt_it(
    builder: RuntimeBuilder, clock: FakeClock
) -> None:
    token = CancellationToken()
    steps: list[str] = []

    def automation(ctx: ExecutionContext) -> None:
        def first(outcome: ExecutionOutcome) -> None:
            steps.append("second")
            ctx.sleep(1)

        def second(outcome: ExecutionOutcome) -> None:
            steps.append("first")
            token.cancel("too late")
            ctx.check()

        ctx.add_finalizer(first)
        ctx.add_finalizer(second)  # finalizers run in reverse order

    result = builder.build().run(automation, cancellation=token)
    assert result.succeeded
    assert steps == ["first", "second"]
