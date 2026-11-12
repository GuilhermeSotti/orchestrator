"""Tests of ``tools/check_docs.py``."""

from __future__ import annotations

from pathlib import Path

from tools import check_docs


def test_documentation_links_of_the_repository_are_valid() -> None:
    assert check_docs.broken_links(check_docs.ROOT) == []


def test_link_checker_reports_missing_targets(tmp_path: Path) -> None:
    (tmp_path / "exists.md").write_text("ok", encoding="utf-8")
    (tmp_path / "doc.md").write_text(
        "\n".join(
            [
                "[ok](exists.md) [anchor](exists.md#part) [web](https://example.com) [self](#top)",
                "[missing](missing.md) `[code](ignored.md)`",
                "```",
                "[fenced](also-ignored.md)",
                "```",
            ]
        ),
        encoding="utf-8",
    )
    assert check_docs.broken_links(tmp_path) == ["doc.md:2: missing.md"]
    assert check_docs.main([str(tmp_path)]) == 1
    assert check_docs.main([str(tmp_path / "exists.md")]) == 0
