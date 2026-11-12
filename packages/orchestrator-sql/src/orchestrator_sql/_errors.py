"""Errors of the SQL Capability. Providers translate driver errors into these."""

from __future__ import annotations

from orchestrator_core import ProviderError


class SqlError(ProviderError):
    """Base class of SQL errors. Messages never contain parameter values."""


class SqlConnectionError(SqlError):
    """The database cannot be reached or opened. Retryable by default."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        """Create the error; connection problems are usually transient."""
        super().__init__(message, retryable=retryable)


class SqlIntegrityError(SqlError):
    """A constraint was violated (unique, foreign key, not null, check)."""


class SqlOperationalError(SqlError):
    """The database failed to run the statement (locks, resources, I/O)."""


class SqlProgrammingError(SqlError):
    """The statement is invalid: syntax, unknown table or column, wrong parameters."""
