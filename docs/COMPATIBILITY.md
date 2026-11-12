# Matriz de compatibilidade

Decisão: [ADR-0009](adr/0009-registro-de-capabilities-e-compatibilidade.md). A CI testa os pacotes juntos, nas versões desta tabela.

| Pacote | Versão | Core API | Depende de | Python |
|---|---|---|---|---|
| `orchestrator-core` | 0.1.0 | fornece `0.1` | — | >= 3.13 |
| `orchestrator-sql` | 0.1.0 | requer `0.1` | `orchestrator-core>=0.1,<0.2` | >= 3.13 |
| `orchestrator-sqlite` | 0.1.0 | — | `orchestrator-core>=0.1,<0.2`, `orchestrator-sql>=0.1,<0.2` | >= 3.13 |

Regras:

- Antes da 1.0, mudança de versão menor do Core pode quebrar compatibilidade; os pacotes dependentes restringem a faixa ao menor atual (`<0.2`).
- Uma Capability declara `core_api`; o registro falha com `IncompatibleCapabilityError` se não for compatível com o `CORE_API_VERSION` instalado.
- Plataformas testadas na CI: Ubuntu e Windows, Python 3.13, 3.14 e 3.15.
