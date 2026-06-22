---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/trace_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# trace_service

## Arquivos-fonte
- `backend/app/services/trace_service.py`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/chat/chat_stream.py`

## Símbolos
- class: `TraceService`
  - Service responsible for retrieving and formatting agent execution traces.
It acts as a layer above ObservabilityService to provide specialized views for the frontend.
- method: `TraceService.__init__(self, observability_service: ObservabilityService)`
- method: `TraceService.get_trace_history(self, conversation_id: str)` -> `List[dict[str, Any]]`
  - Retrieves the execution trace (Chain of Thought) for a given conversation.
- method: `TraceService._format_trace_step(self, event: dict[str, Any])` -> `Optional[dict[str, Any]]`
  - Formats a raw audit event into a standardized trace step.
- function: `get_trace_service(observability_service: ObservabilityService = Depends(get_observability_service))` -> `TraceService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
