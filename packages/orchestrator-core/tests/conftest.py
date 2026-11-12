from __future__ import annotations

import pytest

from orchestrator_core import RuntimeBuilder
from orchestrator_core._redaction import Redactor
from orchestrator_core.testing import (
    EventRecorder,
    FakeClock,
    InMemoryMetrics,
    InMemoryRecordSink,
)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def redactor() -> Redactor:
    return Redactor()


@pytest.fixture
def metrics() -> InMemoryMetrics:
    return InMemoryMetrics()


@pytest.fixture
def events() -> EventRecorder:
    return EventRecorder()


@pytest.fixture
def sink() -> InMemoryRecordSink:
    return InMemoryRecordSink()


@pytest.fixture
def builder(
    clock: FakeClock,
    redactor: Redactor,
    metrics: InMemoryMetrics,
    events: EventRecorder,
    sink: InMemoryRecordSink,
) -> RuntimeBuilder:
    """Builder isolated from the environment, with test doubles wired in."""
    from orchestrator_core import Event

    return (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_clock(clock)
        .with_redactor(redactor)
        .with_metrics(metrics)
        .with_record_sink(sink)
        .on_event(Event, events)
    )
