# Changelog — orchestrator-sql

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versionamento semântico; antes da 1.0, uma versão menor pode quebrar compatibilidade.

## [Não lançado]

## [0.1.0] — 2026-11-12

Primeira versão ([RFC-0003](../../docs/rfc/0003-capability-sql.md)). Substitui o pacote `orchestrator_sql` do scaffold de julho de 2026, que foi arquivado.

### Adicionado

- `SqlCapability`: uma `SqlSession` por execução, conexão fechada no `finalize` e transação esquecida desfeita antes disso.
- `SqlProvider`: port dos Providers (conexão em autocommit, `paramstyle`, tradução de erros, tipos, citação de identificadores, savepoints).
- `SqlSession`: `execute`, `execute_many`, `fetch_all`, `fetch_one`, `scalar`, `transaction` (com savepoints), `create_table`, `drop_table`, `insert`, `insert_many`, `select`, `update` e `delete`.
- Parâmetros portáveis `:nome`, traduzidos para os cinco `paramstyle` do DB-API, ignorando literais, comentários e `::`.
- Validação de identificadores (`validate_identifier`, `TableName`) e definição de tabelas (`Table`, `Column`, `SqlType`).
- Erros `SqlError`, `SqlConnectionError`, `SqlIntegrityError`, `SqlOperationalError` e `SqlProgrammingError`.
- Suíte de conformidade `orchestrator_sql.testing.SqlProviderContract`.

### Removido em relação ao scaffold

- Convenções de fila, coluna `FluxoExecucaoId`, chave estrangeira para `CORE.FluxosExecucao` e gatilho de ambiente ([ADR-0019](../../docs/adr/0019-convencoes-de-fila-fora-da-plataforma.md)).
- Montagem de SQL a partir de texto não validado (tipos, valores padrão, `CHECK` e condições livres).
