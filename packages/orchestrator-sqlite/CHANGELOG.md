# Changelog — orchestrator-sqlite

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versionamento semântico; antes da 1.0, uma versão menor pode quebrar compatibilidade.

## [Não lançado]

Versão 0.2.0 preparada em 2026-11-15 na branch local `feature/core-0.2`, sem push, tag nem release; depende do `orchestrator-core` 0.2.0 e do `orchestrator-sql` 0.2.0 e entra no mesmo Pull Request.

### Alterado

- `SqliteProvider.connect(secrets)`, conforme o port do `orchestrator-sql` 0.2.0. O SQLite não tem credenciais: `secrets` não é usado. Nenhuma mudança para quem usa o Provider pela configuração.
- Dependências `orchestrator-core>=0.2,<0.3` e `orchestrator-sql>=0.2,<0.3`.

### Adicionado

- A suíte de conformidade também roda sobre um Provider SQLite de teste protegido por senha resolvida por referência, e detecta um Provider que guarda a senha.

## [0.1.0] — 2026-11-12

### Adicionado

- `SqliteProvider` sobre `sqlite3`: arquivo ou `:memory:`, modo somente leitura, chaves estrangeiras ativas por padrão, espera configurável por locks.
- Tradução de erros do `sqlite3`; "database is locked" é marcado como repetível.
- Conversão de `bool`, `date`, `datetime` e `Decimal` antes do envio ao driver.
- Aprovado na suíte de conformidade `SqlProviderContract`.
