"""Technical logs in text files, in a folder tree with retention (RFC-0009, answer 1)."""

from __future__ import annotations

import logging
import os
import re
import string
import time
from collections import OrderedDict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Final, TextIO

from orchestrator_core.logs import TEXT_FORMAT, ExecutionContextFilter, RedactingFilter
from orchestrator_records_file._paths import MISSING, add_months, host_and_user, safe_part

__all__ = ["DEFAULT_LOG_PATH", "PLACEHOLDERS", "TextLogHandler"]

DEFAULT_LOG_PATH: Final = "{stage}/{step}/{year}/{month}/{day}/{hostname}_{user}_{pid}.txt"
"""Default file path, relative to the root folder: stage, step, date, host, user, process."""

PLACEHOLDERS: Final = frozenset(
    {
        "automation",
        "execution_id",
        "stage",
        "step",
        "year",
        "month",
        "day",
        "hostname",
        "user",
        "pid",
    }
)
"""Placeholders accepted in the path template."""

_CONTEXT: Final = ("automation", "execution_id", "stage", "step")
_DATE: Final = ("year", "month", "day")
_LITERAL: Final = re.compile(r"[A-Za-z0-9_.-]*")
_VALUE: Final = {"year": r"\d{4}", "month": r"\d{2}", "day": r"\d{2}", "pid": r"\d+"}
_ANY: Final = r"[A-Za-z0-9_.-]+"

type _Segment = tuple[tuple[str, str | None], ...]


def _parse(template: str) -> tuple[_Segment, ...]:
    if not template or template.startswith("/") or "\\" in template or ":" in template:
        msg = "path must be a relative template with '/' between folders"
        raise ValueError(msg)
    segments: list[_Segment] = []
    for text in template.split("/"):
        try:
            parsed = list(string.Formatter().parse(text))
        except ValueError as exc:
            msg = f"invalid path template: {exc}"
            raise ValueError(msg) from None
        parts: list[tuple[str, str | None]] = []
        for literal, field, spec, conversion in parsed:
            if not _LITERAL.fullmatch(literal):
                msg = "path literals may only have letters, digits, '_', '.' and '-'"
                raise ValueError(msg)
            if field is not None and (field not in PLACEHOLDERS or spec or conversion):
                msg = f"unknown placeholder {{{field}}}; use {', '.join(sorted(PLACEHOLDERS))}"
                raise ValueError(msg)
            parts.append((literal, field))
        if not any(field for _, field in parts) and text.strip(".") == "":
            msg = "path folders cannot be empty, '.' or '..'"
            raise ValueError(msg)
        if parts[-1][1] is None and parts[-1][0].endswith("."):
            msg = "path folders and names cannot end with '.'"
            raise ValueError(msg)
        segments.append(tuple(parts))
    return tuple(segments)


def _patterns(segments: tuple[_Segment, ...]) -> tuple[re.Pattern[str], ...]:
    """Return one pattern per depth: the first ``n`` segments, joined by ``/``."""
    seen: set[str] = set()
    pieces: list[str] = []
    patterns: list[re.Pattern[str]] = []
    for segment in segments:
        piece: list[str] = []
        for literal, field in segment:
            piece.append(re.escape(literal))
            if field is None:
                continue
            if field in seen:
                piece.append(f"(?P={field})")
            else:
                seen.add(field)
                piece.append(f"(?P<{field}>{_VALUE.get(field, _ANY)})")
        pieces.append("".join(piece))
        patterns.append(re.compile("/".join(pieces)))
    return tuple(patterns)


class TextLogHandler(logging.Handler):
    """Writes log records to text files under a root folder, one file per process.

    The path of each line comes from a template relative to ``root``; the
    default, :data:`DEFAULT_LOG_PATH`, follows answer 1 of RFC-0009: stage,
    step, year, month, day and ``<host>_<user>_<pid>.txt``. Lines outside a step
    (or outside an execution) use ``_`` for the missing value. Values are
    reduced to letters, digits, ``_``, ``.`` and ``-``, so a path never leaves
    ``root``. With the process id in the name, several processes can write to
    the same folder at once without sharing a file.

    The handler adds :class:`~orchestrator_core.logs.ExecutionContextFilter` and
    :class:`~orchestrator_core.logs.RedactingFilter`, so lines carry the
    correlation fields and resolved secrets are masked. Lines use
    :data:`~orchestrator_core.logs.TEXT_FORMAT`, with UTC times ending in ``Z``
    (or local times, with ``utc=False``, which also changes the date folders).

    Retention: on the first line of each day, files that follow the template
    and belong to days before ``today - retention_months`` are removed, then
    their folders if empty. Files that do not follow the template are never
    touched. Writing errors go to :meth:`logging.Handler.handleError` and never
    reach the automation.

    Example:
        >>> import tempfile
        >>> root = tempfile.mkdtemp()
        >>> handler = TextLogHandler(root)
        >>> logger = logging.getLogger("doctest.text_logs")
        >>> logger.addHandler(handler)
        >>> logger.warning("outside any execution")
        >>> [path.relative_to(root).parts[:2] for path in Path(root).rglob("*.txt")]
        [('_', '_')]
        >>> logger.removeHandler(handler)
        >>> handler.close()
        >>> import shutil
        >>> shutil.rmtree(root)
    """

    def __init__(
        self,
        root: str | os.PathLike[str],
        *,
        path: str = DEFAULT_LOG_PATH,
        retention_months: int | None = 6,
        utc: bool = True,
        level: int | str = logging.NOTSET,
        encoding: str = "utf-8",
        max_open_files: int = 8,
    ) -> None:
        """Create the handler.

        Args:
            root: Existing folder under which the files are created.
            path: Template of the file path relative to ``root``, with ``/``
                between folders and the placeholders in :data:`PLACEHOLDERS`.
            retention_months: Months of files kept; ``None`` disables the
                removal (default: 6, answer 1 of RFC-0009).
            utc: Use UTC for the date folders and the line times; ``False``
                uses the local time of the machine.
            level: Minimum level of the records written.
            encoding: Encoding of the files.
            max_open_files: Files kept open at the same time in this process.

        Raises:
            ValueError: ``root`` is not an existing folder, the template is
                invalid, or retention is enabled without ``{year}``, ``{month}``
                and ``{day}`` in the template.
        """
        super().__init__(level)
        folder = Path(root).absolute()
        if not folder.is_dir():
            msg = f"log folder {folder} does not exist or is not a folder"
            raise ValueError(msg)
        if retention_months is not None and retention_months < 1:
            msg = "retention_months must be at least 1"
            raise ValueError(msg)
        if max_open_files < 1:
            msg = "max_open_files must be at least 1"
            raise ValueError(msg)
        segments = _parse(path)
        fields = {field for segment in segments for _, field in segment if field}
        if retention_months is not None and not set(_DATE) <= fields:
            msg = "retention needs {year}, {month} and {day} in the path"
            raise ValueError(msg)
        self._root = folder
        self._segments = segments
        self._patterns = _patterns(segments)
        self._retention = retention_months
        self._utc = utc
        self._encoding = encoding
        self._max_open = max_open_files
        self._streams: OrderedDict[Path, TextIO] = OrderedDict()
        self._day: date | None = None
        self._pid = os.getpid()
        self._host, self._user = host_and_user()
        formatter = logging.Formatter(TEXT_FORMAT)
        if utc:
            formatter.converter = time.gmtime
            formatter.default_msec_format = "%s.%03dZ"
        self.setFormatter(formatter)
        self.addFilter(ExecutionContextFilter())
        self.addFilter(RedactingFilter())

    @property
    def root(self) -> Path:
        """Folder under which the files are created."""
        return self._root

    def path_for(self, record: logging.LogRecord) -> Path:
        """Return the file that receives ``record`` (after the handler's filters ran)."""
        values = {name: self._context_value(getattr(record, name, None)) for name in _CONTEXT}
        moment = self._moment(record)
        values |= {
            "year": f"{moment.year:04d}",
            "month": f"{moment.month:02d}",
            "day": f"{moment.day:02d}",
            "hostname": self._host,
            "user": self._user,
            "pid": str(os.getpid()),
        }
        parts = [
            "".join(literal + (values[field] if field else "") for literal, field in segment)
            for segment in self._segments
        ]
        return self._root.joinpath(*parts)

    def emit(self, record: logging.LogRecord) -> None:
        """Write ``record`` to its file; errors go to :meth:`handleError`."""
        try:
            if os.getpid() != self._pid:  # files inherited by a forked process
                self._close_streams()
                self._pid = os.getpid()
            day = self._moment(record).date()
            if day != self._day:
                self._close_streams()
                self._day = day
                if self._retention is not None:
                    self._purge(day)
            text = self.format(record)
            stream = self._stream(self.path_for(record))
            stream.write(f"{text}\n")
            stream.flush()
        except RecursionError:
            raise
        except Exception:  # noqa: BLE001 - logging must never break the automation
            self.handleError(record)

    def flush(self) -> None:
        """Flush the open files."""
        self.acquire()
        try:
            for stream in self._streams.values():
                try:
                    stream.flush()
                except OSError:
                    continue
        finally:
            self.release()

    def close(self) -> None:
        """Close the open files and the handler."""
        self.acquire()
        try:
            self._close_streams()
        finally:
            self.release()
        super().close()

    def purge(self, today: date | None = None) -> int:
        """Remove files of days before ``today - retention_months``.

        Args:
            today: Reference day (default: today, in the handler's time base).

        Returns:
            Number of files removed.

        Raises:
            ValueError: The handler has no retention.
        """
        if self._retention is None:
            msg = "retention is disabled for this handler"
            raise ValueError(msg)
        if today is None:
            now = datetime.now(UTC)
            today = (now if self._utc else now.astimezone()).date()
        self.acquire()
        try:
            return self._purge(today)
        finally:
            self.release()

    def _moment(self, record: logging.LogRecord) -> datetime:
        moment = datetime.fromtimestamp(record.created, UTC)
        return moment if self._utc else moment.astimezone()

    @staticmethod
    def _context_value(value: object) -> str:
        if value is None or value in {"", "-"}:
            return MISSING
        return safe_part(value)

    def _stream(self, target: Path) -> TextIO:
        stream = self._streams.get(target)
        if stream is not None:
            self._streams.move_to_end(target)
            return stream
        target.parent.mkdir(parents=True, exist_ok=True)
        stream = target.open("a", encoding=self._encoding)
        self._streams[target] = stream
        while len(self._streams) > self._max_open:
            _, oldest = self._streams.popitem(last=False)
            try:
                oldest.close()
            except OSError:
                continue
        return stream

    def _close_streams(self) -> None:
        while self._streams:
            _, stream = self._streams.popitem()
            try:
                stream.close()
            except OSError:
                continue

    def _purge(self, today: date) -> int:
        assert self._retention is not None  # noqa: S101 - checked by the callers
        cutoff = add_months(today, -self._retention)
        last = len(self._segments) - 1
        removed: list[Path] = []
        for current, folders, files in os.walk(self._root):
            parts = Path(current).relative_to(self._root).parts
            if len(parts) < last:
                folders[:] = [
                    name for name in folders if self._may_hold_expired((*parts, name), cutoff)
                ]
                continue
            folders[:] = []
            for name in files:
                path = Path(current, name)
                match = self._patterns[last].fullmatch("/".join((*parts, name)))
                if match is None or path.is_symlink() or not path.is_file():
                    continue
                day = _day(match)
                if day is None or day >= cutoff:
                    continue
                try:
                    path.unlink()
                except OSError:
                    continue
                removed.append(path)
        self._remove_empty_folders(removed)
        return len(removed)

    def _may_hold_expired(self, parts: tuple[str, ...], cutoff: date) -> bool:
        match = self._patterns[len(parts) - 1].fullmatch("/".join(parts))
        if match is None:
            return False
        known = {name: int(value) for name, value in match.groupdict().items() if name in _DATE}
        year, month, day = (known.get(name) for name in _DATE)
        if year is None:
            return True
        if year != cutoff.year:
            return year < cutoff.year
        if month is None:
            return True
        if month != cutoff.month:
            return month < cutoff.month
        return day is None or day < cutoff.day

    def _remove_empty_folders(self, removed: list[Path]) -> None:
        folders = {path.parent for path in removed}
        for folder in sorted(folders, key=lambda item: len(item.parts), reverse=True):
            current = folder
            while current != self._root and current.is_relative_to(self._root):
                try:
                    current.rmdir()
                except OSError:
                    break
                current = current.parent


def _day(match: re.Match[str]) -> date | None:
    try:
        return date(int(match["year"]), int(match["month"]), int(match["day"]))
    except (IndexError, ValueError):
        return None
