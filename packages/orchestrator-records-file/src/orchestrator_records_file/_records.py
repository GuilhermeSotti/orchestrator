"""Execution records in JSON Lines files (RFC-0009, section 2.2)."""

from __future__ import annotations

import json
import os
import re
import threading
from datetime import UTC, date, timedelta
from pathlib import Path
from typing import Final

from orchestrator_core import ExecutionRecord
from orchestrator_records_file._paths import host_and_user

__all__ = ["JsonLinesRecordSink"]

_PREFIX: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


class JsonLinesRecordSink:
    """Appends one JSON line per execution to a daily file. Thread-safe.

    Implements the Core port :class:`~orchestrator_core.ExecutionRecordSink`.
    Each line is ``record.to_dict()``, already masked by the Runtime, in UTF-8;
    the record carries neither the parameters nor the return value of the
    automation. The file of a day (UTC, from ``finished_at``) is
    ``<prefix>-AAAA-MM-DD-<host>-<pid>.jsonl``: one file per process, so several
    processes can write to the same folder at once. With ``per_process=False``
    the name is ``<prefix>-AAAA-MM-DD.jsonl`` and only one process may write
    with that prefix.

    A write error raises, and the Runtime only logs a warning and counts it in
    ``orchestrator.record_sink.errors``: the status of the execution never
    changes (RFC-0009, answer 6).

    Example:
        >>> import tempfile
        >>> from orchestrator_core import RuntimeBuilder
        >>> folder = tempfile.mkdtemp()
        >>> sink = JsonLinesRecordSink(folder, prefix="vendas")
        >>> runtime = RuntimeBuilder().with_environment({}, prefix=None)
        >>> result = runtime.with_record_sink(sink).build().run(lambda ctx: None)
        >>> line = sink.path_for(result.record.finished_at.date()).read_text("utf-8")
        >>> json.loads(line)["execution_id"] == result.execution_id
        True
        >>> import shutil
        >>> shutil.rmtree(folder)
    """

    def __init__(
        self,
        folder: str | os.PathLike[str],
        *,
        prefix: str = "records",
        per_process: bool = True,
        retention_days: int | None = None,
        fsync: bool = False,
    ) -> None:
        """Create the sink.

        Args:
            folder: Existing folder that receives the files.
            prefix: Start of the file names: letters, digits, ``_``, ``.`` and ``-``.
            per_process: Add the host name and the process id to the file names.
            retention_days: Remove this sink's files of days before
                ``today - retention_days`` when the first record of a day is
                written (default: never remove).
            fsync: Call :func:`os.fsync` after each record.

        Raises:
            ValueError: ``folder`` is not an existing folder, or an argument is
                invalid.
        """
        directory = Path(folder).absolute()
        if not directory.is_dir():
            msg = f"record folder {directory} does not exist or is not a folder"
            raise ValueError(msg)
        if not _PREFIX.match(prefix):
            msg = "prefix must have 1 to 64 letters, digits, '_', '.' or '-', starting alnum"
            raise ValueError(msg)
        if retention_days is not None and retention_days < 1:
            msg = "retention_days must be at least 1"
            raise ValueError(msg)
        self._folder = directory
        self._prefix = prefix
        self._per_process = per_process
        self._retention = retention_days
        self._fsync = fsync
        self._host = host_and_user()[0]
        self._lock = threading.Lock()
        self._day: date | None = None
        self._pattern = re.compile(
            rf"{re.escape(prefix)}-(\d{{4}})-(\d{{2}})-(\d{{2}})(?:-[A-Za-z0-9_.-]+-\d+)?\.jsonl"
        )

    @property
    def folder(self) -> Path:
        """Folder that receives the files."""
        return self._folder

    def path_for(self, day: date) -> Path:
        """Return the file of this process for the records finished on ``day``."""
        name = f"{self._prefix}-{day:%Y-%m-%d}"
        if self._per_process:
            name = f"{name}-{self._host}-{os.getpid()}"
        return self._folder / f"{name}.jsonl"

    def write(self, record: ExecutionRecord) -> None:
        """Append ``record`` as one JSON line.

        Raises:
            OSError: The file could not be written.
            ValueError: The record has a value JSON cannot represent.
        """
        line = json.dumps(
            record.to_dict(), ensure_ascii=False, separators=(",", ":"), allow_nan=False
        )
        data = f"{line}\n".encode()
        day = record.finished_at.astimezone(UTC).date()
        with self._lock:
            if self._retention is not None and day != self._day:
                self._purge(day)
            self._day = day
            with self.path_for(day).open("ab") as stream:
                stream.write(data)
                stream.flush()
                if self._fsync:
                    os.fsync(stream.fileno())

    def purge(self, today: date) -> int:
        """Remove this sink's files of days before ``today - retention_days``.

        Only regular files directly in the folder whose names follow this sink's
        pattern are removed, whatever process wrote them. Files that cannot be
        removed (in use, no permission) are left for the next purge.

        Returns:
            Number of files removed.

        Raises:
            ValueError: The sink has no retention.
        """
        if self._retention is None:
            msg = "retention is disabled for this sink"
            raise ValueError(msg)
        with self._lock:
            return self._purge(today)

    def _purge(self, today: date) -> int:
        assert self._retention is not None  # noqa: S101 - checked by the callers
        cutoff = today - timedelta(days=self._retention)
        removed = 0
        with os.scandir(self._folder) as entries:
            for entry in entries:
                match = self._pattern.fullmatch(entry.name)
                if match is None or not entry.is_file(follow_symlinks=False):
                    continue
                try:
                    day = date(int(match[1]), int(match[2]), int(match[3]))
                except ValueError:
                    continue
                if day < cutoff:
                    try:
                        Path(entry.path).unlink()
                    except OSError:
                        continue
                    removed += 1
        return removed
