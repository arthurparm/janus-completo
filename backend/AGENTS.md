# AGENTS.md — Backend Janus

Aplica-se a `backend/` e complementa o contrato da raiz. Para testes Python em `qa/`, aplique também estas regras quando eles validarem comportamento do backend.

## Navegação e camadas

Investigue no sentido:

```text
endpoint -> service -> repository -> core/model
```

- Endpoints cuidam de transporte, autenticação, validação e resposta.
- Services orquestram casos de uso e regras de domínio.
- Repositories isolam persistência.
- Core contém runtime e mecanismos compartilhados; models definem contratos tipados.

Não mova regra de negócio para endpoint, não acesse persistência por atalho e não instancie dependências de infraestrutura em módulos de contrato. Preserve injeção de dependência e interfaces existentes.

Entry points e mapas: `backend/app/main.py`, `backend/app/api/v1/router.py`, [BACKEND_RUNTIME.md](../BACKEND_RUNTIME.md) e [CODEBASE_MAP.md](../CODEBASE_MAP.md).

## Chat e transportes

- Comportamento compartilhado de turno vive em `backend/app/services/chat/turn_core.py` e serviços comuns.
- REST e SSE podem diferir em framing, polling, heartbeat e idempotência de transporte; devem ser equivalentes em validação, autorização, roteamento, citações, persistência, confirmação, entendimento e resultado normalizado.
- Não duplique regras de domínio entre `message_orchestration_service.py`, `streaming_service.py` e endpoints.
- Persista o resultado antes de emitir sucesso terminal SSE. Preserve ledger SSE e idempotência REST como mecanismos específicos de transporte.
- Respostas estáticas não podem contornar precondições, políticas de citações, persistência ou efeitos definidos pelo contrato compartilhado.

Mudanças de chat exigem testes dos dois transportes e `qa/test_chat_endpoint_contract.py` quando o contrato público for afetado.

## Autonomia, memória e ferramentas

Leia [documentation/janus-project-philosophy.md](../documentation/janus-project-philosophy.md) e [AUTONOMY_RISK.md](../AUTONOMY_RISK.md) antes de alterar esses domínios.

- Uma meta persistida ou executável declara origem, justificativa, resultado mensurável, evidência, horizonte de revisão, custo, recursos, risco, supervisão, estado e motivo de encerramento.
- Reflexão e proposição não autorizam execução externa.
- Cálculo de risco, criação de ação pendente, persistência e apresentação de confirmação permanecem responsabilidades separadas.
- Não remova confirmação, sandbox, allowlist, quota, redaction, retenção, autorização ou auditoria para fazer um fluxo funcionar.
- Memória e conhecimento distinguem fato observado, inferência e conteúdo gerado, sempre com procedência e escopo.

## Implementação

- Use Python `>=3.11,<3.13` e as dependências bloqueadas do projeto.
- Reuse abstrações e fixtures existentes antes de criar novas.
- Mantenha contratos Pydantic, SQLAlchemy, eventos e tipos de retorno compatíveis.
- Dependência nova requer ausência de equivalente, justificativa de manutenção/segurança/licença e documentação.
- Migração deve preservar dados, considerar versões mistas, oferecer rollback e obter autorização antes de qualquer transformação destrutiva.

## Validação

Rode primeiro o teste diretamente afetado. Testes assíncronos exigem `pytest-asyncio`; no ambiente Windows conhecido, o fluxo reproduzível usa Python 3.12:

```powershell
uv run --python 3.12 --with-requirements backend/requirements.txt --with pytest --with pytest-asyncio python -m pytest -q <testes-alvo>
```

Depois aplique, conforme o domínio:

| Mudança | Contrato mínimo |
|---|---|
| Chat REST/SSE | testes unitários afetados + `qa/test_chat_endpoint_contract.py` |
| Tools, risco, confirmação | `qa/test_tool_executor_policy_guards.py` + testes de pending actions |
| Memória | `qa/test_memory_quota_enforcement.py` + testes do serviço |
| LLM/memória generativa | `qa/test_generative_memory_llm_role_priority.py` + roteamento afetado |
| Knowledge/RAG | `qa/test_knowledge_code_query_contract.py` + retrieval afetado |
| Observabilidade | `qa/test_observability_request_dashboard.py` + artefato consumido |
| Migração | `qa/test_db_migration_service_contract.py` + upgrade/rollback |

Para arquivos alterados, execute Ruff e mypy com `backend/pyproject.toml`. Para mudança ampla, execute `python tooling/dev.py qa`. Mudanças em retrieval, citações, qualidade ou latência devem executar o evaluation gate descrito em [OPS_QA.md](../OPS_QA.md), ou registrar por que ele não se aplica.

Não use rede externa ou sleeps arbitrários em testes; cubra sucesso, limites, falha/recuperação, autorização e ausência de efeitos indevidos.
