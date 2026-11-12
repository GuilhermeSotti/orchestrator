"""MVP criterion 5: sequential and parallel executions share no context, state or resources."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from orchestrator_core import Capability, ExecutionContext, RuntimeBuilder


class Session:
    def __init__(self, owner: str) -> None:
        self.owner = owner
        self.items: list[str] = []
        self.open = True


class Sessions(Capability[Session]):
    default_name = "sessions"

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.opened = 0
        self.closed = 0

    def open(self, ctx: ExecutionContext) -> Session:
        session = Session(ctx.execution_id)
        with self.lock:
            self.opened += 1
        ctx.resources.callback(self._close, session)
        return session

    def _close(self, session: Session) -> None:
        session.open = False
        with self.lock:
            self.closed += 1


def automation(ctx: ExecutionContext) -> tuple[str, int]:
    session = ctx.capability(Sessions)
    assert session.owner == ctx.execution_id
    assert ctx.state == {}
    ctx.state["mine"] = ctx.execution_id
    for index in range(50):
        session.items.append(f"{ctx.execution_id}:{index}")
        ctx.check()
    assert all(item.startswith(ctx.execution_id) for item in session.items)
    assert ctx.state["mine"] == ctx.execution_id
    return ctx.execution_id, len(session.items)


@pytest.mark.slow
def test_stress_sequential_and_parallel_executions_are_isolated() -> None:
    capability = Sessions()
    runtime = RuntimeBuilder().with_environment({}, prefix=None).with_capability(capability).build()

    sequential = [runtime.run(automation) for _ in range(200)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        parallel = list(pool.map(lambda _: runtime.run(automation), range(400)))

    results = sequential + parallel
    assert all(result.succeeded for result in results), [r for r in results if not r.succeeded][:1]
    assert len({result.execution_id for result in results}) == 600
    assert all(result.output == (result.execution_id, 50) for result in results)
    assert capability.opened == capability.closed == 600


def test_nested_executions_restore_the_log_correlation() -> None:
    from orchestrator_core import _correlation

    runtime = RuntimeBuilder().with_environment({}, prefix=None).build()

    def inner(ctx: ExecutionContext) -> str | None:
        return _correlation.current().execution_id

    def outer(ctx: ExecutionContext) -> tuple[str | None, str | None]:
        nested = runtime.run(inner)
        return nested.output, _correlation.current().execution_id  # type: ignore[return-value]

    result = runtime.run(outer)
    nested_id, restored_id = result.output  # type: ignore[misc]
    assert nested_id not in {None, result.execution_id}
    assert restored_id == result.execution_id
    assert _correlation.current().execution_id is None
