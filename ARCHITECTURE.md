# Arquitetura

O Orchestrator é uma plataforma modular de automação em Python. Padroniza o ciclo de vida de execução das automações e oferece infraestrutura técnica comum; a lógica de negócio pertence sempre ao projeto consumidor.

A plataforma não depende de frameworks de automação, engines de execução, bancos de dados, provedores de nuvem ou infraestrutura específicos. Novas tecnologias entram como pacotes (Capabilities e Providers), sem alterar o Core.

Decisões que fundamentam este documento: [docs/DECISIONS.md](docs/DECISIONS.md).

## 1. Princípios

- **Core pequeno**: só responsabilidades transversais e abstrações estáveis ([ADR-0004](docs/adr/0004-fronteiras-core-capability-provider.md)).
- **Dependências para dentro**: Provider → Capability → Core; o Core não depende de infraestrutura nem de bibliotecas de terceiros ([ADR-0005](docs/adr/0005-dependencias-do-core.md)).
- **Dependências explícitas**: composição pelo `RuntimeBuilder`, sem descoberta implícita nem singletons ([ADR-0008](docs/adr/0008-composicao-e-injecao-de-dependencias.md)).
- **Extensão sem alterar o Core**: comprovada pela Capability SQL e pelo Provider SQLite.
- **Convenção com customização**: padrões seguros e documentados; toda customização é explícita.
- **Testabilidade**: todo componente é substituível por dublês (`orchestrator_core.testing`).
- **Abstrações justificadas**: nenhum port sem consumidor.

Padrões de referência: SOLID, Clean Architecture, Hexagonal Architecture (Ports & Adapters), injeção de dependências, Builder (composição), Strategy (Providers), arquitetura orientada a eventos (eventos de ciclo de vida) e arquitetura de plugins controlada (registro explícito).

## 2. Vocabulário

| Termo | Significado | No código |
|---|---|---|
| Consumer Project | Projeto que usa o Orchestrator e contém a lógica de negócio | `examples/` |
| Core | Contratos e componentes transversais | `orchestrator-core` |
| Runtime | Executa uma automação pelo pipeline | `Runtime`, `RuntimeBuilder` |
| Execution Pipeline | Sequência extensível de estágios | `Stage`, oito estágios embutidos |
| Execution Context | Dados e serviços de uma execução | `ExecutionContext` |
| Capability | Módulo funcional que amplia o Runtime por contrato | `Capability`; ex.: `SqlCapability` |
| Provider | Implementação concreta de um port de Capability | ex.: `SqliteProvider` |
| Port | Contrato entre componentes | ex.: `SqlProvider`, `MetricsRecorder` |
| Capability Registry | Registro explícito das Capabilities de um Runtime | `with_capability(...)` |

## 3. Visão de componentes

Fluxo de controle de uma execução:

```text
Projeto consumidor ──run(automação)──▶ Runtime ──▶ Execution Pipeline (8 estágios)
                                         │
                                         ├── Execution Context (por execução)
                                         ├── Configuração e segredos
                                         ├── Capability Registry ──▶ Capabilities ──▶ Providers ──▶ infraestrutura
                                         ├── Eventos (barramento síncrono)
                                         ├── Logging (correlação e mascaramento)
                                         └── Métricas (port)
```

Regra de dependência (quem importa quem):

```text
Projeto consumidor ──▶ Provider ──▶ Capability ──▶ Core ──▶ biblioteca padrão
        │                               ▲            ▲
        └───────────────────────────────┴────────────┘
```

A Public API é a superfície exportada pelo Core (`orchestrator_core`, `orchestrator_core.logs`, `orchestrator_core.testing`), listada na [RFC-0002](docs/rfc/0002-escopo-do-mvp-e-api-publica.md). Os testes de fronteira (`tools/test_boundaries.py`) garantem que nenhum pacote importe o que não declara.

## 4. Ciclo de vida da execução

| Fase | Estágio | O que faz |
|---|---|---|
| Preparação | `initialize` | Início no log e evento `ExecutionStarted` |
| Preparação | `provision_dependencies` | Verifica e abre cada Capability; nunca instala pacotes |
| Preparação | `prepare_environment` | Workspace temporário opcional |
| Preparação | `prepare_execution` | Valida os parâmetros |
| Execução | `execute_automation` | Chama a automação do consumidor |
| Teardown | `finalize` | Finalizers e liberação de recursos, em ordem inversa |
| Teardown | `persist_logs` | Registro da execução para os destinos e descarga dos logs |
| Teardown | `shutdown` | Fecha o contexto |

Uma falha na preparação impede a execução; o teardown sempre roda; erros de teardown não mascaram o erro primário. Cancelamento e prazo são cooperativos. Estágios novos são inseridos sem alterar os existentes. Semântica completa: [RFC-0001](docs/rfc/0001-ciclo-de-vida-da-execucao.md).

## 5. Capabilities e Providers

Uma Capability é registrada uma vez no Runtime e, a cada execução, abre um handle próprio daquela execução, liberado no `finalize`. Ela define o contrato usado pela automação e o port dos Providers. Um Provider implementa o port para uma tecnologia e traduz exceções de infraestrutura para erros da Capability.

Previstas na arquitetura (nenhuma implementada além de SQL): Browser, Excel, HTTP, Docker, Filesystem, Queue, Email, Secrets, PDF. Providers previstos: PostgreSQL, SQL Server, MySQL, Azure, AWS, filesystem local, OpenTelemetry. Cada uma começa por RFC. Guia: [Capabilities e Providers](docs/guides/capabilities-e-providers.md).

## 6. Pacotes e repositórios

Durante a série 0.x os pacotes incubam neste repositório, em `packages/`, cada um autossuficiente e com versão própria. A topologia-alvo continua multirrepositório: um pacote vai para repositório próprio ao atingir a 1.0, ganhar mantenedores próprios ou precisar de visibilidade, licença ou cadência diferentes ([ADR-0001](docs/adr/0001-topologia-de-repositorios.md)).

## 7. Compatibilidade

SemVer por pacote; antes da 1.0, versão menor pode quebrar compatibilidade. O Core expõe `CORE_API_VERSION`; Capabilities declaram a versão de API que exigem, verificada no registro. Matriz: [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

## 8. Stack

- Python 3.13 ou superior ([ADR-0012](docs/adr/0012-python-e-plataformas.md)).
- `pyproject.toml` com setuptools por pacote ([ADR-0013](docs/adr/0013-build-e-ferramentas.md)).
- Ruff (lint e formatação compatível com Black), MyPy estrito, Pytest com cobertura.
- Pydantic: recomendado para validação de parâmetros e configurações em projetos consumidores e Capabilities; não é dependência do Core ([ADR-0005](docs/adr/0005-dependencias-do-core.md)).

## 9. Evolução futura

Execução distribuída, agentes remotos, execução em nuvem, marketplace de plugins, registry de pacotes, dashboards, workflow engine, agendamento e automação assistida por IA estão fora do escopo até a 1.0; cada um exige RFC com caso de uso real e deve entrar como pacote ([ADR-0016](docs/adr/0016-escopo-futuro.md)).
