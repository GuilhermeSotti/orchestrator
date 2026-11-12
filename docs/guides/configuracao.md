# Configuração

Referência da configuração do Runtime. Decisão: [ADR-0007](../adr/0007-configuracao-e-segredos.md).

## Fontes e precedência

Da menor para a maior:

1. padrões do Core;
2. arquivo TOML, se informado (`RuntimeBuilder().with_config_file("orchestrator.toml")`);
3. variáveis de ambiente com prefixo (padrão `ORCHESTRATOR`; `with_environment(prefix=None)` desliga);
4. valores explícitos (`with_settings({...})`, que pode ser chamado várias vezes).

Variáveis de ambiente: `ORCHESTRATOR_<TABELA>__<CHAVE>`, com `__` entre os níveis. Exemplos:

| Variável | Chave |
|---|---|
| `ORCHESTRATOR_RUNTIME__TIMEOUT=30` | `runtime.timeout` |
| `ORCHESTRATOR_CAPABILITIES__SQL__DATABASE=vendas.db` | `capabilities.sql.database` |
| `ORCHESTRATOR_APP__REGIAO=Sul` | `app.regiao` |

Variáveis sem `__` depois do prefixo são ignoradas. Valores de variáveis chegam como texto e são convertidos pelos acessores tipados.

## Tabela `[runtime]`

| Chave | Tipo | Padrão | Significado |
|---|---|---|---|
| `name` | texto (1 a 64: letras, dígitos, `.`, `_`, `-`) | `orchestrator` | Nome do Runtime em logs, eventos e métricas |
| `timeout` | número > 0 | sem prazo | Prazo padrão de cada execução, em segundos |
| `workspace` | booleano | `false` | Cria uma pasta temporária privada por execução (`ctx.workspace`) |
| `workspace_root` | caminho | pasta temporária do sistema | Onde criar os workspaces |
| `keep_workspace` | booleano | `false` | Mantém o workspace depois da execução, para depuração |

Chaves desconhecidas em `[runtime]` são erro.

## Tabelas `[capabilities.<nome>]`

Uma por Capability registrada; o conteúdo é validado pela Capability. A SQL, por exemplo:

```toml
[capabilities.sql]
provider = "sqlite"
database = "dados/app.db"
timeout = 5.0
```

## Tabelas do consumidor

Qualquer outra tabela pertence ao projeto consumidor:

```toml
[app]
regiao = "Sul"
limite = 100
```

```python
secao = ctx.config.section("app")
regiao = secao.get_str("regiao")
limite = secao.get_int("limite", 50, minimum=1)
```

Acessores: `get_str`, `get_int`, `get_float`, `get_bool`, `get_path`, `get_choice`, `get_secret_ref`, `section`, `check_keys`. Todo erro cita a chave completa (`app.limite: must be >= 1`).

## Segredos

Segredos nunca ficam no arquivo. A configuração guarda uma referência, resolvida no uso:

```toml
[capabilities.erp]
password = "env:ERP_PASSWORD"     # ou "file:/run/secrets/erp"
```

```python
referencia = ctx.config.capability("erp").get_secret_ref("password")
senha = ctx.secrets.resolve(referencia)  # Secret; senha.reveal() devolve o valor
```

- Esquemas embutidos: `env:` (variável de ambiente) e `file:` (arquivo de texto UTF-8).
- Outros cofres entram com `with_secret_resolver("vault", MeuResolvedor())`.
- Um valor literal no lugar da referência é recusado, e a mensagem não repete o valor.
- O valor resolvido é mascarado (`***`) em logs com os filtros de `orchestrator_core.logs`, em eventos e nos registros de execução. Valores com menos de 4 caracteres não são mascarados.
