"""Stages and the definition of the execution pipeline."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from orchestrator_core._errors import PipelineDefinitionError
from orchestrator_core._results import Phase

if TYPE_CHECKING:
    from orchestrator_core._context import ExecutionContext

_STAGE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_PHASE_ORDER = {Phase.PREPARE: 0, Phase.EXECUTE: 1, Phase.TEARDOWN: 2}


class Stage(ABC):
    """A step of the execution pipeline.

    A stage signals failure by raising. Subclasses define :attr:`name` and
    :attr:`phase` as class attributes and implement :meth:`run`. Stages are
    shared by every execution of a Runtime, so they must not keep execution
    state: use the context instead.

    Example:
        >>> class Notify(Stage):
        ...     name = "notify"
        ...     phase = Phase.TEARDOWN
        ...
        ...     def run(self, ctx):
        ...         ctx.logger.info("finished with %s", ctx.outcome.status)

    Attributes:
        name: Unique name within the pipeline (lowercase, digits and ``_``).
        phase: Phase of the stage, which defines when it runs.
    """

    name: str
    phase: Phase

    @abstractmethod
    def run(self, ctx: ExecutionContext) -> None:
        """Run the stage for the execution described by ``ctx``."""

    def __repr__(self) -> str:
        """Return the stage name and phase."""
        return f"{type(self).__name__}(name={self.name!r}, phase={self.phase.value!r})"


class FunctionStage(Stage):
    """Stage that calls a function.

    Example:
        >>> stage = FunctionStage("audit", Phase.TEARDOWN, lambda ctx: None)
        >>> stage.name
        'audit'
    """

    def __init__(
        self, name: str, phase: Phase, function: Callable[[ExecutionContext], object]
    ) -> None:
        """Create a stage named ``name`` in ``phase`` that calls ``function(ctx)``."""
        self.name = name
        self.phase = phase
        self._function = function

    def run(self, ctx: ExecutionContext) -> None:
        """Call the function with ``ctx``."""
        self._function(ctx)


class PipelineDefinition:
    """Immutable, validated sequence of stages.

    Rules: names are unique and valid; ``initialize`` is the first stage;
    phases never go backwards (prepare, then execute, then teardown).
    """

    __slots__ = ("_stages",)

    def __init__(self, stages: Sequence[Stage]) -> None:
        """Validate ``stages``.

        Raises:
            PipelineDefinitionError: If a rule is violated.
        """
        self._stages = tuple(stages)
        self._validate()

    @property
    def stages(self) -> tuple[Stage, ...]:
        """Stages in execution order."""
        return self._stages

    @property
    def names(self) -> tuple[str, ...]:
        """Stage names in execution order."""
        return tuple(stage.name for stage in self._stages)

    def insert(
        self, stage: Stage, *, before: str | None = None, after: str | None = None
    ) -> PipelineDefinition:
        """Return a new definition with ``stage`` placed next to an existing stage.

        Exactly one of ``before`` and ``after`` must be given.

        Raises:
            PipelineDefinitionError: If the anchor is unknown or a rule is violated.
        """
        if (before is None) == (after is None):
            msg = "give exactly one of before= or after="
            raise PipelineDefinitionError(msg)
        anchor = before if before is not None else after
        names = self.names
        if anchor not in names:
            msg = f"unknown stage {anchor!r}; stages are: {', '.join(names)}"
            raise PipelineDefinitionError(msg)
        index = names.index(anchor) + (0 if before is not None else 1)
        return PipelineDefinition((*self._stages[:index], stage, *self._stages[index:]))

    def _validate(self) -> None:
        seen: set[str] = set()
        previous = Phase.PREPARE
        for position, stage in enumerate(self._stages):
            candidate: object = stage
            if not isinstance(candidate, Stage):
                msg = f"{candidate!r} is not a Stage"
                raise PipelineDefinitionError(msg)
            name = getattr(stage, "name", None)
            phase = getattr(stage, "phase", None)
            if not isinstance(name, str) or not _STAGE_NAME_RE.match(name):
                msg = f"invalid stage name {name!r}: use lowercase letters, digits and '_'"
                raise PipelineDefinitionError(msg)
            if not isinstance(phase, Phase):
                msg = f"stage {name!r} has no valid phase"
                raise PipelineDefinitionError(msg)
            if name in seen:
                msg = f"duplicate stage name {name!r}"
                raise PipelineDefinitionError(msg)
            if position == 0 and name != "initialize":
                msg = "the first stage must be 'initialize'"
                raise PipelineDefinitionError(msg)
            if _PHASE_ORDER[phase] < _PHASE_ORDER[previous]:
                msg = f"stage {name!r} ({phase.value}) cannot run after a {previous.value} stage"
                raise PipelineDefinitionError(msg)
            seen.add(name)
            previous = phase
