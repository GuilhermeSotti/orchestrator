# ADR-0002 — Destino do scaffold de julho de 2026: arquivar e reconstruir

| Campo | Valor |
|---|---|
| Status | Aceito |
| Data | 2026-11-12 |
| Decisão | D-00 |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## Contexto

O commit `6232d68` (2026-07-06) e o trabalho não versionado que veio depois trouxeram um scaffold de `orchestrator_core` e um pacote `orchestrator_sql`, sem ADR nem RFC. A auditoria do código (`docs/audit/CODE_AUDIT.md`) mostrou problemas de desenho: o Core não executava a lógica do consumidor (COD-01), não garantia finalização (COD-02), o `ProcessRunner` travava e ignorava o pipeline (COD-03, COD-04), 18 de 38 módulos não tinham uso (COD-08), e o pacote SQL embutia regras de um consumidor e montava SQL com texto não validado (SQL-01, SQL-02).

## Decisão

1. O estado encontrado em 2026-11-12, inclusive o trabalho nunca commitado, fica preservado no commit-raiz do histórico local e na tag anotada `archive/scaffold-2026-07`.
2. O scaffold sai da árvore principal: `src/`, `tests/`, `packages/orchestrator_sql/`, os exemplos em JSON, `requirements.txt` e o `pyproject.toml` que descrevia o Core.
3. O Core, a Capability SQL e o Provider SQLite foram reconstruídos a partir dos contratos aprovados nas ADRs e RFCs. Nenhum arquivo do scaffold foi reaproveitado; ideias aproveitadas estão citadas nas RFCs (mapeamento de tipos e DDL simples, na RFC-0003).

## Alternativas consideradas

- **Adotar e refatorar.** Exigiria desfazer decisões implícitas (execução por spec JSON, ports sem consumidor, três runners, falha sem finalização) antes de avançar. O volume era pequeno (738 linhas não vazias no Core), e o custo de reescrever era menor que o de corrigir.
- **Descartar.** Perderia o registro do trabalho feito. A tag preserva o histórico sem custo.

## Consequências

- Os contratos nascem de decisões registradas.
- O CLI `orchestrator` e o formato de spec JSON deixam de existir (ver ADR-0003).
- Quem dependia do scaffold encontra o código na tag `archive/scaffold-2026-07`.

## Referências

- `docs/audit/CODE_AUDIT.md`, seções 6, 7, 11 e 12.
