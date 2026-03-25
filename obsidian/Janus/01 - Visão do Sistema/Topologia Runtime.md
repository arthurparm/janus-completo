---
tipo: visao
dominio: sistema
camada: runtime
fonte-de-verdade: codigo
status: ativo
---

# Topologia Runtime

## Objetivo
Descrever onde cada peça roda e como depende das demais em execução.

## Responsabilidades
- Separar PC1 e PC2.
- Mostrar dependências duras e opcionais.

## Entradas
- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`

## Saídas
- Modelo operacional do runtime.

## Dependências
- [[05 - Infra e Operação/PC1 PC2 e Docker]]
- [[05 - Infra e Operação/Bancos Filas e Modelos]]

## Topologia
- PC1:
  - `janus-api`
  - `janus-frontend`
  - `postgres`
  - `redis`
  - `rabbitmq`
- PC2:
  - `neo4j`
  - `qdrant`
  - `ollama`
  - `ollama-model-init`

## Leitura operacional
- O backend não sobe plenamente sem Postgres, Redis e RabbitMQ saudáveis.
- Neo4j, Qdrant e Ollama entram via variáveis apontando para o PC2.
- O frontend depende do `janus-api` saudável.

## Arquivos-fonte
- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`
- `backend/app/config.py`

## Fluxos relacionados
- [[01 - Visão do Sistema/Dependências Externas]]
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]

## Riscos/Lacunas
- O sistema depende de rede estável entre PC1 e PC2.
- Falhas em PC2 degradam memória, RAG e inferência local.
