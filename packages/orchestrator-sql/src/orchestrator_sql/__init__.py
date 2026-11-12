"""SQL Capability of the Orchestrator platform.

The Capability offers parameterized SQL (portable ``:name`` placeholders),
transactions, validated identifiers and simple DDL. Database engines are
supported by Providers, such as ``orchestrator-sqlite``, that implement
:class:`SqlProvider`. The public submodule :mod:`orchestrator_sql.testing`
holds the conformance suite that every Provider must pass.
"""

from orchestrator_sql._capability import SqlCapability
from orchestrator_sql._errors import (
    SqlConnectionError,
    SqlError,
    SqlIntegrityError,
    SqlOperationalError,
    SqlProgrammingError,
)
from orchestrator_sql._identifiers import TableName, validate_identifier
from orchestrator_sql._params import PARAMSTYLES, placeholder_names, translate
from orchestrator_sql._provider import DbapiConnection, DbapiCursor, SqlProvider
from orchestrator_sql._schema import Column, SqlType, Table
from orchestrator_sql._session import Row, SqlSession
from orchestrator_sql._version import __version__

__all__ = [
    "PARAMSTYLES",
    "Column",
    "DbapiConnection",
    "DbapiCursor",
    "Row",
    "SqlCapability",
    "SqlConnectionError",
    "SqlError",
    "SqlIntegrityError",
    "SqlOperationalError",
    "SqlProgrammingError",
    "SqlProvider",
    "SqlSession",
    "SqlType",
    "Table",
    "TableName",
    "__version__",
    "placeholder_names",
    "translate",
    "validate_identifier",
]
