from __future__ import annotations

import csv
import io
import json
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import pytest

from orchestrator_calendar import (
    CalendarSource,
    CalendarSourceError,
    Entry,
    EntryKind,
    FileCalendarSource,
)
from orchestrator_calendar.testing import CalendarSourceContract, InMemoryCalendarSource
from orchestrator_core import CapabilityUnavailableError, ConfigSection, ConfigurationError


def _toml(entries: Sequence[Entry]) -> str:
    blocks = []
    for entry in entries:
        lines = [
            "[[entries]]",
            f"date = {entry.day.isoformat()}",
            f'type = "{entry.kind.value}"',
            f"name = {json.dumps(entry.name, ensure_ascii=False)}",
        ]
        if entry.reference:
            lines.append(f"reference = {json.dumps(entry.reference, ensure_ascii=False)}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def _csv(entries: Sequence[Entry], delimiter: str = ",") -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=delimiter, lineterminator="\n")
    writer.writerow(["date", "type", "name", "reference"])
    for entry in entries:
        writer.writerow(
            [entry.day.isoformat(), entry.kind.value, entry.name, entry.reference or ""]
        )
    return buffer.getvalue()


def _json(entries: Sequence[Entry]) -> str:
    rows = [
        {"date": e.day.isoformat(), "type": e.kind.value, "name": e.name}
        | ({"reference": e.reference} if e.reference else {})
        for e in entries
    ]
    return json.dumps({"entries": rows}, ensure_ascii=False)


class _FileContract(CalendarSourceContract):
    suffix = "toml"

    @pytest.fixture(autouse=True)
    def _folder(self, tmp_path: Path) -> None:
        self.folder = tmp_path
        self.count = 0

    def render(self, entries: Sequence[Entry]) -> str:
        return _toml(entries)

    def make_source(self, entries: Sequence[Entry]) -> CalendarSource:
        self.count += 1
        path = self.folder / f"calendar-{self.count}.{self.suffix}"
        path.write_text(self.render(entries), encoding="utf-8")
        return FileCalendarSource(path, delimiter=getattr(self, "delimiter", ","))


class TestTomlFile(_FileContract):
    pass


class TestCsvFile(_FileContract):
    suffix = "csv"

    def render(self, entries: Sequence[Entry]) -> str:
        return _csv(entries)


class TestCsvFileWithSemicolons(_FileContract):
    suffix = "csv"
    delimiter = ";"

    def render(self, entries: Sequence[Entry]) -> str:
        return "﻿" + _csv(entries, ";")  # as saved by spreadsheet programs


class TestJsonFile(_FileContract):
    suffix = "json"

    def render(self, entries: Sequence[Entry]) -> str:
        return _json(entries)


class TestInMemorySource(CalendarSourceContract):
    def make_source(self, entries: Sequence[Entry]) -> CalendarSource:
        return InMemoryCalendarSource(entries, version=str(hash(tuple(entries))))


@pytest.mark.parametrize(
    ("name", "content", "message"),
    [
        ("a.toml", "[[entries]]\ndate = 2026-02-30\n", "Invalid date|day is out of range"),
        ("a.toml", '[[entries]]\ndate = "2026-2-3"\ntype = "holiday"\nname = "x"\n', "AAAA-MM-DD"),
        (
            "a.toml",
            '[[entries]]\ndate = 2026-01-01T10:00:00\ntype = "holiday"\nname = "x"\n',
            "AAAA",
        ),
        ("a.toml", '[[entries]]\ndate = 2026-01-01\ntype = "feriado"\nname = "x"\n', "EntryKind"),
        ("a.toml", '[[entries]]\ndate = 2026-01-01\ntype = "holiday"\n', "missing name"),
        (
            "a.toml",
            '[[entries]]\ndate = 2026-01-01\ntype = "holiday"\nname = "x"\nobs = 1\n',
            "unknown keys obs",
        ),
        ("a.toml", "version = 2\n", "only the 'entries' list"),
        ("a.toml", '[[entries]]\ndate = 2026-01-01\ntype = "holiday"\nname = 3\n', "must be text"),
        ("a.json", '{"entries": {"date": "2026-01-01"}}', "list of tables"),
        ("a.json", "[1, 2]", "only the 'entries' list"),
        ("a.json", "{not json", "Expecting"),
        ("a.csv", "date,type\n2026-01-01,holiday\n", "CSV header"),
        ("a.csv", "date,type,name,obs\n", "CSV header"),
        ("a.csv", "date,type,name\n2026-01-01,holiday,x,extra\n", "more values than columns"),
        ("a.csv", "date,type,name\n2026-01-01,holiday\n", "missing name"),
        ("a.csv", b"date,type,name\n2026-01-01,holiday,\xff\n", "utf-8"),
    ],
)
def test_invalid_files(tmp_path: Path, name: str, content: str | bytes, message: str) -> None:
    path = tmp_path / name
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    with pytest.raises(CalendarSourceError, match=message) as caught:
        FileCalendarSource(path).load()
    assert not caught.value.retryable


def test_size_limit_and_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "big.csv"
    path.write_text(_csv([Entry(date(2026, 1, 1), EntryKind.HOLIDAY, "x")]), encoding="utf-8")
    with pytest.raises(CalendarSourceError, match="larger than 10 bytes"):
        FileCalendarSource(path, max_bytes=10).load()
    missing = FileCalendarSource(tmp_path / "missing.toml")
    with pytest.raises(CapabilityUnavailableError, match="does not exist"):
        missing.verify()
    with pytest.raises(CalendarSourceError, match="cannot read calendar file"):
        missing.load()


def test_constructor_and_configuration(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="format"):
        FileCalendarSource(tmp_path / "a.xlsx")
    with pytest.raises(ValueError, match="delimiter"):
        FileCalendarSource(tmp_path / "a.csv", delimiter="|")
    with pytest.raises(ValueError, match="max_bytes"):
        FileCalendarSource(tmp_path / "a.csv", max_bytes=0)
    source = FileCalendarSource.from_config(
        ConfigSection({"path": str(tmp_path / "x.txt"), "format": "csv", "delimiter": ";"}, "s")
    )
    assert source.path == tmp_path / "x.txt"
    assert source.describe() == f"file {(tmp_path / 'x.txt').as_posix()}"
    with pytest.raises(ConfigurationError, match="unknown key"):
        FileCalendarSource.from_config(ConfigSection({"path": "a.toml", "url": "x"}, "s"))
    with pytest.raises(ConfigurationError, match=r"s\.path"):
        FileCalendarSource.from_config(ConfigSection({"path": "a.xlsx"}, "s"))
    with pytest.raises(ConfigurationError, match="unknown key"):
        InMemoryCalendarSource.from_config(ConfigSection({"x": 1}, "s"))
