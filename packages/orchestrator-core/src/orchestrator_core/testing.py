"""Test doubles and conformance checks for consumer projects, Capabilities and Providers.

Everything here is deterministic and dependency-free; it does not require pytest.

Example:
    >>> from orchestrator_core import RuntimeBuilder
    >>> clock, metrics, events = FakeClock(), InMemoryMetrics(), EventRecorder()
    >>> runtime = (
    ...     RuntimeBuilder()
    ...     .with_environment({}, prefix=None)
    ...     .with_clock(clock)
    ...     .with_metrics(metrics)
    ...     .on_event(Event, events)
    ...     .build()
    ... )
    >>> runtime.run(lambda ctx: None, name="noop").succeeded
    True
    >>> metrics.counter("orchestrator.executions", status="succeeded")
    1.0
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any

from orchestrator_core._capabilities import Capability
from orchestrator_core._context import ExecutionContext
from orchestrator_core._events import Event
from orchestrator_core._results import ExecutionRecord, ExecutionResult
from orchestrator_core._runtime import RuntimeBuilder

__all__ = [
    "EventRecorder",
    "FakeClock",
    "InMemoryMetrics",
    "InMemoryRecordSink",
    "check_capability_conformance",
]

_DEFAULT_WALL_START = datetime(2026, 1, 1, tzinfo=UTC)


class FakeClock:
    """Deterministic clock: time only moves through :meth:`advance` and sleeps.

    Example:
        >>> clock = FakeClock()
        >>> clock.sleep(1.5)
        >>> clock.monotonic(), clock.sleeps
        (1.5, [1.5])
    """

    def __init__(self, *, start: float = 0.0, wall_start: datetime = _DEFAULT_WALL_START) -> None:
        """Create a clock at ``start`` seconds, whose wall time starts at ``wall_start``."""
        self._lock = threading.Lock()
        self._start = start
        self._now = start
        self._wall_start = wall_start
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        """Return the fake monotonic time."""
        with self._lock:
            return self._now

    def now(self) -> datetime:
        """Return the fake wall time (UTC)."""
        with self._lock:
            return self._wall_start + timedelta(seconds=self._now - self._start)

    def advance(self, seconds: float) -> None:
        """Move time forward by ``seconds``."""
        if seconds < 0:
            msg = "time cannot go backwards"
            raise ValueError(msg)
        with self._lock:
            self._now += seconds

    def sleep(self, seconds: float) -> None:
        """Record the sleep and advance time instantly."""
        self.sleeps.append(seconds)
        self.advance(max(0.0, seconds))

    def wait(self, event: threading.Event, timeout: float) -> bool:
        """Return at once if ``event`` is set; otherwise advance ``timeout`` seconds."""
        if event.is_set():
            return True
        self.sleep(timeout)
        return event.is_set()


class InMemoryMetrics:
    """Thread-safe metrics recorder that keeps everything in memory."""

    def __init__(self) -> None:
        """Create an empty recorder."""
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, frozenset[tuple[str, str]]], float] = {}
        self.observations: list[tuple[str, float, dict[str, str]]] = []

    def increment(
        self, name: str, value: float = 1.0, *, tags: Mapping[str, str] | None = None
    ) -> None:
        """Add ``value`` to the counter ``name`` with ``tags``."""
        key = (name, frozenset((tags or {}).items()))
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    def observe(self, name: str, value: float, *, tags: Mapping[str, str] | None = None) -> None:
        """Keep the observation."""
        with self._lock:
            self.observations.append((name, value, dict(tags or {})))

    def counter(self, name: str, **tags: str) -> float:
        """Sum of the counter ``name`` over every series that contains ``tags``."""
        wanted = set(tags.items())
        with self._lock:
            return sum(v for (n, t), v in self._counters.items() if n == name and wanted <= t)

    def values(self, name: str, **tags: str) -> list[float]:
        """Observed values of ``name`` whose tags contain ``tags``."""
        wanted = set(tags.items())
        with self._lock:
            return [v for n, v, t in self.observations if n == name and wanted <= set(t.items())]


class EventRecorder:
    """Event handler that keeps every event it receives. Thread-safe."""

    def __init__(self) -> None:
        """Create an empty recorder."""
        self._lock = threading.Lock()
        self.events: list[Event] = []

    def __call__(self, event: Event) -> None:
        """Keep ``event``."""
        with self._lock:
            self.events.append(event)

    def of_type[E: Event](self, kind: type[E]) -> list[E]:
        """Return the recorded events that are instances of ``kind``."""
        with self._lock:
            return [event for event in self.events if isinstance(event, kind)]


class InMemoryRecordSink:
    """Record sink that keeps every execution record. Thread-safe."""

    def __init__(self) -> None:
        """Create an empty sink."""
        self._lock = threading.Lock()
        self.records: list[ExecutionRecord] = []

    def write(self, record: ExecutionRecord) -> None:
        """Keep ``record``."""
        with self._lock:
            self.records.append(record)


def check_capability_conformance(
    capability: Capability[Any],
    *,
    name: str | None = None,
    use: Callable[[Any], object] | None = None,
    sequential_runs: int = 3,
    concurrent_runs: int = 8,
    workers: int = 4,
) -> None:
    """Assert that ``capability`` honors the Capability contract.

    It registers ``capability`` in a fresh Runtime and checks that:

    * executions succeed, sequentially and concurrently;
    * every execution receives its own handle (no sharing between executions);
    * the handle is reachable through ``ctx.capability`` during the execution;
    * the context is closed afterwards (handles are no longer reachable).

    Args:
        capability: Instance under test.
        name: Registration name (default: ``default_name``).
        use: Optional function called with the handle inside each execution,
            to exercise it (for example, run a trivial query).
        sequential_runs: Number of executions run one after the other.
        concurrent_runs: Number of executions run in a thread pool.
        workers: Size of the thread pool.

    Raises:
        AssertionError: If a check fails.
    """
    runtime = (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_capability(capability, name=name)
        .build()
    )
    key = type(capability)
    handles: list[object] = []
    contexts: list[ExecutionContext] = []
    lock = threading.Lock()

    def automation(ctx: ExecutionContext) -> None:
        handle = ctx.capability(key, name)
        if use is not None:
            use(handle)
        with lock:
            handles.append(handle)
            contexts.append(ctx)

    def run_once(_: int = 0) -> ExecutionResult:
        return runtime.run(automation, name="capability-conformance")

    results = [run_once() for _ in range(sequential_runs)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results.extend(pool.map(run_once, range(concurrent_runs)))
    failures = [result for result in results if not result.succeeded]
    if failures:
        first = failures[0]
        msg = f"{len(failures)} execution(s) failed; first: {first!r}"
        raise AssertionError(msg) from first.error
    if len({id(handle) for handle in handles}) != len(handles):
        msg = "the same handle was given to more than one execution"
        raise AssertionError(msg)
    for ctx in contexts:
        try:
            ctx.capability(key, name)
        except Exception:  # noqa: BLE001, S112 - expected: the context is closed
            continue
        msg = "a handle was still reachable after the execution finished"
        raise AssertionError(msg)
