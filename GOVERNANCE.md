# Governança

Padrões de engenharia da plataforma Orchestrator. Todo contribuidor segue estas regras.

## 1. Repositórios

Durante a série 0.x, este repositório contém a governança e os pacotes incubados em `packages/`. A topologia-alvo é multirrepositório, com critérios de separação definidos na [ADR-0001](docs/adr/0001-topologia-de-repositorios.md).

## 2. Branches

- Permanente: `main`. Commits diretos em `main` são proibidos.
- Temporárias: `feature/*`, `fix/*`, `hotfix/*`, `release/*`, `experiment/*`, `docs/*` e `chore/*`.

## 3. Pull Requests

Toda mudança entra por Pull Request, com:

- objetivo e motivação;
- evidência de testes (comandos e resultados);
- impacto arquitetural e de compatibilidade;
- ADR, RFC e issues relacionadas.

Merge por **squash**, com a mensagem do PR em Conventional Commits. Os checks obrigatórios da CI precisam passar. Enquanto houver um único mantenedor, a aprovação de outra pessoa não é exigida; com o segundo, passa a ser exigida uma aprovação ([ADR-0014](docs/adr/0014-ci-e-controles-do-github.md)).

## 4. Commits e versões

- Conventional Commits: tipo e escopo em inglês (`feat(core):`, `fix(sql):`, `docs:`), descrição em português.
- Versionamento semântico por pacote: MAJOR para incompatibilidades, MINOR para funcionalidades, PATCH para correções. Antes da 1.0, uma versão MINOR pode quebrar compatibilidade.
- Tags: `<distribuição>/v<versão>` (ex.: `orchestrator-core/v0.1.0`). Tags `archive/*` preservam estados históricos.

Detalhes: [ADR-0018](docs/adr/0018-convencoes-de-commit-branch-e-versao.md).

## 5. Decisões

- Mudanças arquiteturais significativas exigem ADR em `docs/adr/`.
- Funcionalidades grandes ou transversais começam por RFC em `docs/rfc/`, aceita antes da implementação.
- Registro geral: [docs/DECISIONS.md](docs/DECISIONS.md).

## 6. Padrões de código

Obrigatórios: type hints, docstrings no estilo Google em inglês, Ruff (lint e formatação compatível com Black), MyPy estrito, Pytest. Código em inglês; documentação narrativa em português ([ADR-0017](docs/adr/0017-titularidade-licenca-idioma-visibilidade.md)).

## 7. Testes

- Toda funcionalidade nova tem testes; toda correção de bug tem teste de regressão.
- Testes de integração quando há infraestrutura envolvida; testes de estresse para componentes críticos (concorrência do Runtime).
- Cobertura mínima de 90% (linhas e ramos), verificada pela CI.
- Providers passam na suíte de conformidade da sua Capability; Capabilities passam em `check_capability_conformance` ([ADR-0015](docs/adr/0015-testes-entre-pacotes.md)).

## 8. Dependências

Dependência nova exige justificativa no PR: manutenção, adoção, histórico de segurança, licença e cadência de releases. O Core não aceita dependências de terceiros. Bibliotecas abandonadas não são adotadas.

## 9. Segurança

Política em [SECURITY.md](SECURITY.md). Segredos nunca são commitados. Mudanças em criptografia, autenticação, segredos, rede, pipeline de execução, carregamento de plugins ou resolução de dependências exigem revisão arquitetural de segurança.

## 10. Ciclo de vida de uma Capability

Proposta (RFC) → revisão de arquitetura → implementação → testes (inclusive conformidade) → documentação → release → manutenção → depreciação.

## 11. Depreciação

Funcionalidades depreciadas continuam disponíveis por pelo menos uma versão MINOR, salvo questão de segurança. Toda depreciação é documentada no CHANGELOG do pacote.

## 12. Releases

Cada release tem notas (CHANGELOG do pacote) e, quando necessário, guia de migração. Processo: [docs/guides/release.md](docs/guides/release.md). Publicar em índice de pacotes exige RFC e autorização do responsável.

## 13. Classificação de issues

Bug, Feature, Capability, Documentation, Architecture, Security e Technical Debt (rótulos em `.github/labels.yml`).

## 14. Definition of Done

Uma entrega está concluída quando:

- a implementação segue os contratos e a arquitetura;
- type hints e docstrings estão completos;
- Ruff, formatação, MyPy e Pytest passam, com a cobertura mínima;
- testes unitários, de integração e de estresse aplicáveis existem;
- documentação pública, exemplos e CHANGELOG estão atualizados;
- o PR foi revisado conforme a seção 3;
- a CI passou.

## 15. Visão de longo prazo

A plataforma deve suportar várias equipes, centenas de projetos consumidores e Capabilities modulares por muitos anos. Extensibilidade, manutenibilidade e estabilidade têm prioridade sobre velocidade de curto prazo.
