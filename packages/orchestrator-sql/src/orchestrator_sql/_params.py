"""Portable named parameters (``:name``) translated to each DB-API paramstyle.

Consumers always write ``:name`` placeholders. Providers declare their driver's
DB-API ``paramstyle`` and this module rewrites the statement accordingly.
Placeholders inside string literals, quoted identifiers and comments are
ignored, and so are ``::`` casts.
"""

from __future__ import annotations

import functools
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from orchestrator_sql._errors import SqlProgrammingError

PARAMSTYLES: Final = frozenset({"named", "qmark", "numeric", "format", "pyformat"})
_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass(frozen=True, slots=True)
class _Parsed:
    pieces: tuple[str, ...]  # literal SQL; one more piece than placeholders
    names: tuple[str, ...]  # placeholder names, in order of appearance


@functools.lru_cache(maxsize=512)
def _parse(sql: str) -> _Parsed:
    pieces: list[str] = []
    names: list[str] = []
    current: list[str] = []
    i, size = 0, len(sql)
    while i < size:
        char = sql[i]
        if char in {"'", '"'}:
            end = i + 1
            while end < size:
                if sql[end] == char:
                    if end + 1 < size and sql[end + 1] == char:
                        end += 2
                        continue
                    break
                end += 1
            current.append(sql[i : end + 1])
            i = end + 1
        elif sql.startswith("--", i):
            end = sql.find("\n", i)
            end = size if end == -1 else end
            current.append(sql[i:end])
            i = end
        elif sql.startswith("/*", i):
            end = sql.find("*/", i + 2)
            end = size if end == -1 else end + 2
            current.append(sql[i:end])
            i = end
        elif sql.startswith("::", i):
            current.append("::")
            i += 2
        elif char == ":" and (match := _NAME_RE.match(sql, i + 1)):
            pieces.append("".join(current))
            current = []
            names.append(match.group())
            i = match.end()
        else:
            current.append(char)
            i += 1
    pieces.append("".join(current))
    return _Parsed(tuple(pieces), tuple(names))


def placeholder_names(sql: str) -> tuple[str, ...]:
    """Return the ``:name`` placeholders of ``sql``, in order of appearance.

    Example:
        >>> placeholder_names("SELECT ':x', a::int FROM t WHERE id = :id -- :ignored")
        ('id',)
    """
    return _parse(sql).names


def translate(
    sql: str, params: Mapping[str, object] | None, paramstyle: str
) -> tuple[str, Mapping[str, object] | tuple[object, ...]]:
    """Rewrite ``sql`` and ``params`` for a DB-API ``paramstyle``.

    Every placeholder must have a value and every value must be used.

    Example:
        >>> translate("SELECT * FROM t WHERE a = :a AND b = :b", {"a": 1, "b": 2}, "qmark")
        ('SELECT * FROM t WHERE a = ? AND b = ?', (1, 2))

    Raises:
        SqlProgrammingError: If parameters are missing or unused, or the
            paramstyle is unknown. Messages name parameters, never values.
    """
    if paramstyle not in PARAMSTYLES:
        msg = f"unsupported DB-API paramstyle {paramstyle!r}"
        raise SqlProgrammingError(msg)
    values = dict(params or {})
    parsed = _parse(sql)
    missing = sorted(set(parsed.names) - set(values))
    unused = sorted(set(values) - set(parsed.names))
    if missing:
        msg = f"missing SQL parameter(s): {', '.join(missing)}"
        raise SqlProgrammingError(msg)
    if unused:
        msg = f"unused SQL parameter(s): {', '.join(unused)}"
        raise SqlProgrammingError(msg)
    if paramstyle == "named":
        return sql, values
    escape = paramstyle in {"format", "pyformat"}
    pieces = (
        [piece.replace("%", "%%") for piece in parsed.pieces] if escape else list(parsed.pieces)
    )
    if paramstyle == "pyformat":
        markers = [f"%({name})s" for name in parsed.names]
        return _join(pieces, markers), values
    if paramstyle == "numeric":
        order = list(dict.fromkeys(parsed.names))
        markers = [f":{order.index(name) + 1}" for name in parsed.names]
        return _join(pieces, markers), tuple(values[name] for name in order)
    marker = "?" if paramstyle == "qmark" else "%s"
    return _join(pieces, [marker] * len(parsed.names)), tuple(values[n] for n in parsed.names)


def _join(pieces: list[str], markers: list[str]) -> str:
    parts = [pieces[0]]
    for marker, piece in zip(markers, pieces[1:], strict=True):
        parts.extend((marker, piece))
    return "".join(parts)
