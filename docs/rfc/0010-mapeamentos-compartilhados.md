# RFC-0010 — Repositório compartilhado de mapeamentos

| Campo | Valor |
|---|---|
| Status | Aceita em 2026-11-15 pelo responsável |
| Data | 2026-11-14 |
| Autor | Claude, a pedido do responsável |
| Decisor | Responsável pelo projeto (aceite registrado em [DECISIONS](../DECISIONS.md), seção 5) |
| Item de escopo | 6 (repositório compartilhado de mapeamentos) |
| Relacionadas | [RFC-0004](0004-controles-reutilizaveis-escopo-e-sequencia.md) (DS-1, DS-3, DS-6), [RFC-0006](0006-segredos-cofres-e-credenciais-de-providers.md) (2.5), [RFC-0011](0011-calendarios-e-dias-uteis.md) |

## 1. Problema e o que ainda não se sabe

O responsável quer que várias automações reutilizem mapeamentos associados a sistemas externos, com identificação, versão, validação, carga e atualização definidas, e fontes como Excel e SQL por meio de Providers, sem impor formato ou schema a todos os consumidores.

Hoje não existe nada parecido ([SCOPE_DIAGNOSIS](../audit/SCOPE_DIAGNOSIS.md), seção 3.6). As tabelas do consumidor na configuração (`ctx.config.section("app")`) servem a poucos valores de um projeto, não a dados compartilhados, versionados e mantidos fora do código.

"Mapeamento" pode significar coisas diferentes em automação, e o contrato muda conforme o caso:

| Interpretação | Exemplo de uso | Consequência para o contrato |
|---|---|---|
| Tabela de correspondência ("de-para") | Traduzir o código de um item num sistema para o código no outro | Busca por chave; entradas com poucas colunas; volume de centenas a milhares de linhas |
| Localização de elementos de interface | Seletores de tela de um sistema usados por automações de interface | Agrupamento por tela e versão do sistema; leitura por nome; depende de uma Capability de navegador ou desktop, que não existe |
| Associação de contas ou parâmetros por sistema | Qual conta ou endereço usar para cada sistema e ambiente | Valores sensíveis entram só como referência de segredo (seção 6) |

Esta RFC propõe um contrato que atende à primeira interpretação e não impede as outras. A escolha depende de um exemplo real (seção 9, pergunta 1).

## 2. Conceitos

| Conceito | Definição proposta |
|---|---|
| Conjunto de mapeamentos | Coleção nomeada de entradas, identificada por `sistema` e `nome` (ex.: `<sistema>/<conjunto>`) |
| Entrada | Registro com uma chave (uma ou mais colunas) e valores. A plataforma não conhece o significado de nenhuma coluna |
| Esquema | Colunas esperadas, colunas da chave e um validador por entrada, fornecidos pelo consumidor |
| Versão | Identificador do conteúdo carregado, informado pela fonte (seção 4) |
| Origem | Provider, localização e versão de onde o conjunto veio, registrados para rastreabilidade |

## 3. Contrato funcional

Pacote `orchestrator-mappings`, que depende só do Core e traz o Provider de arquivo.

Ilustração com a primeira interpretação da seção 1; os nomes de colunas são do consumidor:

```python
from orchestrator_mappings import MappingSchema, MappingsCapability

ESQUEMA = MappingSchema(key=("codigo_origem",), columns=("codigo_origem", "codigo_destino"))


def automacao(ctx: ExecutionContext) -> None:
    conjunto = ctx.capability(MappingsCapability).load("<sistema>", "<conjunto>", ESQUEMA)
    destino = conjunto.lookup("<código>")["codigo_destino"]  # KeyError com o nome do conjunto
    ctx.logger.info("usando %s versão %s", conjunto.id, conjunto.version)
```

| Nome | Papel |
|---|---|
| `MappingSchema` | Colunas, chave, validador opcional por entrada (uma função; um modelo Pydantic serve) |
| `MappingsCapability.load(system, name, schema)` | Carrega e valida o conjunto na primeira chamada da execução; as seguintes devolvem o mesmo objeto |
| `MappingSet` | `id`, `version`, `source`, `lookup(key)`, `get(key, default)`, `entries` (somente leitura), `len()` |
| `MappingError` | Conjunto inexistente, esquema incompatível, chave repetida, entrada inválida, versão diferente da exigida |

Garantias:

- **Imutável durante a execução.** Uma atualização na fonte não muda o que a execução já carregou; a próxima execução vê a nova versão.
- **Validação completa antes do uso.** Chave ausente ou repetida, coluna faltando e entrada recusada pelo validador falham na carga, com o identificador do conjunto, a posição da entrada (linha) e a coluna. A mensagem não repete valores, que podem ser dados pessoais.
- **Sem escrita.** O pacote só lê. Quem mantém os mapeamentos usa a ferramenta da fonte (planilha, banco). Uma API de escrita só com caso de uso.

## 4. Versão e rastreabilidade

| Fonte | Versão proposta |
|---|---|
| Arquivo (CSV, JSON, TOML) | SHA-256 do conteúdo |
| Excel | SHA-256 do arquivo |
| SQL | Valor de uma coluna ou de uma consulta de versão indicada pelo consumidor; sem ela, o hash das linhas lidas |

- A versão e a origem de cada conjunto carregado aparecem no log da execução e no evento `MappingLoaded`. Com as subetapas da [RFC-0005](0005-core-0-2-subetapas-mascaramento-teardown-e-sinais.md), também poderiam entrar no registro da execução.
- `expected_version`, na configuração, fixa a versão: se a fonte tiver outra, a carga falha. Serve a automações que precisam de reprodutibilidade.
- Sem cache entre execuções na primeira versão. Um cache por versão só com volume que o justifique.

## 5. Providers

| Provider | Pacote | Observações |
|---|---|---|
| Arquivo | `orchestrator-mappings` (embutido) | CSV, JSON e TOML pela biblioteca padrão; caminho validado dentro de uma pasta-base configurada |
| SQL | `orchestrator-mappings-sql` | Usa um registro de `SqlCapability` nomeado na configuração (RFC-0004, DS-1); tabela, colunas, filtro por conjunto e coluna de versão vêm de um mapa do consumidor; nenhum nome fixo |
| Excel | `orchestrator-mappings-excel` | Lê uma tabela nomeada ou uma planilha com linha de cabeçalho; nunca avalia fórmulas: lê os valores gravados; recusa arquivos acima de um limite de tamanho |

Para o Excel, as opções de leitura e os riscos:

| Opção | Avaliação |
|---|---|
| `openpyxl` | Mais usada; licença MIT. Última versão 3.1.5, de junho de 2024, mantida essencialmente por uma pessoa. A documentação avisa que, por padrão, não se protege contra ataques de expansão de entidades XML e recomenda instalar `defusedxml` |
| Leitor mínimo com `zipfile` e `xml.etree` | Sem dependência. A documentação do Python informa que o Expat 2.4.1 ou mais novo não é vulnerável a esses ataques de expansão. Exige manter código de leitura do formato, só para valores simples |
| `python-calamine` | Leitura rápida, compilada; a avaliar quanto a manutenção e suporte à matriz de Python |

Recomendação: decidir na entrega E7.20, com arquivos reais de exemplo e a política da RFC-0004, DS-3. A dependência fica no Provider, nunca na Capability (DS-6).

## 6. Segurança

- Mapeamentos não guardam segredos. Quando uma entrada precisa apontar para uma credencial, guarda a **referência** (`kv:<nome>`), resolvida pela automação com `ctx.secrets`. A plataforma não consegue detectar um segredo literal num mapeamento; a regra fica documentada e é verificada na revisão do conjunto.
- Arquivos e planilhas são entrada não confiável: limite de tamanho, nenhum caminho fora da pasta-base, nenhuma fórmula avaliada, nenhuma macro executada.
- Identificadores SQL do mapa validados e citados; valores como parâmetros (RFC-0003).
- Conteúdo dos mapeamentos nunca vai para logs, só o identificador, a versão e a quantidade de entradas.

## 7. Compatibilidade

Pacotes novos; o Core não muda. O Provider SQL depende de `orchestrator-sql`; o Provider Excel traz a primeira dependência de terceiros da família (DS-3).

## 8. Alternativas consideradas

| Alternativa | Avaliação |
|---|---|
| Cada automação lê a própria planilha | Situação atual; duplica leitura, validação e rastreabilidade |
| Tabelas na configuração TOML | Serve a poucos valores estáticos; sem versão própria nem manutenção fora do código |
| Um pacote de dados da organização, versionado com os mapeamentos dentro | Boa opção quando os mapeamentos mudam pouco: a versão é a do pacote e a revisão acontece por PR. Usa o Provider de arquivo |
| Esquema único imposto a todos | Contraria o pedido e a ADR-0019 |

## 9. Perguntas abertas

1. Um exemplo anonimizado, de duas ou três entradas, do que é um mapeamento hoje; a interpretação da seção 1 que se aplica.

R: Os mapeamentos serão utilizados para centralizar caminhos e referências de elementos de sistemas externos, incluindo seletores e caminhos relacionados a CSS, JavaScript (JS) e interfaces gráficas (GUI).

A interpretação aplicável é a de localização de elementos de interface, conforme a seção 1 da RFC.

O objetivo é manter essas referências unificadas em um arquivo compartilhado, permitindo que as automações utilizem os mesmos mapeamentos. Um exemplo concreto de duas ou três entradas ainda não foi especificado.

2. Onde vive hoje, quem mantém e com que frequência muda.

R: Os mapeamentos deverão ficar centralizados em um arquivo compartilhado e unificado (cada sistema com seu arquivo separado), que poderá ser atualizado manualmente por todos os desenvolvedores dos projetos.

A manutenção será manual, e a frequência das alterações dependerá das mudanças realizadas em cada sistema externo.

O local físico ou repositório específico onde esse arquivo ficará armazenado ainda não foi definido.

3. Quantas automações e projetos compartilham o mesmo conjunto.

R: Todos os projetos que utilizarem a plataforma deverão compartilhar os recursos disponibilizados por ela, incluindo os mapeamentos. O objetivo é que diferentes automações e projetos utilizem os mesmos conjuntos de referências, evitando duplicações e mantendo uma fonte compartilhada de informações.

A quantidade exata de automações e projetos não foi definida.

4. Tamanho: entradas por conjunto.

R: Os conjuntos deverão comportar os mapeamentos necessários para cada sistema, conforme sua utilização pelas automações.

5. As entradas têm período de validade (vigência)? A automação precisa consultar "o valor válido na data X"?

R: A premissa definida é que as automações deverão utilizar sempre a versão mais atualizada do arquivo de mapeamentos.

Não foi estabelecida uma regra de vigência individual para cada entrada, nem a necessidade de consultar qual valor era válido em uma data específica.

6. Uma automação precisa fixar a versão que usa?

R: Não. A automação deverá utilizar sempre a versão mais atualizada disponível do arquivo de mapeamentos, sem necessidade de fixar previamente uma versão específica para cada automação.

7. Buscas necessárias além da chave: inversa, por mais de uma coluna, por prefixo.

R: Somente os nomes padronizados de constraints identificando o elemento que a automação irá interagir.

**Condição de aceite.** Respostas 1, 2 e 5. Sem a primeira, não há como fixar o contrato.

## 10. Critérios de aceite e testes

Os da RFC-0004, seção 5 (E7.19 e E7.20), mais:

- matriz de entradas inválidas (chave repetida, coluna faltando, tipo recusado pelo validador), com a mensagem citando linha e coluna e sem valores;
- a mesma execução recebe o mesmo objeto em duas cargas; duas execuções, objetos independentes;
- `expected_version` diferente da fonte faz a carga falhar;
- a suíte de conformidade do port roda contra os três Providers, com os mesmos dados;
- `check_capability_conformance` aprovada.

## Referências externas (consultadas em 2026-11-13 e 2026-11-14)

- `openpyxl`, README publicado no PyPI (aviso sobre `defusedxml`), reproduzido em <https://socket.dev/pypi/package/openpyxl>; versão 3.1.5 de 28 de junho de 2024 segundo <https://dev.snyk.io/advisor/python/openpyxl>; mensagem do mantenedor sobre a manutenção individual, de abril de 2024, em <https://groups.google.com/g/openpyxl-users/c/js0XQgQtPYY>.
- Documentação do Python, "XML vulnerabilities": <https://docs.python.org/3.12/library/xml.html>.
