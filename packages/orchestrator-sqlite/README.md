# orchestrator-sqlite

**Provider** SQLite para a Capability `orchestrator-sql`, sobre o módulo `sqlite3` da biblioteca padrão. Sem dependências externas.

## Configuração

```toml
[capabilities.sql]
provider = "sqlite"
database = "dados/app.db"   # ou ":memory:" (padrão)
timeout = 5.0               # segundos de espera por um lock
read_only = false
foreign_keys = true
```

- A pasta do arquivo precisa existir; o Provider não cria pastas.
- `read_only = true` exige que o arquivo já exista.
- Um banco `:memory:` dura só enquanto a conexão de uma execução estiver aberta.
- Datas e horários são gravados como texto ISO 8601, booleanos como 0/1 e decimais como texto com afinidade NUMERIC.
- "database is locked" vira `SqlOperationalError` com `retryable = True`, para uso com `ctx.retry`.

## Uso

```python
from orchestrator_sql import SqlCapability
from orchestrator_sqlite import SqliteProvider

builder.with_capability(SqlCapability, providers={"sqlite": SqliteProvider})
```

Ou, sem arquivo de configuração:

```python
builder.with_capability(SqlCapability(SqliteProvider("dados/app.db")))
```

O Provider é validado pela suíte de conformidade `orchestrator_sql.testing.SqlProviderContract`.

## Licença

MIT. Veja [LICENSE](LICENSE).
