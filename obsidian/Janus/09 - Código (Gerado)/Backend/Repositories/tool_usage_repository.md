---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/tool_usage_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# tool_usage_repository

## Arquivos-fonte
- `backend/app/repositories/tool_usage_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/services/tool_executor_service.py`

## Símbolos
- class: `ToolUsageRepository`
- method: `ToolUsageRepository.__init__(self, session: Session | None = None)`
- method: `ToolUsageRepository._get_session(self)` -> `Session`
- method: `ToolUsageRepository.increment_if_within_limit(self, user_id: str, tool_name: str, daily_limit: int)` -> `tuple[bool, int, int]`
  - Incrementa o uso diário se ainda estiver dentro do limite.
Retorna (allowed, current_count, limit).

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
