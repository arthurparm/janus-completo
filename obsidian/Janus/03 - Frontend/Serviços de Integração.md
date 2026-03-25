---
tipo: dominio
dominio: frontend
camada: integracao
fonte-de-verdade: codigo
status: ativo
---

# Serviços de Integração

## Objetivo
Mapear os clientes e adaptadores que conectam UI e backend.

## Responsabilidades
- Explicar os serviços de fronteira.
- Destacar quem centraliza contratos.

## Entradas
- `frontend/src/app/services/*.ts`

## Saídas
- Mapa frontend -> backend.

## Dependências
- [[02 - Backend/API por Bounded Context]]
- [[03 - Frontend/Features e Experiência]]

## Serviços principais
- `backend-api.service`: client central com contratos extensos do backend.
- `chat-stream.service`: streaming SSE para conversa.
- `graph-api.service`: integrações específicas de grafo.
- `auto-analysis.service`: chamadas de autoanálise.
- `response-time-estimator.service`: estimativa de espera percebida.
- `conversation-refresh.service`: refresco de contexto de conversa.

## Leitura operacional
- O frontend ainda usa um grande client consolidado em vez de clients por domínio.
- A composição de tipos no `backend-api.service` documenta boa parte do contrato consumido pela UI.

## Arquivos-fonte
- `frontend/src/app/services/backend-api.service.ts`
- `frontend/src/app/services/chat-stream.service.ts`
- `frontend/src/app/services/graph-api.service.ts`
- `frontend/src/app/services/auto-analysis.service.ts`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Observabilidade]]
- [[07 - Glossário e Inventários/Inventário de Endpoints]]

## Riscos/Lacunas
- O client centralizado tende a crescer sem fronteiras claras entre domínios.
