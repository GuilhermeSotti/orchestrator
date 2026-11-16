from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from orchestrator_calendar import (
    CalendarCapability,
    CalendarCoverageError,
    CalendarError,
    CalendarLoaded,
    CalendarSpec,
    FileCalendarSource,
)
from orchestrator_calendar.testing import InMemoryCalendarSource
from orchestrator_core import (
    CapabilityUnavailableError,
    ConfigSection,
    ConfigurationError,
    ExecutionContext,
    ExecutionStatus,
    RuntimeBuilder,
)
from orchestrator_core.testing import EventRecorder, FakeClock

NOVEMBER = FakeClock(wall_start=datetime(2026, 11, 16, 12, tzinfo=UTC))

FERIADOS = """\
[[entries]]
date = 2026-11-20
type = "holiday"
name = "Consciência Negra"
reference = "Lei 14.759/2023"
"""


def _settings(path: Path, **calendar: object) -> dict[str, object]:
    return {
        "capabilities": {
            "calendar": {
                "calendars": {
                    "operacao": {"weekend": [], "layers": ["feriados"], "coverage": [2026, 2026]}
                    | calendar
                },
                "sources": {"feriados": {"provider": "file", "path": str(path)}},
            }
        }
    }


def _builder(settings: dict[str, object], clock: FakeClock = NOVEMBER) -> RuntimeBuilder:
    return (
        RuntimeBuilder()
        .with_environment({}, prefix=None)
        .with_settings(settings)
        .with_clock(clock)
        .with_capability(CalendarCapability)
    )


def test_configured_calendar_with_saturday_and_sunday_as_business_days(tmp_path: Path) -> None:
    path = tmp_path / "feriados.toml"
    path.write_text(FERIADOS, encoding="utf-8")
    events = EventRecorder()

    def automation(ctx: ExecutionContext) -> dict[str, object]:
        calendar = ctx.capability(CalendarCapability).get("operacao")
        return {
            "saturday": calendar.is_business_day(date(2026, 11, 21)),
            "holiday": calendar.is_business_day(date(2026, 11, 20)),
            "next": calendar.add_business_days(date(2026, 11, 19), 1),
            "today": calendar.today(ctx),
            "why": str(calendar.explain(date(2026, 11, 20))),
        }

    result = _builder(_settings(path)).on_event(CalendarLoaded, events).build().run(automation)
    assert result.status is ExecutionStatus.SUCCEEDED, result.error
    assert result.output["saturday"] is True
    assert result.output["holiday"] is False
    assert result.output["next"] == date(2026, 11, 21)
    assert result.output["today"] == datetime(2026, 11, 16, 12, tzinfo=UTC).astimezone().date()
    assert "Consciência Negra" in str(result.output["why"])
    (loaded,) = events.of_type(CalendarLoaded)
    assert loaded.calendar == "operacao"
    (layer,) = loaded.layers
    assert layer.name == "feriados"
    assert layer.version.startswith("sha256:")
    assert layer.source == f"file {path.as_posix()}"


def test_each_execution_reads_the_file_again(tmp_path: Path) -> None:
    path = tmp_path / "feriados.toml"
    path.write_text(FERIADOS, encoding="utf-8")
    runtime = _builder(_settings(path)).build()

    def automation(ctx: ExecutionContext) -> bool:
        return (
            ctx.capability(CalendarCapability).get("operacao").is_business_day(date(2026, 11, 20))
        )

    assert runtime.run(automation).output is False
    path.write_text("", encoding="utf-8")  # holiday removed by hand
    assert runtime.run(automation).output is True


def test_version_and_source_are_logged(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    path = tmp_path / "feriados.toml"
    path.write_text(FERIADOS, encoding="utf-8")
    with caplog.at_level(logging.INFO, logger="orchestrator_calendar"):
        assert _builder(_settings(path)).build().run(lambda ctx: None).succeeded
    assert "calendar 'operacao' loaded for 2026-11-16 (time zone of the machine: " in caplog.text
    assert "): feriados (file " in caplog.text
    assert "sha256:" in caplog.text


def test_the_execution_fails_before_the_automation_when_coverage_ends(tmp_path: Path) -> None:
    path = tmp_path / "feriados.toml"
    path.write_text(FERIADOS, encoding="utf-8")
    called: list[bool] = []
    settings = _settings(path, min_horizon_days=60)
    result = _builder(settings).build().run(lambda ctx: called.append(True))
    assert result.status is ExecutionStatus.FAILED
    assert isinstance(result.error, CalendarCoverageError)
    assert "needs 2026-11-16 to 2027-01-15" in str(result.error)
    assert called == []
    january = FakeClock(wall_start=datetime(2027, 1, 2, 12, tzinfo=UTC))
    late = _builder(_settings(path), january).build().run(lambda ctx: None)
    assert isinstance(late.error, CalendarCoverageError)


def test_missing_and_invalid_sources_fail_the_execution(tmp_path: Path) -> None:
    missing = _builder(_settings(tmp_path / "missing.toml")).build().run(lambda ctx: None)
    assert isinstance(missing.error, CapabilityUnavailableError)
    repeated = tmp_path / "repetido.toml"
    repeated.write_text(FERIADOS + "\n" + FERIADOS, encoding="utf-8")
    result = _builder(_settings(repeated)).build().run(lambda ctx: None)
    assert "repeated entries for 2026-11-20" in str(result.error)


@pytest.mark.parametrize(
    ("calendar", "message"),
    [
        ({"weekend": None}, "weekend: required list"),
        ({"weekend": ["sabado"]}, "unknown weekday"),
        ({"layers": "feriados"}, "list of names"),
        ({"layers": ["outra"]}, "unknown sources: outra"),
        ({"layers": ["feriados", "feriados"]}, "repeat a layer"),
        ({"coverage": [2026]}, "first year, last year"),
        ({"coverage": [2027, 2026]}, "coverage"),
        ({"coverage": ["2026", "2026"]}, "first year, last year"),
        ({"min_horizon_days": -1}, "min_horizon_days"),
        ({"timezone": "America/Sao_Paulo"}, "unknown key"),
    ],
)
def test_invalid_calendar_configuration(
    tmp_path: Path, calendar: dict[str, object], message: str
) -> None:
    settings = _settings(tmp_path / "f.toml", **calendar)
    table = settings["capabilities"]["calendar"]["calendars"]["operacao"]  # type: ignore[index]
    for key in [key for key, value in calendar.items() if value is None]:
        del table[key]
    with pytest.raises(ConfigurationError, match=message):
        _builder(settings).build()


def test_only_known_providers_can_be_chosen(tmp_path: Path) -> None:
    section = ConfigSection(
        {
            "calendars": {"c": {"weekend": [], "layers": ["s"], "coverage": [2026, 2026]}},
            "sources": {"s": {"provider": "memory"}},
        },
        "capabilities.calendar",
    )
    with pytest.raises(ConfigurationError, match="provider"):
        CalendarCapability.from_config(section)
    capability = CalendarCapability.from_config(
        section, providers={"memory": InMemoryCalendarSource}
    )
    assert isinstance(capability.sources["s"], InMemoryCalendarSource)
    assert capability.calendars["c"] == CalendarSpec(
        weekend=(), layers=("s",), coverage=(2026, 2026)
    )
    with pytest.raises(ConfigurationError, match="unknown key"):
        CalendarCapability.from_config(ConfigSection({"x": {}}, "capabilities.calendar"))
    with pytest.raises(TypeError, match="unexpected options"):
        CalendarCapability.from_config(section, colour="blue")


def test_names_and_unknown_calendar() -> None:
    source = InMemoryCalendarSource()
    with pytest.raises(ValueError, match="invalid calendar or source name"):
        CalendarCapability({"Operação": CalendarSpec((), ("s",), (2026, 2026))}, {"s": source})
    capability = CalendarCapability(
        {"c": CalendarSpec((), ("s",), (2026, 2026))}, {"s": source, "unused": source}
    )

    def automation(ctx: ExecutionContext) -> tuple[str, ...]:
        calendars = ctx.capability(CalendarCapability)
        with pytest.raises(CalendarError, match="unknown calendar 'x'; configured: c"):
            calendars.get("x")
        return calendars.names

    runtime = RuntimeBuilder().with_environment({}, prefix=None).with_clock(NOVEMBER)
    assert runtime.with_capability(capability).build().run(automation).output == ("c",)


def test_file_source_is_built_in() -> None:
    capability = CalendarCapability.from_config(
        ConfigSection(
            {
                "calendars": {"c": {"weekend": [], "layers": ["s"], "coverage": [2026, 2026]}},
                "sources": {"s": {"provider": "file", "path": "calendarios/s.csv"}},
            },
            "capabilities.calendar",
        )
    )
    source = capability.sources["s"]
    assert isinstance(source, FileCalendarSource)
    assert source.path == Path("calendarios/s.csv")
