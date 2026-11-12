# orchestrator-sql

Capability package that provides database abstraction, schema generation and SQL execution for Orchestrator.

## Features

- SQL provider abstraction with pluggable connection strategies
- JSON-driven schema and queue table generation
- Dynamic query execution with result mapping
- `SQLite` fallback for local testing and rapid prototyping

## Usage

Use `SQLProvider` to connect and run SQL commands, then manage schema with `SQLSchemaManager`.

Example schema spec:

```json
{
  "schema": "PA0001",
  "tables": [
    {
      "name": "Dados",
      "columns": [
        { "name": "Id", "type": "INT", "identity": true, "nullable": false, "primary_key": true },
        { "name": "ColunaEx", "type": "VARCHAR(255)", "nullable": false },
        { "name": "CreatedAt", "type": "DATETIME2(3)", "nullable": false, "default": "SYSUTCDATETIME()" },
        { "name": "UpdatedAt", "type": "DATETIME2(3)", "nullable": true },
        { "name": "IsActive", "type": "BIT", "nullable": false, "default": "1" }
      ],
      "indexes": [
        { "name": "IX_Dados_ColunaEx", "columns": ["ColunaEx"] }
      ],
      "queue": true
    }
  ]
}
```

Execute schema creation with:

```python
from orchestrator_sql.sql_provider import SQLProvider
from orchestrator_sql.schema_manager import SQLSchemaManager

provider = SQLProvider(":memory:")
manager = SQLSchemaManager(provider)
manager.apply_specification(context)
```
