# RFC-0004 — Controles reutilizáveis de automação: escopo, arquitetura modular e sequência de entregas

| Campo | Valor |
|---|---|
| Status | Aceita em 2026-11-15 pelo responsável |
| Data | 2026-11-14 |
| Autor | Claude, a pedido do responsável |
| Decisor | Responsável pelo projeto (aceite registrado em [DECISIONS](../DECISIONS.md), seção 5) |
| Origem | Pedido direto do responsável em 2026-11-13; a issue do formulário "RFC" não foi aberta |
| Diagnóstico | [docs/audit/SCOPE_DIAGNOSIS.md](../audit/SCOPE_DIAGNOSIS.md) |
| RFCs relacionadas | [0005](0005-core-0-2-subetapas-mascaramento-teardown-e-sinais.md) a [0012](0012-autenticacao-por-sistema.md), aceitas em 2026-11-15 |

## 1. Problema

O responsável quer que a plataforma ofereça controles reutilizáveis para automações, em bibliotecas modulares: ciclo de vida e finalização, fluxo e subetapas, fila, notificações, logs e registros, mapeamentos compartilhados, fluxos de login, segredos e calendários. O Core 0.1.0 cobre o ciclo de vida e tem a base de logs, registros de execução e segredos por referência; os demais itens não existem (diagnóstico, seção 3).

Esta RFC decide **onde** cada item mora e **em que ordem** entra. Os contratos ficam nas RFCs 0005 a 0012.

Continuam excluídos, aqui e nas RFCs relacionadas: agendamento, execução distribuída, execução em nuvem, dashboard, pausa e retomada, workflow engine genérico e descoberta automática de plugins ([ADR-0016](../adr/0016-escopo-futuro.md), [ADR-0009](../adr/0009-registro-de-capabilities-e-compatibilidade.md)).

## 2. Regras aplicadas

1. O Core contém só o que é transversal e usa só a biblioteca padrão ([ADR-0004](../adr/0004-fronteiras-core-capability-provider.md), [ADR-0005](../adr/0005-dependencias-do-core.md)).
2. Provider → Capability → Core. Cada Capability define o contrato funcional e o port dos seus Providers.
3. Registro e configuração explícitos. O consumidor informa quais Providers a configuração pode escolher (`providers={...}`), como na Capability SQL.
4. Nenhum pacote da plataforma conhece tabelas, colunas, estados, textos ou regras de um consumidor ([ADR-0019](../adr/0019-convencoes-de-fila-fora-da-plataforma.md)). O que é do consumidor entra como mapa ou função fornecidos por ele.
5. Nenhum port sem consumidor: uma entrega só começa com um caso de uso real descrito na RFC correspondente.
6. Um pacote por Pull Request, cada um com `pyproject.toml`, README, CHANGELOG, LICENSE, testes e a suíte de conformidade do seu port ([ADR-0001](../adr/0001-topologia-de-repositorios.md), [ADR-0015](../adr/0015-testes-entre-pacotes.md)).

## 3. Onde cada item mora

| # | Item | Core | Capability | Providers | Projeto consumidor | RFC |
|---:|---|---|---|---|---|---|
| 1 | Ciclo de vida e finalização | Já existe. Proposto: orçamento de teardown e guia de encerramento por sinal | — | — | Ligar sinais ao token no seu ponto de entrada; cooperar com `ctx.check()` | 0005 |
| 2 | Fluxo e subetapas | Proposto: rastreamento de subetapas | — | — | Decidir o que é uma subetapa; a composição do fluxo continua sendo código do consumidor | 0005 |
| 3 | Fila | — | `orchestrator-queue` | `orchestrator-queue-sql`; em memória, para testes | Tabela, colunas, estados, ordenação, classificação das falhas e idempotência do processamento | 0008 |
| 4 | Notificações | Proposto: mascaramento público de texto | `orchestrator-notifications` | `orchestrator-notifications-smtp`, `orchestrator-notifications-teams` | Quais eventos avisam quem; conteúdo das mensagens de negócio | 0007 |
| 5 | Logs e registros | Já existe: logging e `ExecutionRecordSink`. Mudança do port só se o destino SQL for aceito | — | `orchestrator-records-file`, `orchestrator-records-sql` (Providers do port do Core) | Logs de negócio, auditoria, histórico e retenção | 0009 |
| 6 | Mapeamentos | — | `orchestrator-mappings` | Arquivo (embutido), `orchestrator-mappings-sql`, `orchestrator-mappings-excel` | Conteúdo, significado e esquema de cada mapeamento | 0010 |
| 7 | Login por sistema | — | `orchestrator-auth`, condicional | Estratégias por sistema, em pacotes da organização | Escolha das contas; credenciais por referência | 0012 |
| 8 | Segredos | Já existe: `SecretResolver` e `SecretStore` | — | `orchestrator-keyvault` (Provider do port do Core) | Escolha do cofre e da identidade de acesso | 0006 |
| 9 | Calendários | — | `orchestrator-calendar` | Arquivo (embutido), feriados padrão, SQL, Excel | Jurisdições, exceções e convenções de contagem | 0011 |

Dependências entre os pacotes (cada linha depende do nível acima):

```text
orchestrator-core
├── orchestrator-sql ................... Capability (existe)
│   ├── orchestrator-sqlite ............ Provider (existe)
│   └── segundo Provider ............... adiado (roadmap, E4.4)
├── orchestrator-queue ................. Capability
│   └── orchestrator-queue-sql ......... Provider; usa também orchestrator-sql
├── orchestrator-notifications ......... Capability
│   ├── orchestrator-notifications-smtp
│   └── orchestrator-notifications-teams
├── orchestrator-mappings .............. Capability, com Provider de arquivo embutido
│   ├── orchestrator-mappings-sql ...... usa também orchestrator-sql
│   └── orchestrator-mappings-excel
├── orchestrator-calendar .............. Capability, com Provider de arquivo embutido
│   └── Providers de feriados padrão, SQL e Excel
├── orchestrator-auth .................. Capability condicional (RFC-0012)
├── orchestrator-keyvault .............. Provider do port SecretResolver do Core
├── orchestrator-records-file .......... Provider do port ExecutionRecordSink do Core
└── orchestrator-records-sql ........... idem; usa também orchestrator-sql
```

Os nomes são propostos (DS-4). Nenhum desses pacotes existe.

## 4. Decisões transversais solicitadas

Aceita esta RFC, cada decisão entra em `docs/DECISIONS.md` a partir de D-26, com o registro indicado.

| ID | Decisão | Opções | Recomendação |
|---|---|---|---|
| DS-1 | Um Provider pode depender de uma segunda Capability quando ela é a sua infraestrutura (fila sobre SQL)? A ADR-0004 não prevê o caso | (a) Permitir, com regras; (b) proibir: cada Provider abre as próprias conexões | (a), registrada em ADR nova. Regras: dependência declarada no `pyproject.toml` e em `tools/test_boundaries.py`; o Provider obtém o handle por `ctx.capability(...)` de um registro nomeado na sua configuração; pacotes de Capability nunca dependem de outra Capability; sem ciclos |
| DS-2 | Compatibilidade da API do Core antes da 1.0 (ADR-0009, item 5): a igualdade exata obriga a relançar todas as Capabilities a cada versão menor do Core | (a) Manter; (b) cada Capability declara uma faixa de versões de API | (a) por enquanto: juntar numa única 0.2 as mudanças do Core aceitas (RFC-0005 e, se aceita, a mudança de port da RFC-0009) e as do port SQL (RFC-0006, 2.1); rever a regra na segunda versão menor ou na primeira separação de pacote |
| DS-3 | Política para as primeiras dependências de terceiros em tempo de execução (Key Vault, Excel, feriados) | Ver abaixo | Aceitar os cinco pontos antes do primeiro Provider com dependência |
| DS-4 | Nomes dos pacotes | `orchestrator-<capability>` e `orchestrator-<capability>-<tecnologia>`; ou só a tecnologia, como `orchestrator-sqlite` | Prefixo da Capability sempre que a tecnologia servir a mais de uma (SQL, Excel) |
| DS-5 | Fronteira com a ADR-0016 | — | **Rastrear** partes que o código do consumidor executa entra (RFC-0005). **Compor** (a plataforma decidir ordem, repetir, pular ou retomar partes) continua fora |
| DS-6 | Excel: Capability `orchestrator-excel`, prevista na arquitetura, ou dependência direta de cada Provider | (a) Capability desde já; (b) dependência direta no primeiro uso | (b); criar a Capability quando houver o segundo uso |
| DS-7 | "Finalização de processos" inclui encerrar processos do sistema operacional abertos pela automação? | — | Sem recomendação: depende do responsável (diagnóstico, L1.4) |
| DS-8 | Primeiro consumidor real e primeira entrega | Seções 6 e 7 | Seção 6 |

**DS-3, em detalhe.** (1) Toda dependência nova é justificada no PR (manutenção, adoção, segurança, licença), como `GOVERNANCE.md` já exige. (2) O lock com hashes das dependências, pendente na [ADR-0013](../adr/0013-build-e-ferramentas.md), passa a ser pré-requisito. (3) `tools/e2e.py` instala com `--no-index`; para continuar assim, um conjunto de wheels é baixado a partir do lock antes da instalação. (4) Cada dependência precisa suportar toda a matriz de Python da CI, ou o pacote declara a própria matriz. (5) A licença de cada dependência é registrada no README do pacote.

## 5. Sequência de entregas

Cada linha é um Pull Request. Os identificadores continuam o roadmap como "Fase 7"; nada entra em `docs/IMPLEMENTATION_ROADMAP.md` antes do aceite. Toda entrega com código cumpre a Definition of Done de `GOVERNANCE.md` e registra no PR os comandos executados e os resultados: Ruff, formatação, MyPy estrito, Pytest com cobertura mínima, fronteiras, build reproduzível e ponta a ponta.

| ID | Entrega | Depende de | Critério de aceite | Testes |
|---|---|---|---|---|
| | **Etapa 0 — decisões, sem código** | | | |
| E7.1 | Decisão do responsável sobre as RFCs 0004 a 0012 e escolha do primeiro consumidor real | — | Status de cada RFC atualizado; `DECISIONS.md` e roadmap atualizados | — |
| E7.2 | Primeira execução da CI confirmada (roadmap, seção 10, item 2) | — | Jobs `quality`, `tests`, `build` e `e2e` verdes em Ubuntu e Windows; cobertura medida | Os da CI |
| | **Etapa 1 — Core 0.2 ([RFC-0005](0005-core-0-2-subetapas-mascaramento-teardown-e-sinais.md)), só o que for aceito** | | | |
| E7.3 | Mascaramento público de texto | E7.1 | Um valor-sentinela resolvido nunca aparece em texto produzido por finalizer ou estágio que use a API; RFC-0002 e `test_public_api.py` atualizados | Sentinela em finalizer e em estágio de teardown; texto sem segredo passa intacto |
| E7.4 | Orçamento de teardown | E7.1 | Depois de `timed_out` e de `cancelled`, uma operação de teardown com política de retry é tentada e nunca ultrapassa o orçamento | Relógio falso; os quatro status; orçamento esgotado |
| E7.5 | Rastreamento de subetapas | E7.1, DS-5 | Status, duração e erro mascarado de cada subetapa em eventos, resultado e registro; campo de correlação nos logs; a exceção original é preservada | Sucesso, falha, aninhamento, cancelamento dentro da subetapa, 8 threads, limite de quantidade |
| E7.6 | Guia de encerramento por sinal, aplicado aos dois exemplos | E7.1 | O exemplo termina `cancelled`, com teardown, ao receber `SIGTERM` em Linux e `CTRL_BREAK` em Windows; nada é instalado sem chamada explícita | Subprocesso nos dois sistemas |
| E7.7 | Release 0.2.0 dos três pacotes | E7.3 a E7.6; E7.8 e a mudança de port da RFC-0009, se aceitas até aqui (DS-2) | Matriz de compatibilidade atualizada; exemplos instalados a partir dos wheels | `python -m tools.e2e` |
| | **Etapa 2 — segredos ([RFC-0006](0006-segredos-cofres-e-credenciais-de-providers.md))** | | | |
| E7.8 | Caminho para credenciais no port SQL | E7.1 | Um Provider de teste com senha por referência conecta; a senha não aparece em log, evento, registro nem erro; o uso do SQLite não muda para o consumidor | `SqlProviderContract` ampliada; valor-sentinela |
| E7.9 | `orchestrator-keyvault` | E7.1, DS-3 | Resolve a referência com credencial injetada pelo consumidor; erros citam o nome do segredo, nunca o valor; testes unitários sem rede | Cliente falso; teste de integração marcado, fora da CI padrão |
| | **Etapa 3 — notificações ([RFC-0007](0007-capability-de-notificacoes.md))** | | | |
| E7.10 | `orchestrator-notifications`: contrato, canal em memória, suíte de conformidade | E7.3, E7.4 | Nada é enviado sem configuração explícita do evento; falha de canal não muda o status por padrão e fica visível em log, métrica e relatório; com `required`, o aviso de fim muda o status e aparece como erro de teardown, e o de início impede a automação | Matriz de status × política; sentinela; `check_capability_conformance` |
| E7.11 | `orchestrator-notifications-smtp` | E7.10 | Mensagem entregue a um servidor de teste local; tempo limite respeitado; credencial só por referência | Servidor falso com `socketserver`; suíte de conformidade |
| E7.12 | `orchestrator-notifications-teams` | E7.10 | Requisição entregue a um servidor HTTP local; URL do webhook tratada como segredo | Servidor falso com `http.server`; suíte de conformidade |
| | **Etapa 4 — registros e logs ([RFC-0009](0009-destinos-de-registros-e-logs.md))** | | | |
| E7.13 | Guia de logs em arquivo e `orchestrator-records-file` | E7.1 | Um registro por linha, válido como JSON, sob escrita concorrente de 8 threads; falha de escrita aparece como erro de teardown, ou só em log com `required = false` | Concorrência; disco indisponível simulado |
| E7.14 | `orchestrator-records-sql` | E7.8, DS-1 e a mudança de port da RFC-0009, incluída na release de E7.7 | Registro gravado em tabela mapeada pelo consumidor, com conexão própria | SQLite; tabela e colunas com nomes arbitrários |
| | **Etapa 5 — fila ([RFC-0008](0008-capability-de-fila.md))** | | | |
| E7.15 | Limite de linhas na Capability SQL | E7.1 | `select` com limite em todos os dialetos suportados; RFC-0003 e suíte atualizadas | `SqlProviderContract` |
| E7.16 | Segundo Provider SQL (roadmap, E4.4), conforme o banco do consumidor | E7.8, DS-3 | Aprovado na `SqlProviderContract`, com o banco real na CI | Suíte de conformidade; credencial por referência |
| E7.17 | `orchestrator-queue`: contrato, Provider em memória, suíte de conformidade | E7.4 | Nenhum item entregue a dois detentores ao mesmo tempo; todo item adquirido termina concluído, falho, inválido ou devolvido, também em falha, cancelamento e prazo | Concorrência com 8 threads; matriz de desfechos; relógio falso para leases |
| E7.18 | `orchestrator-queue-sql` | E7.15, E7.17, DS-1 | Aprovado na suíte com tabela, colunas e estados fornecidos pelo teste; nenhum nome fixo no pacote | Suíte de conformidade com duas conexões; dois mapas diferentes |
| | **Etapa 6 — dados de referência ([RFC-0010](0010-mapeamentos-compartilhados.md), [RFC-0011](0011-calendarios-e-dias-uteis.md))** | | | |
| E7.19 | `orchestrator-mappings` com Provider de arquivo | E7.1 | Conjunto identificado, validado e com versão registrada no log da execução; entrada inválida falha com o identificador e a linha | Validação; versão; origem indisponível |
| E7.20 | Providers de mapeamentos em SQL e Excel | E7.19, DS-1, DS-3, DS-6 | Aprovados na suíte do port | Suíte de conformidade |
| E7.21 | `orchestrator-calendar` com Provider de arquivo | E7.1 | Cálculos corretos em casos de fronteira; consulta fora do período carregado é erro | Tabela de casos; cobertura de anos |
| E7.22 | Providers de calendário: feriados padrão, SQL, Excel | E7.21, DS-1, DS-3 | Aprovados na suíte do port; origem e versão de cada feriado rastreáveis | Suíte de conformidade |
| | **Etapa 7 — autenticação ([RFC-0012](0012-autenticacao-por-sistema.md))** | | | |
| — | Sem entrega planejada | Fluxo real descrito | — | — |

## 6. Primeira entrega

A ordem depende do primeiro consumidor real:

| Se a primeira automação real… | Começar por |
|---|---|
| precisa avisar falhas por e-mail ou Teams | E7.3, E7.4, E7.10 e um canal (E7.11 ou E7.12) |
| acessa um banco com usuário e senha | E7.8 e E7.16 |
| busca credenciais num cofre | E7.9 |
| consome itens de uma tabela de fila | E7.8, E7.15, E7.16, E7.17 e E7.18 |
| só precisa de logs e registros em arquivo | E7.13 |

Sem essa informação, a recomendação é a fatia "aviso de falha" (primeira linha), demonstrada num exemplo em `examples/`. Motivos: fecha duas lacunas verificadas que qualquer integração de teardown vai encontrar (L1.2 e L8.4 do diagnóstico); não depende de schema nem de regra de consumidor; os dois Providers usam só a biblioteca padrão; e tem valor operacional imediato. Ainda assim, exige saber qual canal existe no ambiente real (seção 7, item 4).

## 7. Informações necessárias de um consumidor real

Sem elas, as RFCs indicadas não podem ser aceitas. Nenhuma regra de negócio foi suposta em seu lugar.

1. **A primeira automação real**: o que faz, em uma frase; que sistemas toca; como é iniciada e como é interrompida (Agendador de Tarefas, serviço, outro orquestrador); sistema operacional e versão de Python da máquina que executa. Destrava DS-8 e a RFC-0005.
    R: A plataforma deverá oferecer recursos parametrizáveis e reutilizáveis, que sirvam como base para a construção de diversas automações diferentes. Portanto, não se trata de desenvolver a plataforma para atender a uma única automação específica, mas de permitir que diferentes projetos construam suas automações utilizando os mesmos controles e recursos compartilhados.
2. **Banco de dados**: motor e versão; forma de autenticação (usuário e senha, autenticação integrada, identidade gerenciada); driver já homologado. Destrava E7.8 e E7.16.
    R: Deverá ser utilizada a versão mais recente disponível do banco de dados. Os usuários e as senhas de acesso deverão ser parametrizáveis, permitindo que cada automação configure suas próprias credenciais, conforme sua necessidade.
3. **Fila**: estrutura da tabela real, sem dados; quem insere os itens; quantas execuções consomem ao mesmo tempo e de quantas máquinas; regra de ordenação; o que é um item inválido; número de tentativas; o que deve acontecer com o item de uma execução que morreu. Destrava a RFC-0008.
    R: Respondido no RFC-0008
4. **Notificações**: canais existentes (servidor SMTP interno, Exchange Online, Teams com Workflows); quem recebe o quê, em quais eventos; idioma e conteúdo mínimo; volume esperado. Destrava a RFC-0007.
    R: Respondido no RFC-0007.
5. **Logs e registros**: onde os logs técnicos precisam ficar, por quanto tempo e quem os consulta; se o histórico de execuções precisa de consulta em banco, e quais consultas; restrições de dados pessoais. Destrava a RFC-0009.
    R: Respondido no RFC-0009.
6. **Mapeamentos**: um exemplo anonimizado, de duas ou três linhas, do que é um "mapeamento"; onde vive hoje; quem mantém; com que frequência muda; se uma automação precisa fixar a versão que usa. Destrava a RFC-0010.
    R: Os mapeamentos deverão centralizar caminhos e referências utilizados nas automações, incluindo elementos e caminhos relacionados a CSS, JavaScript (JS) e interfaces gráficas (GUI).

    Esses mapeamentos deverão ficar unificados em um arquivo compartilhado, que poderá ser atualizado por todos os desenvolvedores dos projetos. A manutenção será manual, e sua frequência dependerá das alterações realizadas em cada sistema.

    As automações deverão utilizar sempre a versão mais atualizada desse arquivo, sem necessidade de fixar uma versão específica do mapeamento para cada execução.
7. **Login**: sistemas; tecnologia de acesso (navegador, desktop, API); segundo fator; onde as credenciais estão hoje. Destrava a RFC-0012.
    R: Os sistemas e as formas de autenticação dependerão das necessidades de cada automação. A plataforma deverá permitir diferentes estratégias de login, de acordo com o sistema utilizado por cada projeto.

    As credenciais poderão ser armazenadas no Azure Key Vault ou em banco de dados SQL, conforme a configuração e a necessidade de cada automação.
8. **Segredos**: cofre em uso; identidade disponível para a máquina que executa; acesso de rede ao cofre. Destrava a RFC-0006.
    R: Respondido no RFC-0006.
9. **Calendários**: jurisdições (nacional, estadual, municipal); calendário civil ou bancário; quem mantém as exceções; horizonte em anos; cálculos necessários. Destrava a RFC-0011.
    R: Os calendários deverão permitir revisão e atualização manual. A manutenção das datas e das informações do calendário será responsabilidade dos usuários ou desenvolvedores responsáveis por mantê-los atualizados.
10. **Distribuição**: quantos projetos vão compartilhar cada controle; se as máquinas podem instalar dependências de terceiros, e de onde. Destrava DS-3.
    R: Todos os projetos que utilizarem a plataforma deverão compartilhar os recursos disponibilizados por ela, incluindo controles reutilizáveis, dependências, calendários, funções auxiliares e demais componentes comuns.

    O objetivo é centralizar esses recursos para que sejam mantidos e evoluídos de forma compartilhada, evitando implementações duplicadas em cada projeto e permitindo que todos os projetos consumidores utilizem os mesmos componentes atualizados.

## 8. Riscos

| Risco | Mitigação |
|---|---|
| Superfície grande para um único mantenedor: até dezesseis pacotes novos, além do segundo Provider SQL já previsto | Entregar só o que tiver caso real; uma fatia vertical por vez |
| Contrato desenhado sem caso real vira abstração errada | Condição de aceite em cada RFC; antes da 1.0, uma versão menor pode quebrar |
| Mudanças em cadeia no Core | Uma única versão 0.2 (DS-2) |
| Primeiras dependências de terceiros | DS-3; Providers isolados em pacotes próprios |
| A CI ainda não foi confirmada no GitHub; cobertura não medida nesta sessão | E7.2 antes de qualquer entrega com código |
| Estas propostas não tiveram revisão independente | Revisão do responsável; revisão de segurança obrigatória para as RFCs 0006, 0007 e 0012 (`GOVERNANCE.md`, seção 9) |

## 9. Compatibilidade e documentos a atualizar no aceite

O aceite desta RFC não muda nenhum contrato público; as mudanças de contrato estão nas RFCs 0005, 0006 e, se aceito o destino SQL, 0009. No aceite, atualizar: `docs/DECISIONS.md` (decisões novas), `docs/IMPLEMENTATION_ROADMAP.md` (Fase 7), `ARCHITECTURE.md` (seção 5), `docs/rfc/README.md` (status) e criar a ADR da DS-1.

## 10. Alternativas consideradas

- **Um pacote único de utilitários.** Junta dependências sem relação (SMTP, Excel, cofre), impede evolução independente e contraria as ADRs 0001 e 0004.
- **Contratos no Core.** Repete o problema do scaffold, que tinha doze ports sem uso no Core (`docs/audit/CODE_AUDIT.md`, COD-08), e contraria a ADR-0004.
- **Deixar tudo com cada consumidor.** Mantém a duplicação que motivou o pedido.
- **Tudo em pacotes da organização, fora da plataforma.** É o lugar certo para o que carrega convenção de consumidor (ADR-0019), não para mecanismos genéricos.
