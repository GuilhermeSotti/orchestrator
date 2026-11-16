# Reconciliação das respostas às RFCs 0004 a 0012

| Campo | Valor |
|---|---|
| Data | 2026-11-15 |
| Fontes | Respostas do responsável gravadas nas RFCs 0004 a 0012 em 2026-11-15, entre 11h51 e 12h16 (horário de Brasília); instruções do responsável na sessão de 2026-11-15 |
| Situação das RFCs | Todas continuam "Proposta. Não aceita". Responder a uma pergunta não equivale a aceitar a RFC (instrução de 2026-11-15) |
| Autor | Claude, a pedido do responsável |
| Revisão independente | Não houve. O ai-harness não tem integração executável nesta sessão (seção 1.5) |
| Documentos anteriores | [SCOPE_DIAGNOSIS](SCOPE_DIAGNOSIS.md) (2026-11-14), [RFC-0004](../rfc/0004-controles-reutilizaveis-escopo-e-sequencia.md) a [RFC-0012](../rfc/0012-autenticacao-por-sistema.md) |

As perguntas e as respostas continuam nas RFCs, sem alteração. Este documento classifica cada resposta, aponta contradições e diz o que pode avançar. Nada aqui é decisão do responsável, salvo quando citado como tal.

## 1. Estado verificado em 2026-11-15

### 1.1 Git na pasta do responsável

Não há terminal no computador do responsável. Os arquivos de `.git` foram copiados da pasta e examinados com `git` numa cópia; nada foi gravado em `.git`.

| Item | Fato | Como foi verificado |
|---|---|---|
| `main` local | `e8eaabe`, o mesmo de 2026-11-13; nenhum commit local novo | `refs/heads/main` e reflog |
| `origin/main` | `564dd24`, quatro commits à frente: `b04bfab` e `968d478` (Dependabot) e os merges dos PRs #1 (`4970e00`) e #2 (`564dd24`), feitos no GitHub em 2026-11-13 às 21h54 | `git log` sobre os objetos copiados |
| O que os PRs mudaram | Ações do GitHub (`setup-python` 7.1.0, `upload-artifact` 7.0.2) e ferramentas de desenvolvimento (ruff 0.17.4, mypy 2.4.1, pytest 9.2.0, coverage 7.17.2, setuptools 84.2.1). Nenhum código de pacote | `git diff e8eaabe 564dd24` |
| Forma do merge | Merge commit, não squash | Pais dos commits `4970e00` e `564dd24` |
| Árvore de trabalho | Três arquivos modificados e dez não rastreados, todos de documentação (entrega de 2026-11-14 e respostas de 2026-11-15). Nenhum arquivo de código ou de configuração alterado | `git status` com o índice da pasta; comparação byte a byte |
| Último `fetch` | 2026-11-15, 12h25 | `FETCH_HEAD` |
| Branches remotas | O `fetch` trouxe `main` e `dependabot/pip/requirements/dev-tools-ff8c5acc02` (do PR #2, já integrado). `feature`, `feature-core` e `teste` não aparecem mais | `FETCH_HEAD` e `refs/remotes` |
| Histórico de julho | A página pública do repositório informa 15 commits em `main`: os 11 recriados em 2026-11-12 e os 4 de 2026-11-13. Os commits de julho (`4c4ff0c`, `d56bcce`) não estão em `main`; o estado da pasta de julho continua na tag `archive/scaffold-2026-07` (`be46f68`) | Página pública e reflog. Indício forte de que o histórico de julho foi substituído no push de 2026-11-13; não confirmado no registro de atividade do GitHub |
| Visibilidade | Público | Página do repositório |

### 1.2 CI no GitHub

Lido na página pública de Actions; os jobs individuais não foram abertos.

| Execução | Gatilho | Commit | Resultado |
|---|---|---|---|
| CI #5 | push em `main` | `564dd24` | Sucesso |
| CI #4 | push em `main` | `4970e00` | Cancelada (substituída pela #5, regra de concorrência do workflow) |
| CI #3 e #2 | PRs do Dependabot | `968d478`, `b04bfab` | Sucesso |
| CI #1 | push em `main` | `e8eaabe` | Sucesso |

O workflow roda Ubuntu e Windows com Python 3.13, 3.14 e 3.15 e exige cobertura de 90%. O sucesso das execuções #1 e #5 indica que a 0.1.0 passou nessa matriz; a confirmação por job fica para o primeiro PR desta entrega.

### 1.3 Ambiente desta sessão

| Item | Situação |
|---|---|
| Sistema e Python | Linux, Python 3.13.18 |
| Ferramentas | ruff 0.16.9, mypy 2.3.1, pytest 9.1.1, setuptools 84.0.0: as versões fixadas em `e8eaabe`. As de `origin/main` não puderam ser instaladas (instalação de pacotes desligada nesta sessão) |
| Cobertura | `coverage.py` ausente. A cobertura foi estimada por linhas com `sys.monitoring`, sem ramos; não substitui o gate da CI |
| Não verificado aqui | Windows, Python 3.14 e 3.15, cobertura de ramos, ferramentas nas versões novas |
| `.venv` da pasta do responsável | Python 3.11; não serve como base (o projeto exige 3.13 ou superior) |

### 1.4 Baseline antes de qualquer alteração de código

Executada na cópia de trabalho equivalente à pasta do responsável (`e8eaabe` mais a documentação).

| Comando | Resultado |
|---|---|
| `ruff check .` | All checks passed |
| `ruff format --check .` | 135 files already formatted |
| `mypy` | Success: no issues found in 48 source files |
| `pytest` | 214 passed, 1 skipped |
| `python tools/check_docs.py` | saída 0 |
| `python -m pytest tools` | 14 passed |
| `python tools/build_packages.py --check` | reproducible: 6 artifacts |
| `python -m tools.e2e` | e2e ok |
| Cobertura estimada de linhas | 96,4% |

### 1.5 ai-harness

A pasta `ai-harness` existe ao lado do repositório, mas a sessão não tem servidor MCP local registrado (`localMcpServers` vazio) nem terminal no computador. Nenhuma chamada ao Maestro foi feita ou simulada, e nenhum resultado aqui é de agente independente.

## 2. Classificações

| Classificação | Significado |
|---|---|
| RESPONDIDA | A resposta permite projetar e testar o comportamento |
| RESPONDIDA PARCIALMENTE | Há uma decisão, mas falta um dado sem o qual o componente não pode ser fechado |
| PENDENTE | Sem resposta, ou "parametrizável" sem tipo, padrão ou semântica |
| CONDICIONAL | Depende de outro componente ou de caso de uso ainda inexistente |
| CONFLITANTE | Contradiz outra resposta, a proposta da RFC ou uma decisão aceita |

"Parametrizável" resolve quem escolhe o valor; não resolve o tipo, o padrão, a validação nem o comportamento. Quando faltam esses elementos, a resposta é classificada como parcial.

## 3. Respostas por RFC

### 3.1 RFC-0004, seção 7

| # | Pergunta | Resposta (síntese) | Classificação | O que falta |
|---:|---|---|---|---|
| 1 | Primeira automação real | A plataforma oferece recursos parametrizáveis para várias automações; não é feita para uma só | CONFLITANTE com "nenhum port sem consumidor" (ARCHITECTURE, seção 1) | Um caso concreto por Capability nova (C3) |
| 2 | Banco de dados | Versão mais recente disponível; usuários e senhas parametrizáveis por automação | RESPONDIDA PARCIALMENTE | Motor (a sintaxe da RFC-0008 é de SQL Server), forma de autenticação e driver |
| 3 | Fila | "Respondido no RFC-0008" | Ver 3.5 | — |
| 4 | Notificações | "Respondido no RFC-0007" | Ver 3.4 | — |
| 5 | Logs e registros | "Respondido no RFC-0009" | Ver 3.6 | — |
| 6 | Mapeamentos | Caminhos e referências de CSS, JS e GUI; arquivo compartilhado; atualização manual por todos; sempre a versão mais atual | RESPONDIDA PARCIALMENTE | Ver 3.7 |
| 7 | Login | Depende de cada automação; estratégias por sistema; credenciais no Key Vault ou em SQL | RESPONDIDA PARCIALMENTE; SQL CONFLITANTE (C4) | Ver 3.9 |
| 8 | Segredos | "Respondido no RFC-0006" | Ver 3.3 | — |
| 9 | Calendários | Revisão e atualização manual por usuários ou desenvolvedores | RESPONDIDA PARCIALMENTE | Ver 3.8 |
| 10 | Distribuição | Todos os projetos compartilham os recursos, inclusive dependências | RESPONDIDA PARCIALMENTE | Se as máquinas podem instalar dependências de terceiros, e de onde (DS-3) |

### 3.2 RFC-0005, seção 8

| # | Pergunta | Resposta (síntese) | Classificação | O que falta |
|---:|---|---|---|---|
| 1 | `teardown_timeout` | Parametrizável; padrão de 60 s; "O limite poderá ser desligado se for 0" | RESPONDIDA | Nada. Diverge do resumo da instrução de 2026-11-15, que dava a semântica do zero como não decidida; prevalece o texto gravado na RFC (C27) |
| 2 | Limite e aninhamento | Limite parametrizável, padrão de 1.000; aninhamento desde a primeira versão | RESPONDIDA | — |
| 3 | Registro ou eventos | Registro sempre necessário; subetapas padrão da plataforma, por exemplo a "finalização dos sistemas", associada ao evento Finished | RESPONDIDA quanto ao registro; PENDENTE quanto às subetapas padrão | Lista, nomes e escopo das subetapas padrão (C28) |
| 4 | Interrupção em produção | Toda automação passa obrigatoriamente pelo evento Finished na finalização | RESPONDIDA PARCIALMENTE | Como as automações são iniciadas e encerradas em produção (C29) |

### 3.3 RFC-0006, seção 8

| # | Pergunta | Resposta (síntese) | Classificação | O que falta |
|---:|---|---|---|---|
| 1 | Cofre e identidade | Parametrizáveis; nada fixo na plataforma | RESPONDIDA (política) | Um cofre real para o teste de integração |
| 2 | Rede | Direta ou por proxy, parametrizável | RESPONDIDA (política) | Se o proxy exige autenticação |
| 3 | Cache | Escopo da execução; descartado ao fim; nunca reutilizado por outra execução | RESPONDIDA | Se o cache é ligado por padrão ("poderão permanecer em cache") |
| 4 | Outras origens | SQL e Azure Key Vault; no SQL, tabela específica com verificação e dados criptografados | CONFLITANTE com a seção 2.5 (C4) | RFC de segurança |
| 5 | Opção para 2.1 | A — `connect(secrets)` | RESPONDIDA | — |

### 3.4 RFC-0007, seção 12

| # | Pergunta | Resposta (síntese) | Classificação | O que falta |
|---:|---|---|---|---|
| 1 | Canais reais | Parametrizáveis; autenticação com tokens | RESPONDIDA PARCIALMENTE | Canal e ambiente reais; tipo de token (C14) |
| 2 | Quem recebe o quê | Destinatários, tipos e status parametrizáveis, inclusive o aviso de início | RESPONDIDA (política) | — |
| 3 | Idioma e conteúdo | PT-BR formal nas mensagens automáticas; conteúdo de negócio parametrizável | RESPONDIDA; CONFLITANTE com a seção 3 e a ADR-0017 (C15) | Alcance da ADR-0017 |
| 4 | Volume e agrupamento | Sem limite predefinido; sem agrupamento | RESPONDIDA; CONFLITANTE com a seção 4 (C12) | — |
| 5 | `required` | Parametrizável para as notificações disparadas durante a execução | RESPONDIDA PARCIALMENTE | Regra para os avisos de ciclo de vida (C13) |
| 6 | Lista de estágios | O Core expõe ao contexto a lista de estágios; a inconsistência é recusada antes da automação | RESPONDIDA | — |

### 3.5 RFC-0008, seção 11

| # | Pergunta | Resposta (síntese) | Classificação | O que falta |
|---:|---|---|---|---|
| 1 | Estrutura da tabela | Modelo de referência `fila_[NOME SUBETAPA]` com 11 colunas; estados Pendente e Processando; nomes configuráveis; índices não especificados | RESPONDIDA PARCIALMENTE | Valores físicos de concluído, falha e inválido; significado de `[ID DE EXECUÇÃO]` e de `idfluxosexec` (C10); índices |
| 2 | Produtor | Inserção por subetapa do desenvolvedor; a Capability oferece funções de inserção | RESPONDIDA | Quais colunas a inserção preenche |
| 3 | Concorrência | Execuções e máquinas parametrizáveis | RESPONDIDA (política) | — |
| 4 | Ordenação | Lógica de captura em SQL Server | RESPONDIDA PARCIALMENTE; CONFLITANTE (C6, C7, C8) | Ordem, atomicidade, dialeto (C9) |
| 5 | Inválido, tentativas, intervalo | Parametrizáveis; padrão de 3 tentativas | RESPONDIDA PARCIALMENTE | Intervalo padrão; o que conta como tentativa (C11) |
| 6 | Execução que morreu | Recuperação manual; sem lease | RESPONDIDA; CONFLITANTE com a captura de itens Processando (C6) | — |
| 7 | Atomicidade com o negócio | Sim, na mesma transação | RESPONDIDA; CONFLITANTE com a seção 6 da RFC (C5) | — |
| 8 | Continuar ou parar | Continua até acabar; encerra em falha definitiva de subetapa essencial; falha de item é diferente | RESPONDIDA | A lista de subetapas essenciais é do consumidor; os quatro exemplos não são lista universal |

### 3.6 RFC-0009, seção 7

| # | Pergunta | Resposta (síntese) | Classificação | O que falta |
|---:|---|---|---|---|
| 1 | Onde, por quanto tempo, quem | Retenção parametrizável, padrão de 6 meses; TXT em `C:[Inicio Parametrizável]/etapa/subetapa/ano/mes/dia/[Hostname]_[UserMachine].txt`; alternativa SQL `PA0000.Logs`; quem consulta: não definido | RESPONDIDA PARCIALMENTE | O que são "etapa" e "subetapa" no caminho; destino de linhas fora de subetapa; quem apaga os arquivos vencidos (C16, C19) |
| 2 | Consulta do histórico | Só manual | RESPONDIDA PARCIALMENTE | Manual em quê: nos arquivos ou num banco (C18) |
| 3 | LGPD | Sim | PENDENTE | Campos proibidos, anonimização e prazos; é decisão jurídica, não técnica |
| 4 | Volume | Parametrizável | PENDENTE | Ordem de grandeza, para dimensionar arquivos e índices |
| 5 | Vários processos | Sim, na mesma pasta; quantidade e máquinas parametrizáveis | RESPONDIDA | — |
| 6 | Falha ao gravar o registro | Ignorada; não interrompe nem altera o status final | RESPONDIDA | — |

### 3.7 RFC-0010, seção 9

| # | Pergunta | Resposta (síntese) | Classificação | O que falta |
|---:|---|---|---|---|
| 1 | Exemplo e interpretação | Localização de elementos de interface (CSS, JS, GUI); exemplo ainda não especificado | RESPONDIDA PARCIALMENTE | Duas ou três entradas reais, anonimizadas |
| 2 | Onde, quem, frequência | Arquivo compartilhado, um por sistema; manutenção manual por todos; frequência conforme o sistema; local não definido | RESPONDIDA PARCIALMENTE | Formato e local do arquivo |
| 3 | Compartilhamento | Todos os projetos; quantidade não definida | RESPONDIDA | — |
| 4 | Tamanho | O necessário para cada sistema | RESPONDIDA (sem número) | — |
| 5 | Vigência | Sempre a versão mais atual; sem vigência por entrada | RESPONDIDA | Se "mais atual" vale por execução ou a cada consulta (C22) |
| 6 | Fixar versão | Não | RESPONDIDA; CONFLITANTE com `expected_version` (C21) | — |
| 7 | Buscas | Só pelo nome padronizado do elemento | RESPONDIDA | — |

### 3.8 RFC-0011, seção 11

| # | Pergunta | Resposta (síntese) | Classificação | O que falta |
|---:|---|---|---|---|
| 1 | Jurisdições | "Todos os feriados serão cadastrados manualmente" | RESPONDIDA | Consequência: o Provider de feriados padrão (biblioteca `holidays`) sai do plano |
| 2 | Civil, bancário, pontos facultativos | Idem | RESPONDIDA | O que for ponto facultativo é cadastrado como o consumidor decidir |
| 3 | Quem mantém | Manual; responsáveis por camada não definidos | RESPONDIDA PARCIALMENTE | Responsáveis |
| 4 | Horizonte | Idem 1 | RESPONDIDA PARCIALMENTE | Até que ano o cadastro precisa estar completo (cobertura) |
| 5 | Cálculos | "Captura de próximo dia útimo, ultimo dia útil" | RESPONDIDA PARCIALMENTE | Se "útimo" é "útil"; se "último dia útil" é o do mês ou o anterior a uma data (C24) |
| 6 | Sábado | "Em todas as operações, Sábado e domingo será dia útil" | RESPONDIDA, a confirmar | Literalmente, só os feriados cadastrados deixam de ser dias úteis (C23) |
| 7 | Fuso | Fuso da máquina em execução | RESPONDIDA | — |

### 3.9 RFC-0012, seção 8

| # | Pergunta | Resposta (síntese) | Classificação | O que falta |
|---:|---|---|---|---|
| 1 | Sistemas | Sem lista fixa; fluxos de autenticação reutilizados entre automações | RESPONDIDA (política) | Um sistema real |
| 2 | Tecnologia de acesso | Interativa (preencher usuário e senha e acionar o login, com mapeamentos por parâmetro e override) e não interativa (token) | RESPONDIDA PARCIALMENTE | Tecnologia (navegador, desktop, API) e tipo de token |
| 3 | Sessões simultâneas | Depende do sistema | RESPONDIDA (política) | — |
| 4 | Segundo fator | Parametrizável | PENDENTE | Mecanismos (código de aplicativo, push, SMS) |
| 5 | Credenciais e rotação | Key Vault ou SQL cifrado; responsável pela rotação não definido | CONFLITANTE quanto ao SQL (C4); PENDENTE quanto à rotação | — |

## 4. Decisões transversais DS-1 a DS-8

A seção 4 da RFC-0004 não recebeu respostas. Nenhuma recomendação foi tratada como decisão.

| DS | Resposta explícita | Classificação | Efeito nesta entrega |
|---|---|---|---|
| DS-1 | Nenhuma | PENDENTE | Bloqueia os Providers que usam a Capability SQL: fila, registros, mapeamentos e calendário em SQL |
| DS-2 | Nenhuma | PENDENTE | Vale a ADR-0009, aceita: igualdade exata da API antes da 1.0. Por isso Core, SQL e SQLite passam juntos à 0.2.0 |
| DS-3 | A resposta 10 diz que todos os projetos compartilham dependências; não diz se as máquinas podem instalar pacotes de terceiros, nem de onde | PENDENTE | Bloqueia Key Vault, Excel e o Provider de SQL Server |
| DS-4 | Nenhuma | PENDENTE | Nenhum pacote novo foi criado |
| DS-5 | Instrução de 2026-11-15: "Não transforme subetapas em workflow engine. A composição do fluxo continua no código do consumidor." | RESPONDIDA PARCIALMENTE (instrução de sessão, ainda não registrada como decisão) | `ctx.step` só rastreia |
| DS-6 | Nenhuma | PENDENTE | — |
| DS-7 | Indício: "finalização dos sistemas" (RFC-0005, resposta 3) | PENDENTE | Nada encerra processos do sistema operacional |
| DS-8 | Resposta 1: plataforma genérica | PENDENTE | A primeira fatia foi escolhida pelo critério "decidido e independente" (seção 7) |

## 5. Contradições, lacunas e bloqueios

Bloqueio: **total** (impede a arquitetura base ou a segurança global), **componente** (impede um pacote ou comportamento), **não bloqueante** (pode ser isolado sem inventar regra) ou **futuro**. A recomendação técnica é do autor deste documento e não substitui a decisão.

| # | Tema | Evidência | Premissa do responsável | Impacto | Bloqueio | Decisão necessária | Recomendação técnica |
|---:|---|---|---|---|---|---|---|
| C1 | Aceitação das RFCs | Todas em "Proposta"; `GOVERNANCE.md`, seção 5, exige RFC aceita antes da implementação | Implementar o que estiver decidido, sem marcar "Aceita" | O código desta entrega fica na árvore de trabalho; não pode ir para `main` sem aceite | Componente (merge) | Aceite formal das partes implementadas (seção 6), antes do PR | Aceitar por parte, como a RFC-0005 já permite |
| C2 | DS-1 a DS-8 | Seção 4 | — | Pacotes novos com Provider sobre SQL ou dependência de terceiros | Componente | DS-1, DS-3 e DS-4 antes do primeiro pacote novo | — |
| C3 | Consumidor real | RFC-0004, resposta 1 | Plataforma genérica | ARCHITECTURE: "nenhum port sem consumidor"; a instrução de 2026-11-15 reafirma que o desejo genérico não basta | Componente (cada Capability nova) | Um caso concreto por Capability, mesmo pequeno | Registrar o caso na própria RFC: o que a automação faz, sistemas, entrada e saída |
| C4 | Segredos em SQL | RFC-0006, 2.5: a plataforma não oferece; respostas 0006-4 e 0012-5 pedem tabela com dados criptografados | Considera SQL cifrado, como no Key Vault | Exige cifra autenticada (dependência de terceiros), gestão e rotação de chaves, auditoria, backups, menor privilégio | Componente | RFC de segurança própria, com os sete controles da seção 2.5 | Até lá, o SQL guarda referências (`kv:...`) e o valor fica no cofre. Nenhuma cifra improvisada |
| C5 | Fila: transação | Resposta 7 exige atomicidade; a seção 6 recomenda registro SQL próprio para a fila | Mesma transação | Com outro registro, a fila usa outra conexão e não há transação comum | Componente | A fila usa a sessão do mesmo registro SQL da automação? | Mesmo registro e conclusão dentro da transação aberta pelo consumidor; provar com falha injetada entre a gravação de negócio e a conclusão |
| C6 | Fila: recuperação | Resposta 6 (manual, sem lease) × resposta 4 (captura itens Processando do mesmo hostname e usuário) | As duas | É retomada automática, restrita ao par máquina e usuário. Com duas execuções simultâneas no mesmo par (permitido pela resposta 3), uma captura o item da outra | Componente | Confirmar a intenção; se mantida, limitar a uma execução consumidora por par hostname e usuário | Opção explícita para retomar os próprios itens em processamento, com o limite documentado e testado |
| C7 | Fila: ordem | A consulta não tem `ORDER BY` | — | Ordem indefinida | Componente | Critério de ordem, ou "sem garantia" | Não escolher; a ordem entra no mapa do consumidor |
| C8 | Fila: atomicidade da captura | `SELECT` seguido de `UPDATE`, sem condição de estado nem bloqueio | Regra funcional da resposta 4 | Duas execuções podem capturar o mesmo item | Componente | Aceitar uma forma atômica que preserve a regra | `UPDATE` condicionado ao estado e verificado pelas linhas afetadas, ou `UPDATE TOP (1) ... OUTPUT` com dicas de bloqueio no SQL Server; teste de concorrência no banco real |
| C9 | Fila: dialeto | `TOP`, `GETDATE()`, `DECLARE` | Banco na versão mais recente | Exige Provider SQL Server, com driver de terceiros (DS-3) | Componente | Confirmar SQL Server, versão e driver | — |
| C10 | Fila: identificador da execução | Colunas `int` `[ID DE EXECUÇÃO]` e `idfluxosexec`; tabelas `FluxosExecucao` e `SubFluxosExecucao` no schema de logs | — | O `execution_id` do Core é texto (32 caracteres); a fila precisa de um inteiro de uma tabela do consumidor | Componente | Origem do `IdFluxoExec` e significado de `[ID DE EXECUÇÃO]` | O consumidor fornece o valor; a plataforma não cria a tabela de execuções |
| C11 | Fila: tentativas | Padrão 3; intervalo sem padrão; a captura não usa `tentativas` | Parametrizável | Semântica indefinida | Componente | Repetição dentro da mesma execução ou nova captura em execução posterior; intervalo padrão | — |
| C12 | Notificações: limite | Seção 4 propõe `max_per_execution = 20` | Sem limite predefinido; sem agrupamento | O limite sai da proposta | Não bloqueante | — | Sem limite; contador de envios para observação |
| C13 | Notificações: `required` | Resposta 5 fala das notificações durante a execução; a seção 4 trata também do ciclo de vida | Parametrizável durante a execução | Não estender a regra automaticamente aos avisos de início e fim | Não bloqueante para o contrato | Regra dos avisos de ciclo de vida | Manter a seção 4 como proposta explícita até a decisão |
| C14 | Notificações: tokens | No Exchange Online, a autenticação básica do SMTP será desligada por padrão no fim de 2026 (RFC-0007, seção 6); webhook de Workflows não é OAuth | Autenticação com tokens | O mecanismo depende do canal | Componente (Providers) | Canal e ambiente reais | — |
| C15 | Notificações: idioma | ADR-0017: mensagens em inglês; seção 3: texto padrão em inglês | PT-BR formal | Conflito com ADR aceita | Componente | Alcance da ADR-0017 para textos destinados a pessoas | Emenda: código e logs em inglês; textos para pessoas configuráveis, com padrão PT-BR |
| C16 | Logs: concorrência | A RFC-0009 trava só entre threads; `[Hostname]_[UserMachine].txt` coincide para duas execuções do mesmo usuário na mesma máquina | Vários processos na mesma pasta | Anexar no mesmo arquivo a partir de processos diferentes não é seguro no Windows sem trava | Componente | Um arquivo por processo ou trava de arquivo | Arquivo por processo (PID ou execução no nome); trava exigiria testes nos dois sistemas |
| C17 | Registros: falha | RFC-0001, seção 9, e docstring do port: falha do destino vira erro de teardown | Ignorar, sem alterar o status | Mudança de comportamento do Core | Resolvido nesta entrega (seção 7) | — | Aviso no log e métrica `orchestrator.record_sink.errors` |
| C18 | Logs em SQL | Schema com `PA0000`, `FluxosExecucao`, `SubFluxosExecucao` e `Ambiente` em D/H/P | Alternativa ao TXT | Nomes do consumidor | Componente | Gravar linhas de log em SQL é necessário agora? Consulta manual em arquivo basta? | Mapa configurável; nenhum nome fixo; nunca criar nem alterar tabelas |
| C19 | Logs em TXT | A RFC-0009, 2.1, propôs só um guia | Estrutura de pastas por etapa, subetapa e data | Exige um componente (handler de `logging`) | Componente | Significado de "etapa" e "subetapa"; onde vai a linha fora de subetapa; quem apaga os vencidos | Handler só com a biblioteca padrão, em pacote próprio ou em `orchestrator_core.logs` (decidir) |
| C20 | Mapeamentos: modelo | Seção 3 é tabular (`lookup` por colunas) | Localização de elementos de interface | O contrato precisa ser refeito | Componente | Exemplo real e tecnologia de automação de interface | — |
| C21 | Mapeamentos: versão | Seção 4: `expected_version` | Nunca fixar | Sai da proposta; o hash carregado continua registrado | Não bloqueante | — | — |
| C22 | Mapeamentos: atualização | Seção 3: imutável durante a execução | "Sempre a versão mais atualizada" | Uma execução longa não veria alteração feita durante ela | Não bloqueante | Confirmar se vale por execução ou por consulta | Por execução |
| C23 | Calendário: fim de semana | Resposta 6, literal | Sábado e domingo são dias úteis | Só feriados cadastrados deixam de ser úteis | Componente (confirmação) | Confirmar | Fim de semana sem padrão, como na seção 2; a resposta vira configuração vazia |
| C24 | Calendário: cálculos | "útimo"; "último dia útil" | — | Semântica ambígua | Componente | Definir os dois cálculos | — |
| C25 | Calendário: fuso | Seção 6: fuso declarado (`zoneinfo`, `tzdata` no Windows) | Fuso da máquina | Sem dependência; o resultado depende da máquina | Não bloqueante | — | Data local da máquina; o fuso efetivo vai para o log |
| C26 | Autenticação | Sem sistema real nem Capability de acesso (navegador, desktop, HTTP) | Interativa e por token | — | Futuro | Sistema real e Capability de acesso | Não criar `orchestrator-auth` agora |
| C27 | Core 0.2: zero | A instrução de 2026-11-15 dava o zero como não decidido; a RFC-0005 diz "poderá ser desligado se for 0" | Resposta gravada | Implementado: zero desliga o limite | Não bloqueante | Confirmar | Registrar o risco: teardown sem limite pode prender o processo |
| C28 | Subetapas padrão | RFC-0005, resposta 3 | Subetapas padrão, como a de finalização dos sistemas | Sem lista, nomes nem escopo | Componente (só as subetapas padrão) | Seção 8, item 2 | — |
| C29 | Finished obrigatório | RFC-0005, resposta 4 | Toda automação passa pelo Finished | O Core publica `ExecutionFinished` em todo encerramento que passa por `Runtime.run`; nada é possível em encerramento forçado (`TerminateProcess`, `SIGKILL`, queda de energia) | Não bloqueante (limite físico) | Como as automações são encerradas em produção | Guia de sinais (implementado); um supervisor externo pode apontar execuções sem Finished |
| C30 | Governança: merge | ADR-0018: squash; PRs #1 e #2 com merge commit | — | Histórico com merges | Não bloqueante | Permitir só squash nas configurações do repositório | Ação do responsável |
| C31 | Governança: branch | `dependabot/pip/...` continua no remoto depois do merge | — | — | Não bloqueante | Remover a branch | Ação do responsável |
| C32 | Documentos desatualizados | `DECISIONS.md` e o roadmap diziam que o remoto estava inacessível | — | — | Resolvido nesta entrega | — | — |
| C33 | Versões das ferramentas | A CI usa as versões novas; esta sessão, as anteriores | — | Diferença possível de lint ou formatação | Não bloqueante | — | A CI do PR é a evidência com as versões novas |
| C34 | Visibilidade | Repositório público; a ADR-0017 deixou a decisão ao responsável | — | — | Não bloqueante | Confirmar que é intencional | — |

## 6. Aceite e bloqueios por RFC e parte

"Implementado" significa: na árvore de trabalho, sem commit, testado nesta sessão (relatório na seção 7). Nenhuma parte foi marcada como aceita.

| RFC | Parte | Decisão | Implementação | Bloqueio restante |
|---|---|---|---|---|
| 0004 | Seção 2, regras | Proposta | — | Regra 5 em conflito com a resposta 1 (C3). A regra 6 (um pacote por PR) não é norma da governança: a 0.2 do Core, do SQL e do SQLite precisa de um PR único, por causa da igualdade exata da API (ADR-0009) |
| 0004 | Seção 3, onde cada item mora | Proposta | — | Itens 5 (TXT), 6 (localizadores), 7 (autenticação) e 8 (SQL cifrado) mudam com as respostas |
| 0004 | Seção 4, DS-1 a DS-8 | Pendente | — | Seção 4 |
| 0004 | Seção 5, sequência | Revista no roadmap, Fase 7 | — | — |
| 0005 | 2.1 Mascaramento (`ctx.redact`, `ExecutionOutcome.error_info`) | Sem pergunta própria; incluída na direção de 2026-11-15 | Implementado | Aceite formal |
| 0005 | 2.2 Orçamento de teardown | Respondida: 60 s, zero desliga | Implementado | Aceite formal, inclusive das consequências listadas em 2.2 |
| 0005 | 2.3 Subetapas | Respondida: 1.000, aninhamento, registro | Implementado | Aceite formal; subetapas padrão pendentes (C28) |
| 0005 | 2.4 Encerramento por sinal | Respondida em parte | Implementado: guia, exemplos, teste em subprocesso | Aceite formal; Windows só na CI |
| 0006 | 2.1 `connect(secrets)` | Respondida: opção A | Implementado em `orchestrator-sql` e `orchestrator-sqlite` 0.2.0 | Aceite formal |
| 0006 | 2.2 `orchestrator-keyvault` | Política respondida | — | DS-3, DS-4, cofre real, proxy; cache por execução exige mudança no `SecretStore` do Core |
| 0006 | 2.3 `SecretStore.protect` | Opcional | — | Sem caso de uso |
| 0006 | 2.5 Segredos em SQL | Conflitante | — | C4 |
| 0007 | Resposta 6: lista de estágios no contexto | Respondida | Implementado (`ExecutionContext.stages`) | Aceite formal |
| 0007 | Capability e Providers | Parcial | — | C3, C12 a C15, DS-3 se houver dependência |
| 0008 | Capability e Provider SQL | Parcial | — | C3, C5 a C11, DS-1, DS-3, limite de linhas no SQL e Provider SQL Server |
| 0009 | Resposta 6: falha de destino ignorada | Respondida | Implementado | Aceite formal |
| 0009 | 2.1 e 2.2, arquivos | Parcial | — | C16, C19 |
| 0009 | 2.3, SQL | Condicional | — | C18, DS-1 |
| 0010 | Toda | Parcial | — | C3, C20, C22 |
| 0011 | Toda | Parcial | — | C3, C23, C24, formato da fonte |
| 0012 | Toda | Condicional | — | C26 |

## 7. O que avançou sem nova decisão

Critério: resposta explícita do responsável, nenhuma regra de negócio suposta, Core só com a biblioteca padrão, reversível antes do merge.

| Fatia | Origem | Conteúdo |
|---|---|---|
| 1. Core 0.2.0 | RFC-0005 (2.1 a 2.4); RFC-0007, resposta 6; RFC-0009, resposta 6 | `ctx.redact`; `ExecutionOutcome.error_info`; `runtime.teardown_timeout` (60 s; zero desliga); `ctx.step` com aninhamento, eventos, métrica, campo `step` nos logs, `runtime.max_steps` (1.000) e subetapas no resultado e no registro; `ctx.stages`; falha de destino de registro sem efeito no status; guia de encerramento por sinal e exemplos; `CORE_API_VERSION = "0.2"` |
| 2. Port SQL 0.2.0 | RFC-0006, 2.1, opção A | `SqlProvider.connect(secrets)`; `SqlCapability.open` entrega `ctx.secrets`; suíte de conformidade e teste de valor-sentinela com um Provider de teste que usa senha por referência; SQLite 0.2.0 |

Resultados dos testes, arquivos e limites: [IMPLEMENTATION_ROADMAP](../IMPLEMENTATION_ROADMAP.md), Fase 7, e o CHANGELOG de cada pacote.

## 8. Decisões pedidas ao responsável, por prioridade

1. **Aceite formal das partes implementadas** (seção 6), antes de abrir o PR da 0.2.0. Opções: aceitar tudo, aceitar por parte, ou pedir mudanças.
2. **Subetapas padrão.** O que a "finalização dos sistemas" cobre e com que nome entra no registro. Opções: (a) o estágio `finalize` (finalizers e liberação de recursos, que o Core já registra como estágio) passa a aparecer também como subetapa padrão; (b) um encerramento de processos do sistema operacional, ligado ao DS-7; (c) as duas coisas. Quais outras subetapas padrão a plataforma deve definir.
3. **Notificações.** Canal e ambiente reais; tipo de token; alcance da ADR-0017 para textos em PT-BR; regra de `required` para os avisos de ciclo de vida.
4. **Fila.** Banco, versão e driver; intenção da captura de itens Processando do mesmo hostname e usuário; ordem; o que é uma tentativa e o intervalo padrão; origem do identificador inteiro da execução; uso da mesma sessão SQL para a atomicidade.
5. **Logs em TXT.** O que são "etapa" e "subetapa" no caminho; um arquivo por processo ou trava; quem apaga os arquivos vencidos; se o SQL de logs é necessário agora.
6. **Segredos em SQL.** Abrir a RFC de segurança, ou adotar referências no SQL com o valor no cofre.
7. **Calendário.** Confirmar que sábado e domingo são dias úteis; definir "próximo dia útil" e "último dia útil"; formato e local das fontes manuais.
8. **Mapeamentos.** Duas ou três entradas reais, o formato do arquivo e a tecnologia de automação de interface.
9. **DS-1, DS-3 e DS-4**, antes do primeiro pacote novo com Provider sobre a Capability SQL ou com dependência de terceiros.
10. **Governança do GitHub.** Permitir só squash; remover a branch do PR #2; confirmar que o histórico de julho foi substituído de propósito; confirmar a visibilidade pública.

## 9. Decisões posteriores (2026-11-15, 15h56)

Acréscimo; as seções 1 a 8 ficam como estavam. Na instrução de 2026-11-15, 15h56, o responsável respondeu aos itens 1, 2 e 6 da seção 8 com decisões de encaminhamento, sem aceitar RFCs ([DECISIONS](../DECISIONS.md), seção 4).

| Item da seção 8 | Conflito | Decisão (DECISIONS, seção 4) | Situação |
|---|---|---|---|
| 1. Aceite formal das partes implementadas | C1 | DE-1: implementações 0.2.0 aprovadas integralmente; as RFCs continuam em proposta | Parcial. O `GOVERNANCE.md`, seção 5, continua pedindo RFC aceita antes da implementação; o merge depende do aceite das partes ou de uma exceção de governança registrada ([consolidação](CORE_020_CONSOLIDATION.md), seção 9) |
| 2. Subetapas padrão | C28 | DE-2: opção C | Proposta técnica na [RFC-0014](../rfc/0014-subetapas-padrao-de-finalizacao.md), não aceita |
| 6. Segredos em SQL | C4 | DE-3: RFC de segurança, sem implementação | [RFC-0013](../rfc/0013-segredos-em-sql-avaliacao-de-seguranca.md), não aceita |

Os demais itens da seção 8 continuam sem resposta. A consolidação do Core 0.2.0 (DE-4) está em [CORE_020_CONSOLIDATION](CORE_020_CONSOLIDATION.md). Desde a consolidação, o que as seções 6 e 7 descrevem como "na árvore de trabalho, sem commit" está na branch local `feature/core-0.2`, ainda sem push.

## 10. Depois do aceite das RFCs (2026-11-15, noite)

Acréscimo; as seções 1 a 9 ficam como estavam. O responsável aceitou todas as RFCs ativas, exceto 0013 e 0014 ([DECISIONS](../DECISIONS.md), seção 5). O aceite autoriza a implementação, mas não resolve sozinho os conflitos da seção 5.

### 10.1 Situação dos conflitos

| Conflito | Situação |
|---|---|
| C1 | Resolvido pelo aceite (DECISIONS, pendência 7) |
| C16, C19 | Implementado com hipóteses, a confirmar: um arquivo por processo (PID no nome); etapa = estágio do pipeline; subetapa = `ctx.step`; pasta `_` fora de subetapa; o destino remove os próprios arquivos vencidos (`orchestrator-records-file`, README) |
| C17 | Resolvido no Core 0.2.0 |
| C18 | Sem implementação: a resposta 2 da RFC-0009 pede só consulta manual, e a seção 2.3 recomenda, nesse caso, carregar os arquivos JSON Lines por um processo externo. O destino SQL dependeria também de mudar o port `ExecutionRecordSink` (DS-2) |
| C23, C24, C25 | Aplicados como configuração e contrato, a confirmar: `weekend = []` para sábado e domingo úteis; as duas leituras de "último dia útil" pelo contrato existente; data e fuso efetivo da máquina no log (`orchestrator-calendar`, README) |
| C5 a C11 | Fila bloqueada: transação comum com o negócio (C5), recuperação de itens (C6), ordem (C7), captura atômica (C8), SQL Server com driver de terceiros (C9, bloqueado também pela D-28), identificador da execução do consumidor (C10) e semântica das tentativas (C11) |
| C20, C22 | Mapeamentos bloqueados: o contrato da RFC-0010 precisa ser refeito para localizadores de interface, com um exemplo real e a tecnologia de automação de interface (C20) |
| C26 | Autenticação por sistema bloqueada: exige uma Capability de acesso (navegador, desktop ou HTTP) e um sistema real. O exemplo com o Google pedido no aceite da RFC-0012 depende de um navegador automatizado, dependência de terceiros (D-28) |
| C27 | A confirmar: zero desliga o limite do teardown |

### 10.2 Respostas das RFCs 0013 e 0014

As sete perguntas de cada uma estão respondidas nos próprios arquivos; nenhuma ficou sem resposta. As duas continuam "Proposta. Não aceita". Pontos que o aceite precisará decidir:

| RFC | Resposta | Ponto |
|---|---|---|
| 0013 | 2 e 3 | Criptografia própria em Python com chave num certificado do Windows. A biblioteca padrão não tem criptografia autenticada: seria preciso uma biblioteca de terceiros (D-28) e revisão de segurança. A chave administrada por uma única pessoa é um risco de custódia e de continuidade, e o certificado do Windows não existe em Linux |
| 0013 | 6 | Usar o cofre e, se não for possível, SQL (opção B), de forma configurável: é a opção B como alternativa, com os controles mínimos da seção 6 |
| 0013 | 7 | Instalar dependências e criar tabelas e usuários na primeira etapa conflita com a D-15 (`provision_dependencies` nunca instala pacotes), com a ADR-0019 (o schema pertence ao consumidor) e com o menor privilégio (criar usuários exige direitos de administrador) |
| 0014 | 1 | Prefixo `PA[número]`: o número vem do consumidor, como em C10 |
| 0014 | 5 | Encerrar processos pelo nome, sem limites, na máquina de execução: pode encerrar processos de outras execuções e usuários (a RFC-0008 permite execuções simultâneas na mesma máquina). Continua vedado sem contrato e autorização explícitos |
| 0014 | 7 | Tempo controlado pelo item da fila, com uma tentativa a mais no item: depende da fila (C6, C11) |

### 10.3 Achado de revisão

`SecretRef.parse` aceita qualquer esquema. Um valor literal com dois-pontos, como uma URL de webhook colada no lugar da referência, vira uma referência com esquema `https` e só falha na resolução, com a mensagem "no secret resolver registered for scheme 'https'", sem expor o alvo. O canal do Teams recusa esse caso na configuração. Validar os esquemas contra os resolvedores registrados ao construir o Runtime mudaria um comportamento público do Core: fica como proposta para a 0.3.

