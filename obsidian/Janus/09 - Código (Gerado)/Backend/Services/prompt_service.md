---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/prompt_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# prompt_service

## Arquivos-fonte
- `backend/app/services/prompt_service.py`

## Dependências de código
- Repositórios
  - `prompt_repository`

## Fluxos de uso (chamadores)
- `backend/app/core/kernel.py`
- `backend/app/services/llm_service.py`
- `backend/app/services/prompt_builder_service.py`
- `backend/app/services/prompt_composer_service.py`

## Símbolos
- class: `PromptService`
  - Service for managing retrieval of dynamic prompts.
- method: `PromptService.__init__(self, repo: PromptRepository)`
- method: `PromptService.get_prompt(self, prompt_name: str, fallback_text: str | None = None)` -> `str`
  - Retrieves the active prompt text by name.
Uses native async repository with proper session management.
- function: `get_prompt_service(request: Request = None)` -> `PromptService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
