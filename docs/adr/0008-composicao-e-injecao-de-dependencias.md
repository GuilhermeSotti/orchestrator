# ADR-0008 — Composição e injeção de dependências

| Campo | Valor |
|---|---|
| Status | Aceito |
| Data | 2026-11-12 |
| Decisão | D-09 |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## Decisão

1. `RuntimeBuilder` é a raiz de composição. Toda dependência entra explicitamente: configuração, Capabilities, estágios, assinantes de eventos, métricas, destinos de registro, resolvedores de segredos e relógio.
2. Injeção por construtor; não há contêiner nem resolução por tipo.
3. Dois escopos:
   - **Runtime**: configuração, registry, barramento de eventos, métricas, estágios, Capabilities (fábricas de handles);
   - **Execução**: `ExecutionContext`, escopo de recursos e handles das Capabilities.
4. Não há singletons de módulo, com uma exceção justificada: o registro de valores a mascarar (`Redactor`) é do processo, porque os filtros de logging também são. O builder aceita outro registro (`with_redactor`) para testes.

## Alternativas consideradas

- **Registro interno de serviços com escopos.** Resolução implícita, mais difícil de testar e de ler.
- **Contêiner de terceiros.** Dependência que o Core não justifica (ADR-0005).

## Consequências

- Testes substituem qualquer dependência pelo builder, sem monkeypatch: `FakeClock`, `InMemoryMetrics`, `EventRecorder`, `InMemoryRecordSink`.

## Referências

- `orchestrator_core.testing`; ADR-0005.
