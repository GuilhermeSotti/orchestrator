# RFC-0012 — Reutilização de fluxos de autenticação por sistema

| Campo | Valor |
|---|---|
| Status | Aceita em 2026-11-15 pelo responsável |
| Observação do responsável no aceite | Crie um caso de exemplo com mapeamentos simples usando o google |
| Data | 2026-11-14 |
| Autor | Claude, a pedido do responsável |
| Decisor | Responsável pelo projeto (aceite registrado em [DECISIONS](../DECISIONS.md), seção 5) |
| Item de escopo | 7 (reutilização de fluxos de login por sistema) |
| Relacionadas | [RFC-0006](0006-segredos-cofres-e-credenciais-de-providers.md), [RFC-0004](0004-controles-reutilizaveis-escopo-e-sequencia.md) (DS-1), [ADR-0010](../adr/0010-retry-explicito.md), [ADR-0019](../adr/0019-convencoes-de-fila-fora-da-plataforma.md) |

## 1. Problema

O responsável quer reutilizar estratégias de autenticação de um mesmo sistema em automações diferentes, **se houver caso de uso concreto**, separando o fluxo de login do armazenamento e da resolução de credenciais, sem senhas ou tokens em código, arquivos versionados, logs ou mapeamentos, e tratando o armazenamento de segredos em SQL como decisão de segurança explícita.

Não existe nada parecido ([SCOPE_DIAGNOSIS](../audit/SCOPE_DIAGNOSIS.md), seção 3.7). Também não há Capability de navegador, HTTP ou desktop em que um fluxo de login rodaria. Nenhum sistema real foi descrito.

## 2. Três responsabilidades separadas

| Responsabilidade | Onde fica | Situação |
|---|---|---|
| Guardar e resolver credenciais | Segredos por referência e Providers de cofre (ADR-0007, RFC-0006) | Existe no Core; cofres propostos na RFC-0006 |
| Executar o fluxo de autenticação de um sistema | Código que usa uma tecnologia de acesso (navegador, HTTP, desktop) | Depende de Capabilities que não existem |
| Reutilizar uma sessão autenticada (cookies, tokens) | Estado sensível, equivalente a um segredo | Não proposto (seção 4) |

## 3. Proposta

### 3.1 Agora: padrão documentado, sem pacote

Enquanto não houver um caso real, cada fluxo de login fica num **pacote da organização**, fora da plataforma, um por sistema, como prevê a ADR-0019 para convenções de um ambiente. O padrão usa só o que já existe:

```python
def entrar(ctx: ExecutionContext, cliente: ClienteDoSistema) -> SessaoDoSistema:
    secao = ctx.config.section("sistema_x")
    usuario = ctx.secrets.resolve(secao.get_secret_ref("usuario"))
    senha = ctx.secrets.resolve(secao.get_secret_ref("senha"))
    sessao = cliente.login(usuario.reveal(), senha.reveal())
    ctx.resources.callback(sessao.logout)  # logout garantido no finalize
    return sessao
```

Regras do padrão:

1. Credenciais só por referência de segredo (`env:`, `file:` ou o cofre da RFC-0006); nunca em mapeamentos, configuração versionada ou código.
2. Logout registrado em `ctx.resources`, para acontecer também em falha, cancelamento e prazo.
3. Nenhuma nova tentativa em credencial recusada: repetir uma senha errada bloqueia contas. Só falhas transitórias (`retryable`) podem ser repetidas, com `ctx.retry` e política explícita (ADR-0010).
4. Nada de credenciais, tokens, cookies ou identificadores de sessão em logs, eventos, mensagens de erro ou capturas de tela. Automações de interface não capturam a tela de login.
5. Preferir autenticação não interativa quando o sistema oferecer (token de API, credenciais de aplicativo, certificado, identidade gerenciada) à automação da tela de login.

### 3.2 Quando houver caso real: Capability `orchestrator-auth`

Justifica-se quando dois ou mais sistemas, ou duas ou mais automações do mesmo sistema, mostrarem a mesma forma de fluxo. Esboço, a confirmar com o caso:

| Elemento | Papel |
|---|---|
| Port `AuthStrategy` | `authenticate(target, credentials) -> AuthenticatedSession`, `logout(session)`, `is_valid(session)` |
| `CredentialRefs` | Mapa de referências de segredo exigidas pela estratégia (usuário, senha, segredo de segundo fator) |
| Erros | `AuthenticationError` (credencial recusada, nunca repetida) e `AuthenticationUnavailableError` (falha transitória, `retryable`) |
| Estratégias | Providers do port, um por sistema, em pacotes da organização. Usam a Capability de acesso (navegador ou HTTP) como infraestrutura, a regra da RFC-0004, DS-1 |
| Ciclo de vida | Sessão por execução, aberta no primeiro uso e encerrada no `finalize` |

Pré-requisito: a RFC da Capability de acesso (Browser ou HTTP) correspondente.

## 4. Pontos que precisam de decisão própria

| Tema | Risco | Posição desta RFC |
|---|---|---|
| Reutilizar sessão ou token entre execuções | Um token persistido é um segredo em repouso | Não proposto. Exigiria armazenamento protegido (cofre ou armazenamento do sistema operacional) e decisão de segurança |
| Segundo fator | Segredo TOTP é um segredo; push e SMS não são automatizáveis com segurança | Semente TOTP só no cofre; fluxos com aprovação humana ficam fora |
| Execuções simultâneas com a mesma conta | Sistemas de sessão única derrubam a sessão anterior ou bloqueiam a conta | Exige saber se o sistema permite (pergunta 3). Um conjunto de contas com exclusividade teria a forma de um lease, como na fila (RFC-0008) |
| Credenciais em SQL | Segredo em banco, em cópia de segurança e em réplica | Não oferecido; ver RFC-0006, 2.5: o SQL guarda referências, os valores ficam no cofre |

## 5. Segurança

Autenticação exige revisão arquitetural de segurança no PR (`GOVERNANCE.md`, seção 9). A tabela da seção 4 e as regras da seção 3.1 são o conteúdo mínimo dessa revisão para qualquer estratégia.

## 6. Compatibilidade

Nenhuma mudança em pacotes existentes. A seção 3.2, se aceita, cria um pacote novo que depende só do Core.

## 7. Alternativas consideradas

| Alternativa | Avaliação |
|---|---|
| Capability de autenticação agora, sem caso real | Abstração por antecipação; o port certo depende da tecnologia de acesso e do sistema |
| Fluxos de login dentro dos pacotes de navegador ou HTTP | Mistura a integração genérica com o sistema específico |
| Copiar o fluxo em cada automação | Situação atual; espalha credenciais e erros de bloqueio de conta |

## 8. Perguntas abertas

1. Quais sistemas e quantas automações usam cada um.

R: Os sistemas utilizados dependerão das necessidades de cada automação. A plataforma não deverá trabalhar com uma lista fixa de sistemas previamente definidos, pois cada projeto poderá utilizar sistemas diferentes.

A quantidade de automações que utilizará cada sistema também não será fixa. A arquitetura deverá permitir que diferentes automações compartilhem e reutilizem os mesmos recursos e fluxos de autenticação de um determinado sistema.

2. Tecnologia de acesso: navegador, desktop, API; existe forma de autenticação não interativa?

R: A plataforma deverá suportar duas modalidades de autenticação: interativa e não interativa, conforme as características de cada sistema e as necessidades da automação.

Autenticação interativa:

Como comportamento padrão, a automação deverá preencher automaticamente os campos de usuário e senha e acionar o botão de login.

Os mapeamentos dos elementos da interface, como campos de usuário, senha e botão de login, deverão ser fornecidos por parâmetros, permitindo que cada automação configure os elementos correspondentes ao sistema utilizado.

Também deverá ser possível realizar override dos mapeamentos e do comportamento padrão quando existirem situações diferentes das previstas inicialmente, permitindo tratar particularidades das telas e dos fluxos de autenticação de cada sistema.

Autenticação não interativa:

Deverá ser realizada por meio da utilização de tokens, permitindo autenticação sem a necessidade de interação com telas de login.

3. O sistema permite sessões simultâneas com a mesma conta? Existe um conjunto de contas de serviço?

R: Esse comportamento dependerá das características e das regras de cada sistema. A plataforma deverá permitir que essa condição seja tratada conforme as particularidades do sistema utilizado pela automação, sem estabelecer uma regra única para todos os sistemas.

4. Segundo fator: qual, e se há conta de serviço sem ele.

R: A configuração do segundo fator de autenticação deverá ser parametrizável, permitindo que cada automação configure o mecanismo necessário conforme as exigências do sistema utilizado.

5. Onde as credenciais estão hoje e quem faz a rotação.

R: O armazenamento das credenciais deverá ser parametrizável, permitindo utilizar o Azure Key Vault ou banco de dados SQL, conforme a necessidade de cada automação.

No caso do SQL, considera-se a utilização de uma tabela específica, com uma lógica de verificação e armazenamento dos dados criptografados, seguindo uma abordagem semelhante à utilizada pelo Azure Key Vault.

A plataforma deverá permitir diferentes configurações de armazenamento, sem depender de uma origem fixa para as credenciais.

A responsabilidade pela rotação das credenciais ainda não foi definida.

**Condição de aceite.** Respostas 1 a 3 e a RFC da Capability de acesso.
