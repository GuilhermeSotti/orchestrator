# ADR-0015 — Testes entre pacotes, exemplos e suítes de conformidade

| Campo | Valor |
|---|---|
| Status | Aceito |
| Data | 2026-11-12 |
| Decisão | D-21 |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## Decisão

1. O Core publica `orchestrator_core.testing`: `FakeClock`, `InMemoryMetrics`, `EventRecorder`, `InMemoryRecordSink` e `check_capability_conformance`, que executa uma Capability em execuções sequenciais e concorrentes e verifica isolamento de handles e fechamento do contexto.
2. Cada Capability publica a suíte que seus Providers precisam passar. A Capability SQL publica `orchestrator_sql.testing.SqlProviderContract`; o Provider SQLite herda a suíte nos seus testes.
3. Os testes de um pacote não importam pacotes que não sejam suas dependências declaradas. Os testes da Capability SQL usam um Provider mínimo construído só com a biblioteca padrão.
4. `tools/test_boundaries.py` verifica as fronteiras de importação entre pacotes (ADR-0001).
5. Os exemplos em `examples/` são projetos consumidores reais, com `pyproject.toml` próprio. Na CI, eles são instalados a partir dos wheels construídos e executados de ponta a ponta.

## Consequências

- Um Provider novo prova conformidade herdando uma classe; uma Capability nova prova o contrato do Core chamando uma função.

## Referências

- `packages/orchestrator-sqlite/tests/test_contract.py`; `tools/test_boundaries.py`.
