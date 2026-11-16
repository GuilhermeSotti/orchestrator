"""Business calendars of the Orchestrator platform (RFC-0011).

Holidays and exceptions are maintained by hand in files (TOML, CSV or JSON),
organized in layers with precedence; each calendar declares its weekend,
possibly empty, and the years it covers. Queries outside the coverage fail.
"""

from orchestrator_calendar._calendar import BusinessCalendar
from orchestrator_calendar._capability import CalendarCapability, Calendars, CalendarSpec
from orchestrator_calendar._model import (
    WEEKDAYS,
    CalendarCoverageError,
    CalendarError,
    CalendarLoaded,
    CalendarSourceError,
    Entry,
    EntryKind,
    Explanation,
    Layer,
    LayerEntry,
    LayerVersion,
    LoadedSource,
)
from orchestrator_calendar._sources import CalendarSource, FileCalendarSource
from orchestrator_calendar._version import __version__

__all__ = [
    "WEEKDAYS",
    "BusinessCalendar",
    "CalendarCapability",
    "CalendarCoverageError",
    "CalendarError",
    "CalendarLoaded",
    "CalendarSource",
    "CalendarSourceError",
    "CalendarSpec",
    "Calendars",
    "Entry",
    "EntryKind",
    "Explanation",
    "FileCalendarSource",
    "Layer",
    "LayerEntry",
    "LayerVersion",
    "LoadedSource",
    "__version__",
]
