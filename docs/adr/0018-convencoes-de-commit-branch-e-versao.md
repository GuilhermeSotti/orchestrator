# ADR-0018 — Convenções de commit, branch, merge e versionamento por pacote

| Campo | Valor |
|---|---|
| Status | Aceito |
| Data | 2026-11-12 |
| Decisão | D-24 |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## Contexto

Não havia convenção de mensagens (REP-08); os prefixos de branch não cobriam documentação e manutenção (GOV-04); a branch `feature` impedia criar `feature/*` (REP-06); havia três lugares para registrar decisões (GOV-06).

## Decisão

1. **Commits**: Conventional Commits (`feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`, `chore`), escopo opcional igual ao pacote (`core`, `sql`, `sqlite`, `examples`, `repo`); `!` ou rodapé `BREAKING CHANGE:` para quebra de compatibilidade.
2. **Branches**: `main` permanente; temporárias `feature/*`, `fix/*`, `hotfix/*`, `release/*`, `experiment/*`, `docs/*` e `chore/*`. As branches antigas `feature`, `feature-core` e `teste` devem ser removidas do remoto depois da reconciliação do histórico.
3. **Merge**: squash merge em `main`, com a mensagem do PR seguindo o item 1.
4. **Versões**: SemVer por pacote; antes da 1.0, uma versão menor pode quebrar compatibilidade. Tags `<distribuição>/v<versão>` (por exemplo `orchestrator-core/v0.1.0`). Tags `archive/*` preservam estados históricos.
5. **Changelog**: um por pacote, no formato Keep a Changelog; o da raiz registra mudanças do repositório (governança, CI, documentação).
6. **Decisões**: ADRs somente em `docs/adr/`, RFCs em `docs/rfc/`. As pastas `ADR/` e `docs/decisions/` foram removidas.

## Referências

- `GOVERNANCE.md`, `CONTRIBUTING.md`.
