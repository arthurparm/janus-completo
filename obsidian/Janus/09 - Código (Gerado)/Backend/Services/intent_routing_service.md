---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/intent_routing_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# intent_routing_service

## Arquivos-fonte
- `backend/app/services/intent_routing_service.py`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/chat/chat_message.py`
- `backend/app/api/v1/endpoints/chat/chat_stream.py`

## Símbolos
- class: `IntentRoutingDecision`
- method: `IntentRoutingDecision.to_dict(self)` -> `dict`
- class: `IntentRoutingService`
- method: `IntentRoutingService.classify(self, message: str)` -> `IntentRoutingDecision`
- method: `IntentRoutingService.resolve_role(self, requested_role: str | None, message: str)` -> `tuple[ModelRole, IntentRoutingDecision | None, bool]`
- method: `IntentRoutingService._detect_risk(self, text: str)` -> `tuple[str, list[str]]`
- method: `IntentRoutingService._detect_urgency(self, text: str)` -> `str`
- method: `IntentRoutingService._guardrails_for(self, *, risk_level: str, urgency_level: str)` -> `list[str]`
- method: `IntentRoutingService._calibrate_confidence(self, *, best_score: float, second_score: float, hit_count: int)` -> `float`
- method: `IntentRoutingService._normalize_text(value: str)` -> `str`
- method: `IntentRoutingService._keyword_hits(self, text: str, keywords: tuple[str, ...])` -> `list[str]`
- function: `get_intent_routing_service()` -> `IntentRoutingService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
