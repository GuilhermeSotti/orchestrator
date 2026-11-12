# Primeiros passos

Como usar o Orchestrator num projeto consumidor. Exemplos completos: [`examples/hello-automation`](../../examples/hello-automation) (só o Core) e [`examples/sales-report`](../../examples/sales-report) (Core, Capability SQL e Provider SQLite).

## 1. Instalar

Enquanto não houver índice de pacotes ([RFC-0002](../rfc/0002-escopo-do-mvp-e-api-publica.md)), instale a partir deste repositório:

```powershell
python -m pip install -e packages\orchestrator-core
python -m pip install -e packages\orchestrator-sql -e packages\orchestrator-sqlite   # se usar SQL
```

## 2. Escrever a automação

A automação é uma função que recebe o `ExecutionContext`. A lógica de negócio fica nela, no seu projeto.

```python
from orchestrator_core import ExecutionContext


def conciliar(ctx: ExecutionContext) -> dict[str, int]:
    dia = ctx.parameters["dia"]
    ctx.logger.info("conciliando %s", dia)
    for lote in range(3):
        ctx.check()  # coopera com cancelamento e prazo
        ...
    return {"lotes": 3}
```

## 3. Compor o Runtime e executar

```python
from orchestrator_core import RuntimeBuilder
from orchestrator_core.logs import configure_logging

configure_logging("INFO")  # opcional; json_output=True para JSON
runtime = RuntimeBuilder().with_config_file("orchestrator.toml").build()
result = runtime.run(conciliar, parameters={"dia": "2026-11-12"}, timeout=300)

if not result.succeeded:
    print(result.status, result.record.error)
result.raise_for_status()  # ou lance ExecutionFailedError
```

`run()` não lança exceção quando a automação falha: o resultado traz o status, o erro original, o desfecho de cada estágio e um registro mascarado (`result.record.to_dict()`).

## 4. Validar parâmetros

Passe um validador; ele roda no estágio `prepare_execution`, antes da automação. Pydantic funciona diretamente:

```python
from pydantic import BaseModel


class Parametros(BaseModel):
    dia: str
    limite: int = 100


result = runtime.run(
    conciliar, parameters={"dia": "2026-11-12"}, parameters_validator=Parametros.model_validate
)
# na automação: ctx.parameters_as(Parametros).limite
```

## 5. Usar recursos com segurança

```python
def automacao(ctx: ExecutionContext) -> None:
    arquivo = ctx.resources.enter(open("saida.txt", "w"))  # fechado no finalize
    ctx.add_finalizer(lambda desfecho: notificar(desfecho.status))
    token = ctx.secrets.resolve("env:API_TOKEN")  # Secret; use token.reveal()
    ctx.retry(lambda: chamar_api(token.reveal()), RetryPolicy.exponential(4), name="api")
```

## 6. Testar

```python
from orchestrator_core import RuntimeBuilder
from orchestrator_core.testing import FakeClock, InMemoryMetrics


def test_conciliar() -> None:
    runtime = RuntimeBuilder().with_environment({}, prefix=None).with_clock(FakeClock()).build()
    result = runtime.run(conciliar, parameters={"dia": "2026-11-12"})
    assert result.output == {"lotes": 3}
```

`with_environment({}, prefix=None)` isola o teste das variáveis `ORCHESTRATOR_*` da máquina.

Próximos passos: [configuração](configuracao.md) e [Capabilities e Providers](capabilities-e-providers.md).
