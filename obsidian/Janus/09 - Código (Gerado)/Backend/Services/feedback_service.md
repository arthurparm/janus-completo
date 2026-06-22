---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/feedback_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# feedback_service

## Objetivo
Feedback Service - Coleta e análise de feedback do usuário.

## Arquivos-fonte
- `backend/app/services/feedback_service.py`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/feedback.py`

## Símbolos
- class: `FeedbackRating`
  - Tipos de rating de feedback.
- class: `FeedbackType`
  - Tipos de feedback.
- class: `Feedback`
  - Representa um feedback do usuário.
- method: `Feedback.to_dict(self)` -> `dict[str, Any]`
- class: `SatisfactionReport`
  - Relatório de satisfação.
- method: `SatisfactionReport.to_dict(self)` -> `dict[str, Any]`
- class: `FeedbackService`
  - Serviço de coleta e análise de feedback.
- method: `FeedbackService.__init__(self, max_memory_size: int = 1000)`
- method: `FeedbackService.record_feedback(self, conversation_id: str, rating: FeedbackRating, message_id: str | None = None, user_id: str | None = None, comment: str | None = None, feedback_type: FeedbackType = FeedbackType.MESSAGE, context: dict[str, Any] | None = None)` -> `Feedback`
  - Registra um feedback do usuário.
- method: `FeedbackService.record_thumbs_up(self, conversation_id: str, message_id: str, user_id: str | None = None, comment: str | None = None)` -> `Feedback`
  - Atalho para registrar feedback positivo (👍).
- method: `FeedbackService.record_thumbs_down(self, conversation_id: str, message_id: str, user_id: str | None = None, comment: str | None = None)` -> `Feedback`
  - Atalho para registrar feedback negativo (👎).
- method: `FeedbackService._update_satisfaction_gauge(self)` -> `None`
  - Atualiza o gauge de satisfação com base nos últimos feedbacks.
- method: `FeedbackService.get_satisfaction_report(self, user_id: str | None = None, hours: int = 24)` -> `SatisfactionReport`
  - Gera relatório de satisfação.
- method: `FeedbackService.get_feedback_by_conversation(self, conversation_id: str)` -> `list[Feedback]`
  - Retorna todos os feedbacks de uma conversa.
- method: `FeedbackService.get_improvement_suggestions(self)` -> `list[dict[str, Any]]`
  - Analisa feedbacks negativos e gera sugestões de melhoria.
Usado pelo Meta-Agent para auto-otimização.
- method: `FeedbackService.get_stats(self)` -> `dict[str, Any]`
  - Retorna estatísticas rápidas do serviço.
- function: `get_feedback_service()` -> `FeedbackService`
  - Retorna instância singleton do FeedbackService.
- function: `initialize_feedback_service(max_memory_size: int = 1000)` -> `FeedbackService`
  - Inicializa o FeedbackService com configurações customizadas.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
