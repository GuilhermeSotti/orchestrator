from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

import pytest

from orchestrator_core import ExecutionFinished, ExecutionStarted
from orchestrator_core._clock import SystemClock
from orchestrator_core._resources import ResourceScope
from orchestrator_core.testing import EventRecorder, FakeClock, InMemoryMetrics


def test_fake_clock() -> None:
    clock = FakeClock(start=10.0, wall_start=datetime(2030, 1, 1, tzinfo=UTC))
    clock.advance(5)
    assert clock.monotonic() == 15.0
    assert clock.now() == datetime(2030, 1, 1, tzinfo=UTC) + timedelta(seconds=5)
    event = threading.Event()
    assert clock.wait(event, 2) is False
    event.set()
    assert clock.wait(event, 100) is True
    assert clock.monotonic() == 17.0
    with pytest.raises(ValueError, match="backwards"):
        clock.advance(-1)


def test_system_clock() -> None:
    clock = SystemClock()
    assert clock.now().tzinfo is UTC
    start = clock.monotonic()
    clock.sleep(0)
    event = threading.Event()
    event.set()
    assert clock.wait(event, 1) is True
    assert clock.monotonic() >= start


def test_in_memory_metrics_filters_by_tags() -> None:
    metrics = InMemoryMetrics()
    metrics.increment("jobs", tags={"status": "ok", "env": "prod"})
    metrics.increment("jobs", 2, tags={"status": "failed", "env": "prod"})
    metrics.observe("latency", 0.5, tags={"env": "prod"})
    assert metrics.counter("jobs") == 3
    assert metrics.counter("jobs", status="failed") == 2
    assert metrics.counter("jobs", env="dev") == 0
    assert metrics.values("latency", env="prod") == [0.5]


def test_event_recorder_filters_by_type() -> None:
    recorder = EventRecorder()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    recorder(ExecutionStarted(execution_id="1", timestamp=now, automation="a", runtime="r"))
    assert len(recorder.of_type(ExecutionStarted)) == 1
    assert recorder.of_type(ExecutionFinished) == []


def test_resource_scope_releases_in_reverse_order_and_collects_errors() -> None:
    from collections.abc import Iterator
    from contextlib import contextmanager

    order: list[str] = []

    @contextmanager
    def managed(name: str) -> Iterator[str]:
        order.append(f"enter:{name}")
        yield name
        order.append(f"exit:{name}")

    scope = ResourceScope()
    assert scope.enter(managed("a")) == "a"
    scope.callback(_raise, RuntimeError("cleanup failed"))
    scope.callback(order.append, "callback")
    assert len(scope) == 3
    errors = scope.close()
    assert order == ["enter:a", "callback", "exit:a"]
    assert [str(e) for e in errors] == ["cleanup failed"]
    assert scope.closed
    assert scope.close() == []
    with pytest.raises(RuntimeError, match="already closed"):
        scope.enter(managed("late"))


def _raise(error: BaseException) -> None:
    raise error
