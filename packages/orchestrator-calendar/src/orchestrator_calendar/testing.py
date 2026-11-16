"""Test helpers: an in-memory calendar source and the conformance suite of sources.

Example:
    >>> from datetime import date
    >>> from orchestrator_calendar import Entry, EntryKind
    >>> source = InMemoryCalendarSource([Entry(date(2026, 1, 1), EntryKind.HOLIDAY, "Ano-novo")])
    >>> source.load().entries[0].name
    'Ano-novo'
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Final, Self

from orchestrator_calendar._calendar import BusinessCalendar
from orchestrator_calendar._capability import CalendarCapability, Calendars, CalendarSpec
from orchestrator_calendar._model import Entry, EntryKind, Layer, LoadedSource
from orchestrator_calendar._sources import CalendarSource
from orchestrator_core import ConfigSection
from orchestrator_core.testing import check_capability_conformance

__all__ = ["SAMPLE_ENTRIES", "CalendarSourceContract", "InMemoryCalendarSource"]

SAMPLE_ENTRIES: Final = (
    Entry(date(2026, 1, 1), EntryKind.HOLIDAY, "Confraternização Universal", "Lei 662/1949"),
    Entry(date(2026, 11, 20), EntryKind.HOLIDAY, "Consciência Negra"),
    Entry(date(2026, 11, 21), EntryKind.BUSINESS_DAY, "Sábado de expediente"),
    Entry(date(2026, 12, 24), EntryKind.NOT_OBSERVED, "Véspera de Natal"),
)
"""Entries used by :class:`CalendarSourceContract`: one of each kind, with and without reference."""


class InMemoryCalendarSource(CalendarSource):
    """Source with fixed entries, for tests."""

    def __init__(self, entries: Sequence[Entry] = (), *, version: str = "memory") -> None:
        """Keep ``entries``; ``version`` is reported as the version of the content."""
        self._loaded = LoadedSource(version, tuple(entries))

    @classmethod
    def from_config(cls, section: ConfigSection) -> Self:
        """Create an empty source; the table must be empty."""
        section.check_keys(())
        return cls()

    def load(self) -> LoadedSource:
        """Return the entries."""
        return self._loaded

    def describe(self) -> str:
        """Return ``memory``."""
        return "memory"


class CalendarSourceContract(ABC):
    """Conformance suite of :class:`CalendarSource` implementations.

    Subclass it in a test module (the class name must start with ``Test``) and
    implement :meth:`make_source`. The same entries must give the same answers
    in any source, such as a file or a database (RFC-0011, section 12).
    """

    @abstractmethod
    def make_source(self, entries: Sequence[Entry]) -> CalendarSource:
        """Return a source whose content is exactly ``entries``."""

    def test_load_returns_the_entries(self) -> None:
        """The source returns the entries it holds, with every field."""
        loaded = self.make_source(SAMPLE_ENTRIES).load()
        assert sorted(loaded.entries, key=_key) == sorted(SAMPLE_ENTRIES, key=_key)  # noqa: S101

    def test_version_follows_the_content(self) -> None:
        """Same content, same version; other content, other version."""
        first = self.make_source(SAMPLE_ENTRIES).load().version
        again = self.make_source(SAMPLE_ENTRIES).load().version
        other = self.make_source(SAMPLE_ENTRIES[:1]).load().version
        assert first == again  # noqa: S101
        assert first != other  # noqa: S101

    def test_answers_like_the_reference(self) -> None:
        """A calendar built on the source answers like the in-memory reference."""
        source = self.make_source(SAMPLE_ENTRIES)
        reference = _calendar(InMemoryCalendarSource(SAMPLE_ENTRIES))
        candidate = _calendar(source)
        day = date(2026, 1, 1)
        while day.year == 2026:
            assert candidate.is_business_day(day) == reference.is_business_day(day), day  # noqa: S101
            day += timedelta(days=1)

    def test_describe_is_short_text(self) -> None:
        """The description fits a log line."""
        description = self.make_source(SAMPLE_ENTRIES).describe()
        assert isinstance(description, str)  # noqa: S101
        assert 0 < len(description) <= 300  # noqa: S101

    def test_capability_conformance(self) -> None:
        """The Capability honors the Core contract with this source."""
        year = datetime.now(UTC).astimezone().year
        spec = CalendarSpec(
            weekend=("saturday", "sunday"),
            layers=("sample",),
            coverage=(min(2026, year), max(2026, year + 1)),
        )
        capability = CalendarCapability(
            {"sample": spec}, {"sample": self.make_source(SAMPLE_ENTRIES)}
        )
        check_capability_conformance(capability, use=_use)


def _key(entry: Entry) -> tuple[date, str]:
    return entry.day, entry.name


def _calendar(source: CalendarSource) -> BusinessCalendar:
    layer = Layer.of("sample", source.describe(), source.load())
    return BusinessCalendar(
        "sample", weekend=["saturday", "sunday"], layers=[layer], coverage=(2026, 2026)
    )


def _use(handle: Calendars) -> object:
    return handle.get("sample").is_business_day(date(2026, 11, 20))
