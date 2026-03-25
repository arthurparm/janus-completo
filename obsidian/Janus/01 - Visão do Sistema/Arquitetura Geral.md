---
tipo: visao
dominio: sistema
camada: arquitetura
fonte-de-verdade: codigo
status: ativo
---

# Arquitetura Geral

## Objetivo
Explicar a arquitetura do Janus como plataforma agentic full stack.

## Responsabilidades
- Descrever camadas principais.
- Explicar o papel do kernel.
- Mostrar a separação entre plano de controle e plano de dados.

## Entradas
- FastAPI montado em `backend/app/main.py`.
- `lifespan` como coordenador de boot e shutdown.
- Kernel com DI manual.
- Angular com rotas standalone.
- Docker dividido entre PC1 e PC2.

## Saídas
- Visão arquitetural útil para onboarding e troubleshooting.

## Dependências
- [[00 - Índice/Mapa Mestre do Sistema]]
- [[01 - Visão do Sistema/Sequência de Boot]]
- [[01 - Visão do Sistema/Dependências Externas]]

## Camadas
- Interface: Angular em `frontend/src/app`.
- BFF/API: FastAPI em `backend/app/main.py` e `backend/app/api/v1`.
- Orquestração interna: kernel, serviços, repositórios e workers.
- Persistência operacional: Postgres, Redis, RabbitMQ.
- Persistência cognitiva: Neo4j e Qdrant.
- Inferência: provedores cloud e Ollama local.

## Leituras centrais
- `main.py` monta a superfície FastAPI em tempo de importação: logging, tracing, middlewares, exception handlers, routers e endpoints utilitários.
- O `lifespan` coordena a sequência de boot: valida segredos, chama `Kernel.startup()`, inicializa graph/prompt loading e publica dependências selecionadas em `app.state`.
- O `Kernel` compõe repositórios e serviços manualmente e sobe a maior parte do runtime assíncrono de fundo.
- O frontend consome a API majoritariamente por `BackendApiService`.

## Arquivos-fonte
- `backend/app/main.py`
- `backend/app/core/kernel.py`
- `backend/app/config.py`
- `frontend/src/app/app.routes.ts`
- `frontend/src/app/services/backend-api.service.ts`

## Fluxos relacionados
- [[02 - Backend/Como o Backend Pensa]]
- [[03 - Frontend/Shell e Navegação]]
- [[05 - Infra e Operação/Bancos Filas e Modelos]]

## Riscos/Lacunas
- O kernel concentra muita composição e aumenta acoplamento estrutural.
- O frontend possui um client API muito largo, sugerindo bounded contexts ainda não totalmente separados.
