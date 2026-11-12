# Changelog — orchestrator-sqlite

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versionamento semântico; antes da 1.0, uma versão menor pode quebrar compatibilidade.

## [Não lançado]

## [0.1.0] — 2026-11-12

### Adicionado

- `SqliteProvider` sobre `sqlite3`: arquivo ou `:memory:`, modo somente leitura, chaves estrangeiras ativas por padrão, espera configurável por locks.
- Tradução de erros do `sqlite3`; "database is locked" é marcado como repetível.
- Conversão de `bool`, `date`, `datetime` e `Decimal` antes do envio ao driver.
- Aprovado na suíte de conformidade `SqlProviderContract`.
