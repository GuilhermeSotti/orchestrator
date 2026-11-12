# Política de segurança

A segurança é um princípio de projeto do Orchestrator: requisitos de segurança entram desde a arquitetura, e não numa fase separada.

Princípios: Secure by Design, menor privilégio, defesa em profundidade, Zero Trust, segurança da cadeia de suprimentos, builds reproduzíveis, dependências explícitas e monitoramento contínuo de vulnerabilidades.

## Versões suportadas

| Pacote | Versão | Correções de segurança |
|---|---|---|
| `orchestrator-core` | 0.1.x | Sim |
| `orchestrator-sql` | 0.1.x | Sim |
| `orchestrator-sqlite` | 0.1.x | Sim |

Antes da 1.0, só a série mais recente de cada pacote recebe correções.

## Como reportar uma vulnerabilidade

**Não abra issue pública.** Use o reporte privado do GitHub: aba **Security → Report a vulnerability** deste repositório. Se a opção não estiver disponível, abra uma issue pedindo um canal privado, sem nenhum detalhe da vulnerabilidade.

Inclua: pacote e versão afetados, descrição, passos para reproduzir, prova de conceito (se houver) e impacto possível.

## Divulgação

Vulnerabilidades são tratadas em privado até haver correção. Depois: release corrigida, nota no CHANGELOG do pacote e aviso de segurança no GitHub; CVE quando aplicável.

## Garantias implementadas

| Tema | Como é tratado |
|---|---|
| Dependências do Core | Nenhuma de terceiros; verificado por teste ([ADR-0005](docs/adr/0005-dependencias-do-core.md)) |
| Segredos | Somente por referência (`env:`, `file:`, resolvedores próprios); valor encapsulado em `Secret`, sem `repr`, sem serialização; literais recusados sem eco do valor ([ADR-0007](docs/adr/0007-configuracao-e-segredos.md)) |
| Logs, eventos e registros | Segredos resolvidos são mascarados (`***`) em mensagens, tracebacks, eventos e registros de execução |
| SQL | Valores sempre como parâmetros; identificadores validados e citados; mensagens de erro sem valores de parâmetros ([RFC-0003](docs/rfc/0003-capability-sql.md)) |
| Plugins | Sem descoberta automática; só Capabilities e Providers registrados explicitamente ([ADR-0009](docs/adr/0009-registro-de-capabilities-e-compatibilidade.md)) |
| Exceções de infraestrutura | Traduzidas pelos Providers para erros da Capability, sem detalhes internos sensíveis |
| Arquivos temporários | Workspace criado com `tempfile.mkdtemp` (acesso restrito ao usuário) e removido no `finalize` |
| Análise estática | Regras `S` do Ruff (equivalentes ao Bandit) na CI |

## Gestão de segredos

Segredos nunca são commitados, nem gravados em código, arquivos de configuração ou logs. Origem: variáveis de ambiente, cofres de segredos ou secret stores de CI/CD. Arquivos `.env` são ignorados pelo Git e não são carregados pelo Core.

## Cadeia de suprimentos

- Ferramentas de desenvolvimento com versões fixadas em `requirements/dev.txt`; lock com hashes pendente ([ADR-0013](docs/adr/0013-build-e-ferramentas.md)).
- Ações do GitHub fixadas por SHA; workflows com permissão mínima.
- Builds reproduzíveis verificados por `tools/build_packages.py --check`; releases publicam o SHA-256 de cada artefato.
- Dependabot para Actions e ferramentas.
- Evolução prevista, ainda não implementada: SBOM, proveniência, artefatos assinados (Sigstore), SLSA e trusted publishing.

## Controles do GitHub

Devem ser habilitados pelo responsável, conforme o plano permitir: alertas e atualizações de segurança do Dependabot, secret scanning com push protection, CodeQL (configuração padrão), dependency review e reporte privado de vulnerabilidades. Passo a passo: [docs/guides/governanca-github.md](docs/guides/governanca-github.md).

## Diretrizes de código seguro

Evite: credenciais no código, execução dinâmica não validada, desserialização insegura, injeção de comandos, injeção de SQL, path traversal e arquivos temporários inseguros. Toda entrada externa é não confiável. Providers validam entradas e saídas, tratam falhas e isolam exceções de infraestrutura.

## Logs

Nunca registre senhas, chaves de API, tokens, connection strings com credenciais, dados pessoais ou identificadores de sessão. Use `orchestrator_core.logs.configure_logging` ou adicione `RedactingFilter` aos seus handlers.

## Revisão de segurança

Mudanças em criptografia, autenticação, segredos, rede, pipeline de execução, carregamento de plugins ou resolução de dependências exigem revisão arquitetural de segurança no PR.

## Resposta a incidentes

1. Avaliar a severidade.
2. Isolar os componentes afetados.
3. Produzir a correção, com teste de regressão.
4. Publicar a versão corrigida.
5. Publicar as notas de release e o aviso de segurança.
6. Analisar a causa raiz.
7. Atualizar a documentação, se necessário.
