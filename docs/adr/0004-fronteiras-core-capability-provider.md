# ADR-0004 — Fronteiras entre Core, Runtime, Capability e Provider

| Campo | Valor |
|---|---|
| Status | Aceito |
| Data | 2026-11-12 |
| Decisão | D-03 |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## Contexto

ARCHITECTURE dizia que Providers implementam "contracts defined by the Core", mas a regra de dependência passa por Capabilities, e o diagrama "Dependency Rule" colocava a Public API como camada mais interna (DOC-05). O scaffold tinha 12 ports de capabilities dentro do Core, nenhum usado (COD-08).

## Decisão

1. **Core** (`orchestrator-core`) contém apenas o que é transversal:
   - Runtime, Execution Pipeline, `Stage` e os oito estágios;
   - `ExecutionContext`, resultados e registros de execução;
   - contrato genérico de `Capability` e o Capability Registry;
   - configuração, segredos por referência e hierarquia de erros;
   - ports transversais: `MetricsRecorder`, `ExecutionRecordSink`, `SecretResolver` e `Clock`.
2. **Capability** (por exemplo `orchestrator-sql`) define o contrato funcional usado pelas automações (o handle, como `SqlSession`) e o port que os Providers implementam (como `SqlProvider`).
3. **Provider** (por exemplo `orchestrator-sqlite`) implementa o port de uma Capability para uma tecnologia, traduz exceções de infraestrutura para erros da Capability (subclasses de `ProviderError`) e nunca expõe credenciais.
4. As dependências apontam para dentro: Provider → Capability → Core. O projeto consumidor pode depender de todos.
5. "Public API" passa a significar os nomes exportados por `orchestrator_core`, `orchestrator_core.logs` e `orchestrator_core.testing`. Módulos iniciados por `_` são internos.

## Alternativas consideradas

- **Core define todos os ports** (SQL, fila, cache...). Faz o Core crescer a cada tecnologia, contra o princípio "novas tecnologias sem alterar o Core".
- **Pacote só de contratos.** Acrescenta um pacote e uma matriz de versões sem ganho enquanto houver um único Core.

## Consequências

- Uma nova tecnologia entra sem mudar o Core. A Fase 4 confirmou isso: a Capability SQL e o Provider SQLite não exigiram mudança de contrato no Core.
- ARCHITECTURE foi reescrito com o diagrama de dependências correto.

## Referências

- RFC-0001 (ciclo de vida), RFC-0003 (Capability SQL), ADR-0009 (registro).
