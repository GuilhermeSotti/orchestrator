"""Validation of identifiers used to build SQL dynamically.

Values always travel as parameters. Table and column names cannot be
parameters, so every name used by the helpers of :class:`SqlSession` is
validated against a portable pattern and then quoted by the Provider.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from orchestrator_sql._errors import SqlProgrammingError

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")


def validate_identifier(name: str) -> str:
    """Return ``name`` if it is a portable identifier.

    A portable identifier starts with a letter or ``_``, has only letters,
    digits and ``_``, and at most 63 characters.

    Raises:
        SqlProgrammingError: If ``name`` is not a portable identifier.
    """
    candidate: object = name
    if not isinstance(candidate, str) or not _IDENTIFIER_RE.match(candidate):
        msg = (
            f"invalid SQL identifier {name!r}: use letters, digits and '_', "
            "starting with a letter or '_' (at most 63 characters)"
        )
        raise SqlProgrammingError(msg)
    return name


@dataclass(frozen=True, slots=True)
class TableName:
    """Validated table name, optionally qualified by a schema.

    Example:
        >>> TableName.parse("sales.orders")
        TableName(name='orders', schema='sales')
    """

    name: str
    schema: str | None = None

    def __post_init__(self) -> None:
        """Validate both parts."""
        validate_identifier(self.name)
        if self.schema is not None:
            validate_identifier(self.schema)

    @classmethod
    def parse(cls, text: str | TableName) -> TableName:
        """Parse ``table`` or ``schema.table``.

        Raises:
            SqlProgrammingError: If a part is not a portable identifier.
        """
        if isinstance(text, TableName):
            return text
        parts = text.split(".")
        if len(parts) == 1:
            return cls(parts[0])
        if len(parts) == 2:  # noqa: PLR2004 - schema and table
            return cls(parts[1], parts[0])
        msg = f"invalid table name {text!r}: use 'table' or 'schema.table'"
        raise SqlProgrammingError(msg)

    def __str__(self) -> str:
        """Return ``schema.table`` or ``table`` (unquoted)."""
        return self.name if self.schema is None else f"{self.schema}.{self.name}"
