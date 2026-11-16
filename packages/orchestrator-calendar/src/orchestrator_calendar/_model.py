"""Entries, layers, explanations, errors and events of business calendars (RFC-0011, section 2)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from orchestrator_core import Event, OrchestratorError, ProviderError

WEEKDAYS: Final = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
"""Names accepted in ``weekend``, in :meth:`datetime.date.weekday` order."""

_TEXT_LIMIT: Final = 200


class CalendarError(OrchestratorError):
    """Base class of the errors of business calendars."""


class CalendarCoverageError(CalendarError):
    """A day outside the years the calendar declares complete.

    Treating an unknown year as "no holidays" is the error this one prevents.
    """


class CalendarSourceError(ProviderError):
    """A calendar source could not be read, or its content is invalid."""


class EntryKind(StrEnum):
    """Kind of a calendar entry."""

    HOLIDAY = "holiday"
    """Not a business day."""
    BUSINESS_DAY = "business_day"
    """A business day, even on a declared weekend day."""
    NOT_OBSERVED = "not_observed"
    """Cancels the holidays of earlier layers: the weekend rule decides."""


@dataclass(frozen=True, slots=True)
class Entry:
    """One dated entry of a source.

    Attributes:
        day: Date of the entry.
        kind: What the entry means for that day.
        name: Name of the holiday or of the exception.
        reference: Optional normative reference (law, decree, notice).
    """

    day: date
    kind: EntryKind
    name: str
    reference: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize the fields.

        Raises:
            ValueError: Invalid kind, empty name or text longer than 200 characters.
        """
        object.__setattr__(self, "kind", EntryKind(self.kind))
        name = self.name.strip()
        if not name or len(name) > _TEXT_LIMIT:
            msg = f"entry name must have 1 to {_TEXT_LIMIT} characters"
            raise ValueError(msg)
        object.__setattr__(self, "name", name)
        reference = (self.reference or "").strip() or None
        if reference is not None and len(reference) > _TEXT_LIMIT:
            msg = f"entry reference must have up to {_TEXT_LIMIT} characters"
            raise ValueError(msg)
        object.__setattr__(self, "reference", reference)


@dataclass(frozen=True, slots=True)
class LoadedSource:
    """What a source read: the version of its content and its entries."""

    version: str
    entries: tuple[Entry, ...]


@dataclass(frozen=True, slots=True)
class Layer:
    """Entries of one source, in a calendar, with the source and the version read.

    Attributes:
        name: Name of the source in the configuration.
        source: Short description of the source (no secrets).
        version: Version of the content, such as ``sha256:...``.
        entries: Entries by day (read-only).
    """

    name: str
    source: str
    version: str
    entries: Mapping[date, Entry]

    @classmethod
    def of(cls, name: str, source: str, loaded: LoadedSource) -> Layer:
        """Build the layer; a day repeated in the same layer is an error.

        Raises:
            CalendarSourceError: Repeated day.
        """
        entries: dict[date, Entry] = {}
        for entry in loaded.entries:
            if entry.day in entries:
                msg = f"layer {name!r}: repeated entries for {entry.day.isoformat()}"
                raise CalendarSourceError(msg)
            entries[entry.day] = entry
        return cls(name, source, loaded.version, MappingProxyType(entries))


@dataclass(frozen=True, slots=True)
class LayerEntry:
    """An entry with the layer, source and version it came from."""

    layer: str
    source: str
    version: str
    entry: Entry


@dataclass(frozen=True, slots=True)
class Explanation:
    """Why a day is, or is not, a business day.

    Attributes:
        day: The day explained.
        business_day: The answer.
        weekend: Whether the day is a declared weekend day.
        decided_by: Entry of the latest layer for the day, or ``None`` when the
            weekend rule alone decided.
        entries: Every entry for the day, in layer order.
    """

    day: date
    business_day: bool
    weekend: bool
    decided_by: LayerEntry | None
    entries: tuple[LayerEntry, ...]

    def __str__(self) -> str:
        """Return a one-line explanation, such as for a log line."""
        verdict = "a business day" if self.business_day else "not a business day"
        rule = "a declared weekend day" if self.weekend else "not a declared weekend day"
        if self.decided_by is None:
            return f"{self.day.isoformat()} is {verdict}: no entry; {rule}"
        found = self.decided_by
        reason = (
            f"{found.entry.kind.value} {found.entry.name!r} in layer {found.layer!r}"
            f" ({found.source}, {found.version})"
        )
        if found.entry.kind is EntryKind.NOT_OBSERVED:
            reason = f"{reason}; {rule}"
        return f"{self.day.isoformat()} is {verdict}: {reason}"


@dataclass(frozen=True, slots=True)
class LayerVersion:
    """Name, source and version of a layer, as loaded by an execution."""

    name: str
    source: str
    version: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CalendarLoaded(Event):
    """A calendar was loaded at the start of an execution (RFC-0011, section 7).

    Attributes:
        calendar: Calendar name.
        layers: Layers in precedence order, with source and version.
    """

    calendar: str
    layers: tuple[LayerVersion, ...]


def weekday_numbers(names: Iterable[str]) -> frozenset[int]:
    """Return the :meth:`~datetime.date.weekday` numbers of day ``names``.

    Raises:
        ValueError: Unknown or repeated name.
    """
    numbers: list[int] = []
    for name in names:
        if name not in WEEKDAYS:
            msg = f"unknown weekday {name!r}; use {', '.join(WEEKDAYS)}"
            raise ValueError(msg)
        numbers.append(WEEKDAYS.index(name))
    if len(set(numbers)) != len(numbers):
        msg = "weekend days must not repeat"
        raise ValueError(msg)
    return frozenset(numbers)
