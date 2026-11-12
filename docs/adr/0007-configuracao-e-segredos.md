# ADR-0007 — Configuração e segredos

| Campo | Valor |
|---|---|
| Status | Aceito |
| Data | 2026-11-12 |
| Decisão | D-08 |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## Contexto

Precedência, formato, validação e tratamento de segredos não estavam definidos.

## Decisão

1. **Precedência**, da menor para a maior: padrões embutidos, arquivo TOML (`with_config_file`), variáveis de ambiente (`with_environment`, prefixo `ORCHESTRATOR` por padrão) e valores explícitos (`with_settings`).
2. **Variáveis de ambiente**: `ORCHESTRATOR_<TABELA>__<CHAVE>`; `__` separa níveis; só variáveis com pelo menos um `__` são lidas; os nomes viram minúsculas.
3. **Tabelas reservadas**: `[runtime]` (do Core) e `[capabilities.<nome>]` (de cada Capability). Qualquer outra tabela pertence ao consumidor, acessível por `ctx.config.section("app")`.
4. **Validação** no `build()`: chaves desconhecidas nas tabelas reservadas são erro (pegam erros de digitação); toda mensagem cita a chave completa, como `capabilities.sql.timeout`.
5. **Segredos** nunca ficam em arquivo de configuração. A configuração guarda uma referência (`env:NOME`, `file:/caminho`); o valor é obtido no uso por `ctx.secrets.resolve(...)`, por resolvedores registrados por esquema (`with_secret_resolver`). Um cofre externo entra como resolvedor de um pacote Provider.
6. O valor resolvido vem dentro de `Secret`, que não aparece em `repr`, `str` nem formatação, não é serializável e é registrado para mascaramento em logs, eventos e registros. Valores com menos de 4 caracteres não são mascarados.
7. O Core não carrega arquivos `.env`.

## Alternativas consideradas

- **YAML.** Exige dependência (ADR-0005).
- **`.env` carregado pelo Core.** Exige dependência e facilita versionar segredos por engano.
- **Segredos literais aceitos com aviso.** Rejeitado: a referência literal é recusada, e a mensagem de erro nunca repete o valor.

## Consequências

- Teste com valor-sentinela: o segredo não aparece em logs de texto e JSON, eventos, registros nem no `repr` do resultado.
- A exceção original continua disponível em `result.error` para uso programático; quem a registrar em log por fora do Runtime deve usar os filtros de `orchestrator_core.logs`.

## Referências

- `packages/orchestrator-core/tests/test_config.py` e `test_secrets.py`; guia `docs/guides/configuracao.md`.
