# ADR-0009 — Capability Registry, descoberta de plugins e compatibilidade

| Campo | Valor |
|---|---|
| Status | Aceito |
| Data | 2026-11-12 |
| Decisão | D-10 e D-11 |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## Contexto

SECURITY exige revisão para carregamento de plugins. No scaffold, o registro duplicado deixava dois objetos ativos (COD-10) e `discover()` executava qualquer entry point instalado (COD-11).

## Decisão

1. **Registro explícito** no builder: uma instância pronta (`with_capability(SqlCapability(provider))`) ou uma classe construída a partir da configuração (`with_capability(SqlCapability, providers={...})`, que chama `from_config` com `[capabilities.<nome>]`).
2. **Nomes** únicos, em minúsculas (`[a-z][a-z0-9_]*`); o padrão é `default_name` da classe. Nome repetido é erro no `build()`. O mesmo tipo pode ser registrado mais de uma vez com nomes diferentes (dois bancos, por exemplo).
3. **Busca** por tipo, com nome quando houver ambiguidade: `ctx.capability(SqlCapability)` ou `ctx.capability(SqlCapability, "erp")`.
4. **Sem descoberta automática** no MVP. Uma descoberta futura por entry points exige RFC com lista de permissão na configuração, verificação de compatibilidade antes de carregar e documentação de que código no mesmo processo não pode ser isolado.
5. **Compatibilidade**:
   - o Core expõe `CORE_API_VERSION` (`"0.1"`);
   - uma Capability declara `core_api`; o registro falha se for incompatível (antes da 1.0, `major.minor` precisa ser igual; depois, mesmo major e minor menor ou igual);
   - cada pacote declara faixas de dependência (`orchestrator-core>=0.1,<0.2`);
   - a matriz fica em `docs/COMPATIBILITY.md` e é exercitada pela CI, que testa os pacotes juntos.

## Alternativas consideradas

- **Entry points sem lista de permissão.** Executa código de qualquer distribuição instalada que declare o grupo.
- **Versão única para todos os pacotes.** Impede releases independentes (ADR-0001).

## Consequências

- Trocar de Provider é mudar a configuração, desde que o consumidor tenha permitido aquele Provider no mapa `providers`.

## Referências

- `packages/orchestrator-core/tests/test_capabilities.py`; `docs/COMPATIBILITY.md`.
