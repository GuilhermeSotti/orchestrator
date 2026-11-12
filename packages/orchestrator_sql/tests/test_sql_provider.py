from orchestrator_sql.sql_provider import SQLProvider


def test_sql_provider_creates_table_and_crud_operations():
    provider = SQLProvider(":memory:")
    provider.create_table(
        "PA0001",
        {
            "name": "Dados",
            "columns": [
                {"name": "Id", "type": "INTEGER", "identity": True, "nullable": False, "primary_key": True},
                {"name": "Name", "type": "VARCHAR(100)", "nullable": False},
                {"name": "IsActive", "type": "BOOLEAN", "nullable": False, "default": "1"},
            ],
            "indexes": [{"name": "IX_Dados_Name", "columns": ["Name"]}],
        },
    )

    provider.insert("PA0001", "Dados", {"Name": "Alice", "IsActive": 1})
    rows = provider.select("PA0001", "Dados", "*")
    assert len(rows) == 1
    assert rows[0]["Name"] == "Alice"

    provider.update("PA0001", "Dados", {"IsActive": 0}, "Name = :name", {"name": "Alice"})
    updated = provider.select("PA0001", "Dados", "*")
    assert updated[0]["IsActive"] == 0

    provider.delete("PA0001", "Dados", "Name = :name", {"name": "Alice"})
    assert provider.select("PA0001", "Dados", "*") == []
