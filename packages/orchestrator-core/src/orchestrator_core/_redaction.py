"""Masking of sensitive values in text (logs, events, records)."""

from __future__ import annotations

import re
import threading

MASK = "***"
"""Replacement for sensitive values."""

MIN_SECRET_LENGTH = 4
"""Values shorter than this are not masked, to avoid garbling unrelated text."""


class Redactor:
    """Thread-safe registry of sensitive values that must never appear in text.

    Secret values resolved by the Runtime are registered automatically and
    remain registered for the lifetime of the process.
    """

    def __init__(self) -> None:
        """Create an empty registry."""
        self._lock = threading.Lock()
        self._values: set[str] = set()
        self._pattern: re.Pattern[str] | None = None

    def register(self, value: str) -> None:
        """Register a sensitive value. Values shorter than 4 characters are ignored."""
        if len(value) < MIN_SECRET_LENGTH:
            return
        with self._lock:
            if value not in self._values:
                self._values.add(value)
                self._pattern = None

    def redact(self, text: str) -> str:
        """Return ``text`` with every registered value replaced by ``***``."""
        pattern = self._compiled()
        if pattern is None or not text:
            return text
        return pattern.sub(MASK, text)

    def clear(self) -> None:
        """Forget every registered value (intended for tests)."""
        with self._lock:
            self._values.clear()
            self._pattern = None

    def __len__(self) -> int:
        """Return how many values are registered."""
        return len(self._values)

    def _compiled(self) -> re.Pattern[str] | None:
        with self._lock:
            if self._pattern is None and self._values:
                ordered = sorted(self._values, key=len, reverse=True)
                self._pattern = re.compile("|".join(re.escape(value) for value in ordered))
            return self._pattern


default_redactor = Redactor()
"""Process-wide registry used by the Runtime and by the logging filters."""
