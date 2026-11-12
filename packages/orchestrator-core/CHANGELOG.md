# Changelog — orchestrator-core

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versionamento semântico; antes da 1.0, uma versão menor pode quebrar compatibilidade.

## [Não lançado]

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
