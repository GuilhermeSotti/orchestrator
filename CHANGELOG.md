# Changelog do repositório

Mudanças de governança, documentação, CI e estrutura. Cada pacote tem o seu changelog em `packages/<pacote>/CHANGELOG.md`.

## [Não lançado]

## 2026-11-12

### Adicionado

- `orchestrator-core` 0.1.0, `orchestrator-sql` 0.1.0 e `orchestrator-sqlite` 0.1.0 em `packages/`.
- Exemplos de projeto consumidor: `examples/hello-automation` e `examples/sales-report`.
- ADRs 0001 a 0019 e RFCs 0001 a 0003; registro de decisões em `docs/DECISIONS.md`.
- Guias: primeiros passos, configuração, Capabilities e Providers, release, governança no GitHub e recuperação do histórico.
- CI com qualidade, testes em Ubuntu e Windows, build reproduzível e testes de ponta a ponta; workflow de release; Dependabot para Actions e ferramentas.
- Ferramentas: verificação de links da documentação, testes de fronteira entre pacotes, build reproduzível e verificação de ponta a ponta com os wheels num ambiente limpo (`tools/`).
- `.gitattributes`, `.editorconfig`, `CLAUDE.md` e `requirements/dev.txt`.

### Alterado

- Histórico Git recriado a partir do estado da pasta; o estado anterior está no commit-raiz e na tag `archive/scaffold-2026-07`.
- Estratégia de repositórios: incubação neste repositório durante a série 0.x (ADR-0001).
- README, ARCHITECTURE, GOVERNANCE, SECURITY e CONTRIBUTING reescritos em português, alinhados às decisões.
- `docs/OPEN_DECISIONS.md` substituído por `docs/DECISIONS.md`.

### Removido

- Scaffold de julho de 2026 (`src/`, `tests/`, `packages/orchestrator_sql/`, specs JSON, `requirements.txt`), arquivado na tag `archive/scaffold-2026-07` (ADR-0002).
- Pastas sem conteúdo (`ADR/`, `config/`, `scripts/`, `assets/`, `templates/`, `docs/architecture`, `docs/decisions`, `docs/diagrams`, `docs/images`).

## 2026-11-11

- Auditoria técnica inicial (`docs/audit/INITIAL_AUDIT.md`), auditoria do código (`docs/audit/CODE_AUDIT.md`), roadmap de implementação e decisões em aberto.
- Correções pontuais: sintaxe TOML de `pyproject.toml`, padrões do `.gitignore`, digitação no README.

## 2026-06-30 a 2026-07-06

- Estrutura inicial do repositório, documentação de governança e arquitetura, roadmap inicial e scaffold do Core (histórico anterior, no remoto).
