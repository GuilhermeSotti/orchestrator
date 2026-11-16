"""File destinations of the Orchestrator platform (RFC-0009).

- :class:`JsonLinesRecordSink`: execution records, one JSON line per execution,
  a file per day and per process (section 2.2).
- :class:`TextLogHandler`: technical logs in text files organized by stage,
  step and date, with retention (answer 1).

Both use only the standard library and never share a file between processes
by default, so several processes can write to the same folder at once.
"""

from orchestrator_records_file._logs import DEFAULT_LOG_PATH, PLACEHOLDERS, TextLogHandler
from orchestrator_records_file._records import JsonLinesRecordSink
from orchestrator_records_file._version import __version__

__all__ = [
    "DEFAULT_LOG_PATH",
    "PLACEHOLDERS",
    "JsonLinesRecordSink",
    "TextLogHandler",
    "__version__",
]
