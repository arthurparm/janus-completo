---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/llm_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# llm_repository

## Arquivos-fonte
- `backend/app/repositories/llm_repository.py`

## Dependências de código
- Repositórios
  - `ab_experiment_repository`
  - `observability_repository`

## Fluxos de uso (chamadores)
- `backend/app/core/agents/debate_orchestrator.py`
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
- `backend/app/services/llm_service.py`

## Símbolos
- class: `LLMRepositoryError`
  - Base exception for LLM repository errors.
- class: `LLMRepository`
  - Camada de Repositório para o Cérebro Híbrido (LLMs).
Abstrai todas as interações diretas com a infraestrutura de LLMs.
- method: `LLMRepository.invoke_llm(self, prompt: str, role: ModelRole, priority: ModelPriority, timeout_seconds: int | None, user_id: str | None = None, project_id: str | None = None, objective_id: str | None = None, llm_config: dict[str, Any] | None = None)` -> `dict[str, Any]`
- method: `LLMRepository.get_cache_entries(self)` -> `list[dict[str, Any]]`
- method: `LLMRepository.invalidate_cache(self, provider: str | None = None)` -> `int`
- method: `LLMRepository.warm_pool(self, specs: list[str] | None = None)` -> `dict[str, int]`
- method: `LLMRepository.invalidate_response_cache(self, prompt: str | None = None, role: str | None = None, priority: str | None = None)` -> `int`
- method: `LLMRepository.get_circuit_breakers(self)` -> `list[dict[str, Any]]`
- method: `LLMRepository.reset_circuit_breaker(self, provider: str)`
- method: `LLMRepository.list_providers(self)` -> `list[dict[str, Any]]`
  - Lista provedores configurados com status de habilitação e modelos padrão.
- function: `get_llm_repository()` -> `LLMRepository`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
