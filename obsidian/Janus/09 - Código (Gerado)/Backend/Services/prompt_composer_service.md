---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/prompt_composer_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# prompt_composer_service

## Objetivo
Prompt Composer Service - Orchestrates modular prompt construction.
Replaces monolithic prompt_builder_service with efficient, composable architecture.

## Arquivos-fonte
- `backend/app/services/prompt_composer_service.py`

## Fluxos de uso (chamadores)
- `backend/app/services/prompt_builder_service.py`

## Símbolos
- class: `CompiledPrompt`
  - Result of prompt composition.
Contains final prompt text and metadata.
- method: `CompiledPrompt.__init__(self, text: str, intent: IntentType, modules_used: list[str], token_count: int)`
- method: `CompiledPrompt.__str__(self)` -> `str`
- class: `PromptComposer`
  - Composes prompts by selecting and rendering relevant modules.
Provides caching, token optimization, and modular composition.
- method: `PromptComposer.__init__(self, prompt_service: PromptService | None = None)`
  - Initialize composer with optional prompt service for dynamic prompts.
- method: `PromptComposer.compose(self, intent: IntentType, context: ConversationContext)` -> `CompiledPrompt`
  - Compose final prompt from relevant modules.
- method: `PromptComposer.estimate_tokens(self, text: str)` -> `int`
  - Estimate token count (chars / 4).
- method: `PromptComposer._estimate_tokens(self, text: str)` -> `int`
  - Internal alias for token estimation.
- method: `PromptComposer._get_cache_key(self, intent: IntentType, persona: str, message_hash: int)` -> `str`
  - Generate cache key for composed prompts.
- function: `get_prompt_composer(prompt_service: PromptService | None = None)` -> `PromptComposer`
  - Get or create singleton PromptComposer instance.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
