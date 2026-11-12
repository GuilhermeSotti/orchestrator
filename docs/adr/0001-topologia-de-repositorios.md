# ADR-0001 — Topologia de repositórios: incubação no repositório `orchestrator`

| Campo | Valor |
|---|---|
| Status | Aceito |
| Data | 2026-11-12 |
| Decisão | D-01 e D-23 (item 2) em `docs/DECISIONS.md` |
| Decisor | Claude, por delegação explícita do responsável pelo projeto (2026-11-12) |

## Contexto

README, ARCHITECTURE e GOVERNANCE definiam uma estratégia multirrepositório: um repositório de governança (`orchestrator-platform`) e um repositório por pacote. Na prática, o repositório remoto `orchestrator` já continha governança e código (ARQ-01). A recomendação anterior (`docs/OPEN_DECISIONS.md`, 2026-11-11) era multirrepositório começando com dois repositórios.

Em 2026-11-12 o escopo passou a incluir a primeira Capability e o primeiro Provider, o que exigiria quatro repositórios de imediato. Além disso:

- há um único mantenedor e os contratos ainda vão mudar durante a série 0.x;
- o remoto não estava acessível no ambiente em que o trabalho foi feito, e repositórios novos não podiam ser criados de lá;
- em repositórios privados, a CI de um pacote não lê outro repositório privado com o `GITHUB_TOKEN` padrão; seria preciso um token adicional.

## Decisão

1. Durante a série 0.x, o repositório `orchestrator` incuba os pacotes distribuíveis em `packages/` e os projetos consumidores de exemplo em `examples/`, junto com a documentação de governança. Ele cumpre o papel previsto para `orchestrator-platform`; o nome não muda.
2. A estratégia multirrepositório continua sendo a topologia-alvo. Cada pacote em `packages/` é autossuficiente para ser separado: `pyproject.toml`, README, CHANGELOG, LICENSE, testes e versão próprios.
3. As fronteiras são verificadas por testes: o Core importa só a biblioteca padrão; a Capability SQL importa só o Core; o Provider SQLite importa só a Capability e o Core (`tools/test_boundaries.py`).
4. Um pacote é separado em repositório próprio quando ocorrer qualquer um destes fatos: atingir a versão 1.0; ganhar mantenedores próprios; precisar de visibilidade ou licença diferente; precisar de cadência de release que o repositório comum atrapalhe. A separação usa `git subtree split --prefix packages/<pacote>` e preserva o histórico.

## Alternativas consideradas

- **Multirrepositório imediato.** Mantém o desenho documentado, mas cria quatro repositórios para um mantenedor, exige token entre repositórios privados e transforma toda mudança de contrato em mudanças coordenadas em vários lugares. Rejeitada para a série 0.x.
- **Monorepo permanente.** Simplifica para sempre, mas abandona o isolamento que motivou a estratégia original. Rejeitada: a incubação mantém o alvo e define quando sair dela.
- **Dois repositórios (governança e Core).** A recomendação anterior. Deixa de fazer sentido com a Capability e o Provider no escopo: o problema de coordenação aparece logo na primeira Capability.

## Consequências

- Mudanças de contrato no Core, na Capability e no Provider entram num único Pull Request, testadas juntas.
- Uma única CI cobre todos os pacotes; não há credencial entre repositórios.
- Cada pacote tem tag de release própria (`<distribuição>/v<versão>`, ver ADR-0018).
- README, ARCHITECTURE e GOVERNANCE foram atualizados. A lista de repositórios futuros vira lista de pacotes previstos.
- Risco: acoplamento acidental entre pacotes. Mitigação: testes de fronteira e dependências declaradas por pacote.

## Referências

- `docs/audit/INITIAL_AUDIT.md` (ARQ-01, GOV-03) e `docs/DECISIONS.md` (D-01).
- ADR-0004 (fronteiras), ADR-0015 (testes entre pacotes), ADR-0018 (tags por pacote).
