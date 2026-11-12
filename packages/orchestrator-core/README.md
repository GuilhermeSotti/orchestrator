# orchestrator-core

Núcleo da plataforma Orchestrator: o **Runtime** que executa automações pelo **Execution Pipeline** de oito estágios, o **Execution Context** de cada execução e os contratos que **Capabilities** e **Providers** implementam.

- Python 3.13 ou superior.
- Nenhuma dependência além da biblioteca padrão ([ADR-0005](../../docs/adr/0005-dependencias-do-core.md)).
- Tipado (`py.typed`), verificado com MyPy em modo estrito.

A lógica de negócio fica no projeto consumidor. O Core fornece o ciclo de vida, a configuração, o registro de Capabilities, logging com correlação e mascaramento de segredos, eventos, métricas, retry explícito, cancelamento e prazo.

## Uso

```python
from orchestrator_core import ExecutionContext, RetryPolicy, RuntimeBuilder
from orchestrator_core.logs import configure_logging


def conciliar_faturas(ctx: ExecutionContext) -> int:
    """Lógica de negócio do projeto consumidor."""
    ctx.logger.info("conciliando o dia %s", ctx.parameters["dia"])
    total = ctx.retry(lambda: 42, RetryPolicy.exponential(max_attempts=3), name="buscar-faturas")
    ctx.check()  # coopera com cancelamento e timeout
    return total


configure_logging("INFO")
runtime = (
    RuntimeBuilder()
    .with_config_file("orchestrator.toml")  # opcional
    .with_settings({"runtime": {"name": "faturas", "timeout": 300}})
    .build()
)
result = runtime.run(conciliar_faturas, parameters={"dia": "2026-11-12"})
result.raise_for_status()
print(result.output, result.duration)
```

## Ciclo de vida

| Fase | Estágios | Comportamento em falha |
|---|---|---|
| Preparação | `initialize`, `provision_dependencies`, `prepare_environment`, `prepare_execution` | Os estágios seguintes de preparação e a execução não rodam |
| Execução | `execute_automation` | Não roda se a preparação falhou |
| Teardown | `finalize`, `persist_logs`, `shutdown` | Sempre roda; erros são agregados e não mascaram o erro primário |

`Runtime.run` nunca lança exceção por falha da automação ou de um estágio: o resultado traz `status` (`succeeded`, `failed`, `cancelled`, `timed_out`), o desfecho de cada estágio e o erro original. `KeyboardInterrupt` e `SystemExit` são relançados depois do teardown. A semântica completa está na [RFC-0001](../../docs/rfc/0001-ciclo-de-vida-da-execucao.md).

## Superfície pública

Os nomes exportados por `orchestrator_core`, `orchestrator_core.logs` e `orchestrator_core.testing` formam a API pública, listada na [RFC-0002](../../docs/rfc/0002-escopo-do-mvp-e-api-publica.md). Módulos com nome iniciado por `_` são internos.

## Escrevendo uma Capability

Veja o [guia de Capabilities e Providers](../../docs/guides/capabilities-e-providers.md). O módulo `orchestrator_core.testing` oferece relógio falso, métricas e eventos em memória e `check_capability_conformance`.

## Licença

MIT. Veja [LICENSE](LICENSE).
