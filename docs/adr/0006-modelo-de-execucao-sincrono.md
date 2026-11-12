# ADR-0006 — Modelo de execução síncrono e concorrência

| Campo | Valor |
|---|---|
| Status | Aceito |
| Data | 2026-11-12 |
| Decisão | D-05 |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## Contexto

O scaffold trazia três runners (local, thread e processo) sem decisão registrada; o de processo travava com resultados grandes e ignorava o pipeline configurado (COD-03, COD-04).

## Decisão

1. O Core é síncrono. `Runtime.run` executa uma automação do início ao fim na thread que chama.
2. O Core não tem runners de thread nem de processo. Paralelismo entre execuções fica com quem chama (`ThreadPoolExecutor`, processos, agendadores). `Runtime` é imutável e seguro para chamadas concorrentes; cada execução tem contexto, recursos e handles próprios.
3. Cancelamento e prazo são cooperativos (RFC-0001). Não existe forma segura de interromper uma thread em Python; interrupção forçada fica com quem orquestra o processo.
4. `contextvars` é usado apenas para correlação de logs. O contexto é passado explicitamente; não há "contexto corrente" global.

## Alternativas consideradas

- **Core assíncrono (`asyncio`).** Oferece cancelamento nativo, mas impõe `async` a todo consumidor; o trabalho bloqueante comum em automação (drivers, navegadores, arquivos) continuaria em threads não canceláveis.
- **As duas APIs.** Dobra a superfície e os testes.

## Consequências

- Os contratos não impedem um Runtime assíncrono futuro, que exigiria RFC.
- Teste de estresse: 200 execuções sequenciais e 400 em 8 threads, sem compartilhamento de estado ou recursos.
- Contextvars não se propagam sozinhos para threads criadas pela automação; quem cria threads usa `contextvars.copy_context().run` para manter a correlação nos logs.

## Referências

- RFC-0001; `packages/orchestrator-core/tests/test_concurrency.py`.
