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

## Alocação de Recursos e Dimensionamento

### Recursos por Serviço (PC1 - Host de Aplicação)

| Serviço | CPU | RAM | Justificativa Operacional |
| --- | --- | --- | --- |
| `janus-api` | 4.0 cores | 4 GB | FastAPI principal com workers orquestrados, processamento de IA e gerenciamento de estado |
| `janus-frontend` | 2.0 cores | 1.5 GB | Angular 20 com hot-reload, otimizado para desenvolvimento e produção |
| `postgres` | 2.0 cores | 1.5 GB | PostgreSQL com pgvector, queries transacionais e operações de indexação |
| `redis` | 1.0 core | 384 MB | Cache de alta performance, rate limiting e pub/sub para hot-reload |
| `rabbitmq` | 1.5 cores | 768 MB | Message broker com gestão de filas complexas e persistência |

**Total PC1**: 10.5 cores CPU + 8.6 GB RAM (recomendado: 12 cores / 16 GB)

### Recursos por Serviço (PC2 - Host de Infraestrutura)

| Serviço | CPU | RAM | Justificativa Operacional |
| --- | --- | --- | --- |
| `neo4j` | 10.0 cores | 24 GB | Graph database com heap 2-8GB + pagecache 12GB, complexidade de traversals |
| `qdrant` | 6.0 cores | 12 GB | Vector database para embeddings, busca semântica e indexação HNSW |
| `ollama` | 12.0 cores | 24 GB | Engine LLM local com GPU, múltiplos modelos carregados simultaneamente |
| `ollama-model-init` | - | - | Container efêmero para inicialização, não requer recursos dedicados |

**Total PC2**: 28.0 cores CPU + 60 GB RAM (recomendado: 32 cores / 64 GB)

### Recomendações de Hardware por Host

**PC1 (Aplicação)**:
- Mínimo: 8 cores CPU, 16 GB RAM, SSD 100GB
- Recomendado: 12 cores CPU, 32 GB RAM, NVMe 200GB
- Storage: IOPS > 3000 para PostgreSQL e Redis

**PC2 (Infraestrutura)**:
- Mínimo: 16 cores CPU, 32 GB RAM, GPU 8GB, SSD 500GB
- Recomendado: 32 cores CPU, 64 GB RAM, GPU 24GB, NVMe 1TB
- Storage: IOPS > 5000 para Neo4j e Qdrant
- GPU: CUDA compatível, mínimo 8GB VRAM

### Notas de Dimensionamento
- Recursos configuráveis via variáveis: `NEO4J_CPUS`, `NEO4J_MEM_LIMIT`, `QDRANT_CPUS`, `QDRANT_MEM_LIMIT`, `OLLAMA_CPUS`, `OLLAMA_MEM_LIMIT`
- Ollama requer GPU para performance adequada (sem GPU, CPU usage aumenta 3-5x)
- Neo4j memory tuning crítico: heap + pagecache devem ser < 80% RAM total
- Qdrant performance linear com CPU cores para busca vetorial

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
| `janus-api` | `curl -f http://localhost:8000/health` | a API respondeu HTTP | não valida Neo4j, Qdrant, Redis, RabbitMQ nem workers; pode falhar se `PUBLIC_API_KEY` exigir `X-API-Key` |
| `janus-frontend` | `wget -qO- http://127.0.0.1:4300/` | a UI serviu HTML | não valida backend |
| `postgres` | `pg_isready` | socket SQL pronto | não valida schema lógico |
| `redis` | `redis-cli ping` | Redis aceitando ping | não valida carga nem pub/sub |
| `rabbitmq` | `rabbitmq-diagnostics -q ping` | nó do broker vivo | não valida filas e policies |
| `neo4j` | `cypher-shell 'RETURN 1'` | autenticação e query básica | não valida ontologia e indexação |
| `qdrant` | `bash -c '</dev/tcp/localhost/6333' || exit 1` | porta aberta | não valida coleção nem API key em uso real |
| `ollama` | `ollama list` | runtime do Ollama respondeu | não garante que os modelos esperados já foram puxados |

## Restart policy (canônico do Compose)

| Serviço | Restart |
| --- | --- |
| `janus-api` | `unless-stopped` |
| `janus-frontend` | `unless-stopped` |
| `postgres` | `unless-stopped` |
| `redis` | `unless-stopped` |
| `rabbitmq` | `unless-stopped` |
| `neo4j` | `unless-stopped` |
| `qdrant` | `unless-stopped` |
| `ollama` | `unless-stopped` |
| `ollama-model-init` | `no` |

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
- `PUBLIC_API_KEY`
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

## Matriz de Impacto de Falhas

### Severidade CRÍTICO (Sistema Indisponível)
| Falha | Impacto | Fallback | Sintoma para Usuário |
| --- | --- | --- | --- |
| **PostgreSQL** | Boot falha completamente | Nenhum | API não responde, erro 500 em todas as requisições |
| **PC1 Completo** | Sistema fora do ar | Nenhum | Site não carrega, serviço completamente indisponível |

### Severidade ALTO (Funcionalidade Core Comprometida)
| Falha | Impacto | Fallback | Sintoma para Usuário |
| --- | --- | --- | --- |
| **Neo4j** | Grafo em modo offline | Queries retornam `[]`, operações de escrita ignoradas | Chat perde contexto de relacionamentos, code analysis falha |
| **Qdrant** | Memória vetorial indisponível | Busca semântica retorna `[]`, RAG sem contexto | Respostas genéricas sem memória de conversas anteriores |
| **Ollama** | LLM local fora | Migra para OpenAI/DeepSeek (com custo) | Maior latência, possível degradação de qualidade |
| **Redis** | Cache indisponível | Operações retornam `None`/`False` | Performance degradada, rate-limit pode falhar |

### Severidade MÉDIA (Funcionalidade Degradada)
| Falha | Impacto | Fallback | Sintoma para Usuário |
| --- | --- | --- | --- |
| **RabbitMQ** | Fila offline | Publicações ignoradas, workers parados | Tarefas em background não executam, processamento lento |
| **Rede PC1→PC2** | Conectividade intermitente | Circuit breaker ativado com retry exponencial | Funcionalidades cognitivas inconsistentes |

### Severidade BAIXA (Impacto Mínimo)
| Falha | Impacto | Fallback | Sintoma para Usuário |
| --- | --- | --- | --- |
| **ollama-model-init** | Modelos não pré-carregados | Ollama carrega sob demanda | Primeira requisição mais lenta |

### Comportamentos de Fallback Detalhados

#### Neo4j (Modo Offline)
- **Circuit Breaker**: Threshold=5, recovery_timeout=30s
- **Comportamento**: Queries retornam listas vazias sem exceções
- **Flag**: `_offline = True` com tentativas de revive automático
- **Impacto**: Perda de graph traversal, code graph analysis, self-memory

#### Qdrant (Modo Offline)
- **Circuit Breaker**: Configurável via `LLM_CIRCUIT_BREAKER_*`
- **Comportamento**: Busca vetorial retorna `[]`, upserts ignorados
- **Recuperação**: `try_revive()` a cada 10 segundos
- **Impacto**: Memória episódica completamente indisponível

#### Redis (Fail-Open)
- **Detecção**: Ping com retry exponencial (3 tentativas)
- **Comportamento**: Cliente inicializa mesmo com falha, operações retornam `None`
- **Impacto**: Cache distribuído perdido, performance degradada

#### RabbitMQ (Modo Offline)
- **Comportamento**: Publicações ignoradas, consumidores tentam reconexão
- **Fallback**: Tenta reconexão a cada 5 segundos
- **Impacto**: Workers não processam tarefas, eventos perdidos

#### Ollama (Health Check com Failover)
- **Detecção**: `_health_check_ollama()` via `llm.invoke("ping")`
- **Comportamento**: Modelos falhantes removidos do pool
- **Recuperação**: Re-verificação periódica dos modelos
- **Impacto**: Migra para provedores cloud com custo associado

### Sistema de Resiliência Global
- **Circuit Breaker Pattern**: Estados CLOSED → OPEN → HALF_OPEN → CLOSED
- **Retry Strategy**: Backoff exponencial com jitter
- **Health Monitoring**: Score geral de saúde (0-100) por componente
- **Alertas**: Integração com Prometheus/Grafana para monitoramento

## Critério mínimo de operação por host
- PC1 só é minimamente utilizável quando `janus-api`, `janus-frontend`, `postgres`, `redis` e `rabbitmq` estão `healthy`.
- PC2 só é minimamente utilizável quando `neo4j`, `qdrant` e `ollama` estão `healthy`.
- `ollama-model-init` não precisa permanecer rodando, mas precisa ter concluído sem impedir a disponibilidade dos modelos exigidos pelo deploy.
- A stack distribuída só fecha de verdade quando PC1 enxerga os endpoints configurados em `NEO4J_URI`, `QDRANT_HOST:QDRANT_PORT` e `OLLAMA_HOST`.

## Estratégia de Deploy

### Ordem Correta de Deploy (PC2 → PC1)

#### Fase 1: Preparação e Validação Pré-Deploy
```bash
# 1. Verificar conectividade entre hosts
ping <PC2_TAILSCALE_IP>

# 2. Validar arquivos de ambiente
ls -la .env.pc1 .env.pc2

# 3. Verificar recursos disponíveis
docker system df
docker system prune -f  # limpar se necessário
```

#### Fase 2: Deploy do PC2 (Infraestrutura)
```bash
# 1. Subir serviços de infraestrutura
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d

# 2. Aguardar health checks (máximo 5 minutos)
timeout 300 bash -c 'until docker compose -f docker-compose.pc2.yml ps | grep -q "healthy"; do sleep 5; done'

# 3. Validar serviços críticos individualmente
curl -sf http://<PC2_TAILSCALE_IP>:7474/browser/ || echo "Neo4j não respondendo"
curl -sf http://<PC2_TAILSCALE_IP>:6333/ || echo "Qdrant não respondendo"
curl -sf http://<PC2_TAILSCALE_IP>:11434/api/tags || echo "Ollama não respondendo"

# 4. Verificar logs de inicialização
docker compose -f docker-compose.pc2.yml logs --tail=50 neo4j | grep -i "started"
docker compose -f docker-compose.pc2.yml logs --tail=50 qdrant | grep -i "started"
docker compose -f docker-compose.pc2.yml logs --tail=50 ollama | grep -i "listening"
```

#### Fase 3: Deploy do PC1 (Aplicação)
```bash
# 1. Build da imagem API (se necessário)
docker build -f backend/docker/Dockerfile -t janus-completo-janus-api:latest backend

# 2. Subir aplicação
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d

# 3. Aguardar health checks locais
timeout 180 bash -c 'until docker compose -f docker-compose.pc1.yml ps | grep janus-api | grep -q "healthy"; do sleep 5; done'

# 4. Validar endpoints críticos
sleep 30  # aguardar bootstrap completo
curl -sf http://localhost:8000/healthz || echo "Healthz falhou"
curl -sf http://localhost:8000/health || echo "Health falhou"
curl -sf http://localhost:8000/api/v1/system/status || echo "System status falhou"
```

Se `PUBLIC_API_KEY` estiver configurada, os endpoints fora do bypass exigem o header `X-API-Key` (por exemplo, `/health` e `/api/v1/*`). Nesse caso, a validação acima precisa usar `-H "X-API-Key: <PUBLIC_API_KEY>"` nesses paths.

### Checklist de Validação Cross-Host

#### Validação de Conectividade
```bash
# Testar conectividade PC1 → PC2
docker exec janus_api python -c "
import requests
try:
    r = requests.get('http://<PC2_TAILSCALE_IP>:11434/api/tags', timeout=5)
    print('Ollama conectado:', r.status_code)
except Exception as e:
    print('Ollama falhou:', e)
"
```

#### Validação de Funcionalidade Cognitiva
```bash
# Testar RAG com Qdrant
curl -X POST http://localhost:8000/api/v1/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test connection", "limit": 1}' || echo "Qdrant search falhou"

# Testar Neo4j
curl -X POST http://localhost:8000/api/v1/graph/query \
  -H "Content-Type: application/json" \
  -d '{"query": "MATCH (n) RETURN count(n) as total"}' || echo "Neo4j query falhou"
```

### Rollback Procedure

#### Rollback Gradual (por serviço)
```bash
# 1. Parar PC1 primeiro (preservar dados PC2)
docker compose -f docker-compose.pc1.yml down

# 2. Se necessário, parar PC2
docker compose -f docker-compose.pc2.yml down

# 3. Remover volumes se necessário reset completo
docker volume rm janus_postgres_data janus_neo4j_data janus_qdrant_data
```

#### Rollback Rápido (emergência)
```bash
# Parar tudo imediatamente
docker compose -f docker-compose.pc1.yml -f docker-compose.pc2.yml down

# Reset completo
docker system prune -a -f --volumes
```

### Pontos de Falha Comuns e Mitigação

#### 1. Timeout de Health Check
**Sintoma**: Containers ficam em "starting" ou "unhealthy"
**Mitigação**: Aumentar `start_period` e `retries` no compose

#### 2. Conectividade Cross-Host
**Sintoma**: API inicia mas funcionalidades cognitivas falham
**Mitigação**: Verificar firewall, Tailscale, rotas de rede

#### 3. Recursos Insuficientes
**Sintoma**: Containers morrem com "OOMKilled"
**Mitigação**: Verificar `mem_limit` e `cpus`, ajustar conforme necessário

#### 4. Portas em Conflito
**Sintoma**: "bind: address already in use"
**Mitigação**: Verificar processos locais: `lsof -i :8000`, `lsof -i :5432`

### Validação Final de Deploy

#### Teste de Carga Básico
```bash
# Testar chat endpoint
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/v1/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "test deployment '$i'"}' \
    -w "%{http_code} %{time_total}s\n"
done
```

#### Verificação de Logs
```bash
# Logs críticos para monitorar
docker logs janus_api --tail=100 | grep -E "(ERROR|WARN|CRITICAL)"
docker logs janus_neo4j --tail=50 | grep -E "(ERROR|WARN)"
docker logs janus_qdrant --tail=50 | grep -E "(ERROR|WARN)"
```

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

## Configuração de Rede

### Topologia de Rede Docker

#### PC1 - Rede Local (`janus-pc1-net`)
```yaml
networks:
  janus-pc1-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

**Serviços na rede PC1:**
- `janus-api` (172.20.0.2)
- `janus-frontend` (172.20.0.3)
- `postgres` (172.20.0.4)
- `redis` (172.20.0.5)
- `rabbitmq` (172.20.0.6)

#### PC2 - Rede Local (`janus-pc2-net`)
```yaml
networks:
  janus-pc2-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.21.0.0/16
```

**Serviços na rede PC2:**
- `neo4j` (172.21.0.2)
- `qdrant` (172.21.0.3)
- `ollama` (172.21.0.4)
- `ollama-model-init` (172.21.0.5)

### Conectividade Cross-Host

#### Configuração Tailscale (Recomendado)
```bash
# Instalar Tailscale em ambos hosts
curl -fsSL https://tailscale.com/install.sh | sh

# Autenticar e obter IPs
sudo tailscale up

# Verificar IPs
tailscale ip -4
```

**Variáveis de ambiente para Tailscale:**
```bash
# .env.pc1
NEO4J_URI=bolt://100.88.71.49:7687
QDRANT_HOST=100.88.71.49
OLLAMA_HOST=http://100.88.71.49:11434
```

#### Configuração VPN Alternativa
```bash
# WireGuard exemplo
# PC1 (cliente)
[Interface]
PrivateKey = <PC1_PRIVATE_KEY>
Address = 10.0.0.2/32
DNS = 1.1.1.1

[Peer]
PublicKey = <PC2_PUBLIC_KEY>
Endpoint = <PC2_PUBLIC_IP>:51820
AllowedIPs = 10.0.0.1/32
PersistentKeepalive = 25
```

### Portas e Firewall

#### PC1 - Portas Necessárias
| Serviço | Porta | Protocolo | Acesso | Descrição |
| --- | --- | --- | --- | --- |
| janus-api | 8000 | TCP | Público | API REST principal |
| janus-frontend | 4300 | TCP | Público | Interface web Angular |
| postgres | 5432 | TCP | Localhost | PostgreSQL com pgvector |
| redis | 6379 | TCP | Localhost | Cache e pub/sub |
| rabbitmq | 5672 | TCP | Localhost | Message broker AMQP |
| rabbitmq-mgmt | 15672 | TCP | Localhost | Management UI |

#### PC2 - Portas Necessárias
| Serviço | Porta | Protocolo | Acesso | Descrição |
| --- | --- | --- | --- | --- |
| neo4j-browser | 7474 | TCP | VPN/Interno | Neo4j Browser UI |
| neo4j-bolt | 7687 | TCP | VPN/Interno | Protocolo Bolt |
| qdrant | 6333 | TCP | VPN/Interno | API REST Qdrant |
| ollama | 11434 | TCP | VPN/Interno | API Ollama |

#### Regras de Firewall (UFW exemplo)
```bash
# PC1 - Permitir acesso público à aplicação
sudo ufw allow 8000/tcp comment "Janus API"
sudo ufw allow 4300/tcp comment "Janus Frontend"

# PC2 - Restringir acesso aos serviços de infra
sudo ufw allow from 10.0.0.0/8 to any port 7687 comment "Neo4j Bolt - VPN only"
sudo ufw allow from 10.0.0.0/8 to any port 6333 comment "Qdrant API - VPN only"
sudo ufw allow from 10.0.0.0/8 to any port 11434 comment "Ollama - VPN only"
```

### Troubleshooting de Conectividade

#### Testar Conectividade Básica
```bash
# Testar conectividade PC1 → PC2
telnet <PC2_IP> 7687  # Neo4j Bolt
telnet <PC2_IP> 6333  # Qdrant
telnet <PC2_IP> 11434 # Ollama

# Testar conectividade dentro do container
docker exec janus_api nc -zv <PC2_IP> 7687
docker exec janus_api nc -zv <PC2_IP> 6333
docker exec janus_api nc -zv <PC2_IP> 11434
```

#### Testar APIs Específicas
```bash
# Testar Neo4j Bolt
docker exec janus_api cypher-shell -a bolt://<PC2_IP>:7687 -u neo4j -p <PASSWORD> "RETURN 1"

# Testar Qdrant
curl -H "api-key: <QDRANT_API_KEY>" http://<PC2_IP>:6333/collections

# Testar Ollama
curl http://<PC2_IP>:11434/api/tags
```

#### Diagnóstico de DNS
```bash
# Verificar resolução de nomes
docker exec janus_api nslookup <PC2_HOSTNAME>
docker exec janus_api cat /etc/resolv.conf

# Testar com IPs diretos vs hostnames
curl http://<PC2_IP>:11434/api/tags  # IP direto
curl http://<PC2_HOSTNAME>:11434/api/tags  # hostname
```

### Configuração de Performance

#### Otimizações de Rede
```yaml
# docker-compose.pc1.yml - adicionar aos serviços
services:
  janus-api:
    sysctls:
      - net.core.somaxconn=65535
      - net.ipv4.tcp_tw_reuse=1
      - net.ipv4.tcp_fin_timeout=15
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
```

#### MTU e Jumbo Frames
```bash
# Verificar MTU atual
ip addr show | grep mtu

# Ajustar MTU se necessário (VPNs podem requerer menor MTU)
sudo ip link set dev eth0 mtu 1400
```

### Segurança de Rede

#### TLS/SSL (Produção)
```bash
# Gerar certificados auto-assinados para testes
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Configurar Neo4j com TLS
# Adicionar ao docker-compose.pc2.yml
environment:
  - NEO4J_dbms_ssl_policy_bolt_enabled=true
  - NEO4J_dbms_ssl_policy_bolt_base__directory=certificates
  - NEO4J_dbms_ssl_policy_bolt_private__key=key.pem
  - NEO4J_dbms_ssl_policy_bolt_public__certificate=cert.pem
```

#### Network Policies (Docker Swarm)
```yaml
# Aplicar políticas de rede restritivas
networks:
  janus-pc1-net:
    driver: overlay
    internal: true  # Sem acesso externo
    attachable: false
```

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
