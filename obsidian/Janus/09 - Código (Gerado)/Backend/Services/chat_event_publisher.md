---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/chat_event_publisher.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# chat_event_publisher

## Objetivo
Chat Event Publisher Service.
Publishes agent events to RabbitMQ with fallback strategies.

## Arquivos-fonte
- `backend/app/services/chat_event_publisher.py`

## Fluxos de uso (chamadores)
- `backend/app/services/chat_service.py`

## Símbolos
- class: `ChatEventPublisher`
  - Publishes agent events with hierarchical fallbacks.
- method: `ChatEventPublisher.__init__(self, db_logger: Any | None = None)`
  - Initialize event publisher.
- method: `ChatEventPublisher.publish_event(self, conversation_id: str, event_type: str, agent_role: str, content: str, task_id: str | None = None, user_id: str | None = None)` -> `None`
  - Publish agent event with fallback strategies.
- method: `ChatEventPublisher._publish_to_rabbitmq(self, conversation_id: str, event_type: str, payload: dict)` -> `None`
  - Primary strategy: Publish to RabbitMQ.
- method: `ChatEventPublisher._publish_to_database(self, payload: dict)` -> `None`
  - Secondary strategy: Store in database.
- method: `ChatEventPublisher._publish_to_log(self, payload: dict)` -> `None`
  - Minimal fallback: Log to file.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
