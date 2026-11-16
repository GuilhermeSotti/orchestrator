"""BusinessCalendar: immutable calendar with declared weekend, layers and coverage."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date, timedelta
from typing import Literal

from orchestrator_calendar._model import (
    WEEKDAYS,
    CalendarCoverageError,
    EntryKind,
    Explanation,
    Layer,
    LayerEntry,
    weekday_numbers,
)
from orchestrator_core import ExecutionContext

__all__ = ["BusinessCalendar"]

_ONE_DAY = timedelta(days=1)


class BusinessCalendar:
    """Business days of one calendar: declared weekend, then layers in precedence order.

    The weekend has no default: each calendar declares its days, possibly none
    (RFC-0011, section 2). For each day, the entry of the latest layer decides:
    ``holiday`` is not a business day, ``business_day`` is, and
    ``not_observed`` cancels the holidays of earlier layers, leaving the weekend
    rule to decide. Any day outside ``coverage`` raises
    :class:`CalendarCoverageError`. Objects are immutable and can be used
    outside executions.

    Example:
        >>> from orchestrator_calendar import Entry, Layer, LoadedSource
        >>> holidays = LoadedSource("v1", (Entry(date(2026, 11, 20), "holiday", "Feriado"),))
        >>> calendar = BusinessCalendar(
        ...     "operacao",
        ...     weekend=["saturday", "sunday"],
        ...     layers=[Layer.of("nacional", "memory", holidays)],
        ...     coverage=(2026, 2026),
        ... )
        >>> calendar.is_business_day(date(2026, 11, 20))
        False
        >>> calendar.add_business_days(date(2026, 11, 19), 1)
        datetime.date(2026, 11, 23)
    """

    __slots__ = ("_coverage", "_effective", "_layers", "_name", "_weekend")

    def __init__(
        self,
        name: str,
        *,
        weekend: Iterable[str],
        layers: Sequence[Layer] = (),
        coverage: tuple[int, int],
    ) -> None:
        """Create the calendar.

        Args:
            name: Calendar name.
            weekend: Names of the weekend days (``"saturday"``...); may be empty.
            layers: Layers in precedence order: later layers prevail.
            coverage: First and last years the calendar declares complete.

        Raises:
            ValueError: Invalid weekend, coverage, or entries outside the coverage.
        """
        first, last = coverage
        if not 2 <= first <= last <= 9998:  # noqa: PLR2004 - one year of margin in each end
            msg = "coverage must be (first year, last year), 2 <= first <= last <= 9998"
            raise ValueError(msg)
        self._name = name
        self._weekend = weekday_numbers(weekend)
        self._coverage = (first, last)
        self._layers = tuple(layers)
        effective: dict[date, LayerEntry] = {}
        for layer in self._layers:
            for day, entry in layer.entries.items():
                if not first <= day.year <= last:
                    msg = f"layer {layer.name!r} has {day.isoformat()}, outside {first}-{last}"
                    raise ValueError(msg)
                effective[day] = LayerEntry(layer.name, layer.source, layer.version, entry)
        self._effective = effective

    @property
    def name(self) -> str:
        """Calendar name."""
        return self._name

    @property
    def weekend(self) -> tuple[str, ...]:
        """Declared weekend days, in week order."""
        return tuple(WEEKDAYS[number] for number in sorted(self._weekend))

    @property
    def coverage(self) -> tuple[int, int]:
        """First and last years the calendar declares complete."""
        return self._coverage

    @property
    def layers(self) -> tuple[Layer, ...]:
        """Layers in precedence order."""
        return self._layers

    def covers(self, day: date) -> bool:
        """Tell whether ``day`` is inside the coverage."""
        return self._coverage[0] <= day.year <= self._coverage[1]

    def is_business_day(self, day: date) -> bool:
        """Tell whether ``day`` is a business day.

        Raises:
            CalendarCoverageError: ``day`` is outside the coverage.
        """
        self._check(day)
        found = self._effective.get(day)
        if found is None or found.entry.kind is EntryKind.NOT_OBSERVED:
            return day.weekday() not in self._weekend
        return found.entry.kind is EntryKind.BUSINESS_DAY

    def explain(self, day: date) -> Explanation:
        """Return why ``day`` is, or is not, a business day.

        Raises:
            CalendarCoverageError: ``day`` is outside the coverage.
        """
        business = self.is_business_day(day)
        entries = tuple(
            LayerEntry(layer.name, layer.source, layer.version, layer.entries[day])
            for layer in self._layers
            if day in layer.entries
        )
        return Explanation(
            day=day,
            business_day=business,
            weekend=day.weekday() in self._weekend,
            decided_by=entries[-1] if entries else None,
            entries=entries,
        )

    def add_business_days(self, day: date, n: int) -> date:
        """Move ``n`` business days forward (``n > 0``) or backward (``n < 0``).

        ``day`` itself is not counted: ``add_business_days(d, 1)`` is the next
        business day after ``d`` and ``add_business_days(d, -1)`` the previous one.

        Raises:
            ValueError: ``n`` is 0 (use :meth:`roll` or :meth:`is_business_day`).
            CalendarCoverageError: The walk leaves the coverage.
        """
        if n == 0:
            msg = "n must not be 0: use roll() or is_business_day()"
            raise ValueError(msg)
        self._check(day)
        step = _ONE_DAY if n > 0 else -_ONE_DAY
        remaining, current = abs(n), day
        while remaining:
            current += step
            if self.is_business_day(current):
                remaining -= 1
        return current

    def roll(self, day: date, direction: Literal["forward", "backward"]) -> date:
        """Return ``day`` if it is a business day, else the next or the previous one.

        Raises:
            ValueError: Unknown direction.
            CalendarCoverageError: The walk leaves the coverage.
        """
        if direction not in {"forward", "backward"}:
            msg = "direction must be 'forward' or 'backward'"
            raise ValueError(msg)
        step = _ONE_DAY if direction == "forward" else -_ONE_DAY
        current = day
        while not self.is_business_day(current):
            current += step
        return current

    def business_days_between(
        self, start: date, end: date, *, include_start: bool, include_end: bool
    ) -> int:
        """Count the business days from ``start`` to ``end``.

        Raises:
            ValueError: ``start`` is after ``end``.
            CalendarCoverageError: A day of the interval is outside the coverage.
        """
        if start > end:
            msg = "start must not be after end"
            raise ValueError(msg)
        self._check(start)
        self._check(end)
        count, current = 0, start
        while current <= end:
            counted = (current != start or include_start) and (current != end or include_end)
            if counted and self.is_business_day(current):
                count += 1
            current += _ONE_DAY
        return count

    def holidays(self, year: int) -> tuple[LayerEntry, ...]:
        """Return the holidays in effect in ``year``, after precedence, by date.

        Raises:
            CalendarCoverageError: ``year`` is outside the coverage.
        """
        self._check(date(year, 1, 1))
        return tuple(
            found
            for day, found in sorted(self._effective.items())
            if day.year == year and found.entry.kind is EntryKind.HOLIDAY
        )

    @staticmethod
    def today(ctx: ExecutionContext) -> date:
        """Return today's date in the time zone of the machine (RFC-0011, answer 7)."""
        return ctx.now().astimezone().date()

    def _check(self, day: date) -> None:
        if not self.covers(day):
            first, last = self._coverage
            msg = f"{day.isoformat()} is outside the coverage {first}-{last} of {self._name!r}"
            raise CalendarCoverageError(msg)

    def __repr__(self) -> str:
        """Return the name, the weekend, the layers and the coverage."""
        layers = ", ".join(layer.name for layer in self._layers)
        first, last = self._coverage
        return (
            f"BusinessCalendar({self._name!r}, weekend={list(self.weekend)},"
            f" layers=[{layers}], coverage={first}-{last})"
        )
