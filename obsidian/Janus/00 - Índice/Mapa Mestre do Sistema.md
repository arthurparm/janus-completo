---
tipo: indice
dominio: sistema
camada: arquitetura
fonte-de-verdade: codigo
status: ativo
---

# Mapa Mestre do Sistema

## Objetivo
Condensar a topologia lógica do Janus em um único mapa operacional.

## Responsabilidades
- Mostrar fronteiras entre frontend, API, workers e infraestrutura.
- Explicar a divisão PC1/PC2.
- Ligar componentes aos fluxos críticos.

## Entradas
- Boot FastAPI.
- Kernel de dependências.
- Rotas Angular.
- Compose de PC1 e PC2.

## Saídas
- Modelo mental único do sistema.

## Dependências
- [[01 - Visão do Sistema/Arquitetura Geral]]
- [[01 - Visão do Sistema/Topologia Runtime]]
- [[05 - Infra e Operação/PC1 PC2 e Docker]]

## Mapa
1. `janus-frontend` entrega a interface Angular.
2. `janus-api` expõe a superfície FastAPI e inicializa o kernel.
3. O kernel conecta repositórios, serviços, monitoramento, scheduler e workers.
4. O backend usa Postgres, Redis e RabbitMQ no PC1.
5. O backend usa Neo4j, Qdrant e Ollama no PC2.
6. A camada de chat, autonomia e observabilidade concentra os fluxos principais.

## Núcleos do sistema
- Núcleo de composição: [[02 - Backend/Kernel e Startup]]
- Núcleo cognitivo: [[02 - Backend/LLM Routing e Prompts]]
- Núcleo de memória: [[02 - Backend/Memória Conhecimento e RAG]]
- Núcleo de execução: [[02 - Backend/Autonomia e Workers]]
- Núcleo de experiência: [[03 - Frontend/Shell e Navegação]]

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Autonomia]]
- [[04 - Fluxos End-to-End/Observabilidade]]

## Arquivos-fonte
- `backend/app/main.py`
- `backend/app/core/kernel.py`
- `backend/app/api/v1/router.py`
- `frontend/src/app/app.routes.ts`
- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`

## Riscos/Lacunas
- O backend é mais amplo do que o conjunto de rotas e telas usadas com frequência.
- Existem capacidades de MAS, audio e vision que podem estar parcialmente conectadas à UX atual.
