# sales-report

Projeto consumidor que usa a Capability `orchestrator-sql` com o Provider `orchestrator-sqlite`. A automação lê pedidos de um CSV, carrega numa tabela de trabalho, agrega por região com uma consulta parametrizada e grava o relatório em CSV.

Demonstra:

- registro da Capability por classe, com os Providers permitidos (`providers={"sqlite": SqliteProvider}`);
- escolha do banco pela configuração (`[capabilities.sql]` ou `ORCHESTRATOR_CAPABILITIES__SQL__*`), sem mudar código;
- transação explícita, parâmetros `:nome` e identificadores validados;
- regras de negócio (colunas, filtros, formato do relatório) no projeto consumidor.

## Executar

```powershell
python -m pip install -e ..\..\packages\orchestrator-core -e ..\..\packages\orchestrator-sql -e ..\..\packages\orchestrator-sqlite -e .
python -m sales_report data\pedidos.csv --output relatorio.csv --minimum 100
```

Para manter os dados num arquivo em vez da memória:

```powershell
$env:ORCHESTRATOR_CAPABILITIES__SQL__DATABASE = "vendas.db"
python -m sales_report data\pedidos.csv
```

## Testar

```powershell
python -m pytest tests
```
