# orchestrator-sql

**Capability** SQL da plataforma Orchestrator. Define o contrato funcional (`SqlSession`) e o port que os **Providers** implementam (`SqlProvider`). Não conhece nenhum banco específico: SQLite, PostgreSQL e outros entram como Providers ([RFC-0003](../../docs/rfc/0003-capability-sql.md)).

- Depende apenas de `orchestrator-core` e da biblioteca padrão.
- Valores sempre como parâmetros, escritos como `:nome` em qualquer banco; o Provider declara o `paramstyle` do driver e a tradução é automática.
- Nomes de tabela e coluna usados pelos utilitários são validados (`[A-Za-z_][A-Za-z0-9_]*`, até 63 caracteres) e citados pelo Provider.
- Transações com `with session.transaction():`, aninhadas por savepoints. Fora delas, cada comando é confirmado sozinho.
- Erros do driver traduzidos para `SqlError` e subclasses, com a marca `retryable` para falhas transitórias. Mensagens nunca trazem valores de parâmetros.
- Sem convenções de consumidor: nenhuma tabela de fila, coluna obrigatória ou gatilho embutido ([ADR-0019](../../docs/adr/0019-convencoes-de-fila-fora-da-plataforma.md)).

## Uso

```toml
# orchestrator.toml
[capabilities.sql]
provider = "sqlite"
database = "dados/vendas.db"
```

```python
from orchestrator_core import ExecutionContext, RuntimeBuilder
from orchestrator_sql import Column, SqlCapability, SqlType, Table
from orchestrator_sqlite import SqliteProvider

PEDIDOS = Table.define(
    "pedidos",
    [
        Column("id", SqlType.INTEGER, primary_key=True),
        Column("regiao", SqlType.TEXT, nullable=False),
        Column("valor", SqlType.NUMERIC),
    ],
)


def automacao(ctx: ExecutionContext) -> int:
    sql = ctx.capability(SqlCapability)
    sql.create_table(PEDIDOS)
    with sql.transaction():
        sql.insert_many("pedidos", [{"id": 1, "regiao": "Sul", "valor": 10}])
    return sql.scalar("SELECT count(*) FROM pedidos WHERE regiao = :regiao", {"regiao": "Sul"})


runtime = (
    RuntimeBuilder()
    .with_config_file("orchestrator.toml")
    .with_capability(SqlCapability, providers={"sqlite": SqliteProvider})
    .build()
)
```

Só os Providers passados em `providers=` podem ser escolhidos pela configuração. Trocar de banco é mudar `provider` e as chaves do Provider no arquivo ou nas variáveis `ORCHESTRATOR_CAPABILITIES__SQL__*`.

## Escrevendo um Provider

Implemente `SqlProvider` (conexão em modo autocommit, `paramstyle`, tradução de erros, mapeamento de tipos) e herde a suíte de conformidade:

```python
from orchestrator_sql.testing import SqlProviderContract


class TestMeuProvider(SqlProviderContract):
    def make_provider(self):
        return MeuProvider(...)
```

## Licença

MIT. Veja [LICENSE](LICENSE).
