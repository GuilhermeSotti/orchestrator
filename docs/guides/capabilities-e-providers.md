# Capabilities e Providers

Como estender o Orchestrator sem alterar o Core. Decisões: [ADR-0004](../adr/0004-fronteiras-core-capability-provider.md), [ADR-0009](../adr/0009-registro-de-capabilities-e-compatibilidade.md) e [ADR-0015](../adr/0015-testes-entre-pacotes.md). Exemplo real: `packages/orchestrator-sql` e `packages/orchestrator-sqlite`.

## Papéis

- **Capability**: o que a automação usa. Define o handle (por exemplo `SqlSession`) e o port que os Providers implementam (por exemplo `SqlProvider`). Depende só do Core.
- **Provider**: implementa o port para uma tecnologia. Depende da Capability e do Core. Traduz exceções da infraestrutura para erros da Capability, sem credenciais nem dados nas mensagens.

## Escrevendo uma Capability

```python
from typing import Any, ClassVar, Self

from orchestrator_core import Capability, ConfigSection, ExecutionContext


class Notifier(Capability["NotifierHandle"]):
    default_name: ClassVar[str] = "notifier"
    core_api: ClassVar[str | None] = "0.1"  # registro falha se o Core for incompatível

    def __init__(self, channel: str) -> None:
        self._channel = channel  # objeto do Runtime: sem estado de execução

    @classmethod
    def from_config(cls, section: ConfigSection, /, **options: Any) -> Self:
        section.check_keys({"channel"})
        return cls(section.get_str("channel"))

    def verify(self) -> None: ...  # dependências presentes? lance CapabilityUnavailableError se não

    def open(self, ctx: ExecutionContext) -> "NotifierHandle":
        handle = NotifierHandle(self._channel)
        ctx.resources.callback(handle.close)  # liberado no finalize
        ctx.add_finalizer(handle.flush_if_succeeded)  # recebe o desfecho
        return handle
```

Regras:

1. A Capability é compartilhada pelas execuções e deve ser segura entre threads; estado de execução fica no handle.
2. Tudo o que for adquirido em `open` é registrado em `ctx.resources`.
3. `verify` não adquire recursos: só confirma pré-requisitos.
4. Configuração em `[capabilities.<nome>]`, validada em `from_config`, com `check_keys` para recusar chaves desconhecidas.
5. Credenciais entram como referência de segredo e são resolvidas com `ctx.secrets`.
6. Uma configuração que depende de estágios instalados pelo consumidor é recusada em `open`, antes da automação, consultando `ctx.stages` (nomes dos estágios do pipeline, em ordem; desde a 0.2.0).
7. Texto que sai do processo (avisos, mensagens para outros sistemas) passa por `ctx.redact(texto)`; finalizers usam `outcome.error_info`, já mascarado.

Registro pelo consumidor:

```python
RuntimeBuilder().with_capability(Notifier)  # construída da configuração
RuntimeBuilder().with_capability(Notifier("ops"), name="ops")  # instância pronta
```

## Escrevendo um Provider

Implemente o port da Capability. Para a Capability SQL, `SqlProvider` exige: `from_config`, `connect(secrets)` (em autocommit), `paramstyle`, `is_driver_error`, `translate_error` e `column_type`; o restante tem padrão. Marque falhas transitórias com `retryable=True`.

Credenciais ([RFC-0006](../rfc/0006-segredos-cofres-e-credenciais-de-providers.md), 2.1, opção A): o Provider guarda só a referência lida em `from_config` (`section.get_secret_ref("password")`) e resolve o valor em `connect(secrets)`, com o `SecretStore` da execução, que o registra para mascaramento. O valor resolvido não fica em atributo, não aparece em `describe()` nem em erro traduzido.

## Testando

- Toda Capability: `orchestrator_core.testing.check_capability_conformance(MinhaCapability(...))` verifica execuções sequenciais e concorrentes, isolamento de handles e fechamento do contexto.
- Todo Provider SQL: herde `orchestrator_sql.testing.SqlProviderContract` e implemente `make_provider()`. Provider com credenciais sobrescreve também `secret_resolvers()`; a suíte verifica que o valor resolvido não fica guardado nem exposto.
- Testes que chamam o Provider fora de uma execução usam `orchestrator_core.testing.make_secret_store(...)`.

## Novo pacote neste repositório

Crie `packages/orchestrator-<nome>/` com `pyproject.toml`, `README.md`, `CHANGELOG.md`, `LICENSE`, `src/` e `tests/`, como os existentes; inclua o caminho em `pyproject.toml` da raiz (Ruff, MyPy, Pytest), em `tools/build_packages.py` e nas fronteiras de `tools/test_boundaries.py`. Uma Capability nova começa por RFC.
