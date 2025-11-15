# Janus AI Architect — Documentação Completa (v1.0.0)

## Índice
- [1. Introdução](#1-introdução)
  - [1.1 Objetivo](#11-objetivo)
  - [1.2 Tecnologias](#12-tecnologias)
  - [1.3 Requisitos do Sistema](#13-requisitos-do-sistema)
- [2. Documentação Técnica](#2-documentação-técnica)
  - [2.1 Arquitetura do Sistema](#21-arquitetura-do-sistema)
  - [2.2 Diagramas de Fluxo por Módulo](#22-diagramas-de-fluxo-por-módulo)
  - [2.3 Funções Críticas (linha por linha)](#23-funções-críticas-linha-por-linha)
  - [2.4 Contratos: Parâmetros de Entrada/Saída](#24-contratos-parâmetros-de-entradasaída)
- [3. Instalação e Configuração](#3-instalação-e-configuração)
  - [3.1 Ambiente de Desenvolvimento](#31-ambiente-de-desenvolvimento)
  - [3.2 Configuração (.env) e Variáveis](#32-configuração-env-e-variáveis)
  - [3.3 Dependências](#33-dependências)
- [4. Manual de Uso](#4-manual-de-uso)
  - [4.1 Exemplos Práticos (API)](#41-exemplos-práticos-api)
  - [4.2 Casos de Uso com Código](#42-casos-de-uso-com-código)
  - [4.3 Erros Comuns e Soluções](#43-erros-comuns-e-soluções)
- [5. Padrões de Documentação](#5-padrões-de-documentação)
  - [5.1 Markdown e Nomenclatura](#51-markdown-e-nomenclatura)
  - [5.2 JSDoc/TSDoc (Frontend Angular)](#52-jsdoctsdoc-frontend-angular)
- [Anexos e Referências](#anexos-e-referências)

---

## 1. Introdução

### 1.1 Objetivo
Fornecer uma arquitetura cognitiva modular e resiliente para aplicações de IA em produção, com:
- API unificada (`/api/v1`) e contratos estáveis.
- Roteamento dinâmico de LLMs por custo/latência/qualidade com budgets, circuit breakers e cache.
- Memória semântica híbrida (grafo + vetor) e fluxos de aprendizagem.
- Observabilidade completa via métricas Prometheus e dashboards Grafana.

Referência: `README.md` e `docs/Architecture.md`.

### 1.2 Tecnologias
- Backend: Python 3.11, FastAPI, Uvicorn, LangChain.
- Datastores: Neo4j (grafo), Qdrant (vetorial).
- Mensageria: RabbitMQ (aio-pika robusto).
- Observabilidade: Prometheus, Grafana.
- Frontend: Angular 20 com Material/CDK.
- Empacotamento: Docker, docker-compose.

### 1.3 Requisitos do Sistema
- Windows, macOS ou Linux.
- Docker e Docker Compose (recomendado) OU Python 3.11 + pip e serviços externos (Neo4j, Qdrant, RabbitMQ, MySQL).
- Acesso opcional a chaves de provedores LLM (OpenAI, Google Gemini); suporte local via Ollama.

---

## 2. Documentação Técnica

### 2.1 Arquitetura do Sistema
- Composição em `janus/app/main.py`:
  - Inicialização paralela de Neo4j, Qdrant e RabbitMQ; construção de serviços e repositórios; arranque de workers; exposição de `/metrics` e middlewares. Referências: `janus/app/main.py:69-76,140-176,210-221`.
- Módulos principais (backend):
  - API (`janus/app/api/v1/endpoints/*`): endpoints para status, LLM, contexto, conhecimento, aprendizado, autonomia, observabilidade, workers.
  - Serviços (`janus/app/services/*`): orquestram lógica de negócios; ex.: `LLMService`, `AutonomyService`, `KnowledgeService`.
  - Repositórios (`janus/app/repositories/*`): integração com Neo4j/Qdrant/RabbitMQ/MySQL.
  - Núcleo (`janus/app/core/*`): LLM manager, memória, resiliência, monitoramento, ferramentas e workers.
  - Configuração (`janus/app/config.py`): variáveis, validações e políticas.
- Infra e ambientes: `docker-compose.yml` define API, Neo4j, Qdrant, Ollama, RabbitMQ, MySQL, Prometheus e Grafana.

Arquitetura (ASCII):
```
[Frontend Angular] --HTTP--> [FastAPI /api/v1]
     |                          |-- Services (LLM, Memory, Knowledge, Autonomy, Observability)
     |                          |-- Repos (Neo4j, Qdrant, RabbitMQ, MySQL)
     |                          |-- Core (LLM Router, Resilience, Monitoring)
     |                          |-- Workers (Consolidator, Harvester, Training)
     \--> /metrics ----> Prometheus ----> Grafana (dashboards)
```

### 2.2 Diagramas de Fluxo por Módulo
- LLM Router (invocação):
```
Client -> POST /api/v1/llm/invoke
  -> LLMService -> get_llm_client(role,priority)
      -> llm_manager.get_llm(...) [cache/CB/budget]
      -> LLMClient.send(prompt) [retry/circuit/timeout]
  <- resposta + métricas (latência, tokens, custo)
```
- Autonomy Loop (planner):
```
POST /api/v1/autonomy/start {config, plan?}
  -> validação de passos (allowlist/blocklist/schema)
  -> AutonomyService.start -> loop contínuo
      -> PolicyEngine valida execução de ferramentas
      -> métricas por ação/ciclo -> Prometheus
```
- Knowledge Consolidation:
```
POST /api/v1/knowledge/consolidate (batch/single)
  -> publish para fila janus.knowledge.consolidation
  -> KnowledgeConsolidator consome -> Neo4j/Qdrant
  -> métricas e stats (/knowledge/stats)
```
- Broker (RabbitMQ):
```
MessageBroker.connect -> publish/consume (robust)
  QoS, requeue on error, reconexão
  validações de política via Management API
```
- Observabilidade:
```
Instrumentator -> /metrics
LLM/Chat/Broker counters & histograms
Grafana dashboards janus-overview, janus-llm-performance
```

### 2.3 Funções Críticas (linha por linha)

1) `lifespan(app)` — inicialização/encerramento do sistema
- Declaração e setup: `janus/app/main.py:69-76`
  - Configura logging e cria gerenciador de contexto assíncrono.
- Infra init paralela: `janus/app/main.py:72-79`
  - `initialize_graph_db`, `initialize_memory_db`, `initialize_broker` em `asyncio.gather`.
- Construção de grafo de dependências: `janus/app/main.py:83-114`
  - Instancia repositórios e serviços (LLM, memory, knowledge, autonomy, observability, chat, tools, assistant).
- Warm de pool LLM (opcional): `janus/app/main.py:115-121`
  - Pré-aquecimento conforme `LLM_POOL_WARM_PROVIDERS`.
- Health Monitoring: `janus/app/main.py:141-149`
  - `get_health_monitor`, `get_poison_pill_handler`; inicia monitoramento periódico.
- Workers: `janus/app/main.py:153-175`
  - Instancia `KnowledgeConsolidator`, `DataHarvester` e inicia consumidor de treinamento.
- Shutdown: `janus/app/main.py:179-199`
  - Para workers, cancela consumidor, encerra monitor e fecha conexões (Neo4j/Qdrant/broker).

Entradas/Saídas:
- Entrada: `FastAPI app`.
- Saída: recursos e serviços inicializados; workers ativos enquanto app está vivo.

2) `get_llm(...)` — seleção de LLM com cache/CB/budget
- Config overrides e exclusões: `janus/app/core/llm/llm_manager.py:551-626`.
- Cache key e pool local: `janus/app/core/llm/llm_manager.py:629-635`.
- Mapa por papel para modelo local: `janus/app/core/llm/llm_manager.py:637-643`.
- Estratégia `LOCAL_ONLY`: `janus/app/core/llm/llm_manager.py:645-675`.
- Catálogo de nuvem: `janus/app/core/llm/llm_manager.py:677-696`.
- Seleção adaptativa (FAST_AND_CHEAP/HIGH_QUALITY): `janus/app/core/llm/llm_manager.py:698-835`.
- Fallback local: `janus/app/core/llm/llm_manager.py:836-864`.

Entradas: `role`, `priority`, `cache_key?`, `exclude_providers?`, `config?`. Saída: instância `BaseChatModel` adequada.

3) `LLMClient.send(prompt, timeout_s?)` — invocação resiliente com custo/tokens
- Validação de prompt: `janus/app/core/llm/llm_manager.py:1006-1009`.
- Timeout auto-tuning e circuit breaker: `janus/app/core/llm/llm_manager.py:1011-1025`.
- Limite dinâmico de geração/cap/fallback local: `janus/app/core/llm/llm_manager.py:1034-1069`.
- Execução síncrona com executor: `janus/app/core/llm/llm_manager.py:1070-1075`.
- Métricas de latência e tokens: `janus/app/core/llm/llm_manager.py:1076-1095`.
- Atualização de gastos e EMA de tokens esperados: `janus/app/core/llm/llm_manager.py:1096-1145`.
- Penalizações por custo/falha e erros tratados: `janus/app/core/llm/llm_manager.py:1147-1216`.
- Sanitização de identidade: `janus/app/core/llm/llm_manager.py:951-997`.

Entradas: `prompt`, `timeout_s?`. Saída: `str` resposta textual sanitizada.

4) `MessageBroker.publish(queue_name, message, ...)`
- Conexão robusta e fallback: `janus/app/core/infrastructure/message_broker.py:30-61`.
- Declaração de fila com argumentos esperados: `janus/app/core/infrastructure/message_broker.py:91-100,124-144`.
- Serialização (msgpack/json) e headers: `janus/app/core/infrastructure/message_broker.py:96-121`.
- Publicação e métricas: `janus/app/core/infrastructure/message_broker.py:121-123`.

Entradas: `queue_name`, `message`, `priority?`, `headers?`, `expiration?`, `use_msgpack?`. Saída: mensagem publicada (ou ignorada se offline).

5) `system_status.get_services_health(...)`
- Coleta health dos serviços: `janus/app/api/v1/endpoints/system_status.py:61-100`.
- Heurística de memória (MB → status): `janus/app/api/v1/endpoints/system_status.py:98-107`.
- Montagem de payload `ServiceHealthResponse`: `janus/app/api/v1/endpoints/system_status.py:108-135`.

Entradas: serviços via `Depends`. Saída: `services[]` com status e texto métrico.

6) Validação de plano (Autonomy)
- Validação de shape, listas e args schema: `janus/app/api/v1/endpoints/autonomy.py:42-89`.
- Atualização de plano e status: `janus/app/api/v1/endpoints/autonomy.py:156-185`.

Entradas: `plan[]`, `allowlist/blocklist`. Saída: erros 422 detalhados ou confirmação de atualização.

### 2.4 Contratos: Parâmetros de Entrada/Saída
- `POST /api/v1/llm/invoke`
  - Entrada: `{ prompt: string, role: string, priority: string, timeout_seconds?: number, user_id?: string, project_id?: string }` (`janus/app/api/v1/endpoints/llm.py:20-27`).
  - Saída: `{ response, provider, model, role, input_tokens?, output_tokens?, cost_usd? }` (`janus/app/api/v1/endpoints/llm.py:28-36`).
- `GET /api/v1/system/status`
  - Saída: `StatusResponse` com app/env/uptime/performance/config (`janus/app/api/v1/endpoints/system_status.py:19-30`).
- `GET /api/v1/system/health/services`
  - Saída: `ServiceHealthResponse.services[]` (`janus/app/api/v1/endpoints/system_status.py:31-39,108-135`).
- `POST /api/v1/autonomy/start`
  - Entrada: `AutonomyStartRequest` com plano opcional (`janus/app/api/v1/endpoints/autonomy.py:18-29`).
  - Saída: `{ status: "started", interval_seconds }` ou 400 se já ativo.
- `PUT /api/v1/autonomy/plan`
  - Entrada: `{ plan: Array<{ tool: string, args: object }> }` (`janus/app/api/v1/endpoints/autonomy.py:38-41`).
  - Saída: `{ status: "updated", steps_count }`.
- Broker Management (interno): `MessageBroker.get_queue_info/validate/reconcile` com retorno de políticas e mismatches (`janus/app/core/infrastructure/message_broker.py:146-161,298-335,365-400`).

---

## 3. Instalação e Configuração

### 3.1 Ambiente de Desenvolvimento
- Docker Compose (recomendado):
  1. Crie `.env` em `janus/config/.env` com variáveis (ver seção 3.2).
  2. Execute `docker-compose up -d` na raiz do projeto.
  3. Aguarde readiness:
     - API: `http://localhost:8000/readyz`
     - Docs/OpenAPI: `http://localhost:8000/docs`
     - Grafana: `http://localhost:3000` (admin/admin)
     - Neo4j: `http://localhost:7474`
     - Qdrant UI: `http://localhost:6333/dashboard`
     - RabbitMQ: `http://localhost:15672`
- Local sem Docker:
  1. Suba Neo4j, Qdrant, RabbitMQ e MySQL localmente.
  2. Python: `py -3.11 -m venv .venv && .venv\Scripts\activate` (Windows) ou `python3.11 -m venv .venv && source .venv/bin/activate` (Unix).
  3. Instale deps: `pip install -r janus/requirements.txt`.
  4. Exporte variáveis `.env` conforme 3.2.
  5. Inicie: `uvicorn app.main:app --host 0.0.0.0 --port 8000` dentro de `janus/`.

### 3.2 Configuração (.env) e Variáveis
- Principais variáveis em `janus/app/config.py`:
  - App: `APP_NAME`, `APP_VERSION`, `ENVIRONMENT`.
  - LLM: `OPENAI_API_KEY`, `GEMINI_API_KEY`, `OLLAMA_HOST`, `LLM_MAX_COST_PER_REQUEST_USD`, `LLM_EXPECTED_KTOKENS_BY_ROLE`.
  - Datastores: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`; `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_API_KEY?`.
  - Broker: `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, políticas de filas.
  - Observabilidade: `LANGCHAIN_TRACING_V2`, `PUBLIC_API_MINIMAL`, `SERVE_STATIC_FILES`.
- Exemplo mínimo:
```
APP_NAME=Janus
APP_VERSION=1.0.0
ENVIRONMENT=development
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
QDRANT_HOST=qdrant
QDRANT_PORT=6333
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=janus
RABBITMQ_PASSWORD=janus_pass
OLLAMA_HOST=http://ollama:11434
OPENAI_API_KEY=
GEMINI_API_KEY=
```

### 3.3 Dependências
- Backend (`janus/requirements.txt`): `fastapi`, `uvicorn[standard]`, `pydantic-settings`, `neo4j>=5.15`, `qdrant-client`, `langchain`, `langchain-openai`, `langchain-google-genai`, `langchain-ollama`, `aio-pika`, `RestrictedPython`, `docker`, `psutil`, `prometheus-client`, `transformers>=4.45.2,<4.50.0`, `onnxruntime`, `cryptography`, `pymysql`.
- Frontend (`front/package.json`): Angular 20, Material/CDK, rxjs, ng2-charts.

---

## 4. Manual de Uso

### 4.1 Exemplos Práticos (API)
- Listar ferramentas:
```
curl -s http://localhost:8000/api/v1/tools
```
- Invocar LLM (flash/cuidados de custo):
```
curl -s -X POST http://localhost:8000/api/v1/llm/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explique a arquitetura do Janus em 3 tópicos",
    "role": "orchestrator",
    "priority": "fast_and_cheap"
  }'
```
- Iniciar autonomia com plano vazio (planner ativo):
```
curl -s -X POST http://localhost:8000/api/v1/autonomy/start \
  -H "Content-Type: application/json" \
  -d '{
    "interval_seconds": 20,
    "risk_profile": "balanced",
    "auto_confirm": true,
    "max_actions_per_cycle": 5,
    "max_seconds_per_cycle": 30
  }'
```
- Consolidação de conhecimento (batch):
```
curl -s -X POST http://localhost:8000/api/v1/knowledge/consolidate \
  -H "Content-Type: application/json" \
  -d '{"mode": "batch", "limit": 5, "min_score": 0.0}'
```
- Métricas Prometheus:
```
curl -s http://localhost:8000/metrics | head -n 50
```

### 4.2 Casos de Uso com Código
- Python (cliente interno de LLM):
```python
from app.core.llm.llm_manager import get_llm_client, ModelRole, ModelPriority

client = get_llm_client(role=ModelRole.ORCHESTRATOR, priority=ModelPriority.FAST_AND_CHEAP)
resp = client.send("Liste 3 objetivos do Janus")
print(resp)
```
- Angular (serviço Janus API, TSDoc aplicado):
```ts
/**
 * Obtém status consolidado do sistema.
 * @returns Promise com payload de status.
 */
export async function getSystemStatus(baseUrl: string): Promise<any> {
  const res = await fetch(`${baseUrl}/api/v1/system/status`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
```
- E2E (coleção .http sugerida dentro do projeto): veja `janus/http/E2E-Production-Scenario.http`.

### 4.3 Erros Comuns e Soluções
- `Qdrant 400 Format error in JSON body` → IDs inválidos; use UUID ou inteiro sem sinal (ver release notes).
- `SyntaxError: f-string expression part cannot include a backslash` → corrigir f-strings; evitar `\n` em expressões; pré-calcular (`docs/Release-Notes-1.0.0.md`).
- Broker offline → API inicia modo degradado; publicação ignorada; checar `rabbitmq` e reexecutar; ver `janus/app/core/infrastructure/message_broker.py:86-90`.
- Circuit breaker aberto no LLM → aguardar recovery ou resetar via endpoint `POST /api/v1/llm/circuit-breakers/{provider}/reset`.

---

## 5. Padrões de Documentação

### 5.1 Markdown e Nomenclatura
- Use títulos com colchetes numéricos e subtítulos com hierarquia clara.
- Nomenclatura consistente com o código (snake_case no Python, PascalCase/kebab-case no Angular).
- Referencie código com `file_path:line_number` para navegação direta.

### 5.2 JSDoc/TSDoc (Frontend Angular)
- Diretriz:
  - Comentar serviços e componentes com breves descrições; documentar parâmetros e retorno.
  - Exemplo aplicado ao componente de página (`front/src/app/pages/documentacao/documentacao.ts:1-12`):
```ts
/**
 * Página de Documentação do Janus.
 * Exibe links e referências úteis para usuários e contribuidores.
 */
export class Documentacao {}
```
- Serviços (`front/src/app/services/janus-api.service.ts`):
```ts
/**
 * JanusApiService: cliente para endpoints do backend Janus.
 * @method getSystemHealth Resumo de saúde de serviços.
 * @method invokeLLM Invoca LLM com parâmetros controlados.
 */
```

---

## Anexos e Referências
- Código:
  - Composição e startup: `janus/app/main.py:69-76,140-176,240-256`
  - Status do sistema: `janus/app/api/v1/endpoints/system_status.py:43-54,56-135`
  - LLM manager e métricas: `janus/app/core/llm/llm_manager.py:23-43,144-169,539-864,1005-1166`
  - Broker e filas: `janus/app/core/infrastructure/message_broker.py:69-123,258-335`
  - Configuração: `janus/app/config.py:74-114,135-183,197-241`
  - Autonomy: `janus/app/api/v1/endpoints/autonomy.py:116-172,190-234`
- Ambientes e dashboards:
  - Compose de serviços: `docker-compose.yml`
  - Grafana dashboards: `janus/grafana/dashboards/*.json`
- Guias existentes complementares: `docs/Architecture.md`, `docs/Configuration.md`, `docs/Usage.md`, `docs/Examples.md`, `docs/Troubleshooting.md`, `docs/Release-Notes-1.0.0.md`.

---

> Esta documentação foi gerada para refletir o estado atual do código (v1.0.0) e inclui referências diretas aos arquivos e linhas para consulta rápida.
