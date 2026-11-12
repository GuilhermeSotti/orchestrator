from __future__ import annotations

from typing import Any

from .sql_provider import SQLProvider
from .mappers.table_mapper import create_default_queue_table_spec


class SQLSchemaManager:
    def __init__(self, provider: SQLProvider) -> None:
        self.provider = provider

    def apply_specification(self, context: Any) -> None:
        spec = self._read_sql_spec(context)
        schema_name = spec.get("schema", "dbo")
        tables = spec.get("tables", [])

        if not isinstance(tables, list):
            raise ValueError("SQL schema specification must include a list of tables")

        self.provider.create_schema(schema_name)
        for table in tables:
            cols = table.get("columns", [])
            id_column_name = None
            for c in cols:
                if c.get("name", "").lower().startswith("id"):
                    id_column_name = c["name"]
                    break

            if id_column_name is None:
                id_column_name = f"Id{table['name']}"
                insert_at = 0
                for i, c in enumerate(cols):
                    if c.get("name", "").lower() == "id":
                        insert_at = i + 1
                        break
                cols.insert(insert_at, {"name": id_column_name, "type": "INT", "identity": True, "nullable": False, "primary_key": True})
                table["columns"] = cols

            if not any(c.get("name", "").lower() == "fluxoexecucaoid" for c in cols):
                insert_at = 0
                for i, c in enumerate(cols):
                    if c.get("name", "").lower() == id_column_name.lower():
                        insert_at = i + 1
                        break
                cols.insert(insert_at, {"name": "FluxoExecucaoId", "type": "INT", "nullable": False})
                table["columns"] = cols

            self.provider.create_table(schema_name, table)

            if table.get("queue", True):
                queue_table = create_default_queue_table_spec(schema_name, table["name"], id_column_name)
                self.provider.create_table(schema_name, queue_table)

                try:
                    dialect = getattr(self.provider, "dialect", "sqlite")
                except Exception:
                    dialect = "sqlite"

                if dialect == "mssql":
                    quote = self.provider._quote_identifier
                    tbl = table["name"]
                    trigger_name = f"tr_{tbl}_Fila"
                    queue_name = queue_table.get("name")
                    trigger_sql = (
                        f"CREATE TRIGGER {quote(trigger_name)} ON {quote(schema_name)}.{quote(tbl)} AFTER INSERT AS BEGIN\n"
                        "    SET NOCOUNT ON;\n\n"
                        f"    INSERT INTO {quote(schema_name)}.{quote(queue_name)}\n"
                        "    (\n"
                        "          FluxoExecucaoId\n"
                        "        , DadosId\n"
                        "        , Usuario\n"
                        "        , Maquina\n"
                        "        , Ambiente\n"
                        "    )\n"
                        "    SELECT\n"
                        "          I.FluxoExecucaoId\n"
                        f"        , I.{id_column_name}\n"
                        "        , SUSER_SNAME()\n"
                        "        , HOST_NAME()\n"
                        "        , 'P'\n"
                        "    FROM inserted AS I;\n\n"
                        "END"
                    )
                    self.provider.execute(trigger_sql)

    def _read_sql_spec(self, context: Any) -> dict[str, Any]:
        if hasattr(context, "spec") and getattr(context.spec, "parameters", None) is not None:
            parameters = context.spec.parameters
            if isinstance(parameters, dict):
                return parameters.get("sql_schema") or parameters.get("database") or {}

        if hasattr(context, "variables") and isinstance(context.variables, dict):
            return context.variables.get("sql_schema") or context.variables.get("database") or {}

        return {}
