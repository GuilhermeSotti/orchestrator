# RFC-0013 — Valores de segredos em SQL: avaliação de segurança

| Campo | Valor |
|---|---|
| Status | Proposta. Não aceita |
| Data | 2026-11-15 |
| Autor | Claude, a pedido do responsável |
| Decisor | Responsável pelo projeto (decisão pendente) |
| Origem | Decisão de encaminhamento de 2026-11-15: elaborar uma RFC de segurança específica e não implementar armazenamento de valores de segredos em SQL antes da decisão ([DECISIONS](../DECISIONS.md), seção 4) |
| Respostas que motivam | [RFC-0006](0006-segredos-cofres-e-credenciais-de-providers.md), pergunta 4; [RFC-0012](0012-autenticacao-por-sistema.md), pergunta 5; [reconciliação](../audit/RFC_RESPONSE_RECONCILIATION.md), C4 |
| Relacionadas | [ADR-0005](../adr/0005-dependencias-do-core.md), [ADR-0007](../adr/0007-configuracao-e-segredos.md), [RFC-0004](0004-controles-reutilizaveis-escopo-e-sequencia.md) (DS-3, DS-4) |

Esta RFC não altera o status das RFCs 0006 e 0012, aceitas em 2026-11-15 ([DECISIONS](../DECISIONS.md), seção 5); o armazenamento de valores de segredos em SQL continua dependendo do aceite desta RFC.

## 1. Problema

O responsável considera guardar credenciais numa tabela SQL específica, "com uma lógica de verificação e armazenamento dos dados criptografados, seguindo uma abordagem semelhante à utilizada pelo Key Vault", e quer que cada automação possa usar o Azure Key Vault ou o SQL como origem.

A RFC-0006, seção 2.5, não oferece essa opção: recomenda que o SQL guarde só **referências** (`kv:erp-usuario-01`) e que os valores fiquem no cofre. Esta RFC avalia, com os controles de segurança necessários, se e como valores podem ficar em SQL.

Situação atual, que continua valendo enquanto não houver decisão: segredos entram só por referência (`env:`, `file:` e resolvedores registrados com `with_secret_resolver`); nenhum pacote da plataforma grava ou lê valores de segredos em banco.

## 2. Requisitos que qualquer opção precisa cumprir

| # | Requisito | Por quê |
|---:|---|---|
| R1 | Cifra autenticada por valor (confidencialidade e integridade), vinculada ao identificador do segredo | Impede ler o valor e também trocar o valor cifrado de uma linha pelo de outra |
| R2 | Chave de proteção fora do banco (cofre ou módulo de hardware), com rotação documentada | Quem tem o banco ou um backup não pode ter a chave |
| R3 | Separação de funções: quem administra o banco não decifra; quem decifra não administra a chave | Um único papel comprometido não basta para obter os valores |
| R4 | Menor privilégio: um usuário de banco dedicado à leitura, outro à gravação e rotação; nenhum acesso amplo à tabela | Limita o alcance de uma credencial vazada |
| R5 | Auditoria de leitura, gravação e alteração, com retenção definida | Responde a "quem leu qual credencial e quando" |
| R6 | Backups e réplicas contêm só valores cifrados; a chave tem a sua própria cópia de segurança, protegida | A perda da chave é perda de todos os valores |
| R7 | Recuperação e continuidade: procedimento testado de restauração, de troca de chave e de acesso de emergência | Rotação e restauração falham quando só existem no papel |
| R8 | Compatibilidade com o Azure Key Vault e com o port `SecretResolver` do Core | A automação escolhe a origem pela referência, sem mudar código |
| R9 | Valores resolvidos registrados para mascaramento (`SecretStore`), nunca em logs, eventos, registros nem erros | Mesmo controle já exigido das demais origens |
| R10 | Segredo de acesso ao próprio SQL vindo de outra origem (cofre, ambiente ou autenticação integrada) | A tabela de segredos não pode guardar a credencial que a abre |

## 3. Ameaças

| Ameaça | Exemplo | Controles |
|---|---|---|
| Administrador do banco lê os valores | Consulta direta na tabela | R1, R2, R3 |
| Vazamento de backup ou réplica | Cópia do `.bak` fora do ambiente | R1, R2, R6 |
| Injeção de SQL em outra aplicação com acesso ao banco | Consulta arbitrária | R4; valores cifrados (R1) |
| Máquina de automação comprometida | Processo malicioso no mesmo usuário | Limite comum a todas as origens: quem executa como a automação obtém o que ela obtém. Mitigação: identidade por máquina, menor privilégio, auditoria (R4, R5) |
| Troca de valores cifrados entre linhas | Mover a senha de um sistema para a linha de outro | R1 (dados associados com o identificador) |
| Perda ou exclusão da chave | Exclusão acidental no cofre | R6, R7 (exclusão reversível e proteção contra expurgo no cofre) |
| Valor antigo depois da rotação | Cache ou réplica atrasada | Versão por linha; cache limitado à execução (RFC-0006, resposta 3) |
| Vazamento pelo próprio código | Mensagem de erro do driver com o valor | R9; tradução de erros sem valores (RFC-0006, 2.1) |

## 4. Opções

| Opção | Como funciona | Quem decifra | Código de criptografia na plataforma | Dependências |
|---|---|---|---|---|
| A. Cofre externo; SQL guarda referências | O SQL guarda `kv:<nome>`; o valor é lido do Key Vault pelo resolvedor `kv:` (RFC-0006, 2.2) | O cofre, para a identidade autorizada | Nenhum | SDK do Key Vault (RFC-0006, DS-3) |
| B. Always Encrypted do SQL Server | O driver cifra e decifra no cliente. A chave de coluna fica no banco, cifrada pela chave mestra, que fica fora do banco (Key Vault, repositório de certificados do Windows ou módulo de hardware) | O driver, na máquina autorizada a usar a chave mestra | Nenhum: a criptografia é do driver | Driver ODBC com Always Encrypted e um pacote Python de acesso (DS-3) |
| C. Cifragem em envelope na plataforma | Uma chave de dados por segredo cifra o valor com AES-GCM; a chave de dados é envolvida por uma chave do Key Vault (operação de wrap) e guardada ao lado do valor cifrado | O Provider da plataforma, depois do unwrap no cofre | Sim: geração de chaves, nonces, dados associados e formato | Biblioteca de criptografia de terceiros (a biblioteca padrão não tem cifra autenticada) e SDK do Key Vault |
| D. Funções nativas do banco (`ENCRYPTBYKEY`, chaves e certificados no próprio banco) | O banco cifra com chaves que ele mesmo guarda | O banco, para quem tem permissão sobre a chave | Não | Nenhuma |
| E. DPAPI do Windows | O valor é cifrado com uma chave da máquina ou do usuário | Só aquela máquina ou usuário | Não | Nenhuma |

Avaliação contra os requisitos:

| Requisito | A | B | C | D | E |
|---|---|---|---|---|---|
| R1 cifra autenticada | Do cofre | Do driver | Da plataforma (a revisar) | Fraca (sem vínculo ao identificador, por padrão) | Sim |
| R2 chave fora do banco | Sim | Sim | Sim | **Não** | Na máquina |
| R3 separação de funções | Sim | Sim | Sim | **Não**: quem administra o banco decifra | Parcial |
| R4 menor privilégio | Do cofre | Banco e chave | Banco e chave | Banco | Usuário do Windows |
| R5 auditoria | Do cofre | SQL Server Audit e cofre | SQL Server Audit e cofre | SQL Server Audit | Fraca |
| R6 backups | Fora do banco | Só valores cifrados | Só valores cifrados | Chaves dentro do backup | Presa à máquina |
| R8 compatibilidade com o Key Vault | Nativa | Chave mestra no Key Vault | Chave de proteção no Key Vault | Não | Não |
| Várias máquinas | Sim | Sim | Sim | Sim | **Não** |
| Depende do Key Vault estar disponível | Sim | Sim, para obter a chave de coluna (há cache no driver) | Sim, para o unwrap | Não | Não |

As opções B e C continuam dependendo do cofre para a chave. O ganho em relação à A não é eliminar o cofre, e sim guardar no banco os valores e os seus metadados (por sistema, conta, ambiente). Esse ganho precisa ser confirmado pelo responsável (pergunta 1).

## 5. Recomendação técnica

Esta seção é recomendação do autor, não decisão:

1. **Padrão: opção A.** O SQL guarda referências e os valores ficam no cofre. Não exige código de criptografia, mantém um único lugar de auditoria e rotação e já é o desenho da RFC-0006.
2. **Se houver motivo para valores em SQL: opção B.** A criptografia fica no driver da Microsoft, a chave mestra fica no Key Vault e a plataforma não implementa cifra.
3. **Opção C só se B for inviável** (outro banco, driver sem suporte), e com revisão de segurança específica do código de criptografia.
4. **D e E não são recomendadas**: D não separa chave e dados; E não atende a várias máquinas.

## 6. Controles mínimos se B ou C for escolhida

1. Tabela dedicada, sem dados de negócio. Colunas mínimas: identificador do segredo, versão, valor cifrado e metadados de chave; datas de criação e de expiração.
2. Usuário de banco só para leitura (por exemplo, por uma view ou procedure restrita a uma linha por identificador), separado do usuário de gravação e rotação. Nenhum outro papel com acesso à tabela.
3. SQL Server Audit com especificação de auditoria de banco para `SELECT`, `INSERT`, `UPDATE` e `DELETE` na tabela, destino protegido e retenção definida.
4. Chave no Key Vault com exclusão reversível e proteção contra expurgo; acesso por identidade de cada máquina; nenhuma credencial do cofre em arquivo versionado.
5. Procedimento de rotação da chave e dos valores, com versões convivendo durante a troca e teste periódico.
6. Backups do banco tratados como dados sensíveis, mesmo cifrados; restauração testada com a chave correspondente.
7. Revisão arquitetural de segurança no PR (`GOVERNANCE.md`, seção 9).

## 7. Como entraria na plataforma, se aceita

- **Sem mudança no Core**, salvo o cache por execução (RFC-0006, resposta 3), que hoje exigiria uma opção no `SecretStore`.
- Um Provider do port `SecretResolver`, num pacote próprio (nome pela DS-4), registrado com um esquema (por exemplo, `sqlvault:`): `RuntimeBuilder().with_secret_resolver("sqlvault", resolvedor)`. A automação continua escolhendo a origem pela referência na configuração (`password = "sqlvault:erp/usuario-01"` ou `"kv:erp-usuario-01"`).
- A credencial de acesso ao banco de segredos vem de outra origem (R10). O resolvedor nunca usa a sessão SQL da automação.
- Tabela, colunas e nomes vêm de um mapa do consumidor, como nas demais propostas (ADR-0019): a plataforma não cria nem altera a tabela.
- Dependências (driver ODBC e pacote Python de acesso; para C, biblioteca de criptografia) seguem a DS-3 e a ADR-0013.

## 8. Perguntas para decisão

1. Qual é o motivo para guardar os **valores** em SQL em vez de no Key Vault: custo, limites do cofre, administração por outra equipe, operação sem acesso ao cofre ou outro?
    R: Esse script será utilizado em diversas situações diferentes onde é possível que não haja KeyValt
2. Banco, versão e edição. O Always Encrypted e o SQL Server Audit dependem do produto e da versão.
    R: O encrypted e decrypted pode ser feito em python usando uma chave de segurança externa
3. Onde fica a chave de proteção (Key Vault, módulo de hardware, certificado do Windows) e quem a administra?
    R: certificado do Windows, somente eu
4. Quem lê, quem grava e quem rotaciona; com que frequência. O responsável pela rotação ainda não foi definido (RFC-0012, resposta 5).
    R: Deverá ser Parametrizavel mas a principio eu
5. Quem consulta a auditoria e por quanto tempo ela é guardada.
    R: Deverá ser parametrizavel mas por default 6 meses
6. As automações precisam funcionar sem acesso ao cofre? Se sim, nenhuma das opções B e C atende, e a decisão volta à A ou exige outro desenho.
    R: Se não há necessidade de secrets, a automação não precisará de cofre. Caso não seja possível o A será utilizado o B e isso deve ser configurável e parametrizavel
7. As máquinas podem instalar o driver ODBC e o pacote Python correspondente (DS-3)?
    R: Sim, a primeira etapa será para instalar estar dependências caso necessário, assim como criar as tabelas e usuários caso não existam ainda. Tudo deve ser parametrizavel e configuravel à parte

## 9. Critérios de aceite e testes, se aceita

- Nenhum valor em claro na tabela: leitura direta, sem o driver habilitado, devolve só dados cifrados.
- Valor cifrado alterado ou trocado de linha é recusado, com erro que cita o identificador e nunca o valor.
- Rotação da chave e dos valores sem interromper execuções em andamento.
- Auditoria registra leitura, gravação e alteração, com o principal e a hora.
- Um usuário de banco sem a permissão dedicada não lê a tabela.
- O teste do valor-sentinela cobre logs, eventos, registros, `describe()` e erros traduzidos.
- Testes de integração com banco e cofre reais, marcados e fora da CI padrão; testes unitários sem rede.

## 10. Fora do escopo

Implementação, criação de tabelas, escolha de driver e qualquer cifra própria antes da decisão.

## Referências externas (consultadas em 2026-11-15)

- Microsoft Learn: [Always Encrypted](https://learn.microsoft.com/sql/relational-databases/security/encryption/always-encrypted-database-engine) e [Always Encrypted com o ODBC Driver for SQL Server](https://learn.microsoft.com/sr-cyrl-rs/sql/connect/odbc/using-always-encrypted-with-the-odbc-driver?view=sql-server-2017).
- Microsoft Learn: [matriz de recursos dos drivers](https://learn.microsoft.com/sql/connect/driver-feature-matrix). O suporte do driver `mssql-python` a Always Encrypted não ficou claro na consulta e precisa ser confirmado antes de qualquer escolha.
- Microsoft Learn: [Key Vault, operação wrap key](https://learn.microsoft.com/en-us/rest/api/keyvault/keys/wrap-key/wrap-key) e [tipos de chave e algoritmos](https://learn.microsoft.com/en-in/Azure/key-vault/keys/about-keys-details).
- Microsoft Learn: [CREATE DATABASE AUDIT SPECIFICATION](https://learn.microsoft.com/en-us/sql/t-sql/statements/create-database-audit-specification-transact-sql).
