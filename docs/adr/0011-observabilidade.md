# ADR-0011 — Observabilidade: logging, eventos e métricas

| Campo | Valor |
|---|---|
| Status | Aceito |
| Data | 2026-11-12 |
| Decisão | D-14 (e as garantias de eventos de D-13) |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## Contexto

No scaffold, os logs eram textos numa lista em memória, sem nível nem mascaramento (COD-15), as métricas do runner estavam erradas (COD-13) e o `EventBus` interrompia a publicação quando um assinante falhava (COD-16).

## Decisão

**Logging**

1. A API é o módulo `logging` da biblioteca padrão. O Core registra em `orchestrator_core.*` e entrega à automação `ctx.logger` (logger `orchestrator.automation`).
2. O Core nunca configura logging sozinho: adiciona `NullHandler` aos seus loggers. A aplicação chama `orchestrator_core.logs.configure_logging()` ou usa os filtros nos próprios handlers.
3. `ExecutionContextFilter` acrescenta `execution_id`, `automation` e `stage` a todo registro emitido durante uma execução, inclusive por loggers do consumidor e das Capabilities (correlação por `contextvars`).
4. `RedactingFilter` mascara segredos registrados na mensagem, no traceback e na pilha. `JsonFormatter` emite uma linha JSON por registro.
5. Uma falha de um estágio é registrada uma única vez, com traceback, no logger `orchestrator_core.runtime`.
6. Falhas de handlers de log nunca interrompem uma execução, como no próprio módulo `logging`.

**Eventos** (garantias completas na RFC-0001)

7. Barramento síncrono, em processo, na ordem de assinatura; falha de assinante registrada e contada, sem interromper o pipeline; sem persistência.

**Métricas**

8. Port `MetricsRecorder` (`increment`, `observe`) com implementação padrão que descarta tudo. Falhas do backend são registradas e ignoradas.
9. Métricas do Core: `orchestrator.executions`, `orchestrator.execution.duration_seconds`, `orchestrator.stage.duration_seconds`, `orchestrator.event_handler.errors` e `orchestrator.retry.attempts`.

**Tracing**: fora do MVP; o `execution_id` basta para correlação. OpenTelemetry, Elastic e semelhantes entram como pacotes Provider; o Core nunca os importa.

## Alternativas consideradas

- **Biblioteca de logging estruturado de terceiros.** Rejeitada pela ADR-0005; o formatador JSON da biblioteca padrão atende.
- **Logs acumulados no contexto.** Perderiam integração com handlers existentes e níveis.

## Referências

- `packages/orchestrator-core/tests/test_observability.py`.
