---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/prompt_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# prompt_repository

## Objetivo
Repositório para gerenciar prompts dinâmicos.
Permite que o Meta-Agent atualize prompts baseado em análises de performance.

## Arquivos-fonte
- `backend/app/repositories/prompt_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/core/infrastructure/prompt_loader.py`
- `backend/app/core/kernel.py`
- `backend/app/services/optimization_service.py`
- `backend/app/services/prompt_service.py`

## Símbolos
- class: `PromptRepository`
  - Repositório para operações CRUD em prompts.
- method: `PromptRepository.__init__(self, session: Session | AsyncSession | None = None)`
- method: `PromptRepository._get_session_sync(self)` -> `Session`
  - Get a sync database session.
- method: `PromptRepository._get_session_async(self)` -> `AsyncSession`
  - Get an async database session.
- method: `PromptRepository.get_active_prompt(self, prompt_name: str, namespace: str = 'default', language: str = 'en', model_target: str = 'general')` -> `Prompt | None`
  - Obtém o prompt ativo para um nome específico.
- method: `PromptRepository.get_active_prompt_sync(self, prompt_name: str, namespace: str = 'default', language: str = 'en', model_target: str = 'general')` -> `Prompt | None`
  - Get the active prompt using a sync session.
- method: `PromptRepository.get_prompt_by_id(self, prompt_id: int)` -> `Prompt | None`
  - Obtém prompt por ID.
- method: `PromptRepository.get_prompt_versions(self, prompt_name: str, namespace: str = 'default')` -> `list[Prompt]`
  - Obtém todas as versões de um prompt.
- method: `PromptRepository.create_prompt_version(self, prompt_name: str, prompt_text: str, version: str, namespace: str = 'default', language: str = 'en', model_target: str = 'general', created_by: str = 'meta-agent', activate: bool = False)` -> `Prompt`
  - Cria uma nova versão de prompt.
- method: `PromptRepository.activate_prompt_version(self, prompt_id: int)` -> `bool`
  - Ativa uma versão específica de prompt.
- method: `PromptRepository._deactivate_prompt(self, session: Session, prompt_name: str, namespace: str, language: str, model_target: str)`
  - Desativa prompt ativo atual.
- method: `PromptRepository.search_prompts(self, name_pattern: str | None = None, namespace: str | None = None, active_only: bool = True)` -> `list[Prompt]`
  - Busca prompts por padrão.
- method: `PromptRepository.get_prompt_stats(self)` -> `dict[str, Any]`
  - Obtém estatísticas dos prompts.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
