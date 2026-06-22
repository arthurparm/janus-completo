---
tipo: indice
dominio: sistema
camada: navegacao
fonte-de-verdade: codigo
status: ativo
---

# Home

## Em uma frase
Este vault é o “manual do Janus” baseado no que o sistema realmente faz.

## O que é
O Janus é um sistema full stack (Frontend Angular + Backend FastAPI) que executa chat, memória/RAG, autonomia (tarefas assíncronas) e observabilidade, usando múltiplos bancos (Postgres/Redis/RabbitMQ/Neo4j/Qdrant) e provedores de LLM (cloud e local).

## Como ler (sem se perder)
- Comece pelo mapa único: [[00 - Índice/Mapa Mestre do Sistema]]
- Depois escolha um caminho:
  - Por domínio: [[00 - Índice/Mapa por Domínio]]
  - Por fluxos críticos: [[00 - Índice/Mapa por Fluxos Críticos]]

## Para dev júnior (onboarding rápido)
- Entenda a regra de ouro: endpoint → service → repository → core/model.
- Leia: [[02 - Backend/Como o Backend Pensa]] e [[03 - Frontend/Shell e Navegação]].

## Para dev sênior (orientação arquitetural)
- Leia: [[01 - Visão do Sistema/Arquitetura Geral]], [[01 - Visão do Sistema/Sequência de Boot]] e [[01 - Visão do Sistema/Topologia Runtime]].
- Use os inventários: [[07 - Glossário e Inventários/Inventário de Serviços]], [[07 - Glossário e Inventários/Inventário de Endpoints]], [[07 - Glossário e Inventários/Inventário de Workers]].

## Para operação (rodar e diagnosticar)
- Leia: [[05 - Infra e Operação/PC1 PC2 e Docker]] e [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]].

## Para não-técnico (o que o produto entrega)
- Leia os fluxos: [[04 - Fluxos End-to-End/Conversa e Chat]], [[04 - Fluxos End-to-End/Login e Identidade]], [[04 - Fluxos End-to-End/Autonomia]], [[04 - Fluxos End-to-End/Observabilidade]].

## Referências de código (onde a verdade está)
- `backend/app/main.py`
- `backend/app/core/kernel.py`
- `backend/app/api/v1/router.py`
- `frontend/src/app/app.routes.ts`
- `frontend/src/app/services/backend-api.service.ts`
- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`

## Riscos/Lacunas
- O sistema é maior que o conjunto de telas mais usadas no frontend.
- Algumas capacidades existem como plataforma e podem estar menos conectadas à UX atual.
