from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _restore_root_logging() -> Iterator[None]:
    """The command line installs a root handler; remove it after each test."""
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    yield
    for handler in list(root.handlers):
        if handler not in handlers:
            root.removeHandler(handler)
            handler.close()
    root.setLevel(level)
