"""Check that relative links in Markdown files point to existing files.

Usage::

    python tools/check_docs.py            # check the repository
    python tools/check_docs.py docs/      # check one folder

External links (``http``, ``https``, ``mailto``) and pure anchors are skipped.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIPPED_DIRS = frozenset(
    {".git", ".venv", "venv", "node_modules", "dist", "build", ".pytest_cache"}
)
_LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_FENCE = re.compile(r"^(```|~~~)")


def markdown_files(base: Path) -> Iterator[Path]:
    """Yield the Markdown files under ``base``, skipping tool and build folders."""
    if base.is_file():
        yield base
        return
    for path in sorted(base.rglob("*.md")):
        if not SKIPPED_DIRS.intersection(path.relative_to(base).parts):
            yield path


def links(text: str) -> Iterator[tuple[int, str]]:
    """Yield ``(line number, target)`` of Markdown links outside code blocks."""
    fenced = False
    for number, line in enumerate(text.splitlines(), start=1):
        if _FENCE.match(line.strip()):
            fenced = not fenced
            continue
        if fenced:
            continue
        for match in _LINK.finditer(re.sub(r"`[^`]*`", "", line)):
            yield number, match.group(1)


def broken_links(base: Path) -> list[str]:
    """Return ``file:line: target`` for every relative link whose target is missing."""
    problems = []
    for path in markdown_files(base):
        for number, target in links(path.read_text(encoding="utf-8")):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
                continue
            relative = target.split("#", 1)[0]
            if relative and not (path.parent / relative).exists():
                shown = path.relative_to(base.parent if base.is_file() else base)
                problems.append(f"{shown}:{number}: {target}")
    return problems


def main(argv: Sequence[str] | None = None) -> int:
    """Check the given folders (default: the repository); return 1 on broken links."""
    arguments = argv if argv is not None else sys.argv[1:]
    targets = [Path(argument).resolve() for argument in arguments] or [ROOT]
    problems = [problem for target in targets for problem in broken_links(target)]
    for problem in problems:
        sys.stderr.write(f"broken link: {problem}\n")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
