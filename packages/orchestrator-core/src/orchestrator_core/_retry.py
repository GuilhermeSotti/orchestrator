"""Retry utility. Nothing is retried unless code asks for it explicitly."""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

from orchestrator_core._clock import Clock, SystemClock

type RetryPredicate = Callable[[BaseException], bool]
"""Decides whether an error should be retried."""


def is_retryable(error: BaseException) -> bool:
    """Default predicate: retry only errors flagged with ``retryable = True``."""
    return isinstance(error, Exception) and bool(getattr(error, "retryable", False))


@dataclass(frozen=True, slots=True)
class RetryAttempt:
    """Information about a failed attempt that is going to be retried.

    Attributes:
        attempt: Number of the attempt that failed (1-based).
        error: Error raised by that attempt.
        delay: Seconds to wait before the next attempt.
    """

    attempt: int
    error: BaseException
    delay: float


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """How many times, how long apart and on which errors to retry.

    The default policy performs a single attempt (no retry).

    Example:
        >>> policy = RetryPolicy.exponential(max_attempts=4, initial_delay=1.0, jitter=0.0)
        >>> [policy.delay_before(n, random.Random(0)) for n in (1, 2, 3)]
        [1.0, 2.0, 4.0]

    Attributes:
        max_attempts: Total attempts, including the first one (>= 1).
        initial_delay: Delay after the first failure, in seconds.
        multiplier: Growth factor of the delay (>= 1).
        max_delay: Upper bound of a single delay, in seconds.
        jitter: Relative random variation of each delay, between 0 and 1.
        max_elapsed: Stop retrying when the next attempt would start later than
            this many seconds after the first one.
        retry_on: Exception types to retry, or a predicate.
    """

    max_attempts: int = 1
    initial_delay: float = 0.5
    multiplier: float = 2.0
    max_delay: float = 30.0
    jitter: float = 0.1
    max_elapsed: float | None = None
    retry_on: tuple[type[BaseException], ...] | RetryPredicate = is_retryable

    def __post_init__(self) -> None:
        """Validate the policy."""
        if self.max_attempts < 1:
            msg = "max_attempts must be >= 1"
            raise ValueError(msg)
        if self.initial_delay < 0 or self.max_delay < 0:
            msg = "delays must be >= 0"
            raise ValueError(msg)
        if self.multiplier < 1:
            msg = "multiplier must be >= 1"
            raise ValueError(msg)
        if not 0 <= self.jitter <= 1:
            msg = "jitter must be between 0 and 1"
            raise ValueError(msg)
        if self.max_elapsed is not None and self.max_elapsed <= 0:
            msg = "max_elapsed must be > 0"
            raise ValueError(msg)

    @classmethod
    def no_retry(cls) -> RetryPolicy:
        """Return the policy with a single attempt."""
        return cls()

    @classmethod
    def exponential(
        cls,
        max_attempts: int,
        *,
        initial_delay: float = 0.5,
        multiplier: float = 2.0,
        max_delay: float = 30.0,
        jitter: float = 0.1,
        max_elapsed: float | None = None,
        retry_on: tuple[type[BaseException], ...] | RetryPredicate = is_retryable,
    ) -> RetryPolicy:
        """Return a policy with exponential backoff and jitter."""
        return cls(
            max_attempts=max_attempts,
            initial_delay=initial_delay,
            multiplier=multiplier,
            max_delay=max_delay,
            jitter=jitter,
            max_elapsed=max_elapsed,
            retry_on=retry_on,
        )

    @classmethod
    def fixed(
        cls,
        max_attempts: int,
        delay: float,
        *,
        max_elapsed: float | None = None,
        retry_on: tuple[type[BaseException], ...] | RetryPredicate = is_retryable,
    ) -> RetryPolicy:
        """Return a policy with a constant delay between attempts."""
        return cls(
            max_attempts=max_attempts,
            initial_delay=delay,
            multiplier=1.0,
            max_delay=delay,
            jitter=0.0,
            max_elapsed=max_elapsed,
            retry_on=retry_on,
        )

    def should_retry(self, error: BaseException) -> bool:
        """Tell whether ``error`` is eligible for another attempt."""
        if not isinstance(error, Exception):
            return False
        if isinstance(self.retry_on, tuple):
            return isinstance(error, self.retry_on)
        return self.retry_on(error)

    def delay_before(self, attempt: int, rng: random.Random) -> float:
        """Return the delay after the failed ``attempt`` (1-based)."""
        delay = min(self.max_delay, self.initial_delay * self.multiplier ** (attempt - 1))
        if self.jitter:
            delay *= 1 + rng.uniform(-self.jitter, self.jitter)
        return max(0.0, delay)


def retry[T](
    operation: Callable[[], T],
    policy: RetryPolicy,
    *,
    clock: Clock | None = None,
    sleep: Callable[[float], None] | None = None,
    rng: random.Random | None = None,
    before_attempt: Callable[[], None] | None = None,
    on_retry: Callable[[RetryAttempt], None] | None = None,
) -> T:
    """Call ``operation`` until it succeeds or ``policy`` gives up.

    The last error is re-raised unchanged, with a note telling how many attempts
    were made. Interrupting errors (``KeyboardInterrupt``...) are never retried.

    Args:
        operation: Callable without arguments.
        policy: Retry policy.
        clock: Time source (system clock by default).
        sleep: Function used to wait; defaults to ``clock.sleep``.
        rng: Random generator for jitter.
        before_attempt: Called before every attempt (e.g. a cancellation check).
        on_retry: Called after a failed attempt that will be retried.
    """
    clock = clock or SystemClock()
    wait = sleep or clock.sleep
    generator = rng or random.Random()  # noqa: S311 - jitter, not cryptography
    started = clock.monotonic()
    attempt = 1
    while True:
        if before_attempt is not None:
            before_attempt()
        try:
            return operation()
        except Exception as exc:
            if attempt >= policy.max_attempts or not policy.should_retry(exc):
                if attempt > 1:
                    exc.add_note(f"orchestrator: gave up after {attempt} attempts")
                raise
            delay = policy.delay_before(attempt, generator)
            elapsed = clock.monotonic() - started
            if policy.max_elapsed is not None and elapsed + delay > policy.max_elapsed:
                exc.add_note(
                    f"orchestrator: stopped retrying after {attempt} attempts "
                    f"(max_elapsed={policy.max_elapsed}s)"
                )
                raise
            if on_retry is not None:
                on_retry(RetryAttempt(attempt=attempt, error=exc, delay=delay))
            wait(delay)
            attempt += 1
