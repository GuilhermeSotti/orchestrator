# Changelog — orchestrator-core

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versionamento semântico; antes da 1.0, uma versão menor pode quebrar compatibilidade.

## [Não lançado]

Versão 0.2.0 preparada em 2026-11-15 na branch local `feature/core-0.2`, sem push, tag nem release. A implementação foi aprovada pelo responsável como decisão de encaminhamento ([DECISIONS](../../docs/DECISIONS.md), seção 4); as RFCs de origem foram aceitas em 2026-11-15 ([DECISIONS](../../docs/DECISIONS.md), seção 5); a autorização do responsável vem antes do merge e da tag.

### Adicionado

- `ExecutionContext.step(nome)`: rastreamento de subetapas, com aninhamento, `StepStarted`, `StepFinished`, `StepOutcome` e `StepRecord`; `ExecutionResult.steps`, `ExecutionRecord.steps` e `ExecutionRecord.steps_truncated`; métrica `orchestrator.step.duration_seconds`; campo `step` nos registros de log ([RFC-0005](../../docs/rfc/0005-core-0-2-subetapas-mascaramento-teardown-e-sinais.md), 2.3).
- `runtime.max_steps` (padrão 1.000): limite de subetapas no resultado e no registro; as seguintes continuam gerando eventos e métricas.
- `runtime.teardown_timeout` (padrão 60 s; `0` desliga): orçamento próprio dos estágios de teardown (RFC-0005, 2.2).
- `ExecutionContext.redact(texto)` e `ExecutionOutcome.error_info`, para texto que sai do processo (RFC-0005, 2.1).
- `ExecutionContext.stages`: nomes dos estágios do pipeline, para Capabilities recusarem configuração incompleta antes da automação ([RFC-0007](../../docs/rfc/0007-capability-de-notificacoes.md), resposta 6).
- `orchestrator_core.testing.make_secret_store` e o parâmetro `secret_resolvers=` de `check_capability_conformance`, para testar Providers que resolvem credenciais.
- Métrica `orchestrator.record_sink.errors`.
- Guia [Encerramento por sinal](../../docs/guides/encerramento-por-sinal.md), com teste em subprocesso (RFC-0005, 2.4). O Core continua sem instalar tratadores de sinal.

### Alterado

- `CORE_API_VERSION` passa a `"0.2"`. Capabilities declaradas para `"0.1"` são recusadas no registro ([ADR-0009](../../docs/adr/0009-registro-de-capabilities-e-compatibilidade.md)).
- Nos estágios de teardown, `ctx.check()`, `ctx.sleep()`, `ctx.retry()`, `ctx.remaining()` e `ctx.deadline_exceeded()` seguem o orçamento de teardown: o cancelamento ou o prazo que encerrou a execução não é relançado, e `ctx.sleep` não acorda pelo token. Na 0.1.0, lançavam na hora depois de cancelamento ou prazo.
- Uma exceção de `ExecutionRecordSink.write` não altera mais o status nem o resultado: vira aviso no log e conta em `orchestrator.record_sink.errors`; os demais destinos continuam recebendo o registro ([RFC-0009](../../docs/rfc/0009-destinos-de-registros-e-logs.md), resposta 6). Na 0.1.0, virava erro de teardown e a execução terminava `failed`.
- `ExecutionRecord.to_dict()` ganha as chaves `steps` e `steps_truncated`.
- `SecretStore` guarda cada valor resolvido só durante a execução: a mesma referência é resolvida uma vez por execução, o estágio `shutdown` descarta os valores e a execução seguinte resolve de novo; falhas de resolução não ficam guardadas ([RFC-0006](../../docs/rfc/0006-segredos-cofres-e-credenciais-de-providers.md), resposta 3).

### Corrigido

- Uma exceção cujo `__str__` falha não interrompe mais o pipeline: `ErrorInfo` usa a mensagem `<exception str() failed>`. Na 0.1.0, `Runtime.run` lançava e o teardown não rodava (encontrado na consolidação de 2026-11-15; teste de regressão em `test_pipeline.py`).
- Uma interrupção (`BaseException`) num assinante de `StepStarted` não deixa mais a subetapa como corrente no restante da execução.

## [0.1.0] — 2026-11-12

Primeira versão, reconstruída a partir de contratos decididos ([ADR-0002](../../docs/adr/0002-destino-do-scaffold.md)). Não reaproveita código do scaffold de julho de 2026.

### Adicionado

- `Runtime` e `RuntimeBuilder`: composição explícita, sem descoberta implícita de plugins.
- Execution Pipeline com os oito estágios documentados, fases de preparação, execução e teardown, e inserção de estágios customizados (`Stage`, `FunctionStage`).
- Teardown garantido: finalizers e recursos liberados em ordem inversa; erros de teardown agregados sem mascarar o erro primário.
- `ExecutionContext` por execução: identidade imutável, `state` do consumidor, parâmetros com validação opcional, workspace temporário opcional.
- `ExecutionResult` e `ExecutionRecord` com status `succeeded`, `failed`, `cancelled` e `timed_out`, desfecho por estágio e erros mascarados.
- Configuração com precedência padrões < arquivo TOML < variáveis de ambiente < valores explícitos, validação com o caminho da chave e acesso tipado (`ConfigSection`).
- Segredos por referência (`env:`, `file:` e resolvedores próprios), valor encapsulado em `Secret` e mascarado em logs, eventos e registros.
- Contrato de `Capability`, registro explícito, verificação de compatibilidade de API (`CORE_API_VERSION = "0.1"`) e escopo de recursos.
- Logging com correlação (`execution_id`, `automation`, `stage`), filtro de mascaramento e saída JSON (`orchestrator_core.logs`).
- Eventos de ciclo de vida em barramento síncrono com isolamento de falhas; port de métricas sem implementação padrão.
- Retry explícito (`RetryPolicy`, `retry`, `ExecutionContext.retry`), cancelamento cooperativo (`CancellationToken`) e prazo por execução.
- Módulo `orchestrator_core.testing`: `FakeClock`, `InMemoryMetrics`, `EventRecorder`, `InMemoryRecordSink` e `check_capability_conformance`.
