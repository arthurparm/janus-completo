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
- `Kernel` com DI manual.
- `settings` de `backend/app/config.py` definindo flags, defaults e validadores usados no boot.
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
- Orquestração interna: `lifespan`, `Kernel`, serviços, repositórios e dois planos de workers (`kernel.workers` e `app.state.orchestrator_workers`).
- Persistência operacional: Postgres, Redis, RabbitMQ.
- Persistência cognitiva: Neo4j e Qdrant.
- Inferência: provedores cloud e Ollama local.

## Plano de dados por store
- Postgres:
  - fonte de verdade transacional para identidade, chat persistido, autonomia, prompts, outbox, manifests e knowledge spaces
- Redis:
  - coordenação efêmera para rate limit, hot-reload de configuração e spend/quota temporária
- RabbitMQ:
  - transporte assíncrono para workers e fan-out operacional
- Qdrant:
  - persistência vetorial para memória episódica, chat por usuário, documentos, preferências, regras e segredos
- Neo4j:
  - persistência estrutural para entidades, experiências consolidadas, code graph, self-memory e projeções estruturais de knowledge spaces

## Separação correta entre controle e dados
- Plano de controle:
  - `main.py`, `lifespan`, `Kernel`, repositórios SQL, scheduler, workers e serviços que decidem quando persistir ou publicar trabalho
- Plano de dados:
  - Postgres e Redis em PC1
  - Neo4j e Qdrant em PC2
  - RabbitMQ como backbone de tarefas assíncronas
- Consequência:
  - a separação continua válida conceitualmente, mas o boot do API não bloqueia só dependências locais de PC1
  - pelo código, `graph_db`, `memory_db`, broker e Redis entram juntos no caminho crítico de `_init_infrastructure()`, então falhas de Neo4j/Qdrant também podem impedir o serving inicial
  - a degradação parcial acontece mais tarde, em serviços opcionais e subsistemas de background, não no núcleo mínimo de infraestrutura

## Leituras centrais
- `main.py` monta a superfície FastAPI em tempo de importação: logging, tracing, middlewares, exception handlers, routers e endpoints utilitários.
- O `lifespan` coordena a sequência de boot: chama o gate de segredos, executa `Kernel.startup()`, inicializa graph/prompt loading, publica dependências selecionadas em `app.state` e ainda monta serviços extras como `AutonomyAdminService`.
- O `Kernel` compõe repositórios e serviços manualmente, sobe a maior parte do runtime assíncrono de fundo e mantém handles internos que não são publicados em `app.state`.
- `config.py` influencia diretamente o boot por defaults como `AUTO_INDEX_ON_STARTUP=True`, `START_ORCHESTRATOR_WORKERS_ON_STARTUP=True`, `FIREBASE_ENABLED=False`, `SERVE_STATIC_FILES=False` e por validadores como o preenchimento automático de `CORS_ALLOW_ORIGINS` em ambiente não produtivo.
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
- O runtime assíncrono fica dividido entre workers rastreados pelo `Kernel`, tasks do orquestrador em `app.state` e tarefas fire-and-forget sem registry única de shutdown.
- `PUBLIC_API_KEY` é consultado dinamicamente em `main.py`, sem aparecer como campo tipado em `AppSettings`, o que enfraquece a previsibilidade da superfície de configuração.
- O frontend possui um client API muito largo, sugerindo bounded contexts ainda não totalmente separados.
- `KnowledgeSpace` e chat grounded são domínios compostos: dependem de Postgres para controle, de Qdrant para recuperação e, em partes do fluxo, de Neo4j para estrutura.
