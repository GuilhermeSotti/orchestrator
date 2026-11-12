# RFC-0001 — Ciclo de vida da execução

| Campo | Valor |
|---|---|
| Status | Aceita e implementada em `orchestrator-core` 0.1.0 |
| Data | 2026-11-12 |
| Decisões | D-06, D-07, D-13, D-15 e D-16 |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## 1. Problema

A documentação listava oito estágios sem definir o que acontece quando um deles falha, é cancelado ou excede o prazo, nem o que cada estágio faz. O scaffold interrompia o pipeline sem finalizar recursos (COD-02) e engolia exceções (COD-05).

## 2. Fases e estágios

| # | Estágio | Fase | O que faz |
|---:|---|---|---|
| 1 | `initialize` | Preparação | Registra o início no log e publica `ExecutionStarted` |
| 2 | `provision_dependencies` | Preparação | Para cada Capability, na ordem de registro: `verify()` e `open(ctx)`; guarda o handle da execução. Nunca instala pacotes |
| 3 | `prepare_environment` | Preparação | Com `runtime.workspace = true`, cria uma pasta temporária privada (`ctx.workspace`) e agenda a remoção |
| 4 | `prepare_execution` | Preparação | Aplica o `parameters_validator`, se houver; o resultado vira `ctx.parameters` |
| 5 | `execute_automation` | Execução | Chama a automação com o contexto e guarda o retorno |
| 6 | `finalize` | Teardown | Executa os finalizers (ordem inversa), depois libera os recursos (ordem inversa) |
| 7 | `persist_logs` | Teardown | Entrega o `ExecutionRecord` aos destinos registrados e descarrega os handlers de log |
| 8 | `shutdown` | Teardown | Fecha o contexto: handles de Capabilities deixam de ser acessíveis |

Estágios customizados podem ser inseridos antes ou depois de qualquer estágio (`with_stage(..., before=...)`), desde que `initialize` continue sendo o primeiro e as fases não regridam (preparação, execução, teardown). Os oito estágios não podem ser removidos nem substituídos.

## 3. Comportamento em falha

| Situação | Comportamento |
|---|---|
| Antes de cada estágio de preparação ou execução | O Runtime verifica cancelamento e prazo; se interrompido, o estágio fica `cancelled` ou `timed_out` e não roda |
| Falha na preparação | Os estágios seguintes de preparação e a execução ficam `skipped`; o teardown roda |
| Falha na execução | O teardown roda; o erro original é preservado, com traceback |
| Falha num estágio de teardown | Os demais estágios de teardown ainda rodam; o erro é agregado e não mascara o erro primário |
| Teardown | Roda sempre, inclusive se a execução foi cancelada antes de começar |
| Vários erros num estágio de teardown | O estágio lança `ExceptionGroup` com todos |
| Execução bem-sucedida com falha no teardown | Status `failed`; o primeiro erro de teardown vira o erro do resultado |
| `KeyboardInterrupt`, `SystemExit` e outros `BaseException` | O teardown roda e a exceção é relançada por `run()`; `KeyboardInterrupt` conta como `cancelled` no evento final |
| Erro de uso antes do início (`automation` não chamável, `timeout` inválido) | `run()` lança `TypeError` ou `ValueError` |

`Runtime.run` não lança exceção por falha de estágio ou da automação: devolve o `ExecutionResult`. `result.raise_for_status()` lança `ExecutionFailedError` com o erro original encadeado.

## 4. Status

| Erro primário | Status |
|---|---|
| Nenhum, sem erros de teardown | `succeeded` |
| Nenhum, com erros de teardown | `failed` |
| `ExecutionCancelledError` ou `KeyboardInterrupt` | `cancelled` |
| `ExecutionTimeoutError` | `timed_out` |
| Qualquer outro | `failed` |

## 5. Cancelamento e prazo

- O cancelamento é cooperativo, por `CancellationToken` passado a `run(..., cancellation=token)`. Pode ser acionado de outra thread.
- O prazo vem de `run(..., timeout=...)` ou de `runtime.timeout`, medido em tempo monotônico a partir do início.
- A automação coopera com `ctx.check()` e `ctx.sleep()`; `ctx.sleep` acorda ao cancelar e não passa do prazo. `ctx.retry` respeita os dois.
- Uma automação que termina depois do prazo sem verificar continua `succeeded`, e o Runtime registra um aviso. Interrupção forçada fica fora do Core (ADR-0006).

## 6. Recursos e finalizers

- `ctx.resources.callback(...)` e `ctx.resources.enter(context_manager)` registram limpezas, liberadas em ordem inversa no `finalize`. Uma falha não impede as demais.
- `ctx.add_finalizer(fn)` registra uma ação que recebe o `ExecutionOutcome` provisório (status e erro), executada antes da liberação dos recursos. Serve para confirmar ou desfazer conforme o resultado.

## 7. Execution Context

Um contexto por execução, nunca compartilhado nem global. Conteúdo:

- identidade imutável: `execution_id`, `automation`, `runtime`, `started_at`;
- serviços: `config` (somente leitura), `logger`, `metrics`, `secrets`, `cancellation`, `resources`, `capability(...)`, `publish(...)`, `retry(...)`, `sleep(...)`, `check()`, `remaining()`, `now()`;
- dados da execução: `parameters` (mapeamento somente leitura ou valor validado), `workspace`, `outcome` (durante o teardown);
- `state`: dicionário mutável que pertence ao consumidor.

## 8. Eventos

| Evento | Quando |
|---|---|
| `StageStarted` | Antes de cada estágio que roda |
| `ExecutionStarted` | No estágio `initialize` |
| `StageFinished` | Depois de cada estágio que roda, com status, duração e erro mascarado |
| `ExecutionFinished` | Depois de todo o pipeline, com o status final |

Garantias: entrega síncrona, na thread da execução, na ordem de assinatura; cada assinante recebe os eventos que são instâncias do tipo assinado; no máximo uma entrega; sem persistência; falha de assinante registrada e contada em `orchestrator.event_handler.errors`, sem interromper nada. Consumidores podem publicar eventos próprios, subclasses de `Event`, com `ctx.publish`.

## 9. Registro da execução (Persist Logs)

O `ExecutionRecord` é produzido no estágio `persist_logs`, com status, desfecho de cada estágio executado até então e erros mascarados, e entregue aos `ExecutionRecordSink` registrados. Falhas em `shutdown` (ou em estágios customizados posteriores a `persist_logs`) aparecem no resultado e nos logs, mas não no registro já entregue. O Core não persiste dados de negócio; armazenar histórico em banco é papel de uma Capability futura.

## 10. Fora do escopo

Checkpoint, retomada, pausa e execução parcial (ADR-0016).

## 11. Verificação

- Matriz de falha com erro injetado em cada um dos oito estágios: `packages/orchestrator-core/tests/test_pipeline.py::test_failure_matrix`.
- Agregação de erros de teardown, finalizers, recursos, `KeyboardInterrupt`, cancelamento, prazo, eventos e estresse de concorrência nos demais testes do pacote.
