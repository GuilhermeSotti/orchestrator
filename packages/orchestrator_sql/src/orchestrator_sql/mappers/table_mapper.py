from __future__ import annotations

from typing import Any


def _quote_identifier(name: str, dialect: str) -> str:
    if dialect == "mssql":
        return f"[{name}]"
    return f'"{name}"'


def _build_column_definition(column: dict[str, Any], dialect: str) -> str:
    name = _quote_identifier(column["name"], dialect)
    column_type = column.get("type", "TEXT")
    parts = [name, column_type]

    identity = column.get("identity", False)
    primary_key = column.get("primary_key", False)

    if identity and dialect == "sqlite" and primary_key:
        return f"{name} INTEGER PRIMARY KEY AUTOINCREMENT"

    if identity and dialect == "mssql":
        parts.append("IDENTITY(1,1)")

    if not column.get("nullable", True):
        parts.append("NOT NULL")

    if "default" in column and column["default"] is not None:
        parts.append(f"DEFAULT {column['default']}")

    if primary_key and not (identity and dialect == "sqlite"):
        parts.append("PRIMARY KEY")

    if column.get("unique", False):
        parts.append("UNIQUE")

    return " ".join(parts)


def _build_constraint(constraint: dict[str, Any], dialect: str) -> str | None:
    constraint_type = constraint.get("type")
    name = constraint.get("name")
    if not name or not constraint_type:
        return None

    if constraint_type == "check":
        expression = constraint.get("expression")
        if expression:
            return f"CONSTRAINT {_quote_identifier(name, dialect)} CHECK ({expression})"
        return None

    if constraint_type == "foreign_key":
        columns = constraint.get("columns", [])
        referenced_table = constraint.get("referenced_table")
        referenced_columns = constraint.get("referenced_columns", [])
        if columns and referenced_table and referenced_columns:
            cols = ", ".join(_quote_identifier(column, dialect) for column in columns)
            ref_cols = ", ".join(_quote_identifier(column, dialect) for column in referenced_columns)
            if dialect == "sqlite" and "." in referenced_table:
                referenced_table = f'"{referenced_table}"'
            return (
                f"CONSTRAINT {_quote_identifier(name, dialect)} FOREIGN KEY ({cols}) "
                f"REFERENCES {referenced_table} ({ref_cols})"
            )
    return None


def map_table_spec_to_ddl(schema_name: str, table_spec: dict[str, Any], dialect: str = "mssql") -> str:
    table_name = table_spec["name"]
    qualified_name = f"{_quote_identifier(schema_name, dialect)}.{_quote_identifier(table_name, dialect)}" if schema_name else _quote_identifier(table_name, dialect)
    columns = [_build_column_definition(column, dialect) for column in table_spec.get("columns", [])]

    constraints: list[str] = []
    if table_spec.get("primary_key"):
        primary_key = table_spec["primary_key"]
        if isinstance(primary_key, list):
            cols = ", ".join(_quote_identifier(column, dialect) for column in primary_key)
            constraints.append(f"CONSTRAINT {_quote_identifier('PK_' + table_name, dialect)} PRIMARY KEY ({cols})")

    for constraint in table_spec.get("constraints", []):
        constraint_text = _build_constraint(constraint, dialect)
        if constraint_text:
            constraints.append(constraint_text)

    body = ",\n    ".join(columns + constraints)
    return f"CREATE TABLE {qualified_name} (\n    {body}\n)"


def create_default_queue_table_spec(schema_name: str, data_table_name: str, data_id_column: str) -> dict[str, Any]:
    queue_name = f"Fila{data_table_name}"
    queue_id_name = f"IdFila{data_table_name}"
    data_table_reference = f"{schema_name}.{data_table_name}"

    return {
        "name": queue_name,
        "columns": [
            {"name": queue_id_name, "type": "BIGINT", "identity": True, "nullable": False, "primary_key": True},
            {"name": "FluxoExecucaoId", "type": "INT", "nullable": False},
            {"name": "DadosId", "type": "INT", "nullable": False},
            {"name": "HoraInsercao", "type": "DATETIME2(3)", "nullable": False, "default": "SYSUTCDATETIME()"},
            {"name": "HoraInicio", "type": "DATETIME2(3)", "nullable": True},
            {"name": "HoraFim", "type": "DATETIME2(3)", "nullable": True},
            {"name": "Status", "type": "VARCHAR(30)", "nullable": False, "default": "'Pendente'"},
            {"name": "Tentativa", "type": "SMALLINT", "nullable": False, "default": "0"},
            {"name": "Usuario", "type": "VARCHAR(100)", "nullable": False},
            {"name": "Maquina", "type": "VARCHAR(100)", "nullable": False},
            {"name": "Ambiente", "type": "CHAR(1)", "nullable": False},
            {"name": "Observacao", "type": "VARCHAR(1000)", "nullable": True},
            {"name": "CreatedAt", "type": "DATETIME2(3)", "nullable": False, "default": "SYSUTCDATETIME()"},
            {"name": "UpdatedAt", "type": "DATETIME2(3)", "nullable": True},
            {"name": "IsActive", "type": "BIT", "nullable": False, "default": "1"},
        ],
        "constraints": [
            {
                "type": "foreign_key",
                "name": "FK_Fila_FluxoExecucao",
                "columns": ["FluxoExecucaoId"],
                "referenced_table": "CORE.FluxosExecucao",
                "referenced_columns": ["Id"],
            },
            {
                "type": "foreign_key",
                "name": "FK_Fila_Dados",
                "columns": ["DadosId"],
                "referenced_table": data_table_reference,
                "referenced_columns": [data_id_column],
            },
            {
                "type": "check",
                "name": "CK_Fila_Ambiente",
                "expression": "Ambiente IN ('D','H','P')",
            },
            {
                "type": "check",
                "name": "CK_Fila_Status",
                "expression": "Status IN ('Pendente','EmExecucao','Concluido','Erro','Cancelado')",
            },
            {
                "type": "check",
                "name": "CK_Fila_Tentativa",
                "expression": "Tentativa >= 0",
            },
        ],
        "indexes": [
            {"name": "IX_Fila_FluxoExecucaoId", "columns": ["FluxoExecucaoId"]},
            {"name": "IX_Fila_DadosId", "columns": ["DadosId"]},
            {"name": "IX_Fila_Status", "columns": ["Status"]},
            {"name": "IX_Fila_HoraInsercao", "columns": ["HoraInsercao"]},
            {"name": "IX_Fila_Pendente", "columns": ["Status", "Tentativa", "HoraInsercao"]},
        ],
    }


class TableMapper:
    @staticmethod
    def map_table_spec_to_ddl(schema_name: str, table_spec: dict[str, Any], dialect: str = "mssql") -> str:
        return map_table_spec_to_ddl(schema_name, table_spec, dialect)
