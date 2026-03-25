---
tipo: qualidade
dominio: testes
camada: riscos
fonte-de-verdade: codigo
status: ativo
---

# Lacunas e Riscos

## Objetivo
Registrar as fragilidades percebidas a partir do código e da cobertura.

## Responsabilidades
- Sinalizar acoplamentos altos.
- Sinalizar zonas de baixa visibilidade.

## Entradas
- Leitura estrutural do backend/frontend.
- Inventário de testes.

## Saídas
- Backlog técnico de risco arquitetural.

## Dependências
- [[06 - Qualidade e Testes/Mapa de Testes]]
- [[02 - Backend/Como o Backend Pensa]]

## Riscos principais
- `BackendApiService` concentra contratos demais.
- `ConversationsComponent` concentra subfluxos demais.
- O kernel compõe quase tudo manualmente.
- O deploy distribuído PC1/PC2 aumenta superfície de falha.
- Capacidades internas do backend são maiores que a UX operacional atual.
- REST e SSE do chat têm capacidades diferentes apesar de servirem a mesma UX.
- `ChatStudyJobService` é in-memory e perde estado em restart.
- `GET /api/v1/chat/start` aceita `title`, mas a implementação descarta o valor.
- `AgentEventsService` depende de `EventSource` sem headers; se `CHAT_AUTH_ENFORCE_REQUIRED` subir, o stream de eventos tende a quebrar.

## Lacunas percebidas
- Pouca evidência de E2E de UX completa.
- Diferença potencial entre saúde de container e saúde lógica.
- Parte das integrações de LLM/local runtime depende fortemente de configuração.
- O frontend escuta `tool_status`, mas o backend atual não emite esse evento em `StreamingService`.
- O fluxo SSE não indexa mensagens no RAG nem chama `maybe_summarize()`, então histórico e grounding podem divergir do caminho REST.
- A criação de pending action fallback depende de `user_id`; em cenários anônimos ou mal resolvidos a UI pode receber confirmação sem ID estruturado.

## Arquivos-fonte
- `backend/app/core/kernel.py`
- `backend/app/services/chat/message_orchestration_service.py`
- `backend/app/services/chat/streaming_service.py`
- `backend/app/services/chat_study_service.py`
- `frontend/src/app/features/conversations/conversations.ts`
- `frontend/src/app/services/backend-api.service.ts`
- `frontend/src/app/services/chat-stream.service.ts`
- `frontend/src/app/core/services/agent-events.service.ts`
- `qa/*.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]

## Riscos/Lacunas
- Esta nota é deliberadamente viva e deve crescer conforme incidentes reais forem mapeados.
