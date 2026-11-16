# RFC-0014 — Subetapas padrão: finalização do ciclo de vida e finalização de sistemas e processos

| Campo | Valor |
|---|---|
| Status | Proposta. Não aceita |
| Data | 2026-11-15 |
| Autor | Claude, a pedido do responsável |
| Decisor | Responsável pelo projeto (decisão pendente) |
| Origem | Decisão de encaminhamento de 2026-11-15: opção C para as subetapas padrão, que contempla as duas dimensões ([DECISIONS](../DECISIONS.md), seção 4); [RFC-0005](0005-core-0-2-subetapas-mascaramento-teardown-e-sinais.md), resposta 3 |
| Relacionadas | [RFC-0001](0001-ciclo-de-vida-da-execucao.md), [ADR-0004](../adr/0004-fronteiras-core-capability-provider.md), [ADR-0006](../adr/0006-modelo-de-execucao-sincrono.md), [ADR-0016](../adr/0016-escopo-futuro.md), [RFC-0004](0004-controles-reutilizaveis-escopo-e-sequencia.md) (DS-4, DS-5, DS-7) |

A decisão C autoriza contemplar as duas dimensões na arquitetura. Não autoriza encerrar processos sem contrato. Nada desta RFC está implementado.

## 1. Três coisas diferentes

| Conceito | O que é | Exemplo | Quem sabe fazer |
|---|---|---|---|
| Finalização do ciclo de vida | Os estágios de teardown do Runtime: `finalize` (finalizers e liberação de recursos), `persist_logs`, `shutdown`, e o evento `ExecutionFinished` no fim | Confirmar ou desfazer uma transação; fechar a sessão SQL; entregar o registro | Core |
| Finalização de um sistema | Encerrar o uso de um sistema externo pela via dele: sair de uma sessão, fechar um documento, fechar a aplicação pela sua própria interface | Logout de um ERP; fechar o navegador; fechar uma planilha sem salvar | Quem abriu: uma Capability ou o consumidor |
| Encerramento de um processo | Pedir ao sistema operacional que um processo termine e, se ele não responder, forçar o término | Processo de uma aplicação que travou depois do logout | Sistema operacional, para processos que a execução possui |

Fechar uma aplicação pela interface é finalizar um sistema; matar o processo dela é encerrar um processo. Os dois podem ser necessários na mesma execução, nessa ordem.

## 2. O que existe na 0.2.0 (verificado no código em 2026-11-15)

- `finalize` executa os finalizers em ordem inversa, com o desfecho provisório (inclusive `error_info`), e depois libera os recursos de `ctx.resources`, também em ordem inversa. Toda limpeza roda, mesmo se outra falhar.
- Os erros do estágio são agregados: um erro é relançado; vários viram `ExceptionGroup`. O estágio entra no registro com status, duração e erro mascarado. Um erro de teardown torna `failed` uma execução bem-sucedida.
- Subetapas abertas por finalizers e limpezas entram no registro com `stage = "finalize"`.
- O teardown tem orçamento próprio (`runtime.teardown_timeout`).
- `ExecutionFinished` é publicado depois de todo o pipeline, em todo encerramento que passa por `Runtime.run` (guia [Encerramento por sinal](../guides/encerramento-por-sinal.md)).

Lacunas, verificadas por experimento:

| # | Lacuna | Evidência |
|---|---|---|
| L1 | Com várias falhas no `finalize`, o registro mostra só a mensagem do grupo | Três limpezas com erro produzem, no registro, `ExceptionGroup: 3 errors in stage 'finalize' (3 sub-exceptions)`; os três erros só existem no objeto `result.teardown_errors`, que não é serializado |
| L2 | Não há status nem duração por finalizer ou limpeza | O registro tem uma linha para o estágio inteiro |
| L3 | Finalizers e limpezas não têm nome | Não dá para saber, pelo registro, qual sistema não fechou |
| L4 | Não há noção de processo pertencente à execução | Nenhuma API registra processos iniciados pela automação; nada os encerra |

## 3. Proposta para a finalização do ciclo de vida

### 3.1 Nomes opcionais em finalizers e limpezas

```python
ctx.add_finalizer(confirmar_lote, step="confirmar_lote")
ctx.resources.callback(navegador.close, step="fechar_navegador")
ctx.resources.enter(sessao_erp, step="logout_erp")
```

Com `step=`, o Core executa a operação dentro de uma subetapa com esse nome: status, duração e erro mascarado entram no registro, nos eventos e nos logs. Sem `step=`, o comportamento é o da 0.2.0. Os nomes seguem a regra das subetapas e nunca contêm dados de negócio.

### 3.2 Subetapas padrão do Core

O Core passa a registrar duas subetapas no `finalize`, quando houver o que executar:

| Nome proposto | Conteúdo |
|---|---|
| `orchestrator_finalizers` | Todos os finalizers, em ordem inversa; as subetapas nomeadas ficam dentro dela |
| `orchestrator_resources` | Toda a liberação de recursos, em ordem inversa; idem |

O prefixo `orchestrator_` passa a ser reservado: `ctx.step("orchestrator_...")` chamado pelo consumidor é recusado. Alternativas ao prefixo: `platform_`, ou nenhum nome reservado, com as subetapas padrão marcadas por um campo `origin = "platform"` no registro.

### 3.3 Erros agrupados no registro

`ErrorInfo` ganha `errors: tuple[ErrorInfo, ...]`, preenchido para `ExceptionGroup` e `BaseExceptionGroup`, com cada erro mascarado. Resolve L1 também para estágios customizados.

### 3.4 O que não muda

Ordem dos estágios, semântica de falha da RFC-0001, orçamento de teardown e `ExecutionFinished` como último evento. Nenhum evento novo: as subetapas usam `StepStarted` e `StepFinished`.

## 4. Proposta para a finalização de sistemas e processos

### 4.1 Sistemas

Não precisa de port novo. Quem abre o sistema registra o fechamento em `ctx.resources`, com o nome da seção 3.1. As Capabilities de acesso que vierem (navegador, desktop, HTTP) seguem a mesma regra, com nomes padronizados por Capability (por exemplo, `fechar_navegador`). O fluxo continua no código do consumidor: o Core não decide o que fechar nem em que ordem, além da ordem inversa de registro.

### 4.2 Processos

Proposta: uma Capability própria, só com a biblioteca padrão (nome pela DS-4, por exemplo `orchestrator-processes`), e não o Core. Motivos: o Core continua pequeno (ADR-0004), e o controle de processos tem código específico de cada sistema operacional.

Contrato em esboço:

```python
processos = ctx.capability(ProcessCapability)
excel = processos.start(["excel.exe", arquivo], name="excel", grace=10.0)
...  # a automação usa o sistema
# no finalize, dentro de "orchestrator_resources": pedir término, esperar "grace", forçar
```

| Regra | Proposta |
|---|---|
| Posse | Só processos iniciados pela Capability, ou adotados explicitamente a partir de um objeto `Popen` da própria execução. Nunca por nome ou por padrão de linha de comando |
| Árvore de processos | Windows: Job Object com encerramento dos membros quando o job é fechado (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`), via `ctypes`. Linux: grupo de processos próprio (`start_new_session=True`) e sinal para o grupo. Processos que saem do grupo ou do job por conta própria não são acompanhados, e isso fica documentado |
| Reuso de PID | A Capability guarda o identificador do processo junto com o handle do Windows ou o objeto `Popen`; nunca reencontra o processo só pelo número |
| Término | Pedido de término (`SIGTERM` no Linux; `CTRL_BREAK_EVENT` para processos de console criados num grupo próprio, no Windows), espera de `grace` e, só então, término forçado da árvore. Fechar janelas de aplicações gráficas por mensagem (`WM_CLOSE`) fica para uma segunda fase |
| Tempo | `grace` por processo, limitado pelo orçamento de teardown quando ele estiver ativo |
| Registro | Uma subetapa por processo, com o nome dado em `start`; o término forçado aparece no log e numa métrica (por exemplo, `orchestrator.processes.forced`) |
| Falha | Processo que não terminou nem à força: erro de teardown (a execução bem-sucedida termina `failed`), conforme a RFC-0001. Alternativa: só aviso, se o responsável preferir |

Fica fora, por exigir contrato e autorização explícitos: encerrar processos que a execução não iniciou, como o costume de automações de interface de encerrar todos os processos de uma aplicação pelo nome, no início ou no fim. Em máquina compartilhada isso encerra o trabalho de outra pessoa ou de outra execução. Se for necessário em máquinas dedicadas, entra como política explícita, desligada por padrão, limitada ao usuário da sessão da automação e registrada no log (pergunta 5).

## 5. Compatibilidade e governança

- 3.1 a 3.3 mudam a API pública do Core: RFC-0002, teste da lista pública, CHANGELOG e matriz de compatibilidade. Pela ADR-0009, isso leva à API `0.3` e a novas versões de `orchestrator-sql` e `orchestrator-sqlite`, mesmo sem mudança funcional neles (DS-2). Convém juntar com a próxima mudança do Core.
- 4.2 é um pacote novo e começa por esta RFC aceita; sem dependência de terceiros, a DS-3 não se aplica, mas a DS-4 (nome) sim.
- Encerramento de processos envolve o pipeline de execução e exige revisão arquitetural de segurança no PR (`GOVERNANCE.md`, seção 9).

## 6. Perguntas para decisão

1. Prefixo reservado para as subetapas padrão: `orchestrator_`, `platform_` ou um campo de origem no registro?
    R: PA[NUMERO DE IDENTIFICAÇÃO DA AUTOMAÇÃO] (EX: PA0001, PA0002). O número de identificação deve ser parametrizavel e configurado à parte
2. As subetapas padrão aparecem sempre, ou só quando houver finalizers ou recursos?
    R: Sempre aparecem
3. O nome em `step=` é opcional para todos ou obrigatório para Capabilities da plataforma?
    R: obrigatório
4. Que processos as automações iniciam hoje (aplicações gráficas, ferramentas de console, navegadores) e em que sistemas operacionais?
    R: Deverão ter incluidos Web e Desktop
5. É preciso encerrar processos pelo nome em máquinas dedicadas? Se sim, com que limites.
    R: Na maquina de execução atual, sem limites
6. Término forçado depois do tempo de espera é aceitável? Qual o tempo padrão?
    R: Por padrão 1 min, mas deve ser parametrizável e configurável à parte, tendo o timeout uma mensagem de retorno e logs
7. Processo que não termina deve falhar a execução ou só gerar aviso?
    R: Deve ser controlado o tempo pela fila do item, o timeout deve ser unitário e ser adicionado um tentativa no item. Sem avisos para atrasos sem erros confirmados

## 7. Critérios de aceite e testes, se aceita

- Registro com uma subetapa por finalizer e por limpeza nomeados, e com cada erro de um grupo.
- Processos de teste iniciados pela Capability terminam no `finalize` em Linux e Windows, inclusive filhos; com `grace` esgotado, o término forçado acontece e é registrado.
- Um processo irmão, não iniciado pela execução, continua vivo depois dela.
- O orçamento de teardown limita a espera.
- Cancelamento, prazo e `KeyboardInterrupt` durante a execução ainda encerram os processos possuídos.

## 8. Alternativas consideradas

| Alternativa | Avaliação |
|---|---|
| Controle de processos no Core | Mais simples de usar, mas traz código específico de sistema operacional para o núcleo, contra a ADR-0004 |
| `psutil` | Resolve árvore de processos e reuso de PID nos dois sistemas, mas é dependência de terceiros (DS-3) |
| Só documentar o padrão, sem pacote | Cada automação refaria o controle de posse e de árvore, que é a parte difícil |
| Subetapa padrão única, `finalize_systems`, sem nomes por operação | Não resolve L1 a L3: o registro continuaria sem dizer qual sistema falhou |

## Referências externas (consultadas em 2026-11-15)

- Microsoft Learn: [Job Objects](https://learn.microsoft.com/windows/win32/procthread/job-objects).
- Documentação do Python: [`subprocess`](https://docs.python.org/3/library/subprocess.html) e [`signal`](https://docs.python.org/3/library/signal.html).
