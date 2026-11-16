# Changelog do repositório

Mudanças de governança, documentação, CI e estrutura. Cada pacote tem o seu changelog em `packages/<pacote>/CHANGELOG.md`.

## [Não lançado]

### Adicionado

- `packages/orchestrator-calendar` 0.1.0, Capability de calendários com fonte em arquivo (RFC-0011), na branch `feature/calendar`; `tools/e2e.py` o usa a partir do wheel.
- `packages/orchestrator-records-file` 0.1.0, destinos em arquivo de registros e logs (RFC-0009), na branch `feature/records-file`; `tools/e2e.py` o usa a partir do wheel.
- `examples/batch-check`: projeto consumidor que demonstra as notificações; `tools/e2e.py` o executa a partir dos wheels contra um servidor SMTP local.
- `packages/orchestrator-notifications-teams` 0.1.0, canal do Microsoft Teams (RFC-0007, seção 6), na branch `feature/notifications-teams`.
- `packages/orchestrator-notifications-smtp` 0.1.0, canal de e-mail (RFC-0007, seção 6), na branch `feature/notifications-smtp`.
- `packages/orchestrator-notifications` 0.1.0, Capability de notificações (RFC-0007), na branch `feature/notifications`.
- Diagnóstico de escopo dos controles reutilizáveis de automação (`docs/audit/SCOPE_DIAGNOSIS.md`).
- RFCs 0004 a 0012, em proposta e não aceitas: escopo e sequência, Core 0.2, segredos, notificações, fila, registros e logs, mapeamentos, calendários e autenticação por sistema.
- Respostas do responsável às perguntas das RFCs 0004 a 0012 (2026-11-15), gravadas nas próprias RFCs.
- Reconciliação das respostas (`docs/audit/RFC_RESPONSE_RECONCILIATION.md`): classificação de cada pergunta, DS-1 a DS-8, 34 conflitos e lacunas, aceite por parte e decisões pedidas.
- Guia de encerramento por sinal (`docs/guides/encerramento-por-sinal.md`).
- Fase 7 no roadmap de implementação.
- RFC-0013 (valores de segredos em SQL: avaliação de segurança) e RFC-0014 (subetapas padrão de finalização do ciclo de vida e de sistemas e processos), em proposta e não aceitas.
- Consolidação do Core 0.2.0 (`docs/audit/CORE_020_CONSOLIDATION.md`): estado inicial, auditoria, correções, compatibilidade, validação e estado da integração.

### Alterado

- `docs/DECISIONS.md`: pendências conferidas em 2026-11-15 e respostas do responsável, sem aceite formal das RFCs.
- `docs/DECISIONS.md`: decisões de encaminhamento de 2026-11-15 (seção 4, DE-1 a DE-4), sem aceite de RFC; pendências 7 a 9 revistas.
- RFCs 0004 a 0012 aceitas pelo responsável em 2026-11-15: cabeçalhos, índice das RFCs, `docs/DECISIONS.md` (seção 5; pendência 7 resolvida), roadmap e changelog do Core. RFC-0013 e RFC-0014 continuam em proposta.
- Roadmap (Fase 7), índice das RFCs, reconciliação (decisões posteriores, seção 9) e guia de recuperação do histórico (nota de 2026-11-15).
- RFC-0001 (notas da 0.2.0), RFC-0002 (seção 2.1, acréscimos da 0.2.0), RFC-0003 (`connect(secrets)`), `docs/COMPATIBILITY.md` (0.2.0), `ARCHITECTURE.md`, `SECURITY.md` e os guias de configuração e de Capabilities e Providers.
- Exemplos 0.2.0: o ponto de entrada liga `SIGTERM` e Ctrl+Break ao token de cancelamento e exige os pacotes 0.2.

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
