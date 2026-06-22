---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/llm_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# llm_service

## Arquivos-fonte
- `backend/app/services/llm_service.py`

## Dependências de código
- Repositórios
  - `llm_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/exception_handlers.py`
- `backend/app/api/v1/endpoints/llm.py`
- `backend/app/api/v1/endpoints/system_overview.py`
- `backend/app/api/v1/endpoints/system_status.py`
- `backend/app/core/agents/debate_orchestrator.py`
- `backend/app/core/autonomy/planner.py`
- `backend/app/core/evolution/evolution_manager.py`
- `backend/app/core/evolution/safe_evolution_manager.py`
- `backend/app/core/kernel.py`
- `backend/app/core/memory/generative_memory.py`
- `backend/app/core/tools/agent_tools.py`
- `backend/app/core/workers/code_agent_worker.py`
- `backend/app/core/workers/debate_critic_worker.py`
- `backend/app/core/workers/debate_proponent_worker.py`
- `backend/app/core/workers/professor_agent_worker.py`
- `backend/app/core/workers/red_team_agent_worker.py`
- `backend/app/core/workers/thinker_agent_worker.py`
- `backend/app/planes/inference/facade.py`
- `backend/app/services/assistant_service.py`
- `backend/app/services/autonomy_admin_service.py`
- `backend/app/services/autonomy_service.py`
- `backend/app/services/chat_service.py`
- `backend/app/services/rag_service.py`

## Símbolos
- class: `LLMServiceError`
  - Base exception for LLM service errors.
- class: `LLMInvocationError`
  - Raised on failure to invoke an LLM.
- class: `LLMTimeoutError`
  - Raised on LLM invocation timeout.
- class: `LLMService`
  - Camada de serviço para gerenciamento do Cérebro Híbrido (LLMs).
Orquestra a lógica de negócio, recebendo suas dependências via DI.
- method: `LLMService.__init__(self, repo: LLMRepository, prompt_service: PromptService | None = None)`
- method: `LLMService.invoke_llm(self, prompt: str, role: ModelRole, priority: ModelPriority, timeout_seconds: int | None, task_type: str | None = None, complexity: str | None = None, policy_overrides: dict[str, Any] | None = None, user_id: str | None = None, project_id: str | None = None, objective_id: str | None = None)` -> `dict[str, Any]`
- method: `LLMService.get_cache_status(self)` -> `list[dict[str, Any]]`
- method: `LLMService.invalidate_cache(self, provider: str | None = None)` -> `int`
- method: `LLMService.get_response_cache_status(self)` -> `list[dict[str, Any]]`
  - Retorna apenas entradas do cache de respostas (prompts/respostas).
- method: `LLMService.invalidate_response_cache(self, prompt: str | None = None, role: str | None = None, priority: str | None = None)` -> `int`
  - Invalida entradas do cache de respostas por filtro (prompt/role/priority) ou completas se não informado.
- method: `LLMService.get_circuit_breaker_statuses(self)` -> `list[dict[str, Any]]`
- method: `LLMService.reset_circuit_breaker(self, provider: str)` -> `str`
- method: `LLMService.get_providers(self)` -> `list[dict[str, Any]]`
- method: `LLMService.warm_pool(self, specs: list[str] | None = None)` -> `dict[str, int]`
- method: `LLMService.get_health_status(self)` -> `dict[str, Any]`
- method: `LLMService.select_provider(self, role: ModelRole, priority: ModelPriority, user_id: str | None = None, project_id: str | None = None)` -> `dict[str, Any]`
  - Seleciona provider/modelo antecipadamente sem invocar o LLM.
- method: `LLMService.is_provider_open(self, provider: str)` -> `bool`
  - Retorna True se o circuit breaker do provider estiver aberto (bloqueado).
- function: `get_llm_service(request: Request)` -> `LLMService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
