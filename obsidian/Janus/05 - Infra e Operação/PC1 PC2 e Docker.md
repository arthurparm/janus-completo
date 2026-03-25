---
tipo: operacao
dominio: infra
camada: deploy
fonte-de-verdade: codigo
status: ativo
---

# PC1 PC2 e Docker

## Objetivo
Registrar a topologia executável de deploy do Janus a partir dos compose files e do bootstrap real do backend.

## Responsabilidades
- Explicar o que cada host realmente sustenta.
- Separar dependência local, dependência remota e tolerância a degradação.
- Tornar explícitos boot, readiness, restart policy, variáveis críticas e critério mínimo de operação.

## Entradas
- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`
- `backend/app/main.py`
- `backend/app/core/kernel.py`
- `backend/app/db/graph.py`
- `backend/app/core/memory/memory_core.py`
- `backend/app/core/memory/providers/qdrant_provider.py`
- `backend/app/core/infrastructure/message_broker.py`

## Saídas
- Mapa operacional do que roda em cada host.
- Contrato de boot e de prontidão da stack.
- Lista de variáveis sem as quais o deploy não fecha.
- Riscos concretos do modo degradado.

## Dependências
- [[01 - Visão do Sistema/Topologia Runtime]]
- [[02 - Backend/Kernel e Startup]]
- [[05 - Infra e Operação/Bancos Filas e Modelos]]

## Topologia executável

| Host | Serviço | Papel no runtime | Portas publicadas | Restart |
| --- | --- | --- | --- | --- |
| PC1 | `janus-api` | API FastAPI, bootstrap do `Kernel`, workers orquestrados e contrato HTTP | `8000:8000` | `unless-stopped` |
| PC1 | `janus-frontend` | UI Angular | `${FRONTEND_PORT:-4300}:4300` | `unless-stopped` |
| PC1 | `postgres` | persistência SQL/transacional | `127.0.0.1:5432:5432` | `unless-stopped` |
| PC1 | `redis` | cache, pub/sub e apoio a serviços internos | `127.0.0.1:6379:6379` | `unless-stopped` |
| PC1 | `rabbitmq` | broker de tarefas e filas | `127.0.0.1:5672:5672`, `127.0.0.1:15672:15672` | `unless-stopped` |
| PC2 | `neo4j` | grafo e ontologias | `7474:7474`, `7687:7687` | `unless-stopped` |
| PC2 | `qdrant` | memória vetorial episódica | `6333:6333` | `unless-stopped` |
| PC2 | `ollama` | inferência local | `11434:11434` | `unless-stopped` |
| PC2 | `ollama-model-init` | pull de modelos configurados | sem porta pública | `no` |

## Persistência por host

### PC1
- `janus_postgres_data`
- `janus_redis_data`
- `janus_rabbitmq_data`
- `janus_app_data`
- `janus_workspace`

### PC2
- `janus_neo4j_data`
- `janus_qdrant_data`
- `janus_ollama_data`

## Boot e dependências reais

### Grafo de dependência do Compose
- `janus-api` só espera `postgres`, `redis` e `rabbitmq` ficarem `healthy`.
- `janus-frontend` só espera `janus-api` ficar `healthy`.
- `neo4j`, `qdrant` e `ollama` não participam do `depends_on` do PC1.
- `ollama-model-init` só começa quando `ollama` fica `healthy`.

### Readiness real do `janus-api`
- O processo HTTP só começa a responder depois do `lifespan` terminar.
- O `lifespan` executa, em ordem:
  - validação de segredos críticos quando `ENVIRONMENT=production`;
  - `Kernel.startup()`;
  - `init_graph()` do LangGraph/checkpointer;
  - carga de prompts globais do banco, tolerante a falha;
  - publicação de serviços em `app.state`;
  - inicialização opcional de usuário de sistema e rate limits;
  - start de workers orquestrados se `START_ORCHESTRATOR_WORKERS_ON_STARTUP=true`;
  - agendamento não bloqueante do self-study check.

### O que pode bloquear o boot
- `POSTGRES`, `REDIS` e `RABBITMQ` precisam passar pelos healthchecks do Compose antes do container `janus-api` ser criado.
- Dentro do `Kernel`, `initialize_graph_db()`, `initialize_memory_db()`, `initialize_broker()` e `RedisManager.initialize()` são aguardados em paralelo.
- `initialize_memory_db()` pode alongar muito o boot quando Qdrant está fora: o `QdrantProvider.initialize()` tenta até 20 vezes com backoff exponencial antes de assumir modo offline.

### O que não derruba o boot, mas degrada o runtime
- Neo4j indisponível coloca o grafo em modo offline sem abortar o processo.
- RabbitMQ indisponível deixa o broker offline sem abortar o processo.
- Redis falhando no `ping` inicial não aborta a API; o client passa a falhar em uso.
- Falha ao carregar prompts globais não aborta o processo.
- Falha ao iniciar workers de background registra erro e pode inserir `background_workers` como healthcheck crítico, mas não derruba o processo.
- `INIT_MAS_AGENTS_ON_STARTUP=false` no deploy do PC1 significa que o sistema multiagente pode subir com zero agentes criados e ainda assim manter a API de pé.

## Fronteira PC1 x PC2
- `backend/app/config.py` assume um modo local por default:
  - `NEO4J_URI=bolt://neo4j:7687`
  - `QDRANT_HOST=qdrant`
  - `OLLAMA_HOST=http://ollama:11434`
- `docker-compose.pc1.yml` transforma isso em deploy distribuído ao exigir:
  - `NEO4J_URI`
  - `QDRANT_HOST`
  - `QDRANT_API_KEY`
  - `OLLAMA_HOST`
- O contrato entre hosts é imposto por variável de ambiente, não por descoberta automática nem por healthcheck cross-host do Compose.

## Healthchecks de container

| Serviço | Probe | O que garante | O que não garante |
| --- | --- | --- | --- |
| `janus-api` | `curl -f http://localhost:8000/health` | a API respondeu HTTP | não valida Neo4j, Qdrant, Redis, RabbitMQ nem workers |
| `janus-frontend` | `wget -qO- http://127.0.0.1:4300/` | a UI serviu HTML | não valida backend |
| `postgres` | `pg_isready` | socket SQL pronto | não valida schema lógico |
| `redis` | `redis-cli ping` | Redis aceitando ping | não valida carga nem pub/sub |
| `rabbitmq` | `rabbitmq-diagnostics -q ping` | nó do broker vivo | não valida filas e policies |
| `neo4j` | `cypher-shell 'RETURN 1'` | autenticação e query básica | não valida ontologia e indexação |
| `qdrant` | abertura de TCP em `6333` | porta aberta | não valida coleção nem API key em uso real |
| `ollama` | `ollama list` | runtime do Ollama respondeu | não garante que os modelos esperados já foram puxados |

## Variáveis críticas

### Obrigatórias no PC1 para o container existir
- `AUTH_JWT_SECRET`
- `POSTGRES_PASSWORD`
- `RABBITMQ_PASSWORD`
- `NEO4J_URI`
- `NEO4J_PASSWORD`
- `QDRANT_HOST`
- `QDRANT_API_KEY`
- `OLLAMA_HOST`

### Obrigatórias no PC2 para os serviços existirem
- `NEO4J_PASSWORD`
- `QDRANT_API_KEY`

### Variáveis que alteram comportamento operacional
- `ENVIRONMENT`
- `JANUS_BUILD_REF`
- `CORS_ALLOW_ORIGINS`
- `START_ORCHESTRATOR_WORKERS_ON_STARTUP`
- `AUTO_INDEX_ON_STARTUP`
- `INIT_MAS_AGENTS_ON_STARTUP`
- `AUTONOMY_SELF_STUDY_LOCAL_ONLY`
- `OLLAMA_ORCHESTRATOR_MODEL`
- `OLLAMA_CODER_MODEL`
- `OLLAMA_CURATOR_MODEL`
- `OLLAMA_AUTO_PULL_MODELS`

### Risco operacional importante
- Se `PUBLIC_API_KEY` for configurada, o middleware global protege `/health`, mas o healthcheck do container `janus-api` continua chamando `/health` sem header.
- Nesse cenário, a API pode continuar funcional para clientes autenticados e ainda assim o container passar a ficar `unhealthy`.
- O endpoint que permanece explicitamente fora dessa proteção é `/healthz`.

## Domínios por host e banco

### PC1 / Postgres
- identidade, sessão e mensagens persistidas;
- autonomia, pending actions, outbox, quotas diárias de tool, prompts e configuração dinâmica persistida;
- metadados documentais e `knowledge_spaces`;
- checkpointer do `graph_orchestrator`.

### PC1 / Redis
- rate limit;
- Pub/Sub de hot-reload;
- budgets e cotas temporárias de spend LLM.

### PC2 / Qdrant
- memória episódica global;
- contexto vetorial de chat por usuário;
- chunks documentais por usuário;
- memórias de preferência e procedural;
- segredos e consolidação vetorial de knowledge spaces.

### PC2 / Neo4j
- grafo de experiências e entidades;
- code graph;
- self-memory;
- projeção estrutural de knowledge spaces.

## O que cada host sustenta
- PC1 sustenta disponibilidade HTTP, frontend, fila, cache e banco transacional.
- PC2 sustenta capacidades de grafo, memória vetorial e inferência local.
- Se PC1 cair, o produto deixa de responder.
- Se PC2 cair, a API pode continuar `up` e até `healthy` no Compose, mas perde partes críticas do comportamento cognitivo.

## Critério mínimo de operação por host
- PC1 só é minimamente utilizável quando `janus-api`, `janus-frontend`, `postgres`, `redis` e `rabbitmq` estão `healthy`.
- PC2 só é minimamente utilizável quando `neo4j`, `qdrant` e `ollama` estão `healthy`.
- `ollama-model-init` não precisa permanecer rodando, mas precisa ter concluído sem impedir a disponibilidade dos modelos exigidos pelo deploy.
- A stack distribuída só fecha de verdade quando PC1 enxerga os endpoints configurados em `NEO4J_URI`, `QDRANT_HOST:QDRANT_PORT` e `OLLAMA_HOST`.

## Validação prática no PC TESTE em 25 de março de 2026
- `janus_api`, `janus_frontend`, `janus_postgres`, `janus_redis` e `janus_rabbitmq` estavam `healthy`.
- O `janus_api` estava configurado com:
  - `NEO4J_URI=bolt://100.88.71.49:7687`
  - `QDRANT_HOST=100.88.71.49`
  - `OLLAMA_HOST=http://100.88.71.49:11434`
  - `START_ORCHESTRATOR_WORKERS_ON_STARTUP=true`
  - `AUTO_INDEX_ON_STARTUP=true`
  - `INIT_MAS_AGENTS_ON_STARTUP=false`
- A validação prática mostrou que container saudável e stack funcional não são a mesma coisa:
  - `/healthz` e `/health` respondiam `ok`;
  - `/api/v1/observability/health/system` retornava `healthy`;
  - o componente crítico `episodic_memory_qdrant` aparecia `degraded` com fallback memory-only ativo.

## Arquivos-fonte
- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/core/kernel.py`
- `backend/app/db/graph.py`
- `backend/app/core/memory/providers/qdrant_provider.py`
- `backend/app/core/infrastructure/message_broker.py`

## Fluxos relacionados
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]
- [[07 - Glossário e Inventários/Inventário de Integrações Externas]]

## Riscos/Lacunas
- O Compose de PC1 não expressa readiness cross-host.
- O modo degradado de Neo4j, Redis e RabbitMQ é tolerado pelo processo, então a ausência dessas dependências pode não aparecer em `/health`.
- O Qdrant é a dependência remota com maior impacto de boot por causa do retry exponencial no startup.
- O healthcheck do `janus-api` fica incompatível com `PUBLIC_API_KEY` se não for trocado para `/healthz` ou enriquecido com header.
