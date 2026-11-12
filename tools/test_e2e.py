"""Tests of ``tools/e2e.py``."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tools import e2e


def test_e2e_environment_hides_the_source_tree_and_local_settings() -> None:
    env = e2e.clean_environment(
        {
            "PATH": "/bin",
            "PYTHONPATH": "src",
            "pythonhome": "x",
            "VIRTUAL_ENV": "/venv",
            "ORCHESTRATOR_RUNTIME__NAME": "leak",
            "PIP_INDEX_URL": "https://example.com/simple",
        }
    )
    assert env.pop("PIP_CONFIG_FILE") == os.devnull
    assert env == {"PATH": "/bin", "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_INPUT": "1"}


def test_e2e_recomputes_the_expected_summary(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("one two\nthree\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("four", encoding="utf-8")
    (tmp_path / "ignored.md").write_text("five six", encoding="utf-8")
    assert e2e.expected_hello_summary(tmp_path) == {"files": 2, "lines": 3, "words": 4}
    e2e.expect(True, "never raised")
    with pytest.raises(e2e.CheckError, match="boom"):
        e2e.expect(False, "boom")
