---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/chat_agent_loop.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# chat_agent_loop

## Objetivo
Chat Agent Loop Service.
Executes ReAct (Reasoning + Acting) loop with tool execution fallbacks.

## Arquivos-fonte
- `backend/app/services/chat_agent_loop.py`

## Fluxos de uso (chamadores)
- `backend/app/services/chat/message_orchestration_service.py`
- `backend/app/services/chat_service.py`

## Símbolos
- class: `ChatAgentLoop`
  - Executes ReAct agent loop with tool calling.
- method: `ChatAgentLoop.__init__(self, llm_service: Any, tool_executor: Any, rag_service: Any | None = None, event_publisher: Any | None = None, prompt_service: Any | None = None)`
  - Initialize agent loop.
- method: `ChatAgentLoop._estimate_tokens(self, text: str)` -> `int`
  - Estimate token count.
- method: `ChatAgentLoop._build_policy(self)` -> `PolicyEngine`
- method: `ChatAgentLoop.run_loop(self, conversation_id: str, initial_prompt: str, persona: str, message: str, role: ModelRole, priority: ModelPriority, timeout_seconds: int | None = None, user_id: str | None = None, project_id: str | None = None, max_iterations: int = 5)` -> `dict[str, Any]`
  - Execute ReAct agent loop.
- method: `ChatAgentLoop._invoke_llm_with_fallback(self, prompt: str, role: ModelRole, priority: ModelPriority, timeout_seconds: int | None, conversation_id: str, user_id: str | None, project_id: str | None)` -> `dict[str, Any]`
  - Invoke LLM with fallback strategies.
- method: `ChatAgentLoop._execute_tools_with_fallback(self, tool_calls: list[dict], policy: PolicyEngine | None, user_id: str | None, project_id: str | None)` -> `list[dict]`
  - Execute tools with fallback strategies.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
