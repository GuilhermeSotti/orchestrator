# Auditoria complementar do código — Orchestrator

| Campo | Valor |
|---|---|
| Data | 2026-11-11 (segunda execução do dia) |
| Objeto | Arquivos de trabalho adicionados à pasta `C:\Users\Particular\Projetos\orchestrator`: `src/`, `tests/`, `packages/`, `.github/`, `examples/`, `docs/` e diretórios auxiliares |
| Tipo | Entrega E0.3 do roadmap: auditoria do código que estava inacessível na auditoria inicial |
| Situação | **Concluída para o que está no disco.** O Git local continua não funcional; o remoto continua inacessível |
| Documentos relacionados | `docs/audit/INITIAL_AUDIT.md`, `docs/OPEN_DECISIONS.md`, `docs/IMPLEMENTATION_ROADMAP.md` |

---

## 1. Resumo executivo

1. **Os testes passam, o pacote constrói e instala.** 13 testes do Core e 2 do pacote SQL aprovados; o wheel do Core foi construído e instalado em ambiente limpo, e o comando `orchestrator` executou.
2. **O Core é um esqueleto de lifecycle: não executa a lógica de nenhum consumidor.** O estágio de execução apenas registra os nomes das tarefas. A CLI responde "Execution success" para `examples/sql-spec.json` sem tocar em banco algum.
3. **Quase metade do Core não é usada.** 18 dos 38 módulos (todos os ports, os adapters em memória, o Event Bus, o serviço de logging e os utilitários) não são importados por nenhum ponto de entrada nem pelos testes.
4. **Há defeitos graves nos runners, confirmados por execução:** o `ProcessRunner` trava quando o resultado é grande (reproduzido com 200 KB e com 2 MB) e ignora o pipeline configurado.
5. **Não há garantia de finalização.** Falha ou exceção interrompem o pipeline sem executar `Finalize`; exceções são engolidas e o traceback se perde.
6. **O pacote SQL embute regras de negócio de um consumidor** (fila, `FluxoExecucaoId`, `CORE.FluxosExecucao`, ambiente `'P'`) e monta SQL com identificadores e expressões sem validação.
7. **Os padrões declarados obrigatórios não são atendidos nem verificados:** Ruff aponta 33 ocorrências e 30 arquivos fora do formato; MyPy aponta 12 erros no Core; faltam 167 docstrings públicas; a CI roda apenas `pytest` em Python 3.11.
8. **Existe trabalho não versionado.** 21 arquivos foram alterados depois do commit `6232d68` e nunca commitados neste clone. O Git segue sem `refs` e sem objetos.

**Recomendação para a decisão D-00:** arquivar o scaffold como referência e reconstruir o Core a partir de contratos aprovados (seção 12). O volume é pequeno (738 linhas não vazias no Core) e os problemas são de desenho, não de acabamento.

---

## 2. O que mudou na pasta e o que continua pendente

### 2.1 Estado do Git

Inalterado em relação à auditoria inicial: `.git` tem os mesmos 34 arquivos, sem `refs/` e com 1 objeto. **A pasta continua sem controle de versão.**

O arquivo `.venv/pyvenv.cfg` registra onde o ambiente virtual foi criado: `c:\Users\guilherme.machado\orchestrator\.venv`, com Python 3.11.9. Isso confirma que a pasta veio de outro perfil ou de outra máquina. O `.git` completo deve estar na pasta de origem.

### 2.2 Arquivos em relação ao index (equivalente a `git status`)

| Situação | Quantidade | Detalhe |
|---|---:|---|
| Rastreados e idênticos ao index | 56 | — |
| Rastreados e modificados | 25 | 21 por trabalho anterior não commitado; 3 pela auditoria inicial (`.gitignore`, `README.md`, `CHANGELOG.md`); `pyproject.toml` pelos dois |
| Rastreado e ausente | 1 | `packages/orchestrator_sql/tests/conftest.py`, renomeado para `tests/__init__.py` (mesmo conteúdo, confirmado por hash) |
| Não rastreados | 19 | 11 arquivos antigos (`ADR/`, `config/`, `scripts/`, 8 em `docs/`), `src/orchestrator_core/stage.py`, o `__init__.py` renomeado, 3 documentos da auditoria e 3 duplicatas |
| Ignorados | 41 | `__pycache__`, `.pytest_cache`, `.vscode/` (sem contar o `.venv/`) |

Os 21 arquivos alterados depois do commit `6232d68` e nunca commitados neste clone:

- Core (14): `__init__.py`, `context.py`, `main.py`, `pipeline.py`, `registry.py`, `runner/base.py`, `spec.py` e os 7 arquivos de `stage/`.
- Pacote SQL (4): `sql_provider.py`, `schema_manager.py`, `mappers/table_mapper.py`, `tests/test_schema_manager.py`.
- Outros (3): `tests/test_core_runtime.py`, `examples/sql-spec.json`, `.github/CODEOWNERS`.

O volume é relevante: `runner/base.py` passou de 843 para 5.234 bytes, `pipeline.py` de 1.827 para 3.476, `tests/test_core_runtime.py` de 2.166 para 5.063 e `schema_manager.py` de 1.512 para 4.239. As datas vão de 2026-07-06 16:07 a 2026-07-21 11:07.

A alteração local de `pyproject.toml` anterior à auditoria ficou totalmente caracterizada: trocando a linha `authors` por `authors = [{ name = "Orchestrator Contributors" }]`, o arquivo reproduz exatamente o blob do index. Nada mais havia mudado.

### 2.3 Itens a limpar ou refazer (nenhum foi alterado nesta sessão)

| Item | Situação | Ação sugerida |
|---|---|---|
| `docs/audit/INITIAL_AUDIT-1.md`, `docs/IMPLEMENTATION_ROADMAP-1.md`, `docs/OPEN_DECISIONS-1.md` | Cópias dos arquivos enviados no chat na primeira execução; já desatualizadas | Apagar |
| `.venv/` | Criado em outra máquina; caminhos absolutos inválidos aqui | Apagar e recriar |
| `src/orchestrator_core/stage.py` | Versão antiga (2026-07-01), sombreada pelo pacote `stage/`; ainda entra no wheel | Remover depois de recuperar o Git |
| `src/orchestrator_core.egg-info/` | Artefato de build versionado e desatualizado (lista `stage.py`, não lista `bootstrap`, `events`, `stage/`) | Retirar do versionamento |

### 2.4 Por que nenhum arquivo de código foi alterado

Sem Git funcional não há como desfazer uma edição, e o trabalho não versionado existe apenas em cópias de pasta. Os defeitos estão registrados com arquivo, linha e correção proposta, para serem tratados em branch própria depois da recuperação.

---

## 3. Método, ambiente e limites

- O código foi copiado para um ambiente de análise isolado e executado ali: Linux, Python 3.13.18, Pytest 9.1.1, Ruff 0.16.9, MyPy 2.3.1, setuptools 84.0.0.
- Cada defeito classificado como **reproduzido** foi confirmado por um experimento executado; os demais vêm da leitura do código e estão marcados como **leitura**.
- Limites:
  - SQLAlchemy não está disponível no ambiente de análise. Os caminhos de código que usam SQLAlchemy ou SQL Server foram apenas lidos.
  - Nada foi executado em Windows nem em Python 3.11, que é a versão do ambiente original.
  - A cobertura é uma estimativa de linhas obtida com `sys.settrace`; não mede ramos nem o processo filho do `ProcessRunner`.
  - O ambiente virtual do usuário não é utilizável fora da máquina de origem.

---

## 4. Verificações executadas

| # | Verificação | Resultado | Classe |
|---:|---|---|---|
| 1 | `pytest` do Core, com `PYTHONPATH=src` | 13 aprovados em 0,12 s | Aprovado |
| 2 | `pytest` do pacote SQL | 2 aprovados em 0,02 s (somente o caminho SQLite da biblioteca padrão) | Aprovado |
| 3 | `pytest` do Core com avisos tratados como erro | 13 aprovados | Aprovado |
| 4 | `pytest` em checkout limpo, sem `PYTHONPATH` e sem instalação editável | Erro de coleta: `ModuleNotFoundError: No module named 'orchestrator_core'` | Reprovado |
| 5 | `ruff check` (regras padrão do Ruff 0.16.9) | 33 ocorrências: 20 em `src/`, 13 no pacote SQL; testes sem ocorrências | Reprovado |
| 6 | `ruff format --check` | 30 de 52 arquivos seriam reformatados | Reprovado |
| 7 | Regras de segurança do Ruff (grupo `S`) | 5 × `S608` em `sql_provider.py` | Reprovado |
| 8 | Regras de docstring pública do Ruff (`D100` a `D107`) | 167 ocorrências | Reprovado |
| 9 | `mypy` no Core | 12 erros em 4 arquivos; 13 em modo estrito | Reprovado |
| 10 | `mypy` no pacote SQL | 1 erro de tipo; 2 de import, por falta de SQLAlchemy no ambiente | Reprovado |
| 11 | Estimativa de cobertura de linhas | Core: 53% (346 de 656), com 20 de 38 arquivos em 0%. Pacote SQL: 69% (287 de 418) | Informativo |
| 12 | Grafo de imports do Core | 38 módulos; 20 alcançáveis; 18 não importados por ninguém; nenhum ciclo; nenhum import de terceiros além de `yaml`, opcional e tardio | Informativo |
| 13 | Build do wheel do Core | `orchestrator_core-0.1.0-py3-none-any.whl`, 45 arquivos; inclui `stage.py`; sem `py.typed` | Aprovado com ressalva |
| 14 | Instalação do wheel em ambiente virtual limpo; `import`; comando `orchestrator` | Instalou; importou; `Execution success: completed`, saída 0 | Aprovado |
| 15 | CLI com `examples/basic-spec.json` e `examples/sql-spec.json` | As duas respondem `Execution success: completed` | Aprovado (ver COD-01) |
| 16 | 13 experimentos de comportamento no Core | Seção 6 | — |
| 17 | 8 experimentos de comportamento no pacote SQL | Seção 7 | — |
| 18 | Varredura de segredos no material novo | 0 ocorrências; `examples/sql-spec.json` usa `sqlite:///:memory:` | Aprovado |
| 19 | Caminhos SQLAlchemy e SQL Server; execução em Windows e em Python 3.11 | — | Não executado |
| 20 | Execuções da CI no GitHub | — | Bloqueado (sem acesso) |

Evidência do ambiente original: o cache do Pytest na pasta (`.pytest_cache`, 2026-07-06 23:50) lista os mesmos 13 testes e registra nenhuma falha na última execução.

---

## 5. O que o código é, de fato

### 5.1 Fluxo real

```text
orchestrator --spec arquivo.json
        │
        ▼
ConfigLoader.load_spec ──► ExecutionSpecification (nome, lista de nomes de tarefas, parâmetros…)
        │
        ▼
runner escolhido por spec.runner.type: LocalRunner | ThreadRunner | ProcessRunner
        │
        ▼
ExecutionPipeline.run ──► InitializeStage ─► ExecuteStage ─► FinalizeStage
                                              │
                                              └─ registra "executing tasks: a, b" e devolve SUCCESS
```

- **Não existe ligação entre o nome de uma tarefa e código.** `tasks` é uma lista de textos. O único meio de executar algo é escrever estágios próprios e montar o pipeline em Python, ou registrar no `CapabilityRegistry` um objeto que forneça estágios.
- **Conceitos fora do vocabulário documentado:** `ExecutionSpecification`, `ExecutionEngine` e `Runner`. O conceito documentado de Runtime não tem classe própria; o mais próximo é `build_runtime()`, que devolve um `ExecutionEngine`.
- **A superfície pública existe em `__all__`** (11 nomes), sem documentação.

### 5.2 Números

| Medida | Core | Pacote SQL |
|---|---:|---:|
| Arquivos Python | 39 | 6 |
| Linhas não vazias | 738 | 455 |
| Módulos alcançáveis a partir dos pontos de entrada | 20 de 38 | — |
| Testes | 13 | 2 |
| Cobertura de linhas estimada | 53% | 69% |
| Ocorrências do Ruff | 20 | 13 |
| Erros do MyPy | 12 | 1 |

### 5.3 Pacote SQL

- É uma biblioteca independente: não importa o Core e não expõe nada que o `CapabilityRegistry` reconheça. Não é uma Capability no sentido do projeto.
- A classe `SQLProvider` concentra conexão, detecção de dialeto, geração de DDL e operações de dados, com ramos `if dialect == "mssql"`. Não há contrato de Capability nem de Provider.
- O gerenciador de schema aplica convenções de um ambiente específico (seção 7, SQL-01).

---

## 6. Achados do Core

"Reproduzido" indica experimento executado; "leitura" indica inspeção do código.

### 6.1 P1 — alto

| ID | Achado | Evidência | Correção proposta |
|---|---|---|---|
| COD-01 | O Core não executa lógica do consumidor: o estágio de execução só registra os nomes das tarefas | `stage/execute_stage.py:10-13`; reproduzido pela CLI (verificação 15) | Decisão D-02: definir como o consumidor entrega a automação |
| COD-02 | Sem garantia de finalização: falha, exceção ou interrupção encerram o pipeline sem executar os estágios restantes; `finished_at` fica vazio | `pipeline.py:33-63`; reproduzido (falha, exceção e `KeyboardInterrupt`). O teste `test_pipeline_stops_on_stage_failure` fixa esse comportamento | Decisão D-06 |
| COD-03 | `ProcessRunner` trava quando o resultado excede o buffer do pipe: faz `process.join()` antes de `queue.get()` | `runner/base.py:124-130`; reproduzido com 200 KB e com 2 MB de parâmetros (processo encerrado pelo limite de tempo); com 1 KB funciona | Ler a fila antes do `join`, com prazo; tratar processo que termina sem resultado |
| COD-04 | `ProcessRunner` ignora o pipeline configurado: o processo filho cria um `ExecutionPipeline()` padrão | `runner/base.py:15-16` e `123`; reproduzido: um pipeline que sempre falha devolveu `success` | Enviar ao filho a definição do pipeline, ou remover o runner |
| COD-05 | Exceções engolidas: qualquer `Exception` em estágio vira `status="failure"` com apenas o texto da exceção em `context.logs`; tipo e traceback se perdem; os ramos estão marcados `# pragma: no cover` | `pipeline.py:60-63`; `runner/base.py:19` e `45`; reproduzido | Hierarquia de erros e resultado com a causa preservada (D-06) |

### 6.2 P2 — médio

| ID | Achado | Evidência | Correção proposta |
|---|---|---|---|
| COD-06 | Campos da spec declarados e nunca usados: `timeout`, `retries`, `strict`, `dependencies`. `StageResult.RETRY` só gera uma linha de log. `timeout` aceita qualquer tipo | Nenhum uso no código; `pipeline.py:53-54`; `spec.py:59`; reproduzido (estágio de 2 s com `timeout=1` concluiu; `RETRY` não repetiu) | Remover o que não tem semântica ou implementar conforme D-06 e D-12 |
| COD-07 | Lifecycle com 3 estágios no pipeline padrão, contra 8 documentados. `LoggingStage` e `ShutdownStage` existem e não entram no padrão. `_prepare_environment` só copia um dicionário | `bootstrap.py:11`; `pipeline.py:27`; `runner/base.py:67-68` | D-06, D-15, D-16 |
| COD-08 | 18 de 38 módulos sem nenhum consumidor: 12 ports, 9 adapters em memória, `EventBus`, `LoggingService`, `utils`. Dois contratos diferentes com o mesmo nome `MetricsPort` | Verificação 12; `ports/metrics.py` e `ports/metrics_port.py` | D-03: manter no Core só contratos com consumidor |
| COD-09 | Contrato de estágio duplicado e inconsistente: `BaseStage` e `Stage` "retrocompatível". O pipeline é anotado com `list[Stage]`, mas os estágios padrão derivam de `BaseStage`. Uma subclasse cujo `run()` chama `super().run()` entra em recursão infinita | `stage/base_stage.py:19-42`; 9 dos 12 erros do MyPy; reproduzido (`RecursionError`) | Um único contrato de estágio |
| COD-10 | `CapabilityRegistry` sem contrato: tudo é `Any`, com detecção por `hasattr`. Registro duplicado sobrescreve o nome e mantém o objeto antigo fornecendo estágios | `registry.py:14-32`; reproduzido (2 objetos ativos após registrar o mesmo nome) | D-10: contrato tipado; duplicidade como erro |
| COD-11 | `discover()` carrega e executa todo entry point do grupo, sem lista de permissão, verificação de compatibilidade ou isolamento de erro. Não é chamado em lugar algum. O ramo `except TypeError` é código morto | `registry.py:34-44`; leitura; erro do MyPy na linha 38 | D-10; revisão de segurança exigida por SECURITY |
| COD-12 | CLI devolve saída 0 mesmo quando o resultado é `failure`. Spec sem `runner.type` gera `ValueError` com traceback. Qualquer extensão diferente de `.json` é tratada como YAML, com dependência não declarada de PyYAML | `main.py:24-35`; `config_loader.py:20-27`; reproduzido (spec sem runner e arquivo inexistente) | D-02; código de saída derivado do resultado; runner padrão |
| COD-13 | Métricas e estado do runner incorretos: `error_count` não conta falha de pipeline; `runner_strategy` vale sempre 1.0; contadores mutáveis sem sincronização | `runner/base.py:57-64`; reproduzido (`error_count` igual a 0 após falha) | D-14 |
| COD-14 | `ExecutionContext` é totalmente mutável e `status` é texto livre que mistura fase e desfecho. `ExecutionSpecification` é `frozen`, mas as coleções internas são alteráveis | `context.py:11-25`; `spec.py:7-19`; reproduzido | D-07 |
| COD-15 | Logs são textos em lista na memória, sem nível, horário ou redação. `LoggingService` descarta a mensagem quando não há `event_port` e não usa `logging` | `context.py:19` e `31-32`; `logging_service.py:20-22`; leitura | D-14 |
| COD-16 | `EventBus`: a exceção de um assinante interrompe a publicação para os seguintes. O pipeline não publica eventos | `events.py:34-36`; reproduzido | D-13 |
| COD-17 | `ThreadRunner` executa em uma thread e bloqueia até o fim: não acrescenta paralelismo, timeout nem cancelamento | `runner/base.py:107-110`; leitura | D-05: remover ou dar semântica |

### 6.3 P3 — baixo

| ID | Achado | Evidência |
|---|---|---|
| COD-18 | `stage.py` antigo sombreado pelo pacote `stage/`; `specification.py` é só um alias; `utils.py` sem uso; import não usado em `runner/base.py:12` | Verificações 5, 12 e 13 |
| COD-19 | Sem `py.typed`; `tests/test_core_runtime.py` altera `sys.path`; `requires-python` e CI em 3.11 | `tests/test_core_runtime.py:8`; `.github/workflows/ci.yml:15` |

### 6.4 Pontos positivos

- Nenhum ciclo de import.
- O código do Core não importa SQLAlchemy nem outra biblioteca de terceiros; a única exceção é `yaml`, opcional e importado só quando necessário, com `safe_load`.
- Contextos de execuções diferentes não compartilham estado (reproduzido).
- Não há singleton de módulo nem estado global; o estado mutável compartilhado está apenas nos contadores dos runners (COD-13).
- A spec não aciona import dinâmico nem execução de código: contém apenas nomes.
- A validação de `ExecutionSpecification.from_mapping` rejeita entradas malformadas nos campos principais.
- Os testes passam em Python 3.13 sem avisos de depreciação.

---

## 7. Achados do pacote SQL

### 7.1 P1 — alto

| ID | Achado | Evidência | Correção proposta |
|---|---|---|---|
| SQL-01 | **Regras de negócio de um consumidor dentro da plataforma.** Toda tabela ganha uma coluna `FluxoExecucaoId` e, por padrão, uma tabela de fila `Fila<Tabela>` com colunas `Usuario`, `Maquina`, `Ambiente`, estados em português, chave estrangeira fixa para `CORE.FluxosExecucao` e, em SQL Server, um gatilho que grava `'P'` como ambiente | `mappers/table_mapper.py:90-152`; `schema_manager.py:40-85` | Levar essas convenções para o projeto consumidor; a plataforma oferece o mecanismo, não o modelo de dados |
| SQL-02 | **SQL montado com texto não validado.** Nomes de schema, tabela e coluna são envolvidos em aspas sem escape; tipo, valor padrão, expressão `CHECK`, tabela referenciada, lista de colunas do `select` e cláusulas `where` entram crus | `sql_provider.py:104-116`, `129-166`, `180-198`, `227-258`; 5 × `S608`; reproduzido: um nome de coluna com aspas criou duas colunas, um valor padrão criou uma coluna extra, e `select()` leu outra tabela | Validar identificadores por expressão regular restrita, escapar ao citar, e não aceitar fragmentos de SQL vindos da spec |
| SQL-03 | **Recuo silencioso para SQLite.** Sem SQLAlchemy instalado, qualquer cadeia de conexão é tratada como nome de arquivo SQLite | `sql_provider.py:33-45`; reproduzido: uma cadeia ODBC criou no diretório atual um arquivo cujo nome contém a senha, e `dialect` informou `sqlite` | Falhar com erro claro quando o driver necessário não estiver disponível |

### 7.2 P2 e P3

| ID | Prioridade | Achado | Evidência |
|---|---|---|---|
| SQL-04 | P2 | URIs `sqlite:///…` não funcionam: são entregues diretamente a `sqlite3.connect`. É o caso da conexão do próprio `examples/sql-spec.json`. O erro resultante não é encapsulado | `sql_provider.py:35-45`; reproduzido (`sqlite3.OperationalError`) |
| SQL-05 | P2 | A segunda tabela de fila de um schema fica sem índices no SQLite, porque os nomes são fixos e a criação usa `IF NOT EXISTS`. Em SQL Server, os nomes fixos das constraints colidiriam | `mappers/table_mapper.py:114-151`; reproduzido no SQLite; leitura para SQL Server |
| SQL-06 | P2 | A coluna de identificação é a primeira cujo nome começa com "id": uma coluna `Idade` é tratada como chave e nenhuma coluna de identidade é criada | `schema_manager.py:25-28`; reproduzido |
| SQL-07 | P2 | `apply_specification` altera a spec recebida, inserindo colunas no dicionário de entrada | `schema_manager.py:37-47`; reproduzido |
| SQL-08 | P2 | Sem separação entre Capability e Provider; duas implementações paralelas de geração de DDL, uma delas sem uso | `sql_provider.py`; `mappers/table_mapper.py:6-87`; leitura |
| SQL-09 | P2 | Só erros de `sqlite3` são encapsulados; exceções do SQLAlchemy vazariam para o chamador. Engine e conexão compartilhada nunca são encerrados | `sql_provider.py:58-95`; leitura |
| SQL-10 | P3 | O pacote não declara dependência do Core; SQLAlchemy é extra opcional aqui e "Core dependency" no `requirements.txt` da raiz; os testes cobrem só SQLite em memória, com asserções do tipo `isinstance(result, list)` | `packages/orchestrator_sql/pyproject.toml:13-14`; testes |

---

## 8. Testes, CI e governança no repositório

| ID | Prioridade | Achado | Evidência |
|---|---|---|---|
| TST-01 | P2 | Sem teste para: exceção em estágio, cancelamento, retry, timeout, CLI, `ConfigLoader`, `EventBus`, `LoggingService`, `discover`, ports, adapters e `ProcessRunner` com pipeline próprio | Verificação 11; leitura dos testes |
| TST-02 | P2 | A suíte depende de instalação editável; um arquivo de teste altera `sys.path`. Os testes do pacote SQL não são executados pela configuração da raiz nem pela CI | Verificação 4; `pyproject.toml` (`testpaths`) |
| CI-01 | P2 | A CI tem um job: Ubuntu, Python 3.11, `pip install -e . pytest`, `pytest -q`. Não há Ruff, MyPy, cobertura, matriz de versões, Windows, bloco `permissions` nem ações fixadas por SHA | `.github/workflows/ci.yml` |
| CI-02 | P2 | As cinco validações de segurança que `SECURITY.md` atribui à CI não existem no workflow | `SECURITY.md`; `.github/workflows/ci.yml` |
| QUA-01 | P2 | Padrões obrigatórios de `GOVERNANCE.md` não atendidos: Ruff, formatação, MyPy e docstrings | Verificações 5, 6, 8 e 9 |
| ENV-01 | P2 | Ambiente real de desenvolvimento: Python 3.11.9, com pytest 9.1.1, pytest-cov 7.1.0, SQLAlchemy 2.0.51 e setuptools 65.5.0. Ruff, MyPy e Pydantic não estão instalados | `.venv/pyvenv.cfg`; conteúdo de `.venv/Lib/site-packages` |
| GOV-05 | P2 | `CODEOWNERS` e `dependabot.yml` citam `@orchestrator-team`, `@platform-team` e `devops-team`; a existência dessas equipes não é verificável, e o formato de equipe é `@organização/equipe`. `ISSUE_TEMPLATE/config.yml` aponta as discussões para `github.com/orchestrator/orchestrator` e o contato de segurança para `https://github.com/` | `.github/CODEOWNERS:2-10`; `.github/dependabot.yml:11-12` e `27-28`; `.github/ISSUE_TEMPLATE/config.yml:4` e `7` |
| GOV-06 | P3 | Três locais para registrar decisões: `ADR/`, `docs/adr/` (com `0000-template.md`) e `docs/decisions/`. Nenhum ADR escrito | Arquivos no disco |

Os modelos de issue, o modelo de Pull Request, `labels.yml` e `docs/guides/github-governance.md` são reaproveitáveis como estão.

---

## 9. Conformidade com a arquitetura documentada

| Elemento documentado | Situação no código | Evidência |
|---|---|---|
| Public API | Parcial: 11 nomes exportados, sem documentação | `src/orchestrator_core/__init__.py` |
| Runtime | Parcial: `ExecutionEngine` e runners; não executa automação do consumidor | COD-01 |
| Execution Pipeline extensível | Parcial: lista de estágios configurável; 3 estágios padrão | COD-07 |
| Lifecycle de 8 estágios | Ausente: 3 no padrão, 5 classes | COD-07 |
| Execution Context | Parcial: existe, isolado por execução, totalmente mutável | COD-14 |
| Configuration | Parcial: leitura de spec JSON; sem precedência, ambiente ou segredos | `config_loader.py` |
| Dependency Injection | Parcial: injeção por construtor em `ExecutionEngine` e runners | `execution_engine.py`; `bootstrap.py` |
| Event Bus | Implementado e não usado | COD-16 |
| Logging | Ausente como serviço: lista de textos no contexto | COD-15 |
| Metrics | Parcial e incorreto: valores gravados no contexto pelo runner | COD-13 |
| Retry | Ausente: campo e resultado existem, sem efeito | COD-06 |
| Capability Registry | Parcial: registro e descoberta sem contrato | COD-10, COD-11 |
| Ports | Declarados e sem consumidor | COD-08 |
| Capabilities | Ausente no sentido do projeto: o pacote SQL não se integra ao registry | Seção 5.3 |
| Providers | Ausente: não há implementação de contrato; há adapters em memória sem uso | COD-08, SQL-08 |
| Core independente de infraestrutura | **Atendido no código**; violado apenas na declaração de `requirements.txt` | Verificação 12 |
| Regra "lógica de negócio fica no consumidor" | **Violada** no pacote SQL | SQL-01 |
| Estratégia multirrepositório | Não seguida | Auditoria inicial, ARQ-01 |

---

## 10. Resolução dos itens em aberto da auditoria inicial

| Item | Resultado |
|---|---|
| REP-01 | **Parcial.** Os arquivos de trabalho estão no disco; o Git continua sem `refs` e sem objetos. Permanece P0, agravado pelo trabalho não versionado (seção 2.2) |
| REP-02 | Mantido: remoto inacessível |
| REP-03 | Esclarecido: a única alteração local anterior era a linha `authors` |
| REP-04 | Confirmado: `egg-info` presente e desatualizado |
| PKG-01 | **Resolvido:** com `src/` presente e a sintaxe corrigida, o wheel constrói e instala |
| PKG-02, PKG-03 | Confirmados; o ambiente e a CI usam Python 3.11 |
| ARQ-01 | Confirmado pela leitura |
| ARQ-02 | **Reduzido:** o código do Core não importa SQLAlchemy; a violação está só em `requirements.txt` |
| ARQ-03 | Confirmado e ampliado: o pipeline padrão tem 3 estágios |
| ARQ-04 | Confirmado e ampliado: 18 de 38 módulos sem consumidor |
| ARQ-05 | Confirmado e ampliado: além de orientado a spec e CLI, o Core não executa a automação |
| DOC-03 | **Corrigido:** `docs/adr/0000-template.md` existe no disco, fora da árvore do commit `6232d68`. O problema real são três locais concorrentes e nenhum ADR (GOV-06) |
| DOC-04 | Confirmado pelo conteúdo da CI (CI-02) |
| GOV-01 | Confirmado |
| SEC-02 | **Resolvido:** revisão feita. Resultados: SQL-02, SQL-03, COD-11. `examples/sql-spec.json` não contém credenciais; a spec não aciona import dinâmico |
| Roteiro da seção 8.4 | Cumprido nos 9 itens |

Continuam não verificáveis: estado de `main` no remoto, Pull Requests, execuções de CI e controles do GitHub.

---

## 11. O que pode ser reaproveitado

| Item | Como aproveitar |
|---|---|
| Campos de `ExecutionContext` (identificador, correlação, início e fim) | Ponto de partida para D-07 |
| `StageResult` e a ideia de `PipelineBuilder` com estágios fornecidos por capabilities | Insumo para D-06 e D-10 |
| Validações de `ExecutionSpecification.from_mapping` | Casos de teste para o modelo de configuração (D-08) |
| Adapters em memória | Base do módulo de apoio a testes (D-21) |
| Os 15 testes | Sementes; o de parada em falha precisa mudar com D-06 |
| Mapeamento de tipos e geração de DDL do pacote SQL | Referência para a Fase 4, sem as convenções de fila |
| `.github/` (modelos e rótulos), `docs/adr/0000-template.md`, `docs/guides/github-governance.md` | Fase 1, com as correções de GOV-05 e GOV-06 |

---

## 12. Recomendação para D-00

**Alternativa B: arquivar o scaffold como referência e reconstruir o Core a partir de contratos aprovados.**

Razões, todas com evidência neste relatório:

1. A função central, executar a automação do consumidor, não existe (COD-01). Não há o que preservar ali.
2. A semântica de falha é a oposta da recomendada em D-06 (COD-02, COD-05), e há um teste que a fixa.
3. Os runners têm dois defeitos graves (COD-03, COD-04) e nenhuma decisão de concorrência registrada (D-05).
4. Quase metade dos módulos não tem consumidor (COD-08). Mantê-los seria preservar abstração antecipada.
5. O contrato de estágio e o registry precisariam ser redesenhados de qualquer forma (COD-09, COD-10).
6. O pacote SQL precisa ser separado das regras de negócio que carrega (SQL-01) e reescrito quanto à montagem de SQL (SQL-02).
7. O custo de reescrever é baixo: 738 linhas não vazias no Core.

Antes de arquivar: recuperar o Git e commitar o estado atual em uma branch de referência, para que o trabalho não versionado não se perca.

Se a decisão for a alternativa A (adotar e corrigir), a ordem sugerida é: COD-03, COD-04, COD-02, COD-05, SQL-03, SQL-02, SQL-01, COD-09, COD-10, COD-08 e os demais. Cada correção com teste de regressão.

---

## 13. Pendências e próximo passo

1. **Agora:** cópia de segurança da pasta inteira.
2. Recuperar o Git e commitar o trabalho não versionado em uma branch (seção 13.1).
3. Apagar as três duplicatas em `docs/` e recriar o `.venv`.
4. Decidir D-00, D-01 e D-02.

### 13.1 Como levar o trabalho não versionado para um repositório íntegro (não executado)

**Caminho A — a pasta de origem ainda tem o `.git` completo.** Com a cópia de segurança feita, substituir o diretório `.git` desta pasta pelo da origem (`C:\Users\guilherme.machado\orchestrator\.git`). Em seguida, `git status` deve listar exatamente os arquivos do Apêndice A.

**Caminho B — clone novo a partir do remoto.** Em PowerShell:

```powershell
# 1) Cópia de segurança
robocopy C:\Users\Particular\Projetos\orchestrator C:\Users\Particular\Projetos\orchestrator.copia-2026-11-11 /E /COPY:DAT /DCOPY:T /R:1 /W:1

# 2) Clone íntegro e branch de referência no commit em que o trabalho se baseia
git clone https://github.com/SicoloS-Guilherme-Machado/orchestrator.git C:\Users\Particular\Projetos\orchestrator-restaurado
cd C:\Users\Particular\Projetos\orchestrator-restaurado
git switch -c experiment/scaffold-2026-07 6232d689c0f89f2cea7f575eb946415d254c34b1

# 3) Trazer os arquivos de trabalho, sem .git, ambiente virtual, caches e duplicatas
robocopy C:\Users\Particular\Projetos\orchestrator . /E /XD .git .venv __pycache__ .pytest_cache /XF *-1.md

# 4) Conferir e commitar
git status
git add -A
git commit -m "chore: preserve uncommitted scaffold work and audit documents"
```

Nos dois caminhos:

- O resultado esperado de `git status` antes do commit é a lista do Apêndice A, mais os documentos da auditoria.
- Se o commit `6232d68` não existir no clone, usar `origin/main` como base e revisar o diff com mais cuidado, porque ele incluirá o que mudou no remoto desde julho.
- Não fazer push sem revisar. O envio ao remoto e o Pull Request seguem a governança do projeto.

---

## Apêndice A — Arquivos modificados em relação ao index

Modificados por trabalho anterior não commitado:

```text
.github/CODEOWNERS
examples/sql-spec.json
packages/orchestrator_sql/src/orchestrator_sql/mappers/table_mapper.py
packages/orchestrator_sql/src/orchestrator_sql/schema_manager.py
packages/orchestrator_sql/src/orchestrator_sql/sql_provider.py
packages/orchestrator_sql/tests/test_schema_manager.py
src/orchestrator_core/__init__.py
src/orchestrator_core/context.py
src/orchestrator_core/main.py
src/orchestrator_core/pipeline.py
src/orchestrator_core/registry.py
src/orchestrator_core/runner/base.py
src/orchestrator_core/spec.py
src/orchestrator_core/stage/__init__.py
src/orchestrator_core/stage/base_stage.py
src/orchestrator_core/stage/execute_stage.py
src/orchestrator_core/stage/finalize_stage.py
src/orchestrator_core/stage/initialize_stage.py
src/orchestrator_core/stage/logging_stage.py
src/orchestrator_core/stage/shutdown_stage.py
tests/test_core_runtime.py
pyproject.toml        (linha authors; depois, a correção de sintaxe da auditoria inicial)
```

Modificados pela auditoria inicial: `.gitignore`, `README.md`, `CHANGELOG.md`.

Renomeado: `packages/orchestrator_sql/tests/conftest.py` → `packages/orchestrator_sql/tests/__init__.py`.

Não rastreados e anteriores à auditoria: `ADR/README.md`, `config/README.md`, `scripts/README.md`, `docs/README.md`, `docs/adr/0000-template.md`, `docs/architecture/README.md`, `docs/decisions/README.md`, `docs/diagrams/README.md`, `docs/guides/README.md`, `docs/guides/github-governance.md`, `docs/images/README.md`, `src/orchestrator_core/stage.py`.

## Apêndice B — Como reproduzir

Na raiz do repositório, com Python 3.11 ou superior e as ferramentas instaladas:

```bash
PYTHONPATH=src python -m pytest -q                                   # verificação 1
cd packages/orchestrator_sql && PYTHONPATH=src python -m pytest -q   # verificação 2
ruff check src tests packages                                        # verificação 5
ruff format --check src tests packages                               # verificação 6
ruff check --select S --ignore S101 src packages                     # verificação 7
mypy src/orchestrator_core                                           # verificação 9
python -m pip wheel --no-deps -w dist .                              # verificação 13
PYTHONPATH=src python -m orchestrator_core.main --spec examples/basic-spec.json   # verificação 15
```

Em PowerShell, defina a variável antes do comando: `$env:PYTHONPATH = "src"`.

Experimento do travamento do `ProcessRunner` (COD-03), a ser executado com limite de tempo:

```python
from orchestrator_core.runner.base import ProcessRunner
from orchestrator_core.spec import ExecutionSpecification

if __name__ == "__main__":
    spec = ExecutionSpecification.from_mapping(
        {"name": "grande", "tasks": ["a"], "parameters": {"blob": "x" * 2_000_000}}
    )
    ProcessRunner().run(spec)  # não retorna
```
