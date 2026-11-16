# ADR-0020 — Provider que usa outra Capability como infraestrutura

| Campo | Valor |
|---|---|
| Status | Aceito |
| Data | 2026-11-15 |
| Decisão | D-26 (DS-1 da [RFC-0004](../rfc/0004-controles-reutilizaveis-escopo-e-sequencia.md)) |
| Decisor | Responsável pelo projeto, pelo aceite da RFC-0004 em 2026-11-15, que adota a recomendação (a) da DS-1 ([DECISIONS](../DECISIONS.md), seção 5) |

## Contexto

A [ADR-0004](0004-fronteiras-core-capability-provider.md) define Provider → Capability → Core, mas não diz se um Provider pode usar uma segunda Capability como infraestrutura. O caso aparece na fila sobre SQL (`orchestrator-queue-sql`, RFC-0008), nos registros em SQL (`orchestrator-records-sql`, RFC-0009) e nos mapeamentos em SQL (RFC-0010).

## Decisão

Permitido, com regras:

1. A dependência é declarada no `pyproject.toml` do Provider e em `tools/test_boundaries.py`.
2. O Provider obtém o handle da outra Capability por `ctx.capability(...)`, com o nome de registro dado na sua configuração; nunca abre conexões por fora dela.
3. Pacotes de **Capability** nunca dependem de outra Capability: só Providers.
4. Sem ciclos entre pacotes.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Proibir: cada Provider abre as próprias conexões | Duplica configuração, credenciais e transações; impede a fila de usar a mesma transação do negócio (RFC-0008, resposta 7) |

## Consequências

- O Provider herda a configuração, as credenciais e o ciclo de vida da Capability usada, inclusive o `finalize`.
- A ordem de registro importa: a Capability usada precisa estar registrada e aberta antes.
- `tools/test_boundaries.py` passa a ter dependências entre Providers e Capabilities de terceiros níveis.

## Referências

[ADR-0004](0004-fronteiras-core-capability-provider.md), [RFC-0004](../rfc/0004-controles-reutilizaveis-escopo-e-sequencia.md) (seções 3 e 4), [RFC-0008](../rfc/0008-capability-de-fila.md), [RFC-0009](../rfc/0009-destinos-de-registros-e-logs.md).
