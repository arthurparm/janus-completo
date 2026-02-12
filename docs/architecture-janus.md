# Arquitetura - Backend (`janus`)

## Escopo

API e runtime agentico responsavel por conversa, memoria, RAG, automacao e observabilidade do sistema Janus.

## Stack

- Python 3.11
- FastAPI + Uvicorn
- SQLAlchemy (async + sync), Postgres/pgvector
- Neo4j, Qdrant, Redis, RabbitMQ
- LangChain + provedores LLM (OpenRouter/OpenAI/Gemini/Ollama/DeepSeek/xAI)
- Prometheus/Grafana/OpenTelemetryC

## Estrutura Arquitetural

### 1. API Layer

- `app/main.py`: bootstrap, middlewares, lifecycle e montagem de rotas
- `app/api/v1/router.py`: composicao dos routers
- `app/api/v1/endpoints/*`: 39 modulos de endpoint, 229 operacoes HTTP

### 2. Service Layer

- `app/services/*`: regras de negocio (chat, llm, memory, observability, autonomy, tool execution, deployment etc.)

### 3. Repository Layer

- `app/repositories/*`: encapsula persistencia de dominio

### 4. Core Runtime

- `app/core/workers/*`: workers assinc para tarefas de longa duracao e autonomia
- `app/core/llm/*`: roteamento, resiliencia, cache e politicas de custo
- `app/core/memory/*`: grafo, vetores, memoria generativa e protecao
- `app/core/infrastructure/*`: auth, rate-limit, broker, tracing, sandbox

### 5. Data Layer

- SQLAlchemy models em `app/models/*`
- DB adapters em `app/db/*`
- Mecanismos de conhecimento em Neo4j + Qdrant + Postgres

## Padrao de Processamento

- Requisicoes sincronas: endpoint -> service -> repository -> resposta
- Processos assinc/event-driven: endpoint/service publica em fila -> worker processa -> estado/evento atualizado

## Integracoes de Infra

- Broker: RabbitMQ (`janus.*` queues)
- Cache/ratelimit: Redis
- Knowledge graph: Neo4j
- Vector search: Qdrant
- Observabilidade: Prometheus, Grafana, OTEL collector

## Seguranca e Governanca

- API Key global opcional
- JWT/local auth + consent/pending actions
- trilha de auditoria (`audit_events`)
- limites de budget e quotas por usuario/projeto

## Riscos e Observacoes

- Arquivo SQL em `janus/sql/init/01_create_config_tables.sql` usa sintaxe `AUTO_INCREMENT` (estilo MySQL), enquanto runtime principal usa Postgres/SQLAlchemy. Requer alinhamento para evitar drift de schema.
- `config.py` e extenso (muitas flags e custos); ganho potencial ao separar por domnios de configuracao.

---

_Gerado pelo workflow BMAD `document-project`_
