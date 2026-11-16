# RFC-0005 — Core 0.2: mascaramento público, orçamento de teardown, subetapas e encerramento por sinal

| Campo | Valor |
|---|---|
| Status | Aceita em 2026-11-15 pelo responsável |
| Data | 2026-11-14 |
| Autor | Claude, a pedido do responsável |
| Decisor | Responsável pelo projeto (aceite registrado em [DECISIONS](../DECISIONS.md), seção 5) |
| Implementação | 2026-11-15: partes 2.1 a 2.4 no `orchestrator-core` 0.2.0 (branch local `feature/core-0.2`, sem release), com as respostas da seção 8; implementação aprovada pelo responsável (DE-1); RFC aceita em 2026-11-15; subetapas padrão na RFC-0014. Detalhes: [reconciliação](../audit/RFC_RESPONSE_RECONCILIATION.md), seção 6 |
| Itens de escopo | 1 (ciclo de vida e finalização) e 2 (fluxo e subetapas) |
| Relacionadas | [RFC-0004](0004-controles-reutilizaveis-escopo-e-sequencia.md) (DS-2, DS-5); pré-requisito das RFCs [0007](0007-capability-de-notificacoes.md) e [0008](0008-capability-de-fila.md) |

## 1. Problema

O diagnóstico ([SCOPE_DIAGNOSIS](../audit/SCOPE_DIAGNOSIS.md)) confirmou, por leitura e por experimento, quatro lacunas no Core 0.1.0:

| Lacuna | Efeito |
|---|---|
| L8.4 — não há como mascarar texto fora do `logging` | Um finalizer recebe a exceção original; uma mensagem montada com `str(outcome.error)` pode levar um segredo para fora |
| L1.2 — `ctx.retry` e `ctx.sleep` lançam na hora quando usados no teardown depois de prazo ou cancelamento | Limpezas e avisos que precisam repetir uma operação falham justamente quando a execução foi interrompida; o teardown não tem prazo próprio |
| Item 2 — não existe subetapa dentro da automação | O consumidor não consegue registrar status, duração e erro de cada parte no registro da execução |
| L1.1 — sinais de término não chegam ao `CancellationToken` | Com `SIGTERM`, o processo morre sem teardown |

## 2. Proposta

Quatro partes independentes. O responsável pode aceitar cada uma separadamente.

### 2.1 Mascaramento público de texto

- `ExecutionContext.redact(text: str) -> str` devolve o texto com os segredos resolvidos trocados por `***`, pelo mesmo registro usado nos logs.
- `ExecutionOutcome.error_info: ErrorInfo | None` traz a descrição já mascarada do erro, para finalizers e estágios de teardown.

```python
def avisar(outcome: ExecutionOutcome) -> None:
    if outcome.error_info is not None:
        enviar(f"{outcome.error_info.type}: {outcome.error_info.message}")  # já mascarado
```

Limites: não substitui os filtros de logging; só mascara valores resolvidos pelo `SecretStore`. Partes derivadas de um segredo composto continuam fora (diagnóstico, L8.5; [RFC-0006](0006-segredos-cofres-e-credenciais-de-providers.md)).

### 2.2 Orçamento de teardown

- Nova chave `runtime.teardown_timeout`, em segundos. Padrão proposto: 30.
- Durante os estágios de teardown, `ctx.check()`, `ctx.sleep()`, `ctx.retry()` e `ctx.remaining()` passam a considerar só esse orçamento. A interrupção que já encerrou a execução não é relançada; esgotado o orçamento, lançam `ExecutionTimeoutError`.
- O orçamento é cooperativo, como o prazo da execução: código de teardown que não usa o contexto não é interrompido ([ADR-0006](../adr/0006-modelo-de-execucao-sincrono.md)).
- Consequências que precisam ser aceitas junto: a execução pode terminar até `teardown_timeout` segundos depois do seu prazo; um cancelamento pedido durante o teardown não o interrompe; e, no teardown, `ctx.sleep` deixa de acordar pelo token de cancelamento, que pode já estar acionado (sem isso, as esperas entre tentativas seriam zeradas).

Muda o comportamento: na 0.1.0, esses métodos lançam na hora quando a execução foi cancelada ou estourou o prazo, e, nos outros casos, seguem o prazo da execução.

### 2.3 Rastreamento de subetapas

```python
def conciliar(ctx: ExecutionContext) -> None:
    with ctx.step("baixar_extrato"):
        ...
    with ctx.step("conciliar_lancamentos"):
        ...
```

| Aspecto | Proposta |
|---|---|
| Nome | Mesma regra dos estágios (`[a-z][a-z0-9_]{0,63}`); pode repetir |
| Eventos | `StepStarted` e `StepFinished`, este com status, duração e erro mascarado |
| Desfecho | `ExecutionResult.steps` (`StepOutcome`, com a exceção original) e `ExecutionRecord.steps` (`StepRecord`, mascarado, incluído em `to_dict()`) |
| Status | Os de `ExecutionStatus`, pelo mesmo mapeamento de erro do Runtime |
| Falha | A exceção é registrada e relançada sem alteração. A plataforma não captura, não repete e não pula |
| Aninhamento | Permitido; cada subetapa registra o nome da que a contém |
| Logs | Campo `step` nos registros (`ExecutionContextFilter`, `JsonFormatter`); `TEXT_FORMAT` não muda |
| Métrica | `orchestrator.step.duration_seconds`, com `runtime`, `step` e `status` |
| Limite | `runtime.max_steps`, padrão proposto 1000. Acima dele, eventos e métricas continuam, o registro para de crescer e marca `steps_truncated` |
| Threads | Aceitas. O aninhamento segue `contextvars`, como a correlação de logs: uma thread criada pela automação precisa de `contextvars.copy_context().run` para herdar a subetapa corrente (ADR-0006) |

Não entra: definição declarativa, dependência entre subetapas, paralelismo gerenciado, repetição, pulo, checkpoint e retomada ([ADR-0016](../adr/0016-escopo-futuro.md), [ADR-0003](../adr/0003-api-publica-biblioteca.md)). A ordem das partes continua sendo o código do consumidor.

Por que no Core: o registro da execução, a correlação dos logs e o mascaramento pertencem ao Core. Um pacote separado só conseguiria publicar eventos próprios, e as subetapas ficariam fora do `ExecutionRecord`.

### 2.4 Encerramento por sinal

Sem mudança de API. Um guia novo e os dois exemplos passam a ligar os sinais ao token no ponto de entrada:

```python
token = CancellationToken()
signal.signal(signal.SIGTERM, lambda *_: token.cancel("SIGTERM"))
if hasattr(signal, "SIGBREAK"):  # Windows: Ctrl+Break
    signal.signal(signal.SIGBREAK, lambda *_: token.cancel("SIGBREAK"))
result = runtime.run(automacao, cancellation=token)
```

O Core não instala tratadores de sinal, pelo mesmo princípio que o impede de configurar o logging ([ADR-0011](../adr/0011-observabilidade.md)): o processo pertence à aplicação. O guia registra os limites: tratadores só na thread principal; a automação precisa cooperar com `ctx.check()` ou `ctx.sleep()`; em Windows, um encerramento por `TerminateProcess` não pode ser interceptado; `SIGINT` já é tratado como `KeyboardInterrupt`.

Um utilitário público (`cancel_on_signals(token)`) só se justifica se dois ou mais consumidores copiarem a receita.

## 3. API pública resultante

Acréscimos à lista da [RFC-0002](0002-escopo-do-mvp-e-api-publica.md), se as quatro partes forem aceitas:

- `ExecutionContext.redact` e `ExecutionContext.step`;
- `ExecutionOutcome.error_info`;
- `StepStarted`, `StepFinished`, `StepOutcome`, `StepRecord`;
- `ExecutionResult.steps`, `ExecutionRecord.steps` e `ExecutionRecord.steps_truncated`;
- `RuntimeSettings.teardown_timeout` e `RuntimeSettings.max_steps`, com as chaves de `[runtime]`;
- campo `step` em `orchestrator_core.logs`; métrica `orchestrator.step.duration_seconds`;
- `CORE_API_VERSION = "0.2"`.

## 4. Compatibilidade

- `orchestrator-core` 0.2.0. Pela regra atual ([ADR-0009](../adr/0009-registro-de-capabilities-e-compatibilidade.md), item 5), `orchestrator-sql` e `orchestrator-sqlite` também precisam de uma 0.2.0, com `core_api = "0.2"` e faixa `>=0.2,<0.3`, mesmo sem mudança funcional (RFC-0004, DS-2).
- Mudanças de comportamento: métodos do contexto durante o teardown (2.2); chaves novas em `ExecutionRecord.to_dict()`; atributo `step` nos registros de log.
- Documentos a atualizar: RFC-0002 (lista), RFC-0001 (seções 5 e 6), `tests/test_public_api.py`, CHANGELOG do Core, `docs/COMPATIBILITY.md` e o guia de configuração.

## 5. Segurança

- `redact` reduz o risco de vazamento em saídas fora do logging; não cobre valores derivados.
- Nomes de subetapas são identificadores de código, validados; nunca recebem dados de negócio.
- A mudança toca o pipeline de execução e exige revisão arquitetural de segurança no PR (`GOVERNANCE.md`, seção 9).

## 6. Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Expor o relógio (`ctx.clock`) e deixar cada Capability limitar o próprio teardown | Cada Capability reimplementaria o limite; sem orçamento comum, os tempos se somam |
| Subetapas num pacote `orchestrator-steps` | Mantém o Core intacto, mas as subetapas ficam fora do registro e da correlação de logs. É a opção certa se o consumidor só precisar de eventos |
| Estágio do pipeline por subetapa (`with_stage`) | Estágios são do Runtime e valem para todas as automações; não descrevem partes de uma automação |
| O Core instalar os tratadores de sinal | Altera o processo da aplicação sem pedido explícito |
| Runner que executa a automação em outro processo, com interrupção forçada | Excluído pela ADR-0006; exige RFC própria com caso real |

## 7. Critérios de aceite e testes

Os da RFC-0004, seção 5 (E7.3 a E7.7), mais:

- 2.1: o teste do valor-sentinela (`test_secrets.py`) passa a cobrir finalizer e estágio de teardown;
- 2.2: a matriz de falha (`test_pipeline.py::test_failure_matrix`) continua passando sem alteração de expectativa para quem não usa o contexto no teardown;
- 2.3: estresse com 8 threads e subetapas aninhadas, sem mistura entre execuções;
- 2.4: teste em subprocesso, em Linux e em Windows, na CI.

## 8. Perguntas abertas

1. Valor padrão de `teardown_timeout` e se zero desliga o limite. 
    R: O valor deverá ser parametrizável, permitindo que cada automação configure seu próprio orçamento de tempo para o teardown. O valor padrão deverá ser de 60 segundos. O limite poderá ser desligado se for 0
2. Subetapas: o limite padrão e se o aninhamento é necessário na primeira versão.
    R: O limite de subetapas deverá ser parametrizável, com valor padrão de 1.000 etapas. O suporte a subetapas aninhadas deverá estar disponível desde a primeira versão, pois essa funcionalidade é necessária.
3. O primeiro consumidor precisa das subetapas no registro, ou eventos bastam? A resposta decide entre Core e pacote (seção 6).
    R: O registro das subetapas será sempre necessário. Não basta disponibilizar essas informações apenas por meio de eventos: elas deverão fazer parte dos registros da execução.

    Além disso, algumas subetapas deverão estar previamente definidas, incluindo subetapas padrão da plataforma. Um exemplo é a subetapa responsável pela finalização dos sistemas, que deverá estar associada ao evento Finished.
4. Como as automações são interrompidas em produção. Em Windows, isso define o alcance real de 2.4.
    R: Todas as automações deverão passar obrigatoriamente pelo evento Finished durante seu processo de finalização. O encerramento deverá respeitar esse fluxo, garantindo que o evento seja executado como parte obrigatória da finalização da automação.

**Condições de aceite.** 2.1 e 2.2 fecham lacunas verificadas e têm consumidor previsto nas RFCs 0007 e 0008; devem entrar junto com o primeiro deles. 2.3 depende de um caso real que precise do desfecho por subetapa. 2.4 depende só da decisão.
