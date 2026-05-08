***

tipo: visao
dominio: sistema
camada: runtime
fonte-de-verdade: codigo
status: ativo
-------------

# Topologia Runtime

## Objetivo

Descrever a topologia real do runtime distribuído e separar dependências locais de PC1 das dependências remotas apontadas para PC2.

## Responsabilidades

- Separar PC1 e PC2.
- Mostrar dependências duras e opcionais.

## Entradas

- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`

## Saídas

- Modelo operacional do runtime distribuído.
- Grafo de dependências entre hosts.

## Dependências

- \[\[05 - Infra e Operação/PC1 PC2 e Docker]]
- \[\[05 - Infra e Operação/Bancos Filas e Modelos]]

## Topologia

- PC1:
  - expõe a aplicação (`janus-api`, `janus-frontend`)
  - concentra estado transacional e coordenação local (`postgres`, `redis`, `rabbitmq`)
  - monta volumes de dados e workspace consumidos pela API
- PC2:
  - concentra persistência cognitiva e capacidade de IA (`neo4j`, `qdrant`, `ollama`)
  - executa `ollama-model-init` apenas como inicialização de modelos

## Grafo de dependências

- `janus-frontend` -> `janus-api`
- `janus-api` -> `postgres`
- `janus-api` -> `redis`
- `janus-api` -> `rabbitmq`
- `janus-api` -> `neo4j` no PC2 via `NEO4J_URI`
- `janus-api` -> `qdrant` no PC2 via `QDRANT_HOST` e `QDRANT_API_KEY`
- `janus-api` -> `ollama` no PC2 via `OLLAMA_HOST`
- `ollama-model-init` -> `ollama`

## Dependências por domínio

- Chat e identidade:
  - Postgres como persistência primária
  - Qdrant como contexto vetorial complementar
- Autonomia:
  - Postgres para runs, steps, goals, self-study state e leases
  - Qdrant para memória episódica/self-study
  - Neo4j para self-memory e conhecimento estrutural derivado
- Documentos e knowledge spaces:
  - Postgres para manifesto e estado do knowledge space
  - Qdrant para chunks e seções canônicas indexadas
  - Neo4j para projeção estrutural do knowledge space consolidado
- Governança operacional:
  - Redis para rate limit, Pub/Sub e spend/quota temporária
  - Postgres para quotas diárias de tools, outbox e pending actions

## Defaults locais vs deploy distribuído

### Defaults do Config.py (Modo Local)

```python
# backend/app/config.py
NEO4J_URI: str = "bolt://neo4j:7687"
QDRANT_HOST: str = "qdrant"
QDRANT_PORT: int = 6333
OLLAMA_HOST: str = "http://ollama:11434"
```

### Overrides do Docker Compose (Modo Distribuído)

O `docker-compose.pc1.yml` transforma o cenário local em distribuído através de variáveis obrigatórias:

#### Variáveis Críticas para Cross-Host

```bash
# .env.pc1 - obrigatórias
NEO4J_URI=bolt://<PC2_TAILSCALE_IP>:7687
QDRANT_HOST=<PC2_TAILSCALE_IP>
QDRANT_API_KEY=<QDRANT_API_KEY>
OLLAMA_HOST=http://<PC2_TAILSCALE_IP>:11434
```

#### Template Completo .env.pc1

```bash
# === CONFIGURAÇÕES DE SEGURANÇA ===
AUTH_JWT_SECRET=your-jwt-secret-here
POSTGRES_PASSWORD=your-postgres-password
RABBITMQ_PASSWORD=your-rabbitmq-password

# === CONECTIVIDADE PC2 (TAILSCALE) ===
# Substitua 100.88.71.49 pelo IP Tailscale real do PC2
NEO4J_URI=bolt://100.88.71.49:7687
NEO4J_PASSWORD=your-neo4j-password
QDRANT_HOST=100.88.71.49
QDRANT_API_KEY=your-qdrant-api-key
OLLAMA_HOST=http://100.88.71.49:11434

# === CONFIGURAÇÕES OPCIONAIS ===
ENVIRONMENT=production
CORS_ALLOW_ORIGINS=["http://localhost:4300"]
START_ORCHESTRATOR_WORKERS_ON_STARTUP=true
AUTO_INDEX_ON_STARTUP=true
```

#### Template Completo .env.pc2

```bash
# === SEGURANÇA PC2 ===
NEO4J_PASSWORD=your-neo4j-password
QDRANT_API_KEY=your-qdrant-api-key

# === RECURSOS (AJUSTAR CONFORME HARDWARE) ===
NEO4J_HEAP_INITIAL=2G
NEO4J_HEAP_MAX=8G
NEO4J_PAGECACHE=12G
NEO4J_MEM_LIMIT=24g
NEO4J_CPUS=10.0
QDRANT_MEM_LIMIT=12g
QDRANT_CPUS=6.0
OLLAMA_MEM_LIMIT=24g
OLLAMA_CPUS=12.0

# === MODELOS OLLAMA ===
OLLAMA_ORCHESTRATOR_MODEL=gpt-oss:20b
OLLAMA_CODER_MODEL=deepseek-coder:6.7b
OLLAMA_CURATOR_MODEL=ministral-3:14b
OLLAMA_AUTO_PULL_MODELS=true
```

### Transição Local → Distribuído

#### Passo 1: Validar Modo Local

```bash
# Em single-host, os defaults funcionam
docker compose -f docker-compose.pc1.yml -f docker-compose.pc2.yml up -d
```

#### Passo 2: Preparar Distribuído

```bash
# Gerar chaves e configurar Tailscale
# Copiar templates e ajustar IPs
# Validar conectividade cross-host
```

#### Passo 3: Deploy Distribuído

```bash
# PC2 primeiro
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d

# Aguardar health checks
timeout 300 bash -c 'until docker compose -f docker-compose.pc2.yml ps | grep -q "healthy"; do sleep 5; done'

# Depois PC1
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d
```

### Diferenças de Comportamento

| Aspecto            | Modo Local             | Modo Distribuído         |
| ------------------ | ---------------------- | ------------------------ |
| **Descoberta**     | DNS interno Docker     | IPs fixos via variáveis  |
| **Latência**       | < 1ms (mesmo host)     | 1-50ms (rede VPN)        |
| **Conectividade**  | Bridge network         | Tailscale/VPN externa    |
| **Falhas**         | Isoladas por container | Impactam funcionalidades |
| **Performance**    | Ótima para dev         | Adequada para produção   |
| **Escalabilidade** | Limitada ao host       | Horizontal por serviço   |

### Configuração Tailscale Detalhada

#### Instalação em Ambos Hosts

```bash
# Ubuntu/Debian
curl -fsSL https://tailscale.com/install.sh | sh

# Autenticar
sudo tailscale up

# Verificar IPs atribuídos
tailscale ip -4
```

#### Verificar Conectividade

```bash
# Do PC1, testar acesso ao PC2
ping $(tailscale ip -4 pc2)
telnet $(tailscale ip -4 pc2) 7687  # Neo4j
telnet $(tailscale ip -4 pc2) 6333  # Qdrant
telnet $(tailscale ip -4 pc2) 11434 # Ollama
```

#### Configuração de Segurança

```bash
# ACLs Tailscale (painel web)
{
  "acls": [
    {
      "action": "accept",
      "src": ["tag:pc1"],
      "dst": ["tag:pc2:7687", "tag:pc2:6333", "tag:pc2:11434"]
    }
  ],
  "nodeAttrs": [
    {
      "target": ["pc1"],
      "attr": ["tag:pc1"]
    },
    {
      "target": ["pc2"],
      "attr": ["tag:pc2"]
    }
  ]
}
```

### Troubleshooting de Conectividade

#### Testar dentro do Container

```bash
# Verificar se variáveis estão corretas
docker exec janus_api env | grep -E "(NEO4J|QDRANT|OLLAMA)"

# Testar conectividade
docker exec janus_api nc -zv $QDRANT_HOST 6333
docker exec janus_api curl -f http://$OLLAMA_HOST:11434/api/tags
```

#### Logs de Conexão

```bash
# Verificar tentativas de conexão
docker logs janus_api --tail=100 | grep -E "(neo4j|qdrant|ollama)" | grep -i "connect"
```

### Boas Práticas

1. **Sempre validar conectividade antes do deploy**
2. **Usar IPs fixos do Tailscale, não hostnames dinâmicos**
3. **Configurar firewall nos hosts para restringir acesso**
4. **Monitorar latência entre hosts regularmente**
5. **Ter plano de rollback rápido se conectividade falhar**

## Leitura operacional

### Dependências de Boot

- O backend só tem bloqueio de boot explícito para `postgres`, `redis` e `rabbitmq`.
- Neo4j, Qdrant e Ollama são dependências remotas mandatórias de configuração, mas não entram em `depends_on` porque vivem fora do host PC1.
- O frontend tem dependência estrita do healthcheck do `janus-api`.
- O deploy resultante é assimétrico: disponibilidade transacional do produto depende de PC1; persistência cognitiva e recursos de memória dependem de PC2.

### Comandos de Verificação de Health

#### Verificar Health de Todos Serviços

```bash
# PC1 - Status geral
docker compose -f docker-compose.pc1.yml ps

# PC2 - Status geral  
docker compose -f docker-compose.pc2.yml ps

# Health específico por serviço
curl -f http://localhost:8000/healthz      # API - sem auth
curl -f http://localhost:8000/health       # API - com auth check
curl -f http://localhost:8000/api/v1/system/status  # Status completo
```

#### Testar Conectividade Cross-Host

```bash
# Do PC1, testar acesso ao PC2
docker exec janus_api bash -c "
echo 'Testing Neo4j...'
timeout 5 cypher-shell -a \$NEO4J_URI -u neo4j -p \$NEO4J_PASSWORD 'RETURN 1' 2>/dev/null && echo 'Neo4j OK' || echo 'Neo4j FAIL'

echo 'Testing Qdrant...'
curl -s -H \"api-key: \$QDRANT_API_KEY\" http://\$QDRANT_HOST:\$QDRANT_PORT/collections >/dev/null && echo 'Qdrant OK' || echo 'Qdrant FAIL'

echo 'Testing Ollama...'
curl -s \$OLLAMA_HOST/api/tags >/dev/null && echo 'Ollama OK' || echo 'Ollama FAIL'
"
```

### Logs Importantes para Monitoramento

#### Logs de Boot e Inicialização

```bash
# Verificar ordem de inicialização
docker logs janus_api --tail=200 | grep -E "(startup|boot|init|ready)"

# Verificar conexões a serviços externos
docker logs janus_api --tail=100 | grep -E "(neo4j|qdrant|ollama)" | grep -i "connect"

# Verificar erros críticos
docker logs janus_api --tail=50 | grep -E "(ERROR|CRITICAL|FATAL)"
```

#### Logs por Serviço Crítico

```bash
# Neo4j - Queries e conexões
docker logs janus_neo4j --tail=50 | grep -E "(started|bolt|query)"

# Qdrant - Collections e busca
docker logs janus_qdrant --tail=50 | grep -E "(collection|search|index)"

# Ollama - Modelos e inferência
docker logs janus_ollama --tail=50 | grep -E "(model|load|infer)"
```

### Métricas de Performance Esperadas

#### Latência Entre Componentes

| Conexão               | Latência Esperada | Limite Aceitável |
| --------------------- | ----------------- | ---------------- |
| PC1 → PC2 (Tailscale) | 1-10ms            | < 50ms           |
| API → PostgreSQL      | < 5ms             | < 20ms           |
| API → Redis           | < 2ms             | < 10ms           |
| API → Neo4j           | 5-15ms            | < 50ms           |
| API → Qdrant          | 5-15ms            | < 50ms           |
| API → Ollama          | 50-200ms          | < 500ms          |

#### Tempos de Boot

| Componente  | Tempo Esperado | Limite Crítico |
| ----------- | -------------- | -------------- |
| PostgreSQL  | 10-20s         | 60s            |
| Redis       | 5-10s          | 30s            |
| RabbitMQ    | 15-30s         | 90s            |
| Neo4j       | 30-60s         | 180s           |
| Qdrant      | 10-20s         | 60s            |
| Ollama      | 20-40s         | 120s           |
| API (total) | 60-120s        | 300s           |

#### Utilização de Recursos

| Serviço   | CPU Normal | RAM Normal | Alerta                 |
| --------- | ---------- | ---------- | ---------------------- |
| janus-api | 10-50%     | 1-3GB      | CPU > 80%, RAM > 3.5GB |
| postgres  | 5-30%      | 500MB-1GB  | CPU > 70%, RAM > 1.4GB |
| redis     | 1-10%      | 100-300MB  | RAM > 350MB            |
| neo4j     | 10-40%     | 2-8GB      | CPU > 90%, RAM > 20GB  |
| qdrant    | 5-30%      | 2-6GB      | CPU > 80%, RAM > 10GB  |
| ollama    | 20-80%     | 4-16GB     | CPU > 95%, RAM > 22GB  |

### Health Checks Detalhados

#### Testar Circuit Breakers

```bash
# Verificar estado dos circuit breakers
curl -s http://localhost:8000/api/v1/observability/health/system | jq '.components | to_entries[] | select(.key | contains("circuit"))'

# Forçar teste de conexão
docker exec janus_api python -c "
from app.core.infrastructure.health import health_check
import asyncio
result = asyncio.run(health_check())
print(result)
"
```

#### Monitorar Métricas Prometheus

```bash
# Acessar métricas brutas
curl -s http://localhost:8000/metrics | grep -E "(janus|health|circuit)"

# Filtrar por serviço específico
curl -s http://localhost:8000/metrics | grep -E "neo4j.*up"
curl -s http://localhost:8000/metrics | grep -E "qdrant.*up"
curl -s http://localhost:8000/metrics | grep -E "ollama.*up"
```

### Diagnóstico de Problemas Comuns

#### Falha de Conectividade Cross-Host

```bash
# 1. Verificar variáveis de ambiente
docker exec janus_api env | grep -E "(NEO4J|QDRANT|OLLAMA)_HOST"

# 2. Testar DNS/resolução
docker exec janus_api nslookup $(docker exec janus_api printenv QDRANT_HOST)

# 3. Testar portas
docker exec janus_api nc -zv $(docker exec janus_api printenv QDRANT_HOST) 6333

# 4. Verificar logs de erro
docker logs janus_api --tail=50 | grep -A5 -B5 "Connection.*refused"
```

#### Performance Degradada

```bash
# Verificar latência de resposta
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health

# onde curl-format.txt contém:
# time_namelookup:  %{time_namelookup}\n\
# time_connect:  %{time_connect}\n\
# time_appconnect:  %{time_appconnect}\n\
# time_pretransfer:  %{time_pretransfer}\n\
# time_redirect:  %{time_redirect}\n\
# time_starttransfer:  %{time_starttransfer}\n\
# time_total:  %{time_total}\n\
# speed_download:  %{speed_download}\n
# Monitorar uso de recursos
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
```

### Dashboard de Monitoramento

#### Configurar Grafana (Opcional)

```bash
# Adicionar ao docker-compose.pc1.yml
monitoring:
  image: grafana/grafana:latest
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
  volumes:
    - grafana_data:/var/lib/grafana
  networks:
    - janus-pc1-net
```

#### Queries PromQL Úteis

```promql
# Disponibilidade por serviço
janus_service_up{service="neo4j"}
janus_service_up{service="qdrant"}
janus_service_up{service="ollama"}

# Latência de resposta
histogram_quantile(0.95, rate(janus_request_duration_seconds_bucket[5m]))

# Taxa de erro
rate(janus_requests_total{status=~"5.."}[5m])

# Uso de recursos
container_cpu_usage_seconds_total{name=~"janus_.*"}
container_memory_usage_bytes{name=~"janus_.*"}
```

## Efeito de falha resumido

- Falha em Postgres: quebra fonte de verdade transacional e parte do estado do orquestrador.
- Falha em Redis: degrada coordenação e proteção, mas não remove a persistência canônica.
- Falha em Qdrant: remove recuperação vetorial e pipelines de memória/documento.
- Falha em Neo4j: remove recuperação estrutural, code graph e self-memory.

## Arquivos-fonte

- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`
- `backend/app/config.py`

## Fluxos relacionados

- \[\[01 - Visão do Sistema/Dependências Externas]]
- \[\[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]

## Riscos/Lacunas

- O sistema depende de rede estável entre PC1 e PC2 para todas as funções de grafo, vetor e inferência local.
- Como o Compose de PC1 não observa a saúde de PC2, falhas remotas podem aparecer apenas como erro funcional em runtime.
- A diferença entre defaults do `config.py` e overrides obrigatórios do compose torna perigoso assumir topologia single-host a partir do código isolado.

