# RFC-0003 — Capability SQL e Provider SQLite

| Campo | Valor |
|---|---|
| Status | Aceita e implementada em `orchestrator-sql` 0.1.0 e `orchestrator-sqlite` 0.1.0 |
| Data | 2026-11-12 |
| Entrega | E4.1 do roadmap |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## 1. Escolha

SQL com Provider SQLite foi a primeira Capability: não exige dependência fora da biblioteca padrão, prova a separação entre Capability e Provider e é útil para automações (tabelas de trabalho, conciliações). Não havia informação sobre o primeiro projeto consumidor real que indicasse outra.

## 2. Contrato funcional (`SqlSession`)

Uma sessão por execução, aberta no `provision_dependencies` e fechada no `finalize`.

- Comandos: `execute`, `execute_many`, `fetch_all`, `fetch_one`, `scalar`. Valores só como parâmetros, escritos como `:nome`.
- Transações: `with session.transaction():` confirma no sucesso e desfaz no erro; aninhada, usa savepoints. Fora de transação, cada comando é confirmado sozinho. Uma transação esquecida aberta é desfeita no `finalize`.
- Utilitários com identificadores validados: `create_table`, `drop_table`, `insert`, `insert_many`, `select` (igualdade, `None` vira `IS NULL`), `update` e `delete` (os dois exigem `where` não vazio).
- `quote(nome)` valida e cita um identificador para SQL escrito à mão.
- Resultados como `Row`, mapeamento imutável por nome de coluna; nomes de coluna repetidos no resultado são erro.

## 3. Port do Provider (`SqlProvider`)

- `from_config(section)`, `verify()`, `connect()` em modo autocommit.
- `paramstyle` do driver; a Capability traduz `:nome` para `named`, `qmark`, `numeric`, `format` ou `pyformat`, ignorando literais, identificadores entre aspas, comentários e `::`. Parâmetro faltando ou sobrando é erro, e a mensagem cita nomes, nunca valores.
- `is_driver_error` e `translate_error` para `SqlConnectionError`, `SqlIntegrityError`, `SqlOperationalError`, `SqlProgrammingError` ou `SqlError`, com `retryable` para falhas transitórias.
- `column_type(SqlType)`, `adapt(valor)`, `quote_identifier`, comandos de transação e de savepoint, `describe()` sem credenciais.

## 4. Identificadores

Nomes usados pelos utilitários seguem `[A-Za-z_][A-Za-z0-9_]{0,62}`, opcionalmente `esquema.tabela`, e são citados pelo Provider (aspas duplas por padrão). Isso corrige SQL-02: tipos, valores padrão, `CHECK` e condições livres não são mais montados a partir de texto.

## 5. Configuração

```toml
[capabilities.sql]
provider = "sqlite"        # chave do mapa providers= dado pelo consumidor
database = "dados/app.db"  # demais chaves pertencem ao Provider
```

Só os Providers passados em `providers=` podem ser escolhidos. Credenciais de Providers futuros entram como referência de segredo (ADR-0007).

## 6. Excluído

Valores padrão em DDL, migrações, pool de conexões, ORM, acesso assíncrono, convenções de fila (ADR-0019).

## 7. Conformidade

`orchestrator_sql.testing.SqlProviderContract`: paramstyle conhecido, parâmetros, tipos portáveis com nome de tabela reservado, utilitários, transações aninhadas, tradução de erros, conformidade com o contrato de Capability do Core e desfazimento de transação esquecida. O Provider SQLite passa na suíte.

## 8. Segundo Provider (E4.4)

Adiado. O ambiente desta entrega não tinha outro banco disponível para validar um segundo Provider de verdade. A troca por configuração foi provada com o mesmo Provider (memória para arquivo, sem mudar código), e a tradução de parâmetros foi testada para os cinco paramstyles. Próximo passo: `orchestrator-postgres`, com serviço PostgreSQL na CI, herdando `SqlProviderContract`.

## 9. Extensibilidade (E4.5)

Nenhuma mudança de contrato no Core foi necessária para a Capability e o Provider. Uma correção de robustez do Core (flush de handlers de log quebrados não pode falhar uma execução) foi encontrada pelos testes do exemplo e registrada em commit próprio.
