---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/feedback.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# feedback

## Objetivo
Feedback API Endpoints - Quick Win para coleta de feedback do usuário.

## Arquivos-fonte
- `backend/app/api/v1/endpoints/feedback.py`

## Rotas
- `GET /conversation/{conversation_id}`
- `GET /report`
- `GET /stats`
- `GET /suggestions`
- `POST /`
- `POST /thumbs-down`
- `POST /thumbs-up`

## Dependências de código
- Serviços
  - `feedback_service`

## Símbolos
- class: `FeedbackRatingEnum`
- class: `FeedbackTypeEnum`
- class: `FeedbackRequest`
  - Request para registrar feedback.
- class: `QuickFeedbackRequest`
  - Request simplificada para thumbs up/down.
- class: `FeedbackResponse`
  - Response após registrar feedback.
- class: `SatisfactionReportResponse`
  - Response com relatório de satisfação.
- class: `FeedbackStatsResponse`
  - Response com estatísticas rápidas.
- function: `record_feedback(request: FeedbackRequest)`
  - Registra feedback do usuário sobre uma mensagem ou conversa.
- function: `thumbs_up(request: QuickFeedbackRequest)`
  - Registra feedback positivo (👍) para uma mensagem.
- function: `thumbs_down(request: QuickFeedbackRequest)`
  - Registra feedback negativo (👎) para uma mensagem.
- function: `get_feedback_stats()`
  - Retorna estatísticas rápidas de feedback.
- function: `get_satisfaction_report(hours: int = Query(24, description='Janela de tempo em horas', ge=1, le=720))`
  - Gera relatório detalhado de satisfação.
- function: `get_improvement_suggestions()`
  - Retorna sugestões de melhoria baseadas em feedbacks negativos.
- function: `get_conversation_feedback(conversation_id: str)`
  - Retorna todos os feedbacks de uma conversa específica.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
