# RFC-0008 — Capability de fila e Provider SQL

| Campo | Valor |
|---|---|
| Status | Aceita em 2026-11-15 pelo responsável |
| Data | 2026-11-14 |
| Autor | Claude, a pedido do responsável |
| Decisor | Responsável pelo projeto (aceite registrado em [DECISIONS](../DECISIONS.md), seção 5) |
| Item de escopo | 3 (controle de fila) |
| Relacionadas | [ADR-0019](../adr/0019-convencoes-de-fila-fora-da-plataforma.md) (exige esta RFC), [RFC-0003](0003-capability-sql.md), [RFC-0004](0004-controles-reutilizaveis-escopo-e-sequencia.md) (DS-1), [RFC-0005](0005-core-0-2-subetapas-mascaramento-teardown-e-sinais.md) (2.2), [RFC-0006](0006-segredos-cofres-e-credenciais-de-providers.md) (2.1) |

## 1. Problema e caso de uso

O responsável quer contratos genéricos para adquirir, processar, concluir e tratar falhas de itens de fila, com Providers para tecnologias diferentes e SQL como possível Provider, sem impor tabelas, colunas, estados ou nomes de um consumidor.

O scaffold de julho de 2026 mostra que existe um consumidor com fila em tabelas SQL; as convenções dele ficaram fora da plataforma (ADR-0019) e não são usadas aqui. A estrutura real da fila, a concorrência esperada e as regras de tentativa não são conhecidas (seção 11). Por isso esta RFC fixa a forma do contrato e deixa as políticas em aberto, para decidir "somente conforme requisitos concretos".

## 2. O que a Capability é e o que não é

É o lado do **consumo** de uma fila de trabalho: uma execução adquire um item, processa e registra o desfecho.

Não é: produtor de itens (só entra com caso real), agendador, despachante, pool de trabalhadores nem execução distribuída. Uma execução processa os seus itens em sequência; paralelismo é mais de uma execução, iniciada por quem chama ([ADR-0006](../adr/0006-modelo-de-execucao-sincrono.md)).

## 3. Contrato funcional

Pacote `orchestrator-queue`, que depende só do Core.

```python
from orchestrator_queue import InvalidItemError, QueueCapability


def processar_itens(ctx: ExecutionContext) -> int:
    fila = ctx.capability(QueueCapability)
    concluidos = 0
    # adquire um item por vez; para em fila vazia, no limite, no cancelamento ou no prazo
    for item in fila.items(limit=100):
        with item:  # sucesso: concluído; exceção: falha registrada
            if not item_valido(item.payload):  # regra do consumidor
                raise InvalidItemError("<motivo>")
            processar(item.payload)  # lógica do consumidor
            concluidos += 1
    return concluidos
```

| Nome | Papel |
|---|---|
| `WorkItem` | `id`, `payload` (mapeamento somente leitura, opaco para a plataforma), `attempt` e `reference` opcional |
| `WorkQueue.acquire()` | Adquire o próximo item disponível, ou `None` |
| `WorkQueue.complete(item, *, output=None)` | Marca como concluído |
| `WorkQueue.fail(item, error, *, retry)` | Registra a falha; com `retry=True`, o item volta a ficar disponível enquanto houver tentativas |
| `WorkQueue.reject(item, reason)` | Marca como inválido; nunca é tentado de novo |
| `WorkQueue.release(item)` | Devolve sem contar tentativa |
| `WorkQueue.renew(item)` | Prorroga o lease, quando houver; chamada pela automação em processamentos longos. Sem threads de fundo (ADR-0006) |
| `WorkQueue.items(limit=None)` | Iteração que adquire um item por vez e verifica `ctx.check()` entre eles |

Estados lógicos: `pending`, `in_progress`, `completed`, `failed` e `invalid`. O valor físico de cada um é do Provider e do consumidor.

Classificação proposta dentro de `with item:`:

| O que acontece | Desfecho do item |
|---|---|
| O bloco termina sem erro | `complete` |
| `InvalidItemError` | `reject` |
| Erro com `retryable = True` e tentativas restantes | `fail` com `retry=True` |
| Qualquer outro erro | `fail` com `retry=False` |
| Cancelamento ou prazo | `release` |

Depois de registrar o desfecho, a exceção é **relançada**: nada é engolido por padrão. Continuar para o próximo item é escolha explícita: com `fila.items(on_error="continue")`, o `with item:` registra o desfecho e suprime a exceção do item. Cancelamento, prazo e exceções que não derivam de `Exception` nunca são suprimidos.

## 4. Garantias e ciclo de vida

| Tema | Proposta |
|---|---|
| Exclusividade | Um item nunca tem dois detentores ao mesmo tempo |
| Entrega | Pelo menos uma vez, quando há novas tentativas ou lease. O efeito "exatamente uma vez" exige processamento idempotente do consumidor |
| Lease | Opcional (`lease_seconds`). Sem lease, um item de execução morta fica `in_progress` até uma recuperação explícita. Com lease, volta a ficar disponível quando o prazo vence; o detentor antigo que tentar concluir recebe `LeaseLostError` |
| Tentativas | `max_attempts` explícito; padrão 1, sem nova tentativa ([ADR-0010](../adr/0010-retry-explicito.md)) |
| Ordenação | Definida pelo Provider a partir do que o consumidor informar; sem ordenação informada, não há garantia |
| Finalização | O handle registra um finalizer: todo item ainda detido no `finalize` é devolvido. Nenhum item fica `in_progress` por falha, cancelamento ou prazo da execução, a menos que a própria devolução falhe; nesse caso o erro vira erro de teardown e o item depende do lease ou de recuperação. Repetir a devolução numa falha transitória usa o orçamento de teardown (RFC-0005, 2.2) |
| Observabilidade | Eventos `QueueItemAcquired` e `QueueItemFinished`; métrica `orchestrator.queue.items` por fila e desfecho; logs com o `id` do item, nunca o `payload` |

## 5. Port do Provider

`QueueProvider`: `from_config(section, **options)`, `verify()` e `open(ctx)`, que devolve o backend da execução.

Backend: `claim(owner, lease_seconds)`, `complete(claim, output)`, `fail(claim, error, final, retry_after)`, `reject(claim, reason)`, `release(claim)`, `renew(claim, lease_seconds)` e `close()`. O `claim` carrega um token que impede um detentor antigo de alterar um item readquirido.

O pacote publica `orchestrator_queue.testing`: um Provider em memória e a suíte `QueueProviderContract` (exclusividade sob concorrência, transições, contagem de tentativas, vencimento de lease com relógio injetado, devolução no `finalize`).

## 6. Provider SQL (`orchestrator-queue-sql`)

- Depende de `orchestrator-queue` e de `orchestrator-sql` (RFC-0004, DS-1). Usa a sessão de um registro de `SqlCapability` nomeado na sua configuração, obtida por `ctx.capability(SqlCapability, nome)`. Recomenda-se um registro próprio para a fila, separado do usado pela automação, para que o estado da fila não entre nas transações de negócio.
- **Nenhum nome é fixo no pacote.** Tabela, colunas, valores dos estados, colunas do `payload` e ordenação vêm de um mapa fornecido pelo consumidor, validado com `validate_identifier`. Não há valores padrão para eles.
- Aquisição atômica por atualização condicionada ao estado, verificada pelo número de linhas afetadas; portável entre dialetos. Depende de o driver informar corretamente as linhas afetadas, o que a suíte de conformidade verifica. Otimizações por dialeto ficam para depois.
- Colunas opcionais (detentor, vencimento do lease, tentativas, erro) habilitam os recursos correspondentes; sem a coluna, o recurso fica desligado, com erro claro se for pedido.
- A plataforma não cria nem altera a tabela.

```toml
[capabilities.queue]
provider = "sql"
sql = "fila_db"  # nome do registro de SqlCapability
max_attempts = 3  # valores ilustrativos; os reais vêm do caso de uso
lease_seconds = 900
# tabela, colunas e estados: fornecidos pelo consumidor, em código ou nesta tabela
```

Pré-requisitos em `orchestrator-sql`: limite de linhas em `select` (hoje ausente) e caminho para credenciais (RFC-0006, 2.1). Para uso real falta também o segundo Provider SQL (roadmap, E4.4).

## 7. Segurança e privacidade

- O `payload` pode conter dados pessoais: nunca vai para logs, eventos ou métricas.
- O texto do erro gravado na fila é mascarado (RFC-0005, 2.1) e truncado.
- Identificadores do mapa são validados e citados; valores sempre como parâmetros (RFC-0003).
- O Provider usa o usuário de banco configurado para a sessão; recomenda-se permissão só sobre a tabela da fila.

## 8. Compatibilidade

Pacotes novos. `orchestrator-queue` funciona com o Core 0.1, mas só com o Core 0.2 consegue repetir a devolução de itens no teardown depois de prazo ou cancelamento (RFC-0005, 2.2); como a release 0.2 vem antes na sequência (RFC-0004, E7.7), a dependência proposta é do Core 0.2. `orchestrator-queue-sql` depende de `orchestrator-sql` com limite de linhas. Nenhuma mudança na ADR-0019: as convenções do consumidor continuam fora, agora como um mapa que ele fornece ou publica num pacote da organização.

## 9. Alternativas consideradas

| Alternativa | Avaliação |
|---|---|
| Utilitários de fila dentro de `orchestrator-sql` | Rejeitada pela ADR-0019 e pela RFC-0003, seção 6 |
| Cada consumidor escreve o SQL da sua fila | É a situação atual; duplica a parte difícil (exclusividade, devolução no `finalize`, recuperação) |
| Só Providers de mensageria (filas de nuvem, brokers) | O caso conhecido é fila em tabela; o contrato proposto não impede esses Providers depois |
| Provider SQL com conexão própria | Duplicaria configuração e credenciais que a Capability SQL já resolve |
| Engolir a exceção do item por padrão | Esconde falhas; a continuação deve ser pedida |

## 10. Critérios de aceite e testes

Os da RFC-0004, seção 5 (E7.15, E7.17 e E7.18), mais:

- 8 threads adquirindo de uma fila de 1000 itens: cada item entregue exatamente a um detentor;
- matriz de desfechos da seção 3, incluindo cancelamento e prazo no meio de um item;
- execução interrompida com item detido: o item volta a `pending` no `finalize`;
- a suíte do Provider SQL roda com dois mapas diferentes de tabela, colunas e estados, para provar que nenhum nome é fixo;
- `check_capability_conformance` aprovada.

## 11. Perguntas abertas

1. Estrutura da tabela real, sem dados: colunas, estados, índices.

R: A estrutura de referência da tabela de fila deverá seguir o modelo abaixo. O nome da tabela será composto pelo prefixo fila_ seguido do nome da subetapa correspondente.

Tabela de exemplo: fila_[NOME SUBETAPA]
Coluna	Tipo	Configuração original
fila_[NOME SUBETAPA]_id	int	Unchecked
[ID DE EXECUÇÃO]	int	Unchecked
hora_insercao	datetime	Unchecked
hora_inicio	datetime	Checked
hora_fim	datetime	Checked
tentativas	int	Unchecked
status	varchar(15)	Unchecked
observacao	varchar(MAX)	Checked
idfluxosexec	int	Checked
usuario	varchar(50)	Checked
hostname	varchar(50)	Checked

Os estados utilizados como referência são Pendente e Processando, conforme a lógica de captura apresentada na resposta da pergunta 4. A estrutura não deverá ser fixa na plataforma: deverá permitir a configuração dos nomes das tabelas e colunas conforme cada projeto consumidor.

Não foi especificada uma definição de índices nesta resposta.

2. Quem insere os itens; a plataforma precisa do lado produtor?

R: A inserção dos itens na fila será realizada por uma subetapa criada pelo desenvolvedor da automação. Para isso, a Capability de fila deverá disponibilizar funções auxiliares que permitam inserir novos itens na fila, além das funcionalidades de consumo e processamento.

3. Quantas execuções consomem ao mesmo tempo, e de quantas máquinas.

R: A quantidade de execuções consumidoras simultâneas e a quantidade de máquinas utilizadas deverão ser parametrizáveis, permitindo configurar esses limites conforme a necessidade de cada projeto e ambiente de execução.

4. Regra de ordenação e de prioridade.

R: A captura dos itens deverá seguir a lógica abaixo, baseada na estrutura de fila apresentada. A consulta seleciona um único item que esteja com status Pendente ou que esteja com status Processando e pertença à mesma combinação de hostname e usuario da execução atual. Também deverá considerar somente itens cuja hora_insercao seja menor ou igual à data e hora atual.

Após selecionar o item, seu status deverá ser atualizado para Processando, registrando o hostname, o usuário, a hora de início e o identificador da execução. Caso nenhum item seja encontrado, deverá retornar -1.
DECLARE @idFila AS int;
SET @idFila = -1;

SELECT TOP 1 @idFila = [Nome da Coluna]
FROM [Nome da Tabela]
WHERE
(
    status = 'Pendente'
    OR
    (
        hostname = '[Hostname]'
        AND usuario = '[AgentName]'
        AND status = 'Processando'
    )
)
AND hora_insercao <= GETDATE();

IF @idFila >= 0
BEGIN
    UPDATE %in_nomeTabela%
    SET
        status = 'Processando',
        hostname = '[Hostname]',
        usuario = '[AgentName]',
        hora_inicio = GETDATE(),
        idfluxosexec = [IdFluxoExec]
    WHERE
        [Nome da Coluna] = @idFila;

    SELECT @idFila;
END
ELSE
BEGIN
    SELECT -1;
END


Os nomes da tabela, da coluna identificadora, do hostname, do agente e do identificador da execução deverão ser substituíveis conforme a configuração do consumidor.

5. O que é um item inválido; quantas tentativas; intervalo entre elas.

R: A definição do que caracteriza um item inválido, a quantidade de tentativas e o intervalo entre as tentativas deverão ser parametrizáveis. A quantidade padrão deverá ser de 3 tentativas, podendo ser alterada conforme a necessidade de cada automação.

6. O que deve acontecer com o item de uma execução que morreu: lease automático ou recuperação manual.

R: A recuperação dos itens de uma execução interrompida deverá ser manual. Não deverá ocorrer recuperação automática por meio de lease. A decisão de recuperar e disponibilizar novamente os itens ficará sob responsabilidade do processo de recuperação definido pelo projeto consumidor.

7. A conclusão do item precisa ser atômica com as gravações de negócio no mesmo banco?

R: Sim. A conclusão do item da fila deverá ser atômica em conjunto com as gravações dos dados de negócio realizadas no mesmo banco de dados. Dessa forma, a conclusão do item e as respectivas operações de negócio deverão fazer parte da mesma transação, evitando que uma operação seja confirmada sem a outra.

8. Continuar ou parar depois de uma falha de item; limite de falhas seguidas.

R: A automação deverá continuar o processamento até que todos os itens pendentes tenham sido processados.

Entretanto, deverá ser encerrada quando ocorrer uma falha definitiva, após as tentativas configuradas, em alguma subetapa essencial para o funcionamento do processo.

São exemplos de subetapas essenciais:
- Login no sistema.
- Captura dos itens da fila.
- Captura das credenciais.
- Captura de dias úteis e feriados.
Essas subetapas são pré-requisitos para o processamento dos itens. Portanto, caso alguma delas falhe após suas tentativas, não haverá condições de continuar processando os itens da fila, e a automação deverá ser finalizada.

A falha em uma subetapa essencial deverá ser diferenciada de uma falha no processamento individual de um item, pois esta última não implica necessariamente a interrupção de toda a automação.
     
**Condição de aceite.** Respostas 1 a 6 de um consumidor real. Sem elas, o contrato pode ser revisado, mas não aceito.
