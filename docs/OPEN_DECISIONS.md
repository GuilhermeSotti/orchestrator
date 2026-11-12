# Decisões em aberto — Orchestrator

| Campo | Valor |
|---|---|
| Atualizado em | 2026-11-11, após a auditoria inicial (`docs/audit/INITIAL_AUDIT.md`) e a auditoria do código (`docs/audit/CODE_AUDIT.md`) |
| Substitui | A lista de 24 perguntas do kit de contexto; todas foram preservadas e mapeadas na seção 6 |
| Natureza | **Nenhum item abaixo é decisão tomada.** Cada um traz problema, alternativas, recomendação e a forma de registro. A decisão cabe ao responsável pelo projeto |

Como ler:

- **Recomendação** é a posição técnica desta auditoria, para ser aceita, ajustada ou rejeitada.
- **Formalização** indica o registro exigido por `GOVERNANCE.md`: ADR em `docs/adr/` para decisão arquitetural; RFC para funcionalidade grande.
- **Bloqueia** aponta a fase de `docs/IMPLEMENTATION_ROADMAP.md` que não deve começar sem a decisão.
- IDs como ARQ-01 remetem aos achados da auditoria inicial; IDs como COD-01, SQL-01, CI-01 e GOV-05 remetem aos achados da auditoria do código.

---

## 1. Quadro geral

| ID | Tema | Recomendação resumida | Formalização | Bloqueia |
|---|---|---|---|---|
| D-00 | Destino do scaffold existente | Arquivar como referência e reconstruir a partir de contratos | ADR | Fases 2 e 3 |
| D-01 | Papel deste repositório e localização do código | Manter multirrepositório: governança aqui, Core em `orchestrator-core` | ADR | Fases 1 e 3 |
| D-02 | Forma da Public API | Biblioteca Python primeiro; spec e CLI fora do Core | ADR | Fase 2 |
| D-03 | Fronteiras e dono de cada contrato | Core só com contratos transversais; cada Capability define o seu port | ADR | Fase 2 |
| D-04 | Dependências permitidas no Core | Pydantic como única dependência, restrita às fronteiras de dados | ADR | Fase 2 |
| D-05 | Execução síncrona ou assíncrona | Síncrono no MVP, sem impedir runtime assíncrono futuro | ADR | Fase 2 |
| D-06 | Falha, teardown, cancelamento e timeout | Teardown sempre executa; erro primário preservado; cancelamento cooperativo | RFC | Fase 3 |
| D-07 | Execution Context | Identidade imutável, estado explícito, um contexto por execução | RFC (com D-06) | Fase 3 |
| D-08 | Configuração e segredos | Argumentos > ambiente > arquivo TOML > defaults; segredos por referência | ADR | Fase 3 |
| D-09 | Dependency Injection | Injeção por construtor e raiz de composição; sem contêiner | ADR | Fase 3 |
| D-10 | Registry e descoberta de plugins | Registro explícito no MVP; descoberta com lista de permissão depois | ADR; RFC para descoberta | Fase 3 |
| D-11 | Compatibilidade entre pacotes | Faixas SemVer mais verificação em tempo de registro | ADR | Fase 4 |
| D-12 | Retry | Política e utilitário no Core; aplicação sempre explícita | ADR | Fase 3 |
| D-13 | Event Bus | Síncrono, em processo, falha de handler isolada | ADR | Fase 3 |
| D-14 | Logging, métricas e tracing | `logging` da biblioteca padrão com contexto e redação; métricas por port sem implementação padrão | ADR | Fase 3 |
| D-15 | Estágio Provision Dependencies | Verificar e inicializar capabilities; nunca instalar pacotes em tempo de execução | ADR | Fase 3 |
| D-16 | Persistência e estágio Persist Logs | Core sem contrato de persistência de dados; apenas descarga de logs e do registro da execução | ADR | Fase 3 |
| D-17 | Versões de Python e plataformas | `>=3.13`; Windows e Linux no CI | ADR | Fase 1 |
| D-18 | Build, dependências e lockfile | Manter setuptools; grupos de dependência e lockfile; uma só fonte de verdade | ADR | Fase 1 |
| D-19 | Controles mínimos de CI e GitHub | Proteção de `main`, checks obrigatórios, ações fixadas por SHA; verificar o que o plano permite | ADR | Fase 1 |
| D-20 | Escopo do MVP e publicação | Escopo do roadmap; distribuição inicial por tag e wheel em release | RFC | Fase 3 |
| D-21 | Testes entre repositórios | Kit de testes no Core e workflows reutilizáveis | ADR | Fase 4 |
| D-22 | Itens futuros | Fora do escopo até 1.0; cada um exige RFC | Registro no roadmap | — |
| D-23 | Titularidade, licença, nomes, idioma e visibilidade | Decisão do responsável | Registro em GOVERNANCE | Fase 1 |
| D-24 | Convenções de commit, branch e merge | Conventional Commits, squash merge, prefixos `docs/*` e `chore/*` | Atualização de GOVERNANCE | Fase 1 |
| D-25 | Convenções de fila e de schema embutidas no pacote SQL | Retirar da plataforma; manter no consumidor ou em pacote próprio da organização | ADR | Fase 4 |

---

## 2. Decisões que bloqueiam tudo

### D-00 — Destino do scaffold existente

- **Problema.** O scaffold de `orchestrator_core` e o pacote `orchestrator_sql` entraram sem ADR ou RFC. A auditoria do código mostrou que o Core não executa a automação do consumidor (COD-01), não garante finalização (COD-02), tem dois defeitos graves no `ProcessRunner` (COD-03, COD-04) e mantém 18 de 38 módulos sem consumidor (COD-08). O pacote SQL embute regras de negócio de um consumidor (SQL-01) e monta SQL com texto não validado (SQL-02).
- **Alternativas.**
  - A. Adotar como base e refatorar incrementalmente.
  - B. Arquivar como referência (branch ou tag) e reconstruir o Core a partir dos contratos aprovados, reaproveitando testes e ideias.
  - C. Descartar.
- **Trade-offs.** A preserva o trabalho, mas herda decisões implícitas (execução por spec, ports sem consumidor, três runners, falha sem finalização) que precisam ser desfeitas antes de avançar, e exige corrigir os defeitos listados. B custa reescrever um volume pequeno (738 linhas não vazias no Core) e faz cada contrato nascer de uma decisão registrada. C não traz ganho sobre B.
- **Recomendação.** B. As razões estão na seção 12 de `docs/audit/CODE_AUDIT.md`, e o que pode ser reaproveitado, na seção 11. Antes de arquivar, é preciso recuperar o Git e commitar o estado atual, que inclui 21 arquivos nunca versionados.
- **Impacto.** Define o ponto de partida das Fases 2 e 3. Com A, a Fase 3 é substituída por um backlog de correções.
- **Formalização.** ADR. **Status:** aberta; pronta para decisão.

### D-01 — Papel deste repositório e localização do código

- **Problema.** README, ARCHITECTURE e GOVERNANCE definem estratégia multirrepositório, com este repositório como base de governança. A árvore rastreada contém `pyproject.toml` com `name = "orchestrator-core"`, `src/orchestrator_core/` e `packages/orchestrator_sql/` (ARQ-01). O remoto se chama `orchestrator`; a documentação o chama de `orchestrator-platform` (GOV-03).
- **Alternativas.**
  - A. Multirrepositório, como documentado: este repositório fica só com governança; o Core vai para `orchestrator-core`; o pacote SQL vai para `orchestrator-sql` quando a Fase 4 começar.
  - B. Monorepo com vários pacotes distribuíveis em `packages/`, CI única e versão por pacote.
  - C. Incubação: manter o Core aqui até os contratos estabilizarem e separar depois.
- **Trade-offs.**
  - A isola responsabilidades, permite cadência de release independente e torna fisicamente impossível uma dependência de infraestrutura vazar para o Core. Custa coordenação entre repositórios enquanto os contratos mudam e alguma duplicação de configuração, mitigável com workflows reutilizáveis.
  - B permite mudanças atômicas e refatoração barata enquanto os contratos são instáveis. Contraria a estratégia documentada, exige ferramental de versão e release por pacote e facilita acoplamento.
  - C dá velocidade agora e transfere o custo da separação para depois, com ambiguidade no período.
- **Recomendação.** A, começando com **exatamente dois repositórios**: governança e `orchestrator-core`. Capabilities e Providers só ganham repositório na Fase 4. O custo com dois repositórios é baixo e a decisão documentada é preservada. Se a prioridade for velocidade de iteração, B ou C são defensáveis, desde que um ADR reverta explicitamente a estratégia.
- **Impacto.** Movimentação de arquivos, CI, Dependabot e documentação. Nenhum impacto em API pública, pois nada foi publicado.
- **Formalização.** ADR-0001. **Status:** aberta.

### D-02 — Forma da Public API

- **Problema.** Não está definido como um projeto consumidor usa o Orchestrator. O scaffold lê uma spec JSON por uma CLI e percorre três estágios, mas a spec só contém nomes de tarefas: nada liga esses nomes a código, e o estágio de execução apenas os registra (COD-01, COD-12).
- **Alternativas.**
  - A. Biblioteca: o consumidor importa o pacote, compõe o Runtime em Python e entrega a sua automação como função ou objeto.
  - B. Spec declarativa (JSON ou YAML) interpretada por uma CLI ou engine.
  - C. Biblioteca no Core; CLI e spec como camada opcional, em pacote separado, mais tarde.
- **Trade-offs.** A mantém a lógica de negócio como código do consumidor, com tipagem e testes comuns. B exige schema versionado, modelo de segurança para import dinâmico e caminhos de arquivo, e desloca lógica para um formato que tende a virar o workflow engine listado como evolução futura. C adia B sem fechá-lo.
- **Recomendação.** C: biblioteca primeiro; nenhum interpretador de spec no MVP.
- **Esboço ilustrativo** (não é contrato aprovado; os nomes são hipotéticos):

  ```python
  from orchestrator_core import ExecutionContext, RuntimeBuilder


  def conciliar_faturas(ctx: ExecutionContext) -> None:
      """Lógica de negócio: pertence ao projeto consumidor."""


  runtime = RuntimeBuilder().with_config_file("orchestrator.toml").build()
  result = runtime.run(conciliar_faturas)
  result.raise_for_status()
  ```

- **Impacto.** Define a superfície pública e o exemplo de consumidor.
- **Formalização.** ADR-0002. **Status:** aberta.

---

## 3. Contratos do Core

### D-03 — Fronteiras entre Core, Runtime, Capability e Provider

- **Problema.** ARCHITECTURE diz que Providers implementam "contracts defined by the Core", mas a regra de dependência passa por Capabilities. O diagrama "Dependency Rule" coloca "Public API" como camada mais interna (DOC-05). O scaffold tem 12 ports dentro do Core, nenhum com consumidor (COD-08), e o pacote SQL concentra contrato e implementação em uma única classe (SQL-08). `ExecutionSpecification`, `ExecutionEngine` e `Runner` existem no código e não fazem parte do vocabulário documentado.
- **Alternativas.**
  - A. O Core define todos os ports, inclusive os de SQL, fila, cache e similares.
  - B. O Core define apenas contratos transversais; cada pacote de Capability define o seu contrato funcional e o port que os Providers implementam.
  - C. Um pacote só de contratos, do qual Core, Capabilities e Providers dependem.
- **Trade-offs.** A simplifica a descoberta, mas faz o Core crescer a cada tecnologia nova, o que contraria "New technologies must be added without changing the Core". B mantém o Core pequeno e alinha a dependência `Provider → Capability → Core`. C acrescenta um pacote e uma matriz de versões sem benefício enquanto houver um único Core.
- **Recomendação.** B.
  - No Core: `Stage`, pipeline, `ExecutionContext`, `ExecutionResult`, contrato genérico de `Capability`, registry, configuração, hierarquia de erros e os ports transversais de logging, métricas, eventos e resolução de segredos.
  - Na Capability: contrato funcional e port do Provider.
  - No Provider: implementação concreta, seleção por configuração explícita e tradução das exceções de infraestrutura para os erros do contrato.
  - "Public API" passa a significar a superfície exportada e documentada de `orchestrator-core`; os demais módulos são internos.
- **Impacto.** Reescrita de dois trechos de ARCHITECTURE; remoção dos ports de capability do Core.
- **Formalização.** ADR-0003. **Status:** aberta.

### D-04 — Dependências permitidas no Core

- **Problema.** SECURITY afirma que o Core nunca depende diretamente de bibliotecas de terceiros; a stack-alvo inclui Pydantic (DOC-06). `requirements.txt` lista SQLAlchemy como dependência do Core (ARQ-02).
- **Alternativas.**
  - A. Nenhuma dependência de terceiros: apenas biblioteca padrão.
  - B. Pydantic 2 como única dependência, usada só em modelos de configuração e na validação de entradas.
  - C. Pydantic em todos os modelos do Core.
- **Trade-offs.** A dá a máxima estabilidade e nenhum conflito de versão com consumidores, ao custo de validação escrita à mão. B traz validação robusta com uma dependência compilada que todos os consumidores herdam. C acopla todos os contratos à API e às versões maiores do Pydantic.
- **Recomendação.** B. Ports, protocolos e exceções ficam em biblioteca padrão. `pydantic-settings` é uma distribuição separada e não entra no MVP. SQLAlchemy sai da lista de dependências do Core. A frase de SECURITY passa a referir-se a bibliotecas de integração.
- **Impacto.** Texto de SECURITY; teste automatizado que verifica o conjunto de imports do Core.
- **Formalização.** ADR-0004. **Status:** aberta.

### D-05 — Execução síncrona ou assíncrona; concorrência

- **Problema.** Não definido. Afeta todos os contratos. O scaffold traz três runners (local, thread e processo) sem decisão registrada: o de thread não acrescenta nada (COD-17) e o de processo trava com resultado grande e ignora o pipeline configurado (COD-03, COD-04).
- **Alternativas.**
  - A. Core síncrono.
  - B. Core assíncrono (`asyncio`), com adaptação de código bloqueante em threads.
  - C. As duas APIs.
- **Trade-offs.** A é a mais simples e combina com bibliotecas de automação bloqueantes; o timeout só pode ser cooperativo ou imposto no nível do processo, porque não há forma segura de interromper uma thread. B oferece cancelamento e timeout nativos e concorrência de E/S, mas impõe `async` a todo consumidor, e o trabalho bloqueante continua em threads não canceláveis. C duplica superfície e testes.
- **Recomendação.** A no MVP, sem runners de thread ou de processo dentro do Core. Uma execução por chamada; paralelismo entre execuções fica com quem invoca, de preferência em processos separados. Os contratos não devem impedir um runtime assíncrono futuro: contexto passado explicitamente, sem estado em thread-local, `contextvars` apenas para correlação de logs.
- **Impacto.** Contratos de `Stage` e de `Capability`.
- **Formalização.** ADR-0005. **Status:** aberta.

### D-06 — Falha, teardown, cancelamento, timeout e erros

- **Problema.** A documentação lista 8 estágios e não define o que acontece quando um deles falha, é cancelado ou excede o prazo. No scaffold, o pipeline padrão tem 3 estágios (COD-07); falha ou exceção encerram a execução sem finalização (COD-02); exceções são engolidas (COD-05); `timeout`, `retries` e o resultado `RETRY` não têm efeito (COD-06). Um teste fixa a parada sem finalização.
- **Alternativas.**
  - A. Interromper na primeira falha, sem garantia de finalização.
  - B. Fases de preparação, execução e teardown; o teardown sempre executa.
  - C. Compensação por estágio, com operação de desfazer para cada um.
- **Trade-offs.** A vaza recursos. B é previsível e testável. C é mais do que o MVP precisa.
- **Recomendação.** B, com a semântica abaixo.

  | Situação | Comportamento proposto |
  |---|---|
  | Classificação dos estágios | Preparação: Initialize, Provision Dependencies, Prepare Environment, Prepare Execution. Execução: Execute Automation. Teardown: Finalize, Persist Logs, Shutdown |
  | Falha na preparação | Os estágios seguintes de preparação e a execução não rodam; o teardown roda |
  | Falha em Execute Automation | O teardown roda; o erro original é preservado |
  | Falha em estágio de teardown | Os demais estágios de teardown ainda rodam; o erro é agregado e não mascara o erro primário |
  | Teardown | Roda sempre que Initialize tiver começado; cada estágio é idempotente e tolera inicialização parcial |
  | Recursos | Registrados em um escopo da execução e liberados em ordem inversa durante Shutdown |
  | Cancelamento | Cooperativo, por sinalizador no contexto; `KeyboardInterrupt` e `SystemExit` são relançados depois do teardown |
  | Timeout | Prazo cooperativo por execução e, opcionalmente, por estágio; interrupção forçada fica fora do Core |
  | Resultado | `run()` devolve um resultado com status (`SUCCEEDED`, `FAILED`, `CANCELLED`, `TIMED_OUT`), desfecho por estágio e erros; só lança exceção para erro de uso ou de configuração anterior ao início |
  | Erros | Hierarquia com raiz única, que distingue configuração, estágio, capability e provider, e marca o que é repetível |

- **Fora do MVP.** Checkpoint, retomada, pausa e execução parcial.
- **Impacto.** Núcleo do Runtime; a matriz de testes de falha deriva desta tabela.
- **Formalização.** RFC-0001. **Status:** aberta.

### D-07 — Execution Context

- **Problema.** Conteúdo, mutabilidade, escopo e isolamento não definidos.
- **Alternativas.**
  - A. Identidade e serviços imutáveis, mais um espaço de estado explícito pertencente ao consumidor.
  - B. Contexto totalmente mutável, em estilo dicionário.
- **Trade-offs.** B é flexível e cria acoplamento oculto entre estágios. A torna o fluxo de dados visível.
- **Recomendação.** A. O contexto carrega identificador da execução, nome da automação, instante de início em UTC, configuração validada somente leitura, acesso a logger, eventos, métricas e capabilities, sinalizador de cancelamento e prazo. Um contexto por execução, nunca compartilhado; nenhum "contexto corrente" global.
- **Impacto.** Assinatura de todos os estágios e capabilities.
- **Formalização.** RFC-0001. **Status:** aberta.

### D-08 — Configuração e segredos

- **Problema.** Precedência, formato, validação e tratamento de segredos não definidos.
- **Alternativas de formato.** TOML (leitura pela biblioteca padrão), YAML (exige dependência), JSON (sem comentários), arquivos `.env` (exigem dependência e são fáceis de versionar por engano).
- **Recomendação.**
  - Precedência: argumentos explícitos, depois variáveis de ambiente com prefixo próprio, depois arquivo TOML, depois defaults documentados.
  - Validação na inicialização, com falha imediata e mensagem que identifica a chave.
  - Segredos nunca em arquivo de configuração. A configuração guarda uma referência; o valor é obtido por um port de resolução de segredos no momento do uso, fica em tipo que não aparece em `repr` nem em logs e não é incluído em eventos.
  - O Core não carrega `.env`.
- **Impacto.** Módulo de configuração; filtro de redação de logs.
- **Formalização.** ADR-0006. **Status:** aberta.

### D-09 — Dependency Injection

- **Problema.** Mecanismo de composição e escopos não definidos.
- **Alternativas.**
  - A. Injeção por construtor e uma raiz de composição (builder), sem contêiner.
  - B. Registro interno de serviços por tipo, com escopos.
  - C. Contêiner de terceiros.
- **Trade-offs.** A é explícita e testável com substituição direta de objetos. B e C trazem resolução implícita e, no caso de C, uma dependência que o Core não justifica.
- **Recomendação.** A. Dois escopos: do Runtime (configuração, registry, destinos de log) e da execução (contexto e escopo de recursos). Nenhum singleton de módulo.
- **Formalização.** ADR-0007. **Status:** aberta.

### D-10 — Capability Registry e descoberta de plugins

- **Problema.** Forma de registro, conflitos de nome, versões, carregamento e nível de confiança não definidos. SECURITY exige revisão de segurança para carregamento de plugins. No scaffold, o registry não tem contrato e o registro duplicado deixa dois objetos ativos (COD-10); `discover()` carrega e executa todo entry point do grupo, sem lista de permissão (COD-11).
- **Alternativas.**
  - A. Registro explícito em código.
  - B. Descoberta automática por entry points.
  - C. Entry points com lista de permissão na configuração.
  - D. Manifesto próprio.
- **Trade-offs.** B carrega código de qualquer distribuição instalada que declare o grupo. C preserva a conveniência com controle explícito. Enumerar entry points não importa o código do plugin; carregá-lo importa.
- **Recomendação.** A no MVP. C depois, por RFC: enumerar, filtrar pela lista de permissão, verificar a compatibilidade declarada e só então carregar.
  - Chave de registro: o tipo do contrato da capability; duplicidade é erro no registro, salvo substituição explícita.
  - "Plugin seguro": código Python no mesmo processo não pode ser isolado. A confiança vem da instalação controlada e da lista de permissão; isso deve estar escrito na documentação.
- **Formalização.** ADR-0008; RFC para a descoberta. **Status:** aberta.

### D-11 — Compatibilidade entre Core, Capabilities e Providers

- **Problema.** Pacotes independentes precisam declarar e verificar compatibilidade.
- **Alternativas.**
  - A. Faixas de versão nas dependências de cada pacote.
  - B. Versão de contrato exposta pelo Core e verificada no registro.
  - C. Versão única para todos os pacotes.
- **Recomendação.** A e B combinadas: a faixa é resolvida na instalação e o registro falha com mensagem clara se a versão de contrato não for suportada. Antes de 1.0, uma versão menor pode quebrar compatibilidade, e as faixas devem refletir isso. Matriz de compatibilidade publicada no repositório de governança e exercitada no CI.
- **Formalização.** ADR-0009. **Status:** aberta.

### D-12 — Retry

- **Problema.** Política, limites, classificação de erros e idempotência não definidos.
- **Alternativas.**
  - A. O Core oferece a política e um utilitário; quem aplica é a capability ou o consumidor, por operação.
  - B. Reexecução do estágio Execute Automation pelo pipeline.
  - C. Biblioteca de terceiros.
- **Trade-offs.** B repete a automação inteira e só é segura quando ela é idempotente. C adiciona uma dependência para algo pequeno.
- **Recomendação.** A no MVP: tentativas máximas, espera fixa ou exponencial com variação aleatória, tempo total máximo, filtro por tipo de erro. **Padrão: sem retry.** B fica como opção posterior, apenas quando o consumidor declarar a automação idempotente.
- **Formalização.** ADR-0010. **Status:** aberta.

### D-13 — Event Bus

- **Problema.** Garantias de ordenação, entrega e tratamento de falhas não definidas. O `EventBus` do scaffold não é usado pelo pipeline e interrompe a publicação quando um assinante falha (COD-16).
- **Alternativas.**
  - A. Publicação síncrona em processo.
  - B. Barramento assíncrono com fila.
  - C. Integração com broker externo.
- **Recomendação.** A, com contrato mínimo: eventos de lifecycle imutáveis; ordem de publicação preservada; no máximo uma entrega; falha de handler registrada e contabilizada, sem interromper o pipeline; sem persistência. Entrega externa é assunto de Capability.
- **Formalização.** ADR-0011. **Status:** aberta.

### D-14 — Logging, métricas e tracing

- **Problema.** Contratos independentes de backend, contexto e sanitização não definidos. No scaffold, os logs são textos em uma lista na memória, sem nível nem redação (COD-15), e as métricas do runner estão incorretas (COD-13).
- **Recomendação.**
  - Logging: `logging` da biblioteca padrão como API. O Core fornece enriquecimento com identificador da execução e estágio, um filtro de redação e um formatador estruturado opcional. Destinos são handlers.
  - Métricas: port mínimo (contador, medida de duração), com implementação padrão que não faz nada.
  - Tracing: fora do MVP; o identificador de execução basta para correlação.
  - OpenTelemetry, Elastic e similares: pacotes de Provider; o Core nunca os importa.
- **Alternativa descartada.** Biblioteca de logging estruturado de terceiros no Core, por D-04.
- **Formalização.** ADR-0012. **Status:** aberta.

### D-15 — Semântica do estágio Provision Dependencies

- **Problema.** "Dependencies" pode significar pacotes Python, recursos externos ou a montagem das capabilities. SECURITY exige revisão para resolução de dependências.
- **Alternativas.**
  - A. O estágio verifica e inicializa as capabilities declaradas.
  - B. O estágio instala pacotes em tempo de execução.
  - C. Ambos, com opção explícita.
- **Trade-offs.** B e C introduzem risco de cadeia de suprimentos, execução não reprodutível e necessidade de rede e permissões.
- **Recomendação.** A. A instalação de pacotes pertence à construção do ambiente, com lockfile.
- **Formalização.** ADR-0013. **Status:** aberta.

### D-16 — Persistência e estágio Persist Logs

- **Problema.** Não está definido se o Core define contratos de persistência. "Persist Logs" vem antes de "Shutdown", de modo que os logs do próprio Shutdown não seriam cobertos.
- **Recomendação.** O Core não define persistência de dados de negócio. "Persist Logs" grava o registro da execução (status, desfecho por estágio, erros) e descarrega os logs acumulados; os destinos permanecem abertos até o fim de Shutdown. Armazenamento de histórico em banco é Capability futura.
- **Formalização.** ADR-0014, ou seção da RFC-0001. **Status:** aberta.

---

## 4. Stack, qualidade e distribuição

### D-17 — Versões de Python e plataformas

- **Problema.** ARCHITECTURE indica Python 3.13+; `pyproject.toml` declara `>=3.11` (PKG-02). O ambiente de desenvolvimento original e a CI usam Python 3.11 (ENV-01, CI-01). Os testes atuais passam em 3.13 no ambiente de análise. Plataformas não definidas.
- **Alternativas.** `>=3.13`, como documentado; `>=3.12`; `>=3.11`.
- **Recomendação.** `>=3.13`, sem limite superior, com 3.13, 3.14 e 3.15 no CI (a 3.15 é estável desde outubro de 2026). Rever apenas se o primeiro projeto consumidor estiver preso a uma versão anterior. Plataformas: Windows e Linux no CI desde a primeira release; o ambiente de desenvolvimento atual é Windows.
- **Formalização.** ADR-0015. **Status:** aberta.

### D-18 — Build, dependências de desenvolvimento e lockfile

- **Problema.** Duas fontes de verdade divergentes (`pyproject.toml` e `requirements.txt`), sem lockfile, sem Ruff e MyPy declarados (PKG-03); forma de licença depreciada (PKG-04).
- **Alternativas para o backend de build.** setuptools (atual), hatchling, flit-core, uv_build.
- **Alternativas para dependências e lock.**
  - A. `requirements.txt` manual (atual).
  - B. Grupos de dependência no `pyproject.toml` e lockfile gerado por `uv`.
  - C. `pip-tools`, com arquivos compilados e hashes.
  - D. Poetry ou PDM.
- **Recomendação.** Manter setuptools, porque trocar não resolve nenhum problema atual; exigir `setuptools>=77` e usar `license = "MIT"`. Para dependências, B: uma só fonte de verdade, ferramenta única em Windows e CI, lockfile versionado. C é a alternativa para quem prefere ficar apenas com pip. A adoção de uma ferramenta nova é decisão do responsável.
- **Observação.** Grupos de dependência são entendidos pelo pip e pelo uv. O formato padronizado de lockfile `pylock.toml` existe, mas o suporte no pip ainda é experimental.
- **Formalização.** ADR-0016. **Status:** aberta.

### D-19 — Controles mínimos de CI e do GitHub

- **Problema.** GOVERNANCE declara obrigatórios Secret Scanning, Dependabot, CodeQL, Signed Releases e Dependency Review. A configuração no GitHub não é verificável hoje, e parte pode não estar disponível para repositório privado (SEC-01). No repositório, a CI roda apenas `pytest` em Python 3.11 (CI-01); as validações de segurança descritas em SECURITY não existem (CI-02); `CODEOWNERS` e `dependabot.yml` citam equipes cuja existência não é verificável (GOV-05).
- **Recomendação de conjunto mínimo.**
  - Proteção ou ruleset em `main`: PR obrigatório, checks obrigatórios, sem push forçado.
  - CI com `ruff check`, `ruff format --check`, `mypy`, `pytest`, em matriz de versões e sistemas.
  - Workflows com permissões mínimas e ações fixadas por SHA.
  - Dependabot para pip e GitHub Actions, com agrupamento.
  - Secret scanning, push protection, code scanning e dependency review **onde o plano permitir**.
- **Pontos a decidir.**
  1. Em repositório privado, esses quatro últimos dependem dos produtos GitHub Secret Protection e GitHub Code Security, disponíveis nos planos Team e Enterprise; em repositório público são gratuitos. As opções são: tornar o repositório público, contratar os produtos, ou registrar a lacuna e cobri-la com ferramentas executadas no CI. Qualquer ferramenta adicional é dependência nova e precisa de justificativa.
  2. Quantas aprovações um PR exige. O histórico local mostra um único autor de commits; o autor de um PR não pode aprová-lo, de modo que exigir aprovação com mantenedor único bloqueia todo merge. É preciso definir quem revisa ou ajustar a regra de "review approved" da Definition of Done.
- **Formalização.** ADR-0017 e atualização de GOVERNANCE e SECURITY. **Status:** aberta.

### D-20 — Escopo do MVP e forma de publicação

- **Problema.** Escopo do primeiro pacote e canal de distribuição não definidos.
- **Recomendação de escopo.** O da Fase 3 de `docs/IMPLEMENTATION_ROADMAP.md`.
- **Alternativas de distribuição.**
  - A. PyPI público.
  - B. Índice privado compatível com PyPI.
  - C. Sem índice: tag Git e wheel anexado a uma release; instalação por referência.
- **Recomendação.** C para a 0.1.0, por não exigir infraestrutura; decidir entre A e B antes da Fase 5. Se A for uma possibilidade, verificar desde já se o nome `orchestrator-core` está livre no índice.
- **Restrição.** Publicar exige autorização explícita.
- **Formalização.** RFC-0002. **Status:** aberta.

### D-21 — Testes entre repositórios, exemplos e modelos

- **Problema.** Como garantir que Capabilities, Providers, exemplos e modelos continuam compatíveis com o Core.
- **Recomendação.** O Core distribui um módulo de apoio a testes com implementações em memória e uma suíte de conformidade que cada Capability e Provider executa. Os adapters em memória do scaffold servem de base. O repositório de governança mantém workflows reutilizáveis e modelos de repositório. O exemplo de consumidor é instalado a partir do wheel e executado no CI do Core.
- **Formalização.** ADR-0018. **Status:** aberta.

---

## 5. Produto e governança

### D-22 — Itens de evolução futura

- **Problema.** ARCHITECTURE lista execução distribuída, agentes remotos, execução em nuvem, marketplace de plugins, registry de pacotes, dashboards, workflow engine, scheduling e automação assistida por IA.
- **Recomendação.** Todos fora do escopo até a 1.0 do Core. Antecipar qualquer um exige RFC com caso de uso real. Checkpoint, retomada e pausa de execuções entram na mesma regra.
- **Formalização.** Registro no roadmap. **Status:** aberta.

### D-23 — Titularidade, licença, nomes, idioma e visibilidade

- **Problema.** Identidades divergentes (GOV-02), nome do repositório (GOV-03), idioma misto (DOC-07) e visibilidade do repositório, que afeta D-19 e D-20.
- **Pontos a decidir pelo responsável.**
  1. O projeto é pessoal ou de uma organização? Alinhar titular do copyright em `LICENSE`, autores do pacote, conta dona do remoto e contato de segurança.
  2. Nome do repositório de governança: `orchestrator` ou `orchestrator-platform`.
  3. Idioma da documentação. As instruções do projeto pedem português para documentação explicativa; ARCHITECTURE, GOVERNANCE e SECURITY estão em inglês. Escolher por público-alvo e registrar a regra.
  4. Repositório privado ou público.
- **Observação.** Esta auditoria não oferece avaliação jurídica.
- **Formalização.** Registro em GOVERNANCE. **Status:** aberta.

### D-24 — Convenções de commit, branch e merge

- **Problema.** Sem convenção de mensagens (REP-08); os prefixos de branch não cobrem documentação e manutenção (GOV-04); a branch `feature` bloqueia `feature/*` (REP-06); há três locais para registrar decisões: `ADR/`, `docs/adr/` e `docs/decisions/` (GOV-06).
- **Recomendação.** Conventional Commits, já usado no commit `6232d68`; squash merge em `main`; acrescentar `docs/*` e `chore/*` aos prefixos; renomear ou remover `feature`, `feature-core` e `teste`; CHANGELOG com seções por tipo e por versão; ADRs somente em `docs/adr/`, com o modelo que já existe ali, e remoção de `ADR/`.
- **Formalização.** Atualização de GOVERNANCE e CONTRIBUTING. **Status:** aberta.

### D-25 — Convenções de fila e de schema embutidas no pacote SQL

- **Problema.** O pacote `orchestrator_sql` acrescenta a toda tabela a coluna `FluxoExecucaoId` e, por padrão, uma tabela de fila com colunas `Usuario`, `Maquina` e `Ambiente`, estados em português, chave estrangeira fixa para `CORE.FluxosExecucao` e um gatilho que grava `'P'` como ambiente (SQL-01). São regras de um ambiente específico dentro de um pacote da plataforma, o que contraria a regra fundamental de responsabilidade.
- **Alternativas.**
  - A. Mover essas convenções para o projeto consumidor que as usa.
  - B. Criar um pacote próprio da organização, fora do conjunto de pacotes da plataforma, que dependa da Capability SQL e aplique as convenções.
  - C. Manter no pacote SQL como opção desligada por padrão.
- **Trade-offs.** A é a mais simples se houver um único consumidor. B evita duplicação quando várias automações da mesma organização seguem o mesmo modelo de fila. C mantém na plataforma nomes de tabelas e regras que só fazem sentido em um ambiente.
- **Recomendação.** A, ou B se mais de um projeto consumidor usar o mesmo modelo. Em nenhum dos casos a Capability SQL deve conhecer `CORE.FluxosExecucao` ou os valores de `Ambiente`.
- **Impacto.** Escopo da primeira Capability (Fase 4).
- **Formalização.** ADR. **Status:** aberta.

---

## 6. Correspondência com as 24 perguntas originais do kit

| Pergunta original | Decisão |
|---|---|
| 1. Contratos públicos mínimos do primeiro `orchestrator-core` | D-02, D-03, D-20 |
| 2. Fronteira entre Core, Runtime, Capability e Provider | D-03 |
| 3. Descoberta e registro de Capabilities | D-10 |
| 4. Compatibilidade de versões entre pacotes | D-11 |
| 5. Runtime síncrono, assíncrono ou ambos | D-05 |
| 6. Contrato e escopo do Execution Context | D-07 |
| 7. Timeout, retry, backoff, limites e classificação de erros | D-06, D-12 |
| 8. Semântica de falha por estágio e garantia de cleanup | D-06 |
| 9. Checkpoint, retomada, pausa, cancelamento, execução distribuída | D-06 (cancelamento), D-22 (demais) |
| 10. Garantias do Event Bus | D-13 |
| 11. Precedência de configuração | D-08 |
| 12. Declaração e provisionamento de dependências | D-15 |
| 13. Ciclo de vida dos objetos de Dependency Injection | D-09 |
| 14. Isolamento entre execuções e projetos consumidores | D-05, D-07 |
| 15. Contratos de logging, métricas e tracing; OpenTelemetry | D-14 |
| 16. Solicitação, escopo e mascaramento de segredos | D-08 |
| 17. Significado de "plugin seguro" | D-10 |
| 18. Controles de CI e GitHub desde o primeiro pacote | D-19 |
| 19. Escopo do primeiro pacote publicável e critérios do MVP | D-20 |
| 20. Build, versionamento, publicação e retirada de suporte | D-18, D-20, D-11 |
| 21. Matriz de Python | D-17 |
| 22. Plataformas de execução | D-17 |
| 23. Testes de exemplos, modelos e compatibilidade entre repositórios | D-21 |
| 24. Dashboard, scheduling, workflow engine, agentes remotos, nuvem | D-22 |

Decisões acrescentadas pelas auditorias: D-00, D-01, D-02, D-04, D-16, D-23, D-24 e D-25.

---

## 7. Processo de decisão

- Decisão arquitetural significativa: ADR em `docs/adr/`, numerado, com contexto, alternativas, decisão e consequências.
- Funcionalidade grande ou transversal: RFC, com aprovação antes da implementação.
- Uma decisão só sai desta lista quando o ADR ou a RFC correspondente estiver aceito.
- Decisões relacionadas e tomadas em conjunto podem ser registradas em um único ADR. A numeração sugerida neste documento não é obrigatória.
- Escolha de tecnologia considera manutenção, adoção, segurança, licença, cadência de releases e custo operacional.

## Referências

- GitHub Docs — About GitHub Advanced Security: <https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security>
- PEP 735 — Dependency Groups in `pyproject.toml`: <https://peps.python.org/pep-0735/>
- PEP 751 — A file format to record Python dependencies for installation reproducibility: <https://peps.python.org/pep-0751/>
- What's New in Python 3.15: <https://docs.python.org/3/whatsnew/3.15.html>
