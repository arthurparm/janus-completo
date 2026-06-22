---
tipo: visao
dominio: sistema
camada: arquitetura
fonte-de-verdade: codigo
status: ativo
---

# Arquitetura Geral

## Em uma frase
Arquitetura do Janus = UI Angular → API FastAPI → serviços/workers → bancos (transacional + cognitivo) → observabilidade.

## O que é
O Janus é uma plataforma interna para conversa, automação e observabilidade. Ele mistura:
- Caminhos síncronos (requisição HTTP/SSE do usuário)
- Caminhos assíncronos (tarefas em fila e loops)
- Memória/recuperação (vetores + grafo) para dar contexto ao chat e à autonomia

## As camadas (sem jargão)
- Interface: Angular (`frontend/src/app`).
- API: FastAPI (`backend/app/main.py`, `backend/app/api/v1`).
- Cérebro do backend: serviços + kernel (onde as dependências são montadas).
- Execução assíncrona: workers (consumidores de filas e loops).
- Dados:
  - PC1: Postgres/Redis/RabbitMQ (controle e operação)
  - PC2: Neo4j/Qdrant/Ollama (conhecimento, memória e inferência local)

## Para dev júnior
- Onde olhar primeiro quando “algo não funciona”:
  1) rota/endpoints
  2) serviço que implementa a regra
  3) repositório que persistiu/consultou
  4) dependência externa (fila/banco/LLM)
- Use como mapa: [[00 - Índice/Mapa Mestre do Sistema]].

## Para dev sênior
- Ponto sensível: boot e composição. O que entra no caminho crítico do startup decide disponibilidade.
- O runtime assíncrono tem múltiplos “registros” (kernel vs orquestrador HTTP), então é fácil ter duplicação de consumers se a configuração estiver errada.

## Para operação
- Regra operacional: subir PC2 → subir PC1 (infra antes da aplicação).
- O que importa no incidente:
  - healthchecks
  - status de workers/filas
  - degradação (quando Neo4j/Qdrant/LLM falham)

## Para não-técnico
- Pense no Janus como “um operador assistido”: você pede, ele busca contexto e executa de forma controlada, registrando evidências e métricas.

## Referências de código (onde a verdade está)
- `backend/app/main.py`
- `backend/app/core/kernel.py`
- `backend/app/config.py`
- `frontend/src/app/app.routes.ts`
- `frontend/src/app/services/backend-api.service.ts`

## Leituras relacionadas
- [[00 - Índice/Mapa Mestre do Sistema]]
- [[01 - Visão do Sistema/Sequência de Boot]]
- [[01 - Visão do Sistema/Dependências Externas]]
- [[02 - Backend/Como o Backend Pensa]]
- [[05 - Infra e Operação/PC1 PC2 e Docker]]

## Riscos/Lacunas
- Kernel concentra composição e aumenta acoplamento.
- Runtime assíncrono pode ficar “difícil de enxergar” se você olhar só um endpoint/status.
