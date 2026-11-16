"""File-name parts and dates shared by the record sink and the log handler."""

from __future__ import annotations

import calendar
import getpass
import re
import socket
from datetime import date
from typing import Final

MISSING: Final = "_"
"""Name part used for unknown values, such as the step of a line outside steps."""

_UNSAFE: Final = re.compile(r"[^A-Za-z0-9_.-]")
_RESERVED: Final = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{number}" for number in range(1, 10)}
    | {f"LPT{number}" for number in range(1, 10)}
)


def safe_part(value: object, *, limit: int = 100) -> str:
    """Return ``value`` as a portable file-name part.

    Characters other than letters, digits, ``_``, ``.`` and ``-`` become ``_``;
    leading and trailing dots are removed, so ``..`` never reaches a path; names
    reserved by Windows get a ``_`` prefix; an empty result becomes ``_``.

    Example:
        >>> safe_part("../vendas diárias"), safe_part("aux"), safe_part("")
        ('_vendas_di_rias', '_aux', '_')
    """
    text = _UNSAFE.sub("_", str(value))[:limit].strip(".")
    if not text:
        return MISSING
    if text.split(".", 1)[0].upper() in _RESERVED:
        return f"_{text}"
    return text


def host_and_user() -> tuple[str, str]:
    """Return the host name and the user name of this process, as name parts."""
    try:
        user = getpass.getuser()
    except Exception:  # noqa: BLE001 - OSError or KeyError when no user can be determined
        user = MISSING
    return safe_part(socket.gethostname()), safe_part(user)


def add_months(day: date, months: int) -> date:
    """Return ``day`` moved by ``months`` calendar months, clamped to the month's end.

    Example:
        >>> add_months(date(2026, 8, 31), -6), add_months(date(2024, 8, 31), -6)
        (datetime.date(2026, 2, 28), datetime.date(2024, 2, 29))
    """
    index = day.year * 12 + day.month - 1 + months
    year, month = divmod(index, 12)
    month += 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))
