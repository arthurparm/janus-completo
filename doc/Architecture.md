# Arquitetura do Sistema

Este documento descreve a arquitetura do Janus AI Architect, organizada para garantir clareza, consistência e escalabilidade. O sistema adota um paradigma multiagente com padrão Orquestrador-Trabalhador, API assíncrona, barramento de mensagens, memória hierárquica e observabilidade profunda.

## Visão Geral

- API (`FastAPI`) expõe endpoints REST sob ` /api/v1`.
- Serviços de domínio coordenam lógica (LLM, Ferramentas, Memória, Aprendizado).
- Núcleo cognitivo provê roteamento de LLMs, memória, reflexões e meta-agente.
- Workers assíncronos processam tarefas de treinamento e consolidação.
- Infraestrutura desacoplada via RabbitMQ, Neo4j (grafo) e Qdrant (vetores).
- Observabilidade com métricas Prometheus e dashboards Grafana.

## Componentes Principais

- API e Endpoints: `app/main.py`, `app/api/v1/endpoints/*.py`
  - Exemplos: `learning.py` (aprendizado), `tools.py` (ferramentas), `llm.py` (LLM).
- Serviços de Domínio: `app/services/*`
  - `learning_service.py`, `tool_service.py`, `llm_service.py`, `knowledge_service.py`.
- Repositórios: `app/repositories/*`
  - Integrações e persistência (Neo4j/Qdrant), cache e circuit breakers.
- Núcleo Cognitivo: `app/core/*`
  - `llm_manager`, memória semântica, Reflexion, meta-agente, resilience utils.
- Workers: `app/core/workers/*`
  - `neural_training_worker.py`, `data_harvester.py`, consolidadores assíncronos.
- Infraestrutura: `app/core/infrastructure/*`
  - `message_broker.py` (RabbitMQ), `health_monitor.py`, rate limiting.
- Configuração: `app/config.py`
  - Padrões, validações e variáveis para todos os módulos.

## Fluxos Críticos

1) Ferramentas Dinâmicas (Action Module)
- Endpoints: `/api/v1/tools` (listar/detalhes), `/create/from-function`, `/create/from-api`, `DELETE /{tool_name}`.
- Serviço registra e valida ferramentas, com categorias, permissões, tags e rate limit.
- Memória semântica registra novas "habilidades" para uso futuro.

2) Aprendizado (Neural Training)
- Endpoints: `/harvest`, `/train`, `/training/status`, `/models`, `/evaluate`, `/stats`, `/experiments`.
- `publish_neural_training_task` envia tarefas para `janus.neural.training` (RabbitMQ).
- Worker `process_neural_training_task` executa treinamento; atualiza status, modelos e experimentos.

3) Memória Semântica (Semantic Memory / Knowledge)
- Consolidação de conhecimento, indexação e consultas relacionadas.
- Armazenamento: Neo4j (grafo de conceitos) e Qdrant (embeddings).

4) Roteamento de LLMs
- Roteia chamadas entre OpenAI/Gemini/Ollama por prioridade e custo.
- Circuit Breakers por provedor; cache de respostas; quotas e budgets por usuário/projeto.
- Fallback para modelo local ("cérebro soberano") quando cloud indisponível.

## Barramento de Mensagens (RabbitMQ)

- Fila principal de treinamento: `janus.neural.training` (Enum `QueueName.NEURAL_TRAINING`).
- Política: filas duráveis, reintentos com backoff e DLQ (quando configurado).
- `message_broker.py` gerencia conexão, declaração de filas e validação de política.

## Persistência e Memória

- Neo4j: grafo de entidades/conceitos; queries e consolidação.
- Qdrant: vetor semântico (similaridade) e indexação de embeddings.
- Memória Hierárquica: curto prazo (TTL), episódica (eventos), semântica (conhecimento consolidado).
- Quotas: limites por origem para itens/bytes e redaction de PII.

## Observabilidade e Resiliência

- Métricas: `/metrics` (Prometheus), health/liveness/readiness em `/healthz`, `/livez`, `/readyz`.
- Circuit Breakers e retries com backoff exponencial em provedores e integrações.
- Dashboards: `dashboards/janus_component_resilience_dashboard.json` (Grafana).
- Logs estruturados por componente e workers.

## Convenções e Versionamento

- Prefixo de API: ` /api/v1` com tags por domínio (LLM, Tools, Learning, Knowledge).
- Padrões de DTOs Pydantic para requests/responses; validações e erros claros.
- Rate limiting por IP/API key; orçamentos por usuário/projeto para LLMs.
- Configuração centralizada via `.env` carregada por `app/config.py`.

## Referências de Código

- Endpoints: `app/api/v1/endpoints/learning.py`, `tools.py`, `llm.py`
- Serviços: `app/services/learning_service.py`, `tool_service.py`, `llm_service.py`
- Workers: `app/core/workers/neural_training_worker.py`, `data_harvester.py`
- Sistema de Treino: `app/core/workers/neural_training_system.py`
- Infra: `app/core/infrastructure/message_broker.py`, `app/core/monitoring/health_monitor.py`
- Configs: `app/config.py`, `app/models/schemas.py`