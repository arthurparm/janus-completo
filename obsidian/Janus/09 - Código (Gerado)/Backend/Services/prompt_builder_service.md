---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/prompt_builder_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# prompt_builder_service

## Objetivo
Prompt Builder Service - Modular Architecture
Delegates to PromptComposer for efficient, intent-based prompt generation.

## Arquivos-fonte
- `backend/app/services/prompt_builder_service.py`

## Fluxos de uso (chamadores)
- `backend/app/core/kernel.py`
- `backend/app/services/chat/message_orchestration_service.py`
- `backend/app/services/chat/streaming_service.py`
- `backend/app/services/chat_service.py`

## Símbolos
- class: `PromptBuilderService`
  - Service for building LLM prompts using modular composition.
Uses intent classification and selective module loading for token efficiency.
- method: `PromptBuilderService.__init__(self, prompt_service: PromptService | None = None)`
  - Initialize prompt builder.
- method: `PromptBuilderService.build_prompt(self, persona: str, history: list[dict[str, Any]], new_user_message: str, summary: str | None, relevant_memories: str | None = None)` -> `str`
  - Build complete prompt for LLM using modular composition.
- method: `PromptBuilderService.is_capabilities_query(self, message: str)` -> `bool`
  - Check if message is asking about capabilities.
- method: `PromptBuilderService.is_tool_request(self, message: str)` -> `bool`
  - Check if message is requesting tool creation.
- method: `PromptBuilderService.is_script_request(self, message: str)` -> `bool`
  - Check if message is requesting script generation.
- method: `PromptBuilderService.is_discovery_query(self, message: str)` -> `bool`
  - Check if message is an interactive discovery query.
- method: `PromptBuilderService.is_docs_query(self, message: str)` -> `bool`
  - Check if message is asking for tool documentation.
- method: `PromptBuilderService.render_discovery_intro(self, tools: Any)` -> `str`
  - Render introductory message listing available tools.
- method: `PromptBuilderService.render_tools_documentation(self, tools: Any)` -> `str`
  - Render detailed documentation for all tools.
- method: `PromptBuilderService.render_local_capabilities(self, tools: Any)` -> `str`
  - Render local capabilities overview.
- method: `PromptBuilderService.estimate_tokens(self, text: str)` -> `int`
  - Estimate token count using character heuristic (char/4).
Used for quick cost/size estimation without full tokenization.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
