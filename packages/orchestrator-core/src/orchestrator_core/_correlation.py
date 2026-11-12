"""Log correlation through context variables (the only use of contextvars in the Core)."""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import NamedTuple

_execution_id: ContextVar[str | None] = ContextVar("orchestrator_execution_id", default=None)
_automation: ContextVar[str | None] = ContextVar("orchestrator_automation", default=None)
_stage: ContextVar[str | None] = ContextVar("orchestrator_stage", default=None)


class Correlation(NamedTuple):
    """Correlation fields of the current execution, or ``None`` outside one."""

    execution_id: str | None
    automation: str | None
    stage: str | None


class Binding(NamedTuple):
    """Tokens needed to restore the previous correlation."""

    execution_id: Token[str | None]
    automation: Token[str | None]
    stage: Token[str | None]


def current() -> Correlation:
    """Return the correlation fields of the current context."""
    return Correlation(_execution_id.get(), _automation.get(), _stage.get())


def bind(execution_id: str, automation: str) -> Binding:
    """Make ``execution_id`` and ``automation`` current."""
    return Binding(_execution_id.set(execution_id), _automation.set(automation), _stage.set(None))


def unbind(binding: Binding) -> None:
    """Restore the correlation that was current before :func:`bind`."""
    _stage.reset(binding.stage)
    _automation.reset(binding.automation)
    _execution_id.reset(binding.execution_id)


def enter_stage(name: str) -> Token[str | None]:
    """Make ``name`` the current stage."""
    return _stage.set(name)


def exit_stage(token: Token[str | None]) -> None:
    """Restore the previous stage."""
    _stage.reset(token)
