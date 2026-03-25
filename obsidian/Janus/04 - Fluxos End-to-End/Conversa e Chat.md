---
tipo: fluxo
dominio: chat
camada: end-to-end
fonte-de-verdade: codigo
status: ativo
---

# Conversa e Chat

## Objetivo
Descrever o fluxo principal do produto, do prompt à resposta.

## Responsabilidades
- Cobrir criação de conversa, envio de mensagem e SSE.
- Mostrar pontos de roteamento, citação e confirmação.

## Entradas
- Prompt do usuário.
- Contexto de conversa e usuário.

## Saídas
- Resposta do assistente.
- Estado de roteamento, citações e possíveis pending actions.

## Dependências
- [[02 - Backend/LLM Routing e Prompts]]
- [[02 - Backend/Memória Conhecimento e RAG]]
- [[03 - Frontend/Serviços de Integração]]

## Sequência
1. `Home` ou `Conversations` inicia conversa via `/api/v1/chat/start`.
2. A tela `conversations` envia mensagem por HTTP ou SSE.
3. O backend resolve identidade e knowledge space ativo.
4. `intent_routing_service` ajusta o papel do modelo.
5. `ChatService` delega para orchestration, command handler, RAG e tool executor.
6. O resultado volta com resposta, citações, sinais de risco/confiança e eventualmente `pending_action_id`.

## Leitura operacional
- A feature `conversations` também orquestra docs, memória, RAG e feedback.
- O backend recalcula citações se necessário.
- Streaming usa SSE com controle de slot por usuário.

## Arquivos-fonte
- `frontend/src/app/features/conversations/conversations.ts`
- `frontend/src/app/services/chat-stream.service.ts`
- `backend/app/api/v1/endpoints/chat/chat_message.py`
- `backend/app/api/v1/endpoints/chat/chat_stream.py`
- `backend/app/services/chat_service.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Documentos Conhecimento e Memória]]
- [[04 - Fluxos End-to-End/Ferramentas e Sandbox]]

## Riscos/Lacunas
- O chat é o ponto de convergência de muitos subsistemas; falhas aqui tendem a parecer “genéricas” para o operador.
