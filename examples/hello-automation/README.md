# hello-automation

Projeto consumidor mínimo: usa só o `orchestrator-core`. A automação conta arquivos, linhas e palavras dos arquivos `.txt` de uma pasta e grava um resumo em JSON.

Demonstra:

- automação como função que recebe o `ExecutionContext`;
- parâmetros validados no estágio `prepare_execution`;
- configuração em `orchestrator.toml`, sobrescrevível por variáveis `ORCHESTRATOR_*`;
- workspace temporário por execução, removido no `finalize`;
- logs correlacionados e resultado com o registro da execução.

## Executar

```powershell
python -m pip install -e ..\..\packages\orchestrator-core -e .
python -m hello_automation data --output summary.json --config orchestrator.toml
```

O código de saída é 0 quando a execução termina com `succeeded`.

## Testar

```powershell
python -m pytest tests
```
