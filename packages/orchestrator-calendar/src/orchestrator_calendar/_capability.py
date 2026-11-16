"""CalendarCapability: loads the configured calendars at the start of each execution."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from types import MappingProxyType
from typing import Any, ClassVar, Self

from orchestrator_calendar._calendar import BusinessCalendar
from orchestrator_calendar._model import (
    CalendarCoverageError,
    CalendarError,
    CalendarLoaded,
    Layer,
    LayerVersion,
    weekday_numbers,
)
from orchestrator_calendar._sources import CalendarSource, FileCalendarSource
from orchestrator_core import Capability, ConfigSection, ConfigurationError, ExecutionContext

__all__ = ["CalendarCapability", "CalendarSpec", "Calendars"]

_logger = logging.getLogger("orchestrator_calendar")
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


@dataclass(frozen=True, slots=True)
class CalendarSpec:
    """Definition of one calendar.

    Attributes:
        weekend: Weekend days (``"saturday"``...); empty when every weekday is a
            business day. Required: there is no default (RFC-0011, section 2).
        layers: Source names, in precedence order (later layers prevail).
        coverage: First and last years the calendar declares complete.
        min_horizon_days: Days after today that must be inside the coverage
            when an execution starts (RFC-0011, section 7).
    """

    weekend: tuple[str, ...]
    layers: tuple[str, ...]
    coverage: tuple[int, int]
    min_horizon_days: int = 0

    def __post_init__(self) -> None:
        """Validate the definition.

        Raises:
            ValueError: Invalid weekend, layers, coverage or horizon.
        """
        weekday_numbers(self.weekend)
        if len(set(self.layers)) != len(self.layers):
            msg = "a calendar must not repeat a layer"
            raise ValueError(msg)
        first, last = self.coverage
        if not 2 <= first <= last <= 9998:  # noqa: PLR2004 - same limits as BusinessCalendar
            msg = "coverage must be [first year, last year], with first <= last"
            raise ValueError(msg)
        if self.min_horizon_days < 0:
            msg = "min_horizon_days must not be negative"
            raise ValueError(msg)


class Calendars:
    """Handle of one execution: the calendars loaded when it started."""

    def __init__(self, calendars: Mapping[str, BusinessCalendar]) -> None:
        """Keep ``calendars`` (read-only)."""
        self._calendars = MappingProxyType(dict(calendars))

    @property
    def names(self) -> tuple[str, ...]:
        """Configured calendar names."""
        return tuple(self._calendars)

    def get(self, name: str) -> BusinessCalendar:
        """Return the calendar ``name``.

        Raises:
            CalendarError: Unknown calendar.
        """
        try:
            return self._calendars[name]
        except KeyError:
            known = ", ".join(self._calendars) or "none"
            msg = f"unknown calendar {name!r}; configured: {known}"
            raise CalendarError(msg) from None


class CalendarCapability(Capability[Calendars]):
    r"""Business calendars maintained by hand, in layers (RFC-0011).

    Every execution reads its sources again when it starts, so a file edited
    by hand is seen by the next execution; the version read (SHA-256 for files)
    appears in the log and in the :class:`CalendarLoaded` event. An execution
    fails to start when today, or today plus ``min_horizon_days``, is outside
    a calendar's coverage. "Today" is the date of the machine's time zone
    (answer 7).

    Configuration (``[capabilities.calendar]``)::

        [capabilities.calendar.calendars.operacao]
        weekend = []  # required; [] when Saturday and Sunday are business days
        layers = ["feriados", "excecoes"]  # precedence: later layers prevail
        coverage = [2026, 2027]
        min_horizon_days = 30  # optional, default 0

        [capabilities.calendar.sources.feriados]
        provider = "file"  # built in; others only through providers=
        path = "calendarios/feriados.toml"

    Example:
        >>> import tempfile
        >>> from pathlib import Path
        >>> from orchestrator_core import RuntimeBuilder
        >>> folder = Path(tempfile.mkdtemp())
        >>> lines = ["date,type,name", "2026-12-25,holiday,Natal"]
        >>> _ = (folder / "f.csv").write_text("\n".join(lines))
        >>> capability = CalendarCapability(
        ...     {"operacao": CalendarSpec(weekend=(), layers=("f",), coverage=(2026, 2026))},
        ...     {"f": FileCalendarSource(folder / "f.csv")},
        ... )
        >>> from datetime import date
        >>> def automation(ctx):
        ...     calendar = ctx.capability(CalendarCapability).get("operacao")
        ...     return calendar.is_business_day(date(2026, 12, 26))
        >>> builder = RuntimeBuilder().with_environment({}, prefix=None)
        >>> builder.with_capability(capability).build().run(automation).output
        True
    """

    default_name: ClassVar[str] = "calendar"
    core_api: ClassVar[str | None] = "0.2"

    def __init__(
        self, calendars: Mapping[str, CalendarSpec], sources: Mapping[str, CalendarSource]
    ) -> None:
        """Create the Capability.

        Args:
            calendars: Calendar definitions by name.
            sources: Sources by name, referenced by the calendars' layers.

        Raises:
            ValueError: Invalid names, or a layer without a source.
        """
        for name in (*calendars, *sources):
            if not _NAME_RE.match(name):
                msg = f"invalid calendar or source name {name!r}: use [a-z][a-z0-9_]{{0,63}}"
                raise ValueError(msg)
        for name, spec in calendars.items():
            missing = [layer for layer in spec.layers if layer not in sources]
            if missing:
                msg = f"calendar {name!r} uses unknown sources: {', '.join(missing)}"
                raise ValueError(msg)
        self._calendars = MappingProxyType(dict(calendars))
        self._sources = MappingProxyType(dict(sources))

    @property
    def calendars(self) -> Mapping[str, CalendarSpec]:
        """Calendar definitions by name."""
        return self._calendars

    @property
    def sources(self) -> Mapping[str, CalendarSource]:
        """Sources by name."""
        return self._sources

    @classmethod
    def from_config(
        cls,
        section: ConfigSection,
        /,
        *,
        providers: Mapping[str, type[CalendarSource]] | None = None,
        **options: Any,  # noqa: ANN401 - interface of Capability.from_config
    ) -> Self:
        """Create the Capability from ``[capabilities.calendar]``.

        Args:
            section: The configuration table.
            providers: Source classes the configuration may choose, besides the
                built-in ``file``.
            **options: Not accepted; present for the Capability interface.

        Raises:
            ConfigurationError: Invalid configuration.
            TypeError: Unexpected options.
        """
        if options:
            msg = f"unexpected options: {', '.join(sorted(options))}"
            raise TypeError(msg)
        section.check_keys(("calendars", "sources"))
        available: dict[str, type[CalendarSource]] = {"file": FileCalendarSource}
        available.update(providers or {})
        sources: dict[str, CalendarSource] = {}
        tables = section.section("sources")
        for name in tables:
            table = tables.section(name)
            provider = table.get_choice("provider", sorted(available))
            settings = {key: value for key, value in table.items() if key != "provider"}
            sources[name] = available[provider].from_config(ConfigSection(settings, table.path))
        calendars: dict[str, CalendarSpec] = {}
        tables = section.section("calendars")
        for name in tables:
            table = tables.section(name)
            table.check_keys(("weekend", "layers", "coverage", "min_horizon_days"))
            try:
                calendars[name] = CalendarSpec(
                    weekend=_strings(table, "weekend", required=True),
                    layers=_strings(table, "layers", required=True),
                    coverage=_coverage(table),
                    min_horizon_days=table.get_int("min_horizon_days", 0, minimum=0),
                )
            except ValueError as exc:
                raise ConfigurationError(str(exc), key=table.path) from None
        try:
            return cls(calendars, sources)
        except ValueError as exc:
            raise ConfigurationError(str(exc), key=section.path or None) from None

    def verify(self) -> None:
        """Check every source used by a calendar."""
        for name in self._used_sources():
            self._sources[name].verify()

    def open(self, ctx: ExecutionContext) -> Calendars:
        """Read the sources, build the calendars and check their coverage.

        Raises:
            CalendarSourceError: A source could not be read or is invalid.
            CalendarCoverageError: Today or the horizon is outside a coverage.
        """
        layers: dict[str, Layer] = {}
        for name in self._used_sources():
            source = self._sources[name]
            layers[name] = Layer.of(name, source.describe(), source.load())
        local = ctx.now().astimezone()
        today = local.date()
        loaded: dict[str, BusinessCalendar] = {}
        for name, spec in self._calendars.items():
            calendar = BusinessCalendar(
                name,
                weekend=spec.weekend,
                layers=[layers[layer] for layer in spec.layers],
                coverage=spec.coverage,
            )
            horizon = today + timedelta(days=spec.min_horizon_days)
            if not (calendar.covers(today) and calendar.covers(horizon)):
                first, last = spec.coverage
                msg = (
                    f"calendar {name!r} covers {first}-{last}, but this execution needs"
                    f" {today.isoformat()} to {horizon.isoformat()}"
                )
                raise CalendarCoverageError(msg)
            loaded[name] = calendar
            versions = tuple(
                LayerVersion(lay.name, lay.source, lay.version) for lay in calendar.layers
            )
            _logger.info(
                "calendar %r loaded for %s (time zone of the machine: %s): %s",
                name,
                today.isoformat(),
                local.tzname() or local.strftime("%z"),
                "; ".join(f"{v.name} ({v.source}, {v.version})" for v in versions) or "no layers",
            )
            ctx.publish(
                CalendarLoaded(
                    execution_id=ctx.execution_id,
                    timestamp=ctx.now(),
                    calendar=name,
                    layers=versions,
                )
            )
        return Calendars(loaded)

    def _used_sources(self) -> list[str]:
        used: list[str] = []
        for spec in self._calendars.values():
            used.extend(layer for layer in spec.layers if layer not in used)
        return used


def _strings(section: ConfigSection, key: str, *, required: bool) -> tuple[str, ...]:
    if key not in section:
        if required:
            raise ConfigurationError("required list", key=section.key_path(key))
        return ()
    value = section[key]
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
        raise ConfigurationError("expected a list of names", key=section.key_path(key))
    return tuple(value)


def _coverage(section: ConfigSection) -> tuple[int, int]:
    value = section.get("coverage")
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 2  # noqa: PLR2004 - first and last year
        or not all(type(item) is int for item in value)
    ):
        raise ConfigurationError(
            "expected [first year, last year]", key=section.key_path("coverage")
        )
    return value[0], value[1]
