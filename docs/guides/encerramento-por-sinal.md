# Encerramento por sinal

Como fazer um pedido de término do sistema operacional passar pelo teardown e pelo evento `ExecutionFinished`. Origem: [RFC-0005](../rfc/0005-core-0-2-subetapas-mascaramento-teardown-e-sinais.md), seção 2.4, e a resposta do responsável à pergunta 4 ("todas as automações deverão passar obrigatoriamente pelo evento Finished").

## O problema

O Core não instala tratadores de sinal: o processo pertence à aplicação, pelo mesmo princípio que impede o Core de configurar o logging ([ADR-0011](../adr/0011-observabilidade.md)). Sem tratador, `SIGTERM` encerra o processo na hora, sem `finalize`, sem registro e sem `ExecutionFinished` (diagnóstico, experimento EX1; reproduzido de novo em 2026-11-15: código de saída −15, nenhuma linha de teardown).

## A receita

No ponto de entrada do projeto consumidor, ligue os sinais de término ao `CancellationToken` da execução:

```python
import signal

from orchestrator_core import CancellationToken

token = CancellationToken()
signal.signal(signal.SIGTERM, lambda *_: token.cancel("SIGTERM"))
if hasattr(signal, "SIGBREAK"):  # Windows: Ctrl+Break
    signal.signal(signal.SIGBREAK, lambda *_: token.cancel("SIGBREAK"))
result = runtime.run(automacao, cancellation=token)
```

Os dois exemplos (`examples/hello-automation` e `examples/sales-report`) fazem isso em `__main__.py`, com `cancel_on_signals` e `restore_signals`, e devolvem os tratadores anteriores depois da execução.

O que acontece com a receita:

1. o sinal aciona o token;
2. a próxima chamada de `ctx.check()`, `ctx.sleep()` ou `ctx.retry()` da automação lança `ExecutionCancelledError` (`ctx.sleep` acorda na hora);
3. o teardown roda (`finalize`, `persist_logs`, `shutdown`), com orçamento próprio (`runtime.teardown_timeout`, 60 s por padrão; `0` desliga);
4. `ExecutionFinished` é publicado com status `cancelled`, e `token.reason` diz qual sinal chegou.

## O que a plataforma garante

| Encerramento | Teardown e `ExecutionFinished` |
|---|---|
| Sucesso, falha, cancelamento pelo token, prazo esgotado | Sim |
| `KeyboardInterrupt` (Ctrl+C), `SystemExit` | Sim; a exceção é relançada por `run()` depois do evento |
| `SIGTERM` (Linux, macOS) e Ctrl+Break (Windows), com a receita | Sim |
| `SIGTERM` sem a receita | Não |
| Encerramento forçado: `SIGKILL`, `TerminateProcess` no Windows (usado, por exemplo, por `taskkill /F`), queda de energia, `os._exit` | Não. Nada roda dentro do processo; nenhuma biblioteca consegue interceptar |

No Windows, `os.kill(pid, sinal)` e `Popen.send_signal` com qualquer sinal que não seja `CTRL_C_EVENT` ou `CTRL_BREAK_EVENT` chamam `TerminateProcess`. Para pedir o término de forma interceptável, crie o processo com `CREATE_NEW_PROCESS_GROUP` e envie `CTRL_BREAK_EVENT`.

## Limites

- `signal.signal` só funciona na thread principal.
- A automação precisa cooperar: uma chamada longa que não volta ao Python (driver, rede, aplicação externa) atrasa o cancelamento até retornar.
- Quem encerra o processo (supervisor, agendador, operador) deve esperar pelo menos `runtime.teardown_timeout` mais uma margem entre o pedido de término e um encerramento forçado. Com `teardown_timeout = 0`, o teardown não tem limite cooperativo.
- O que fazer com os sistemas abertos pela automação (fechar janelas, encerrar processos) continua sendo código do consumidor, em finalizers ou em `ctx.resources`. A subetapa padrão de "finalização dos sistemas" pedida pelo responsável ainda não tem escopo definido ([reconciliação](../audit/RFC_RESPONSE_RECONCILIATION.md), C28).

## Verificação

`packages/orchestrator-core/tests/test_signals.py` roda a receita num processo filho e envia `SIGTERM` (Linux) ou `CTRL_BREAK_EVENT` (Windows): o filho termina com código 0, status `cancelled`, finalizer executado e `ExecutionFinished` publicado. Verificado em Linux em 2026-11-15; no Windows, roda na CI.
