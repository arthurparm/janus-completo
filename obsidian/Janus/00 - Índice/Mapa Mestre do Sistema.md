---
tipo: indice
dominio: sistema
camada: arquitetura
fonte-de-verdade: codigo
status: ativo
---

# Mapa Mestre do Sistema

## Em uma frase
Este é o mapa mínimo para entender “quem chama quem” e “onde os dados vivem”.

## O que existe (as peças)
- Frontend (`janus-frontend`): a interface Angular que o operador usa.
- Backend (`janus-api`): a API FastAPI e o motor que toma decisões.
- Kernel: composição interna (dependências, serviços, workers).
- Infra PC1: Postgres + Redis + RabbitMQ (transação, cache, filas).
- Infra PC2: Neo4j + Qdrant + Ollama (grafo, vetores/memória, LLM local).

## Como funciona (do clique ao resultado)
1. O operador faz algo no frontend.
2. O frontend chama um endpoint do backend.
3. O endpoint delega para um serviço.
4. O serviço usa repositórios e “cores” (memória/LLM/tools).
5. Se for assíncrono, o backend publica em filas e workers processam.
6. O resultado volta para a UI (ou fica disponível por status/observabilidade).

## Para dev júnior
- Regra prática: “endpoint só traduz HTTP; o serviço decide; o repositório persiste”.
- Leia os fluxos: [[04 - Fluxos End-to-End/Conversa e Chat]] e [[04 - Fluxos End-to-End/Login e Identidade]].

## Para dev sênior
- Entenda a composição e boot: [[01 - Visão do Sistema/Arquitetura Geral]] e [[01 - Visão do Sistema/Sequência de Boot]].
- Entenda o runtime assíncrono: [[02 - Backend/Autonomia e Workers]].

## Para operação
- Ponto crítico: a ordem PC2 → PC1 evita dependências faltando no startup.
- Healthchecks e status: [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]].

## Para não-técnico
- Janus é um “assistente operacional”: você conversa, o sistema busca contexto, executa ações controladas e registra evidências.

## Referências de código (onde a verdade está)
- `backend/app/main.py`
- `backend/app/core/kernel.py`
- `backend/app/api/v1/router.py`
- `frontend/src/app/app.routes.ts`
- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`

## Riscos/Lacunas
- O backend tem capacidades além do que a UI expõe todo dia.
- Há subsistemas (ex.: MAS/audio/vision) que podem estar mais “plataforma” do que “produto” no uso atual.
