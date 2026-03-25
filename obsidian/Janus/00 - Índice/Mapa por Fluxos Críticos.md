---
tipo: indice
dominio: sistema
camada: navegacao
fonte-de-verdade: codigo
status: ativo
---

# Mapa por Fluxos Críticos

## Objetivo
Agrupar o sistema pelo que ele faz ponta a ponta.

## Responsabilidades
- Mostrar como a UI atravessa API, serviços, persistência e workers.
- Servir de ponte entre visão arquitetural e operação real.

## Entradas
- Rotas Angular.
- Endpoints FastAPI.
- Serviços e workers.

## Saídas
- Roteiro de leitura por jornada funcional.

## Dependências
- [[04 - Fluxos End-to-End/Login e Identidade]]
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Autonomia]]
- [[04 - Fluxos End-to-End/Observabilidade]]
- [[04 - Fluxos End-to-End/Documentos Conhecimento e Memória]]
- [[04 - Fluxos End-to-End/Ferramentas e Sandbox]]

## Fluxos
- Acesso e sessão: [[04 - Fluxos End-to-End/Login e Identidade]]
- Conversa, SSE e feedback: [[04 - Fluxos End-to-End/Conversa e Chat]]
- Metas, planos e workers: [[04 - Fluxos End-to-End/Autonomia]]
- Saúde e operador: [[04 - Fluxos End-to-End/Observabilidade]]
- Documentos, memória e recuperação: [[04 - Fluxos End-to-End/Documentos Conhecimento e Memória]]
- Tooling, criação dinâmica e sandbox: [[04 - Fluxos End-to-End/Ferramentas e Sandbox]]

## Arquivos-fonte
- `frontend/src/app/app.routes.ts`
- `frontend/src/app/features/conversations/conversations.ts`
- `backend/app/api/v1/endpoints/chat/*`
- `backend/app/api/v1/endpoints/autonomy.py`
- `backend/app/api/v1/endpoints/observability.py`
- `backend/app/api/v1/endpoints/tools.py`

## Riscos/Lacunas
- Alguns fluxos administrativos têm pouca visibilidade no frontend atual.
