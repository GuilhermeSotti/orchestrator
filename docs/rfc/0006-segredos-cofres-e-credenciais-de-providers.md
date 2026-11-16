# RFC-0006 — Segredos: cofres como Providers, credenciais em Providers e limites de armazenamento

| Campo | Valor |
|---|---|
| Status | Aceita em 2026-11-15 pelo responsável |
| Data | 2026-11-14 |
| Autor | Claude, a pedido do responsável |
| Decisor | Responsável pelo projeto (aceite registrado em [DECISIONS](../DECISIONS.md), seção 5) |
| Implementação | 2026-11-15: parte 2.1, opção A, no `orchestrator-sql` e no `orchestrator-sqlite` 0.2.0 (branch local `feature/core-0.2`, sem release); implementação aprovada pelo responsável (DE-1); RFC aceita em 2026-11-15. Valores de segredos em SQL: RFC-0013. Partes 2.2 e 2.5 bloqueadas: [reconciliação](../audit/RFC_RESPONSE_RECONCILIATION.md), C4 |
| Itens de escopo | 8 (credenciais e segredos) e parte do 7 (credenciais dos fluxos de login) |
| Relacionadas | [ADR-0007](../adr/0007-configuracao-e-segredos.md), [RFC-0003](0003-capability-sql.md), [RFC-0004](0004-controles-reutilizaveis-escopo-e-sequencia.md) (DS-3), [RFC-0005](0005-core-0-2-subetapas-mascaramento-teardown-e-sinais.md) |

## 1. Problema

O modelo de segredos por referência existe e é testado, mas o diagnóstico ([SCOPE_DIAGNOSIS](../audit/SCOPE_DIAGNOSIS.md), seção 3.8) encontrou:

- L8.1 — nenhum Provider de cofre, como o Azure Key Vault;
- L8.2 — o port SQL não tem caminho para credenciais: `SqlProvider.connect()` não recebe contexto nem `SecretStore`. Isso bloqueia qualquer Provider SQL com senha;
- L8.5 — só o valor exato resolvido é mascarado; partes de um segredo composto aparecem em claro;
- L8.3 e L8.6 — não há segredos fora de uma execução, nem cache.

O responsável pediu Providers de cofre, Core independente de serviços externos, proteção dos valores resolvidos e tratamento do armazenamento de segredos em SQL como decisão de segurança explícita.

## 2. Proposta

### 2.1 Credenciais em Providers de Capability (port SQL)

- `SqlProvider.connect(self, secrets: SecretStore) -> DbapiConnection`. O Provider guarda as referências lidas em `from_config` com `section.get_secret_ref(...)` e resolve o valor a cada conexão.
- `SqlCapability.open(ctx)` passa `ctx.secrets`.
- O valor resolvido não é guardado em atributo, não entra em `describe()` e não aparece em erro traduzido.
- A suíte `SqlProviderContract` passa a abrir sessões dentro de execuções, porque um `SecretStore` só existe ali.

| Opção | Descrição | Avaliação |
|---|---|---|
| A | `connect(secrets)` | Recomendada: o Provider recebe só o que precisa |
| B | `connect(ctx)` | Uniforme com `Capability.open(ctx)`, mas entrega ao Provider mais do que ele usa |
| C | A Capability resolve e entrega um mapa de `Secret` | O Provider deixa de controlar quando resolve; a Capability precisa conhecer as chaves de cada Provider |

Convenção para ports novos: o método chamado a cada execução recebe o contexto ou o `SecretStore`; nenhum Provider lê credenciais do ambiente por conta própria.

### 2.2 Cofre como Provider: `orchestrator-keyvault`

Pacote novo, Provider do port `SecretResolver` do Core. A composição é explícita e feita pelo consumidor:

```python
from azure.identity import ManagedIdentityCredential  # escolha do consumidor
from orchestrator_keyvault import KeyVaultSecretResolver

resolver = KeyVaultSecretResolver(
    "https://<cofre>.vault.azure.net", credential=ManagedIdentityCredential()
)
runtime = RuntimeBuilder().with_secret_resolver("kv", resolver).build()
```

```toml
[capabilities.erp]
password = "kv:erp-password"  # ou "kv:erp-password/<versão>"
```

| Aspecto | Proposta |
|---|---|
| Cofre | Um resolvedor por cofre. A URL é fixada na composição e nunca vem da referência: a configuração não consegue apontar para outro host |
| Alvo | `<nome>[/<versão>]`, validado contra as regras de nome do cofre |
| Erros | `SecretResolutionError` com o nome do segredo; nunca o valor nem o corpo da resposta. Falhas transitórias marcadas como `retryable` |
| Rede | Tempo limite explícito |
| Cache | Opcional, em memória, por resolvedor, com validade configurável; desligado por padrão |
| Mascaramento | O valor passa pelo `SecretStore`, que já o registra para mascaramento |
| Identidade | Escolha do consumidor (identidade gerenciada, entidade de serviço com segredo em `env:`); o pacote só recebe a credencial pronta |
| Dependências | `azure-keyvault-secrets` e `azure-identity`, da Microsoft, licença MIT, mais as dependências transitivas (como `azure-core` e `msal`), que entram no lock e na análise de licenças (RFC-0004, DS-3) |
| Logs do SDK | O pacote nunca liga o log detalhado do SDK, que inclui corpos de requisição e resposta |

Outros cofres seguem o mesmo padrão, um pacote por cofre, quando houver necessidade concreta.

### 2.3 Segredos compostos

Recomendação de uso, sem código: um segredo por valor sensível. A senha fica separada do restante da cadeia de conexão.

Opcional, no Core 0.2: `SecretStore.protect(value: str) -> Secret`, que registra para mascaramento um valor derivado pelo consumidor ou por um Provider.

### 2.4 Segredos fora de uma execução

Não proposto agora. Só passa a ser necessário se o destino SQL da [RFC-0009](0009-destinos-de-registros-e-logs.md) for aceito, e lá a opção preferida é entregar o contexto ao destino, não criar um `SecretStore` do escopo do Runtime.

### 2.5 Armazenamento de segredos em SQL

A plataforma não oferece. A alternativa recomendada cobre o caso comum: **o SQL guarda referências** (`kv:erp-usuario-01`) e os valores ficam no cofre. Um repositório de mapeamentos pode guardar referências do mesmo modo ([RFC-0010](0010-mapeamentos-compartilhados.md)).

Se o responsável decidir que valores precisam ficar em SQL, a decisão é de segurança e exige RFC própria. Controles mínimos antes de qualquer código:

1. cifragem em envelope, com a chave fora do banco (cofre ou módulo de hardware);
2. cifra autenticada por valor, vinculada ao identificador do segredo;
3. usuário de banco dedicado, com o menor privilégio;
4. auditoria de leituras;
5. procedimento de rotação de chaves e de valores;
6. tratamento dos backups;
7. revisão arquitetural de segurança.

A biblioteca padrão não tem cifra simétrica autenticada: seria necessária uma dependência de criptografia, num pacote Provider, nunca no Core.

## 3. O que continua por conta do consumidor

Sem mudança em relação à ADR-0007: instalar os filtros de `orchestrator_core.logs` nos seus handlers; não registrar `result.error` nem `result.output` sem máscara; valores com menos de 4 caracteres não são mascarados. Observação menor, sem proposta: a mensagem de esquema desconhecido repete o esquema digitado (diagnóstico, EX9).

## 4. Compatibilidade

- 2.1: `orchestrator-sql` 0.2.0 e `orchestrator-sqlite` 0.2.0. Quebra para autores de Providers; nenhum efeito para quem só usa `SqlSession`. Atualizar a RFC-0003 (seção 3), os CHANGELOGs e a matriz.
- 2.2: pacote novo; o Core não muda.
- 2.3, opcional: acréscimo à API pública do Core (RFC-0002).

## 5. Segurança

Mudanças em segredos, rede e autenticação exigem revisão arquitetural de segurança no PR (`GOVERNANCE.md`, seção 9).

| Ameaça | Tratamento |
|---|---|
| Referência que aponta para outro cofre | URL do cofre fixa na composição |
| Vazamento por mensagem de erro do SDK | Tradução para `SecretResolutionError` sem o corpo da resposta |
| Vazamento por log de depuração do SDK | Nunca habilitado pelo pacote |
| Valor em memória | O cache, se ligado, guarda o valor pelo tempo de validade; desligado por padrão |
| Dependência comprometida | RFC-0004, DS-3: lock com hashes e justificativa no PR |

## 6. Alternativas consideradas

| Alternativa | Avaliação |
|---|---|
| Carregar os segredos do cofre em variáveis de ambiente antes de iniciar a automação | Funciona hoje com `env:`, sem código novo nem dependência. Recomendada como solução imediata. Limites: sem rotação durante a execução; depende de quem inicia o processo |
| Chamar a API REST do cofre com `urllib` | Sem dependências, mas reimplementa a obtenção de tokens, que é código sensível |
| Uma Capability de segredos | Duplica o port `SecretResolver`, que já é do Core |

## 7. Critérios de aceite e testes

Os da RFC-0004, seção 5 (E7.8 e E7.9), mais:

- 2.1: o teste do valor-sentinela cobre a senha de um Provider de teste em log, evento, registro, `describe()` e erro traduzido;
- 2.2: nenhum teste unitário usa rede; o teste de integração com um cofre real é marcado e roda fora da CI padrão; o pacote é testado em toda a matriz de Python, ou declara a própria (DS-3).

## 8. Perguntas abertas

1. Qual cofre está em uso e qual identidade a máquina que executa tem.

R: A escolha do cofre e da identidade ou credencial utilizada pela máquina executora deverá ser parametrizável. A plataforma não deverá depender de um cofre ou de uma identidade fixa, permitindo que cada automação configure esses elementos conforme o ambiente em que será executada.

2. Acesso de rede ao cofre: direto ou por proxy.

R: A forma de acesso ao cofre deverá ser parametrizável, permitindo configurar tanto o acesso direto quanto o acesso por proxy, conforme as características e restrições do ambiente de execução.

3. Cache: que validade é aceitável diante da política de rotação.

R: O cache deverá ter escopo limitado à própria execução da automação. Os segredos resolvidos poderão permanecer em cache durante essa execução, mas todo o conteúdo armazenado deverá ser descartado ao término dela. Uma nova execução deverá iniciar sem reutilizar o cache da execução anterior.

4. Outras origens necessárias além do cofre.

R: Neste momento, as origens previstas são SQL e Azure Key Vault. No caso do SQL, considero a utilização de uma tabela específica, com uma lógica de verificação e armazenamento dos dados criptografados, seguindo uma abordagem semelhante à utilizada pelo Key Vault.

Outras origens poderão ser adicionadas futuramente, conforme surgirem novas necessidades dos projetos consumidores.

5. Opção para 2.1 (A, B ou C).

R: A opção escolhida é a A — connect(secrets). O Provider deverá receber diretamente o SecretStore no método de conexão, utilizando-o para resolver as referências das credenciais necessárias, sem receber todo o ExecutionContext.
    
**Condições de aceite.** 2.1 depende de haver um Provider SQL com credenciais no plano (E7.16). 2.2 depende das respostas 1 e 2.

## Referências externas (consultadas em 2026-11-14)

- `azure-keyvault-secrets` no PyPI: <https://pypi.org/project/azure-keyvault-secrets/>. A versão 4.12.0, de 28 de outubro de 2026, exige Python 3.10 ou superior e declara classificadores até 3.14; a matriz da CI inclui 3.15, que precisa ser verificada na entrega.
