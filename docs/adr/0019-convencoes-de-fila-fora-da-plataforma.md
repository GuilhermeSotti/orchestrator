# ADR-0019 — Convenções de fila e de schema fora da plataforma

| Campo | Valor |
|---|---|
| Status | Aceito |
| Data | 2026-11-12 |
| Decisão | D-25 |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## Contexto

O pacote SQL do scaffold acrescentava a toda tabela a coluna `FluxoExecucaoId`, criava por padrão uma tabela de fila com `Usuario`, `Maquina` e `Ambiente`, estados em português, chave estrangeira fixa para `CORE.FluxosExecucao` e um gatilho que gravava `'P'` como ambiente (SQL-01). São regras de um ambiente específico.

## Decisão

1. Essas convenções pertencem ao projeto consumidor que as usa. A Capability SQL não conhece tabelas, colunas, estados ou ambientes de nenhum consumidor.
2. Se mais de um projeto consumidor seguir o mesmo modelo de fila, as convenções podem virar um pacote da organização, fora da plataforma, que dependa da Capability SQL.
3. Uma futura Capability de fila genérica (Queue, prevista na arquitetura) exige RFC própria e não herda essas convenções.

## Consequências

- O código do scaffold com essas regras fica disponível na tag `archive/scaffold-2026-07`, para o consumidor que precisar recriá-las.

## Referências

- `docs/audit/CODE_AUDIT.md` (SQL-01); RFC-0003.
