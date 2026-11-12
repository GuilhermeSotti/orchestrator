from orchestrator_sql.schema_manager import SQLSchemaManager
from orchestrator_sql.sql_provider import SQLProvider


class DummySpec:
    def __init__(self, parameters):
        self.parameters = parameters


class DummyContext:
    def __init__(self, spec):
        self.spec = spec


def test_schema_manager_creates_data_and_queue_tables():
    provider = SQLProvider(":memory:")
    manager = SQLSchemaManager(provider)
    spec = DummySpec(
        {
            "database": {
                "schema": "PA0001",
                "tables": [
                    {
                        "name": "Dados",
                        "columns": [
                            {"name": "ColunaEx", "type": "VARCHAR(255)", "nullable": False},
                        ],
                        "queue": True,
                    }
                ],
            }
        }
    )
    context = DummyContext(spec)

    manager.apply_specification(context)

    result = provider.select("PA0001", "Dados", "*")
    assert isinstance(result, list)
    queue_rows = provider.select("PA0001", "FilaDados", "*")
    assert isinstance(queue_rows, list)
