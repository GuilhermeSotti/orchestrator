# RFC-0009 — Destinos de registros de execução e de logs técnicos

| Campo | Valor |
|---|---|
| Status | Aceita em 2026-11-15 pelo responsável |
| Data | 2026-11-14 |
| Autor | Claude, a pedido do responsável |
| Decisor | Responsável pelo projeto (aceite registrado em [DECISIONS](../DECISIONS.md), seção 5) |
| Implementação | 2026-11-15: resposta 6 (falha de destino sem efeito no status) no Core 0.2.0, branch local `feature/core-0.2`, sem release; aprovada, DE-1. Seção 2.2 e resposta 1 no pacote `orchestrator-records-file` 0.1.0, branch local `feature/records-file`, sem push, com as hipóteses registradas no README do pacote para C16 (um arquivo por processo) e C19 (etapa = estágio, subetapa = `ctx.step`, pasta `_` fora de subetapa, remoção pelo próprio destino). A opção `required` da seção 2.2 não existe: a resposta 6 a substituiu. Destino SQL (2.3): C18 e DS-1, bloqueado |
| Item de escopo | 5 (logs e registros) |
| Relacionadas | [RFC-0001](0001-ciclo-de-vida-da-execucao.md) (seção 9), [ADR-0011](../adr/0011-observabilidade.md), [RFC-0004](0004-controles-reutilizaveis-escopo-e-sequencia.md) (DS-1, DS-2), [RFC-0006](0006-segredos-cofres-e-credenciais-de-providers.md) (2.1 e 2.4) |

## 1. Problema

O responsável quer preservar a distinção entre o logging técnico do Runtime e os logs de negócio, auditoria ou histórico do consumidor, e avaliar destinos em arquivo e em SQL, conforme retenção, consulta, privacidade e volume, mantendo a correlação por execução e o mascaramento de segredos.

O que existe ([SCOPE_DIAGNOSIS](../audit/SCOPE_DIAGNOSIS.md), seção 3.5):

| Camada | O que é | Quem é dono |
|---|---|---|
| Logs técnicos | Registros do módulo `logging`, com `execution_id`, `automation` e `stage`, mascaramento e saída JSON (`orchestrator_core.logs`) | Core (mecanismo); aplicação (destino) |
| Registro da execução | `ExecutionRecord`, mascarado, entregue aos `ExecutionRecordSink` no estágio `persist_logs` | Core (conteúdo e port); Providers (destinos) |
| Logs de negócio, auditoria, histórico | O que a automação decide registrar sobre o próprio trabalho | Projeto consumidor |

Faltam: um destino em arquivo para os logs (`configure_logging` só instala um handler de stream) e qualquer destino real para os registros (só existe o `InMemoryRecordSink`, para testes). Um destino SQL esbarra em dois fatos: os destinos rodam depois que `finalize` liberou os recursos, e `write(record)` não recebe contexto nem segredos.

## 2. Proposta

### 2.1 Logs técnicos em arquivo: guia, sem código novo

Um guia novo mostra como compor um `logging.handlers.RotatingFileHandler` ou `TimedRotatingFileHandler` com `ExecutionContextFilter`, `RedactingFilter` e, se desejado, `JsonFormatter`. O guia registra os limites da biblioteca padrão:

- a rotação não é segura com mais de um processo escrevendo no mesmo arquivo: cada processo usa o seu arquivo, ou os processos escrevem em stream e um coletor externo grava;
- em Windows, a rotação falha se outro programa mantiver o arquivo aberto;
- `RedactingFilter` mascara só segredos resolvidos pelo Runtime; dados pessoais não são detectados e não devem ser registrados (`SECURITY.md`, seção "Logs").

Mudar a API (por exemplo, `configure_logging(handler=...)`) só se dois consumidores repetirem a mesma montagem.

### 2.2 Registros em arquivo: `orchestrator-records-file`

Provider do port `ExecutionRecordSink` do Core, só com a biblioteca padrão.

| Aspecto | Proposta |
|---|---|
| Formato | JSON Lines: uma linha por execução, com `record.to_dict()`, UTF-8 |
| Arquivo | Um por dia (UTC), `<prefixo>-AAAA-MM-DD.jsonl`, numa pasta configurada que precisa existir |
| Concorrência | Trava entre threads do processo. Processos diferentes usam prefixos diferentes; o pacote não tenta travar arquivos entre processos |
| Durabilidade | `flush` a cada registro; `fsync` opcional (`fsync = true`) |
| Retenção | Desligada por padrão. Com `retention_days`, remove só arquivos com o seu próprio prefixo e padrão de nome, na sua pasta |
| Falha | Erro de escrita lança exceção: vira erro de teardown e a execução termina `failed` (comportamento atual do port, RFC-0001). Com `required = false`, o pacote registra a falha em log e não lança |
| Conteúdo | Só o `ExecutionRecord`, que não contém parâmetros nem o retorno da automação |

Configuração, entregue pelo consumidor na composição (o port do Core não tem tabela de configuração própria):

```python
from orchestrator_records_file import JsonLinesRecordSink

sink = JsonLinesRecordSink(folder="logs/registros", prefix="vendas-maquina01", retention_days=90)
runtime = RuntimeBuilder().with_record_sink(sink).build()
```

### 2.3 Registros em SQL: `orchestrator-records-sql`, condicional

Só faz sentido se o consumidor precisar consultar o histórico em banco (seção 7, pergunta 2). Duas barreiras técnicas e as opções:

| Barreira | Opções | Recomendação |
|---|---|---|
| A sessão SQL da execução já está fechada em `persist_logs` | (a) Conexão própria do destino, aberta a cada registro; (b) mover o destino para antes de `finalize` | (a): o registro precisa incluir os erros de `finalize` (D-16) |
| O destino não tem acesso a segredos | (a) O port recebe o `SecretStore` da execução: `write(record, secrets)`; (b) segredos no escopo do Runtime (diagnóstico, L8.3); (c) o consumidor resolve a credencial por fora, sem mascaramento | (a), com a mesma lógica de menor privilégio da RFC-0006, opção A |

A opção (a) da segunda linha muda o port do Core: quebra destinos customizados existentes (fora do repositório, nenhum conhecido; dentro, só o `InMemoryRecordSink`). Para não exigir uma versão 0.3 do Core logo depois da 0.2, a mudança precisa ser decidida antes da release 0.2 (RFC-0004, E7.7 e DS-2).

O destino SQL, se aceito:

- depende de `orchestrator-sql` e usa um `SqlProvider` configurado para ele, com credenciais por referência (RFC-0006, 2.1). Não usa a sessão da automação. É o caso de Provider que depende de uma segunda Capability (RFC-0004, DS-1);
- grava numa tabela cujo nome e cujas colunas vêm de um mapa do consumidor, validado como identificadores. Nenhum nome é fixo no pacote. Campos do registro sem coluna mapeada são descartados; `stages` pode ir para uma coluna de texto em JSON;
- não cria nem altera a tabela;
- segue a política de falha da seção 2.2 (`required`).

Alternativa sem mudança no Core: um processo externo carrega os arquivos JSON Lines da seção 2.2 no banco. Resolve a consulta com atraso e sem código novo na plataforma; é a recomendação enquanto não houver necessidade de consulta imediata.

### 2.4 Logs de negócio, auditoria e histórico

Ficam com o consumidor. A plataforma já oferece o que eles precisam para correlação e proteção: `ctx.logger` e qualquer logger do consumidor recebem `execution_id`, `automation` e `stage` (`ExecutionContextFilter`); segredos resolvidos são mascarados; eventos próprios podem ser publicados com `ctx.publish`.

Não é proposta uma Capability de auditoria: não há caso de uso, e uma auditoria genérica tende a virar um repositório de dados de negócio dentro da plataforma (RFC-0001, seção 9). Se um consumidor precisar de trilha de auditoria estruturada, com retenção e consulta próprias, isso pede RFC com o caso real.

## 3. Privacidade, retenção e volume

| Tema | Logs técnicos | Registros de execução |
|---|---|---|
| Conteúdo | Mensagens escritas pelo código; podem conter dados pessoais se o consumidor os registrar | Identidade da execução, status, duração, estágios, tipo e mensagem mascarada dos erros |
| Proteção já existente | Mascaramento de segredos resolvidos | Mascaramento; sem parâmetros nem retorno |
| Risco remanescente | Dados pessoais e partes de segredos compostos (diagnóstico, L8.5) | Mensagens de erro podem conter dados pessoais vindos de exceções de terceiros |
| Retenção | Do coletor ou do destino; fora da plataforma | `retention_days` do destino em arquivo; no SQL, do banco |
| Volume | Proporcional ao que o código registra | Uma linha por execução |

## 4. Compatibilidade

- 2.1: só documentação.
- 2.2: pacote novo; nenhuma mudança no Core.
- 2.3: pacote novo e, se aceita a opção (a), mudança no port `ExecutionRecordSink` do Core 0.2 (RFC-0002, RFC-0001 seção 9, `InMemoryRecordSink`, CHANGELOG e matriz de compatibilidade).

## 5. Segurança

- Arquivos de registro e de log são criados com as permissões padrão do processo; a pasta deve ter acesso restrito à conta que executa as automações. O guia mostra como verificar.
- Nenhum destino registra o valor de uma credencial; as do destino SQL entram por referência.
- Nomes de tabela e coluna do destino SQL são validados e citados; valores sempre como parâmetros (RFC-0003).
- A retenção nunca apaga arquivos fora do padrão de nome do próprio destino.

## 6. Alternativas consideradas

| Alternativa | Por que não, ou não agora |
|---|---|
| Handler de `logging` que grava em SQL | Mistura logs técnicos com banco; cada linha vira uma escrita remota; um erro do banco gera novas linhas de log sobre o próprio erro |
| Coletor externo (agente de logs) lendo os arquivos JSON | Bom destino para busca centralizada; fica fora da plataforma e é compatível com as seções 2.1 e 2.2 |
| Provider de observabilidade (OpenTelemetry) | Previsto pela ADR-0011 como pacote; sem caso de uso nesta etapa |
| Destino em arquivo dentro do Core | Contraria o port: implementações de destino ficam fora do Core (`ExecutionRecordSink`, docstring; ADR-0004) |

## 7. Perguntas abertas

1. Onde os logs técnicos precisam ficar, por quanto tempo e quem os consulta.

R: O período de retenção dos logs deverá ser parametrizável, com prazo padrão de 6 meses.

Inicialmente, os logs poderão ser armazenados em arquivos TXT, organizados na seguinte estrutura de diretórios:

C:[Inicio Parametrizável]/etapa/subetapa/ano/mes/dia/[Hostname]_[UserMachine].txt

Como alternativa, os logs poderão ser armazenados em SQL, utilizando a seguinte estrutura de tabela:

CREATE TABLE PA0000.Logs(
    Id INT IDENTITY PRIMARY KEY,
    FluxoExecucaoId INT NOT NULL,
    SubFluxoExecucaoId INT NOT NULL,
    DataHora DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    Linha INT NULL,
    Descricao NVARCHAR(MAX) NOT NULL,
    Ambiente CHAR(1) NOT NULL CHECK (Ambiente IN ('D','H','P')),
    Hostname VARCHAR(100) NOT NULL,
    Username VARCHAR(100) NOT NULL,
    CONSTRAINT FK_Log_Exec FOREIGN KEY(FluxoExecucaoId) REFERENCES PA0000.FluxosExecucao(Id),
    CONSTRAINT FK_Log_SubExec FOREIGN KEY(SubFluxoExecucaoId) REFERENCES PA0000.SubFluxosExecucao(Id)
);

O diretório inicial de armazenamento deverá ser parametrizável.

Observação: A definição de quem será responsável por consultar os logs técnicos ainda não foi especificada.

2. O histórico de execuções precisa de consulta em banco? Quais consultas, com que atraso aceitável.

R: O histórico de execuções deverá permitir consultas exclusivamente manuais. Não há necessidade, neste momento, de consultas automáticas.

Não foram especificados tipos de consultas predefinidas nem um requisito de atualização em tempo real.

3. Restrições de dados pessoais (LGPD) para logs e registros.

R: Sim. Os logs técnicos e os registros de execução deverão respeitar as restrições aplicáveis da LGPD.

4. Volume esperado: execuções por dia e linhas de log por execução.

R: O volume de execuções por dia e a quantidade de linhas de log por execução deverão ser parametrizáveis, permitindo adequação conforme a necessidade de cada projeto consumidor.

5. Mais de um processo escreve na mesma pasta ao mesmo tempo? Em quais máquinas?

R: Sim. Deverá ser permitido que múltiplos processos escrevam na mesma pasta simultaneamente. A quantidade de processos e as máquinas envolvidas deverão ser parametrizáveis, conforme o ambiente de execução.

6. Uma falha ao gravar o registro deve fazer a execução terminar failed?

R: Não. Qualquer erro ocorrido durante a gravação do registro deverá ser simplesmente ignorado, sem interromper a automação ou alterar o status final da execução.

**Condições de aceite.** 2.1 e 2.2 dependem só das respostas 1, 4 e 5. 2.3 depende da resposta 2 e da decisão sobre o port antes da release 0.2.

## 8. Critérios de aceite e testes

Os da RFC-0004, seção 5 (E7.13 e E7.14), mais:

- 8 threads gravando no mesmo destino em arquivo: cada linha é um JSON válido e nenhuma se perde;
- disco cheio ou pasta sem permissão simulados: com `required`, erro de teardown; sem, log de aviso e status inalterado;
- retenção: arquivos fora do padrão de nome nunca são removidos;
- o valor-sentinela não aparece em nenhuma linha gravada;
- destino SQL, se aceito: tabela e colunas com nomes arbitrários; credencial por referência; a sessão da automação não é usada.
