# ADR-0010 — Retry explícito

| Campo | Valor |
|---|---|
| Status | Aceito |
| Data | 2026-11-12 |
| Decisão | D-12 |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## Decisão

1. O Core oferece `RetryPolicy` (tentativas, espera fixa ou exponencial com variação aleatória, espera máxima, tempo total máximo, filtro de erros), a função `retry` e o atalho `ctx.retry(operação, política, name=...)`.
2. **Padrão: sem retry.** Nada é repetido sem pedido explícito.
3. O filtro padrão repete apenas erros com `retryable = True`. Providers marcam falhas transitórias (lock de banco, conexão recusada).
4. `ctx.retry` respeita cancelamento e prazo: a espera acorda ao cancelar e não ultrapassa o prazo. Cada nova tentativa gera um aviso no log e a métrica `orchestrator.retry.attempts`.
5. Ao desistir, o erro original é relançado sem troca de tipo, com uma nota (PEP 678) dizendo quantas tentativas foram feitas.
6. O Runtime não reexecuta automações inteiras. Uma opção futura exigiria RFC e automação declarada idempotente.

## Alternativas consideradas

- **Reexecutar o estágio de execução.** Só é seguro para automações idempotentes; o padrão errado causaria efeitos duplicados.
- **Biblioteca de terceiros.** Dependência desnecessária (ADR-0005).

## Referências

- `packages/orchestrator-core/tests/test_retry_and_interruptions.py`.
