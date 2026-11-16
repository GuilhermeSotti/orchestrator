from __future__ import annotations

from datetime import date

import pytest

from orchestrator_calendar import (
    BusinessCalendar,
    CalendarCoverageError,
    Entry,
    EntryKind,
    Layer,
    LoadedSource,
)

H, B, N = EntryKind.HOLIDAY, EntryKind.BUSINESS_DAY, EntryKind.NOT_OBSERVED


def _layer(name: str, *entries: tuple[date, EntryKind, str], version: str = "v1") -> Layer:
    loaded = LoadedSource(version, tuple(Entry(day, kind, label) for day, kind, label in entries))
    return Layer.of(name, f"memory {name}", loaded)


NATIONAL = _layer(
    "nacional",
    (date(2025, 12, 25), H, "Natal"),
    (date(2026, 1, 1), H, "Ano-novo"),
    (date(2026, 11, 15), H, "Proclamação da República"),  # a Sunday
    (date(2026, 11, 20), H, "Consciência Negra"),  # a Friday
    (date(2026, 12, 25), H, "Natal"),
)
EXCEPTIONS = _layer(
    "excecoes",
    (date(2026, 11, 20), N, "Expediente normal"),
    (date(2026, 11, 21), B, "Sábado de fechamento"),
    version="v2",
)


def _calendar(weekend: tuple[str, ...] = ("saturday", "sunday")) -> BusinessCalendar:
    return BusinessCalendar(
        "operacao", weekend=weekend, layers=[NATIONAL, EXCEPTIONS], coverage=(2025, 2026)
    )


@pytest.mark.parametrize(
    ("day", "business"),
    [
        (date(2026, 11, 19), True),  # Thursday
        (date(2026, 11, 20), True),  # holiday cancelled by a later layer
        (date(2026, 11, 21), True),  # Saturday forced as a business day
        (date(2026, 11, 22), False),  # Sunday
        (date(2026, 11, 15), False),  # holiday on a Sunday
        (date(2026, 12, 25), False),
        (date(2025, 12, 31), True),  # year boundary
        (date(2026, 1, 1), False),
    ],
)
def test_boundary_cases(day: date, business: bool) -> None:
    assert _calendar().is_business_day(day) is business


def test_empty_weekend_makes_only_holidays_non_business() -> None:
    calendar = BusinessCalendar("todos", weekend=[], layers=[NATIONAL], coverage=(2025, 2026))
    assert calendar.is_business_day(date(2026, 11, 21))  # Saturday
    assert calendar.is_business_day(date(2026, 11, 22))  # Sunday
    assert not calendar.is_business_day(date(2026, 11, 20))
    assert calendar.weekend == ()


def test_later_layers_prevail() -> None:
    reversed_order = BusinessCalendar(
        "x", weekend=["saturday", "sunday"], layers=[EXCEPTIONS, NATIONAL], coverage=(2025, 2026)
    )
    assert not reversed_order.is_business_day(date(2026, 11, 20))
    assert _calendar().is_business_day(date(2026, 11, 20))


def test_next_and_previous_business_days() -> None:
    calendar = _calendar()
    assert calendar.add_business_days(date(2026, 11, 19), 1) == date(2026, 11, 20)
    assert calendar.add_business_days(date(2026, 11, 21), 1) == date(2026, 11, 23)
    assert calendar.add_business_days(date(2026, 11, 23), -1) == date(2026, 11, 21)
    assert calendar.add_business_days(date(2026, 12, 24), 1) == date(2026, 12, 28)
    assert calendar.add_business_days(date(2026, 1, 2), -1) == date(2025, 12, 31)
    assert calendar.add_business_days(date(2026, 11, 16), 5) == date(2026, 11, 21)
    with pytest.raises(ValueError, match="must not be 0"):
        calendar.add_business_days(date(2026, 11, 16), 0)


def test_roll_and_last_business_day_of_a_month() -> None:
    calendar = _calendar()
    assert calendar.roll(date(2026, 11, 19), "forward") == date(2026, 11, 19)
    assert calendar.roll(date(2026, 11, 22), "forward") == date(2026, 11, 23)
    assert calendar.roll(date(2026, 11, 22), "backward") == date(2026, 11, 21)
    assert calendar.roll(date(2026, 1, 31), "backward") == date(2026, 1, 30)  # last of January
    with pytest.raises(ValueError, match="direction"):
        calendar.roll(date(2026, 1, 1), "sideways")  # type: ignore[arg-type]


def test_business_days_between_needs_explicit_limits() -> None:
    calendar = _calendar()
    monday, friday = date(2026, 11, 16), date(2026, 11, 20)
    assert calendar.business_days_between(monday, friday, include_start=True, include_end=True) == 5
    assert (
        calendar.business_days_between(monday, friday, include_start=False, include_end=False) == 3
    )
    assert (
        calendar.business_days_between(monday, monday, include_start=True, include_end=False) == 0
    )
    with pytest.raises(ValueError, match="after"):
        calendar.business_days_between(friday, monday, include_start=True, include_end=True)


def test_queries_outside_the_coverage_always_fail() -> None:
    calendar = _calendar()
    with pytest.raises(CalendarCoverageError, match="2027-01-01 is outside the coverage 2025-2026"):
        calendar.is_business_day(date(2027, 1, 1))
    with pytest.raises(CalendarCoverageError):
        calendar.add_business_days(date(2026, 12, 30), 3)
    with pytest.raises(CalendarCoverageError):
        calendar.roll(date(2024, 12, 31), "forward")
    with pytest.raises(CalendarCoverageError):
        calendar.holidays(2024)
    with pytest.raises(CalendarCoverageError):
        calendar.business_days_between(
            date(2026, 12, 1), date(2027, 1, 5), include_start=True, include_end=True
        )
    everything_off = BusinessCalendar("x", weekend=_ALL_DAYS, coverage=(2026, 2026))
    with pytest.raises(CalendarCoverageError):
        everything_off.add_business_days(date(2026, 6, 1), 1)


_ALL_DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def test_explain_points_to_the_layer_and_version() -> None:
    calendar = _calendar()
    cancelled = calendar.explain(date(2026, 11, 20))
    assert cancelled.business_day
    assert [found.layer for found in cancelled.entries] == ["nacional", "excecoes"]
    assert cancelled.decided_by is not None
    assert (cancelled.decided_by.layer, cancelled.decided_by.version) == ("excecoes", "v2")
    assert str(cancelled) == (
        "2026-11-20 is a business day: not_observed 'Expediente normal' in layer 'excecoes'"
        " (memory excecoes, v2); not a declared weekend day"
    )
    sunday = calendar.explain(date(2026, 11, 22))
    assert sunday.decided_by is None
    assert str(sunday) == "2026-11-22 is not a business day: no entry; a declared weekend day"


def test_holidays_after_precedence() -> None:
    names = [found.entry.name for found in _calendar().holidays(2026)]
    assert names == ["Ano-novo", "Proclamação da República", "Natal"]


def test_invalid_definitions() -> None:
    with pytest.raises(ValueError, match="unknown weekday"):
        BusinessCalendar("x", weekend=["sabado"], coverage=(2026, 2026))
    with pytest.raises(ValueError, match="repeat"):
        BusinessCalendar("x", weekend=["sunday", "sunday"], coverage=(2026, 2026))
    with pytest.raises(ValueError, match="coverage"):
        BusinessCalendar("x", weekend=[], coverage=(2027, 2026))
    with pytest.raises(ValueError, match="outside 2026-2026"):
        BusinessCalendar("x", weekend=[], layers=[NATIONAL], coverage=(2026, 2026))
    with pytest.raises(ValueError, match="name"):
        Entry(date(2026, 1, 1), H, " ")
    with pytest.raises(ValueError, match="not a valid"):
        Entry(date(2026, 1, 1), "feriado", "x")  # type: ignore[arg-type]


def test_repr_and_properties() -> None:
    calendar = _calendar()
    assert repr(calendar) == (
        "BusinessCalendar('operacao', weekend=['saturday', 'sunday'],"
        " layers=[nacional, excecoes], coverage=2025-2026)"
    )
    assert calendar.coverage == (2025, 2026)
    assert [layer.name for layer in calendar.layers] == ["nacional", "excecoes"]
    assert calendar.name == "operacao"
