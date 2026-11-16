# Matriz de compatibilidade

Decisão: [ADR-0009](adr/0009-registro-de-capabilities-e-compatibilidade.md). A CI testa os pacotes juntos, nas versões desta tabela.

| Pacote | Versão | Core API | Depende de | Python | Situação |
|---|---|---|---|---|---|
| `orchestrator-core` | 0.2.0 | fornece `0.2` | — | >= 3.13 | Na branch local `feature/core-0.2`, sem release (2026-11-15) |
| `orchestrator-sql` | 0.2.0 | requer `0.2` | `orchestrator-core>=0.2,<0.3` | >= 3.13 | Na branch local `feature/core-0.2`, sem release |
| `orchestrator-sqlite` | 0.2.0 | — | `orchestrator-core>=0.2,<0.3`, `orchestrator-sql>=0.2,<0.3` | >= 3.13 | Na branch local `feature/core-0.2`, sem release |
| `orchestrator-notifications` | 0.1.0 | requer `0.2` | `orchestrator-core>=0.2,<0.3` | >= 3.13 | Na branch local `feature/notifications`, sem release |
| `orchestrator-notifications-smtp` | 0.1.0 | — | `orchestrator-core>=0.2,<0.3`, `orchestrator-notifications>=0.1,<0.2` | >= 3.13 | Na branch local `feature/notifications-smtp`, sem release |
| `orchestrator-notifications-teams` | 0.1.0 | — | `orchestrator-core>=0.2,<0.3`, `orchestrator-notifications>=0.1,<0.2` | >= 3.13 | Na branch local `feature/notifications-teams`, sem release |
| `orchestrator-records-file` | 0.1.0 | — | `orchestrator-core>=0.2,<0.3` | >= 3.13 | Na branch local `feature/records-file`, sem release |
| `orchestrator-calendar` | 0.1.0 | requer `0.2` | `orchestrator-core>=0.2,<0.3` | >= 3.13 | Na branch local `feature/calendar`, sem release |
| `orchestrator-core` | 0.1.0 | fornece `0.1` | — | >= 3.13 | Release (tag `orchestrator-core/v0.1.0`) |
| `orchestrator-sql` | 0.1.0 | requer `0.1` | `orchestrator-core>=0.1,<0.2` | >= 3.13 | Release (tag `orchestrator-sql/v0.1.0`) |
| `orchestrator-sqlite` | 0.1.0 | — | `orchestrator-core>=0.1,<0.2`, `orchestrator-sql>=0.1,<0.2` | >= 3.13 | Release (tag `orchestrator-sqlite/v0.1.0`) |

As versões 0.1.0 e 0.2.0 não se misturam: pela regra da ADR-0009 (igualdade exata antes da 1.0), a `SqlCapability` 0.1.0 é recusada pelo Core 0.2.0, e a 0.2.0 pelo Core 0.1.0. Por isso as três 0.2.0 entram juntas, num único Pull Request.

Quebras da 0.2.0 para quem estende a plataforma: `SqlProvider.connect()` passou a `connect(secrets)`; falha de `ExecutionRecordSink` não altera mais o status; os métodos de tempo do contexto mudam de comportamento no teardown. Quem só usa `SqlSession` e o `Runtime` não precisa mudar código, só a faixa de versões.

Regras:

- Antes da 1.0, mudança de versão menor do Core pode quebrar compatibilidade; os pacotes dependentes restringem a faixa ao menor atual (`<0.2`).
- Uma Capability declara `core_api`; o registro falha com `IncompatibleCapabilityError` se não for compatível com o `CORE_API_VERSION` instalado.
- Plataformas testadas na CI: Ubuntu e Windows, Python 3.13, 3.14 e 3.15.
