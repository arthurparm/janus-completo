---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/chat_event_logger.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# chat_event_logger

## Arquivos-fonte
- `backend/app/services/chat_event_logger.py`

## Dependências de código
- Repositórios
  - `observability_repository`

## Fluxos de uso (chamadores)
- `backend/app/core/kernel.py`

## Símbolos
- class: `ChatEventDbLogger`
- method: `ChatEventDbLogger.__init__(self, repo: ObservabilityRepository)`
- method: `ChatEventDbLogger.log_event(self, payload: dict[str, Any])` -> `None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
