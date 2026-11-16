"""Calendar sources: the port of the Providers and the built-in file source (RFC-0011, 5)."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import tomllib
from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Final, Self

from orchestrator_calendar._model import CalendarSourceError, Entry, EntryKind, LoadedSource
from orchestrator_core import CapabilityUnavailableError, ConfigSection, ConfigurationError

__all__ = ["CalendarSource", "FileCalendarSource"]

FORMATS: Final = ("toml", "csv", "json")
_FIELDS: Final = ("date", "type", "name", "reference")
_REQUIRED: Final = ("date", "type", "name")
_ISO_DATE: Final = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DEFAULT_MAX_BYTES: Final = 1_048_576


class CalendarSource(ABC):
    """Port of the calendar Providers: where the entries of one layer come from.

    Each execution calls :meth:`load` once per source at its start, so a source
    maintained by hand is read again by the next execution.
    """

    @classmethod
    @abstractmethod
    def from_config(cls, section: ConfigSection) -> Self:
        """Create the source from its table, without the ``provider`` key.

        Raises:
            ConfigurationError: Unknown or invalid keys.
        """

    def verify(self) -> None:  # noqa: B027 - optional hook with a no-op default
        """Check that the source can be read; raise ``CapabilityUnavailableError`` if not."""

    @abstractmethod
    def load(self) -> LoadedSource:
        """Read the entries and the version of the content.

        Raises:
            CalendarSourceError: The source cannot be read or has invalid content.
        """

    @abstractmethod
    def describe(self) -> str:
        """Return a short description for logs and explanations, without secrets."""


class FileCalendarSource(CalendarSource):
    """Entries in a TOML, CSV or JSON file; the version is the SHA-256 of the bytes.

    Formats (dates in ``AAAA-MM-DD``; ``reference`` is optional)::

        # TOML
        [[entries]]
        date = 2026-11-20
        type = "holiday"            # holiday, business_day or not_observed
        name = "Dia Nacional de Zumbi e da Consciência Negra"
        reference = "Lei 14.759/2023"

        # CSV, with header; delimiter "," (default) or ";"
        date,type,name,reference
        2026-11-20,holiday,Dia Nacional de Zumbi e da Consciência Negra,Lei 14.759/2023

        # JSON
        {"entries": [{"date": "2026-11-20", "type": "holiday", "name": "..."}]}

    Unknown keys or columns, invalid dates and files larger than ``max_bytes``
    are errors. Relative paths are relative to the working directory.
    """

    def __init__(
        self,
        path: str | os.PathLike[str],
        *,
        file_format: str | None = None,
        delimiter: str = ",",
        max_bytes: int = _DEFAULT_MAX_BYTES,
    ) -> None:
        """Create the source.

        Args:
            path: File with the entries.
            file_format: ``toml``, ``csv`` or ``json`` (default: from the extension).
            delimiter: CSV delimiter, ``,`` or ``;``.
            max_bytes: Largest file accepted.

        Raises:
            ValueError: Unknown format or delimiter, or ``max_bytes`` below 1.
        """
        self._path = Path(path)
        chosen = (file_format or self._path.suffix.removeprefix(".")).lower()
        if chosen not in FORMATS:
            msg = f"calendar file format must be one of {', '.join(FORMATS)}"
            raise ValueError(msg)
        if delimiter not in {",", ";"}:
            msg = "delimiter must be ',' or ';'"
            raise ValueError(msg)
        if max_bytes < 1:
            msg = "max_bytes must be at least 1"
            raise ValueError(msg)
        self._format = chosen
        self._delimiter = delimiter
        self._max_bytes = max_bytes

    @classmethod
    def from_config(cls, section: ConfigSection) -> Self:
        """Create the source from ``path`` and optional ``format``, ``delimiter``, ``max_bytes``."""
        section.check_keys(("path", "format", "delimiter", "max_bytes"))
        path = section.get_path("path")
        try:
            return cls(
                path,
                file_format=section.get_choice("format", FORMATS, None),
                delimiter=section.get_choice("delimiter", (",", ";"), ","),
                max_bytes=section.get_int("max_bytes", _DEFAULT_MAX_BYTES, minimum=1),
            )
        except ValueError as exc:
            raise ConfigurationError(str(exc), key=section.key_path("path")) from None

    @property
    def path(self) -> Path:
        """File with the entries."""
        return self._path

    def verify(self) -> None:
        """Check that the file exists."""
        if not self._path.is_file():
            msg = f"calendar file {self._path} does not exist or is not a file"
            raise CapabilityUnavailableError(msg)

    def load(self) -> LoadedSource:
        """Read and validate the file."""
        try:
            with self._path.open("rb") as stream:
                data = stream.read(self._max_bytes + 1)
        except OSError as exc:
            reason = exc.strerror or type(exc).__name__
            msg = f"cannot read calendar file {self._path}: {reason}"
            raise CalendarSourceError(msg) from None
        if len(data) > self._max_bytes:
            msg = f"calendar file {self._path} is larger than {self._max_bytes} bytes"
            raise CalendarSourceError(msg)
        version = f"sha256:{hashlib.sha256(data).hexdigest()}"
        try:
            rows = self._rows(data)
            entries = tuple(_entry(index, row) for index, row in enumerate(rows, start=1))
        except (ValueError, UnicodeDecodeError, tomllib.TOMLDecodeError, csv.Error) as exc:
            msg = f"invalid calendar file {self._path}: {exc}"
            raise CalendarSourceError(msg) from None
        return LoadedSource(version=version, entries=entries)

    def describe(self) -> str:
        """Return ``file <path>``."""
        return f"file {self._path.as_posix()}"

    def _rows(self, data: bytes) -> list[Mapping[str, object]]:
        if self._format == "csv":
            reader = csv.DictReader(
                io.StringIO(data.decode("utf-8-sig"), newline=""), delimiter=self._delimiter
            )
            columns = reader.fieldnames or []
            if set(columns) - set(_FIELDS) or not set(_REQUIRED) <= set(columns):
                msg = f"CSV header must have {', '.join(_REQUIRED)} and optionally reference"
                raise ValueError(msg)
            rows: list[Mapping[str, object]] = []
            for index, row in enumerate(reader, start=1):
                values = {str(key): value for key, value in row.items() if key is not None}
                if len(values) != len(row):
                    msg = f"entry {index}: more values than columns"
                    raise ValueError(msg)
                rows.append({key: value for key, value in values.items() if value is not None})
            return rows
        text = data.decode("utf-8")
        document = tomllib.loads(text) if self._format == "toml" else json.loads(text)
        if not isinstance(document, dict) or set(document) - {"entries"}:
            msg = "the file must have only the 'entries' list"
            raise ValueError(msg)
        entries = document.get("entries", [])
        if not isinstance(entries, list) or not all(isinstance(row, dict) for row in entries):
            msg = "'entries' must be a list of tables"
            raise ValueError(msg)
        return entries


def _entry(index: int, row: Mapping[str, object]) -> Entry:
    unknown = sorted(set(row) - set(_FIELDS))
    if unknown:
        msg = f"entry {index}: unknown keys {', '.join(unknown)}"
        raise ValueError(msg)
    missing = [key for key in _REQUIRED if row.get(key) in {None, ""}]
    if missing:
        msg = f"entry {index}: missing {', '.join(missing)}"
        raise ValueError(msg)
    raw_date, kind, name, reference = row["date"], row["type"], row["name"], row.get("reference")
    if isinstance(raw_date, str) and _ISO_DATE.match(raw_date):
        day = date.fromisoformat(raw_date)
    elif type(raw_date) is date:
        day = raw_date
    else:
        msg = f"entry {index}: date must be AAAA-MM-DD"
        raise ValueError(msg)
    if not isinstance(kind, str) or not isinstance(name, str):
        msg = f"entry {index}: type and name must be text"
        raise ValueError(msg)
    if reference is not None and not isinstance(reference, str):
        msg = f"entry {index}: reference must be text"
        raise ValueError(msg)
    try:
        return Entry(day, EntryKind(kind), name, reference)
    except ValueError as exc:
        msg = f"entry {index} ({day.isoformat()}): {exc}"
        raise ValueError(msg) from None
