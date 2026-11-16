# batch-check

Projeto consumidor que demonstra a Capability `orchestrator-notifications` com os canais SMTP e Teams. A automação confere os arquivos de lote de uma pasta (`*.txt`, primeira linha de cabeçalho): um arquivo sem registros faz a execução falhar.

Demonstra:

- registro da Capability antes das demais e escolha do canal pela configuração (`providers={"smtp": ..., "teams": ...}`);
- avisos de ciclo de vida com os estágios `NotifyStarted` e `NotifyOutcome` e a tabela `lifecycle` de `orchestrator.toml`;
- uma notificação de negócio (`send()`) com o texto do consumidor;
- subetapas (`ctx.step`) e o erro mascarado no aviso de falha.

## Executar

```powershell
python -m pip install -e ..\..\packages\orchestrator-core -e ..\..\packages\orchestrator-notifications -e ..\..\packages\orchestrator-notifications-smtp -e ..\..\packages\orchestrator-notifications-teams -e .
python -m batch_check data --config orchestrator.toml
```

A configuração de exemplo envia para um servidor SMTP local, sem TLS, na porta 2525. Sem servidor, a entrega falha, o aviso fica no log e a execução continua `succeeded`: o canal não é `required`. Para outra porta: `$env:ORCHESTRATOR_CAPABILITIES__NOTIFICATIONS__CHANNELS__OPS__PORT = "2526"`.

## Testar

```powershell
python -m pytest tests
```
