# Janus — AI Architect

> **Documentação Unificada**: Este documento é a Fonte Única da Verdade (SSOT) para arquitetura, operação, desenvolvimento e roadmap do Janus.

## Índice

- [1. Visão Geral](#1-visão-geral)
  - [1.1 Objetivos e Princípios](#11-objetivos-e-princípios)
  - [1.2 Filosofia de Design](#12-filosofia-de-design-e-decisões-arquiteturais)
  - [1.3 Tecnologias e Componentes](#13-tecnologias-e-componentes)
  - [1.4 Estrutura do Projeto](#14-estrutura-do-projeto)
- [2. Arquitetura](#2-arquitetura)
  - [2.1 Topologia](#21-topologia)
  - [2.2 Camadas e Responsabilidades](#22-camadas-e-responsabilidades)
- [3. Processos Ponta a Ponta](#3-processos-ponta-a-ponta)
  - [3.1 Conversas e LLM Routing](#31-conversas-e-llm-routing)
  - [3.2 Memória e Conhecimento](#32-memória-e-conhecimento)
  - [3.3 Autonomia e Meta-Agente](#33-autonomia-e-meta-agente)
  - [3.4 Aprendizado Contínuo](#34-aprendizado-contínuo-e-fine-tuning)
  - [3.5 Observabilidade](#35-observabilidade)
  - [3.6 Inicialização e Ciclo de Vida](#36-inicialização-e-ciclo-de-vida-kernel-e-daemon)
  - [3.7 Parlamento (Agentes)](#37-parlamento-router--coder--professor--sandbox)
  - [3.8 Resiliência](#38-resiliência-e-auto-healing)
  - [3.9 Produtividade](#39-produtividade-google)
- [4. API de Backend](#4-api-de-backend)
  - [4.1 Superfície de Endpoints](#41-superfície-de-endpoints)
  - [4.2 Contratos](#42-contratos)
  - [4.3 Router e Modos](#43-router-e-modos-de-exposição-full-vs-minimal)
  - [4.11 Recipes e Exemplos](#411-recipes-rápidos-de-uso-da-api)
- [5. Frontend (Site)](#5-frontend-site)
- [6. Ambientes e Deploy](#6-ambientes-e-deploy)
- [7. Segurança e Governança](#7-segurança-e-governança)
- [8. Troubleshooting](#8-troubleshooting)
- [9. Referências e Código](#9-referências-e-código)
- [10. Roadmap & Dívida Técnica](#10-roadmap--dívida-técnica)

---

## 1. Visão Geral

### 1.1 Objetivos e Princípios

O Janus foi projetado como uma **Arquitetura Cognitiva Resiliente (ACR)**: um sistema que não apenas responde, mas mantém contexto, aprende com o uso e se protege de falhas inevitáveis (provedores instáveis, limites de custo, latência variável e dados incompletos).

Pilares fundamentais:

- **Autonomia supervisionada**: loops de percepção-ação com um Meta-Agente que inspeciona a saúde do sistema e propõe ações corretivas.
- **Memória híbrida**: episódios em vetor (Qdrant) para recuperação difusa + grafo (Neo4j) para relações estruturadas + cache LRU/TTL para velocidade.
- **Eficiência de custo**: roteamento dinâmico que reserva modelos caros para raciocínio complexo e usa modelos baratos/locais para tarefas simples.
- **Resiliência por design**: circuit breakers, retries, timeouts, modo degradado e métricas para detecção precoce.
- **Contratos estáveis**: API unificada (`/api/v1`) para desacoplar frontend, workers e integrações externas.

### 1.2 Filosofia de Design e Decisões Arquiteturais

O Janus segue um conjunto de decisões “conscientes” (trade-offs explícitos) para que o sistema seja sustentável em produção.

1. **Por que memória híbrida (vetor + grafo + cache)?**
   - *Decisão*: armazenar o “registro bruto” (episódios) no Qdrant e consolidar, em background, entidades e relações no Neo4j. O cache de curto prazo reduz custo/latência em interações repetidas.

2. **Por que o roteamento de LLM é obrigatório?**
   - *Decisão*: seleção adaptativa por prioridade, custo estimado, saúde do provedor e histórico de latência/erros, com fallback automático.

3. **Por que existe um Meta-Agente separado?**
   - *Decisão*: um supervisor em loop (LangGraph) que observa métricas, detecta anomalias e propõe planos, com etapa de reflexão/critique antes de executar ações.

4. **Por que “hot path” e “cold path”?**
   - *Decisão*: gravar rápido no hot path (chat) e consolidar depois, assincronamente, com workers dedicados (RabbitMQ).

### 1.3 Tecnologias e Componentes

- **Backend**: Python 3.11, FastAPI, Uvicorn.
- **LLM**: LangChain/LangGraph, OpenAI/Anthropic/Gemini/Ollama.
- **Datastores**: Neo4j (grafo), Qdrant (vetorial), MySQL (perfil/usuário).
- **Mensageria**: RabbitMQ (consolidação, harvesting, training).
- **Observabilidade**: Prometheus, Grafana.
- **Frontend**: Angular 20 + Material/CDK.
- **Deploy**: Docker e docker-compose.

### 1.4 Estrutura do Projeto

```
/ (raiz)
├─ README.md                      # Este arquivo (SSOT)
├─ docker-compose.yml             # Orquestração local
├─ front/                         # Aplicação Angular (UI)
├─ janus/                         # Backend (FastAPI, serviços, workers)
│  ├─ app/                        # Código da aplicação
│  │  ├─ api/                     # Endpoints REST (/api/v1)
│  │  ├─ core/                    # LLM, memória, infra, tools, workers
│  │  ├─ db/                      # Conectores (Neo4j/Qdrant/MySQL)
│  │  ├─ services/                # Orquestração e regras de negócio
│  │  ├─ models/                  # Modelos Pydantic/ORM
│  │  ├─ repositories/            # Persistência e integrações
│  │  ├─ config.py                # Configurações
│  │  └─ main.py                  # Lifecycle
│  ├─ tests/                      # Testes
│  ├─ docker/                     # Dockerfiles
│  ├─ grafana/                    # Dashboards
│  └─ observability/              # Compose e configs
├─ docs/                          # Guias específicos e assets
└─ scripts/                       # Utilitários e automações
```

---

## 2. Arquitetura

### 2.1 Topologia

- Composição do app: [main.py](janus/app/main.py#L1-L300)
- Inicialização paralela de Neo4j, Qdrant e RabbitMQ.

```text
   [Frontend Angular] --HTTP--> [FastAPI /api/v1]
      |                          |-- Services (LLM, Memory, Knowledge, Autonomy)
      |                          |-- Repos (Neo4j, Qdrant, RabbitMQ, MySQL)
      |                          |-- Core (LLM Router, Resilience, Monitoring)
      |                          |-- Workers (Consolidator, Harvester, Training)
      \--> /metrics ----> Prometheus ----> Grafana (dashboards)
```

### 2.2 Camadas e Responsabilidades

- **API**: [endpoints](janus/app/api/v1/endpoints) — definem contratos HTTP.
- **Serviços**: [services](janus/app/services) — orquestração e casos de uso.
- **Núcleo**: [core](janus/app/core) — políticas de LLM, memória, ferramentas, workers.
- **Persistência**: [repositories](janus/app/repositories), [db](janus/app/db).
- **Configuração**: [config.py](janus/app/config.py).

---

## 3. Processos Ponta a Ponta

### 3.1 Conversas e LLM Routing

O coração da interação é o roteador dinâmico de modelos, que decide "quem responde" baseado no contexto.

**Lógica de Decisão (Scoring):**
- **Score = (Peso * Custo) + (Peso * Latência) + Penalidade de Erro**
- `FAST_AND_CHEAP`: Favorece modelos locais (Ollama) ou cloud baratos (Gemini Flash).
- `HIGH_QUALITY`: Favorece modelos com maior raciocínio (GPT-4o).
- **Fallback**: Se o principal falhar, o `CircuitBreaker` abre e tenta o próximo.

Referências:
- [router.py](janus/app/core/llm/router.py): Algoritmo de seleção.
- [llm_manager.py](janus/app/core/llm/llm_manager.py): Gestão de ciclo de vida.

#### 3.1.2 Sequência Lógica do Chat (Request/Response)
1. **Validação**: papel, prioridade.
2. **Recuperação**: histórico e persona.
3. **RAG**: busca experiências relevantes (MemoryService).
4. **Prompt**: monta contexto.
5. **Invocação**: LLMService (com cache/budget).
6. **Tools**: loop de ferramentas se necessário.
7. **Persistência**: armazena interação.
8. **Async**: publica tarefas de consolidação.

### 3.2 Memória e Conhecimento

O Janus implementa "Consolidação Assimétrica":

1. **Caminho Quente (Hot Path)**: Interação salva no **Qdrant** (vetor) como "Episódio".
2. **Caminho Frio (Cold Path)**: Worker (`KnowledgeConsolidator`) extrai Entidades e Relações via LLM e salva no **Neo4j**.

Referências:
- [memory_core.py](janus/app/core/memory/memory_core.py)
- [knowledge_consolidator_worker.py](janus/app/core/workers/knowledge_consolidator_worker.py)

#### 3.2.7 Detalhamento interno do `MemoryCore`
O `MemoryCore` implementa quotas, PII redaction, criptografia e cache LRU/TTL para proteger dados e garantir performance mesmo com Qdrant instável (modo degradado/offline).

### 3.3 Autonomia e Meta-Agente

O Meta-Agente é um **Grafo de Estado (LangGraph)** que implementa um loop OODA (Observe, Orient, Decide, Act) com Reflexão.

**Ciclo:** `Monitor` -> `Diagnose` -> `Plan` -> `Reflect` -> `Execute`.

Referências:
- [autonomy.py](janus/app/api/v1/endpoints/autonomy.py)
- [meta_agent.py](janus/app/core/agents/meta_agent.py)

#### 3.3.2 Policy Engine
Controla o risco antes de agir:
1. **Blocklist/Allowlist**
2. **PermissionLevel vs RiskProfile** (Conservative, Balanced, Aggressive)
3. **Rate limit**
4. **Quota por ciclo**

Referência: [policy_engine.py](janus/app/core/autonomy/policy_engine.py)

### 3.4 Aprendizado Contínuo
**Pipeline de Dados**: O `DataHarvester` coleta interações de alta qualidade, normaliza, deduplica e salva para fine-tuning.
Suporta testes A/B de modelos (`ABExperimentModels`).

### 3.5 Observabilidade
Métricas expostas em `/metrics` e consumidas por Prometheus/Grafana. Monitora latência, erros, tokens/custo, cache e saúde de serviços.

### 3.6 Inicialização e Ciclo de Vida
O `Kernel.startup()` inicializa infraestrutura, serviços e workers na ordem correta, suportando modo API (FastAPI) e modo Daemon.

### 3.7 Parlamento (Router → Coder → Professor → Sandbox)
Pipeline multi-agente via RabbitMQ onde um `TaskState` é roteado.
- **Router**: Decide o próximo agente.
- **Coder**: Gera código.
- **Professor**: Revisa código.
- **Sandbox**: Executa código e devolve resultado.

Referência: [collaboration_service.py](janus/app/services/collaboration_service.py)

### 3.8 Resiliência
- **Health Monitor**: Checks periódicos.
- **Poison Pill Handler**: Isola mensagens que causam crash repetido.
- **Auto-Healer**: Tenta reconectar broker e resetar circuit breakers.

### 3.9 Produtividade (Google)
Integração assíncrona com Google Calendar/Mail via workers e OAuth.

---

## 4. API de Backend

### 4.1 Superfície de Endpoints
A fonte de verdade é [janus/app/api/v1/router.py](janus/app/api/v1/router.py).
Domínios: Chat, LLM, Memória/RAG, Autonomia, Usuários, Workers, Observabilidade.

### 4.2 Contratos Principais
- `POST /api/v1/chat/message`: Chat síncrono.
- `GET /api/v1/chat/stream/{id}`: Chat SSE.
- `GET /api/v1/rag/search`: Busca vetorial.
- `POST /api/v1/documents/upload`: Ingestão de arquivos.

### 4.3 Router e Modos
Controlado por `PUBLIC_API_MINIMAL`. "Full API" expõe tudo; "Minimal API" expõe apenas chat/governança.

### 4.11 Recipes Rápidos de Uso da API

#### Python (requests)

**Invocar LLM com roteamento adaptativo:**
```python
import requests

payload = {
  "prompt": "Explique a arquitetura do Janus em 3 tópicos",
  "role": "orchestrator",
  "priority": "fast_and_cheap"
}

resp = requests.post("http://localhost:8000/api/v1/llm/invoke", json=payload)
print(resp.status_code, resp.json())
```

**Agendar treinamento e consultar status:**
```python
import requests

train_payload = {
  "dataset_id": "ds-2024-10",
  "model": "custom-bert",
  "epochs": 3
}

ack = requests.post("http://localhost:8000/api/v1/learning/train", json=train_payload).json()
print("ACK:", ack)

status = requests.get("http://localhost:8000/api/v1/learning/train/status", params={"job_id": ack.get("job_id")}).json()
print("STATUS:", status)
```

#### cURL

**Iniciar conversa:**
```bash
curl -s -X POST "http://localhost:8000/api/v1/chat/start" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"title": "Demo Janus"}'
```

**Upload de arquivo:**
```bash
curl -s -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@meu-arquivo.pdf"
```

---

## 5. Frontend (Site)

- Localizado em `front/`.
- Angular 20 + Material.
- Consome `/api/v1`.
- Consulte [front/README.md](front/README.md) para detalhes de setup.

---

## 6. Ambientes e Deploy

O `docker-compose.yml` sobe a stack completa (Backend, Frontend, Neo4j, Qdrant, Ollama, MySQL, RabbitMQ, Observability).

**Setup Rápido:**
1. Configure `janus/app/.env` (baseado em [config.py](janus/app/config.py)).
2. `docker compose up -d --build`.
3. Acesse:
   - Frontend: `http://localhost:4300`
   - API Docs: `http://localhost:8000/docs`
   - Grafana: `http://localhost:3000`

---

## 7. Segurança e Governança

1. **Tokens**: Janus utiliza tokens próprios assinados (HMAC), não JWT padrão.
2. **Consentimentos**: Escopos de permissão persistidos no MySQL.
3. **Policy Engine**: Valida execuções de ferramentas contra perfil de risco.
4. **Endurecimento**: Rate limit por IP/Key, sanitização de logs.

---

## 8. Troubleshooting

- **Checklist**:
  1. `GET /healthz` (API viva?)
  2. `GET /api/v1/system/health/services` (Componentes?)
  3. `GET /api/v1/tasks/health/rabbitmq` (Broker?)
- **Erros Comuns**:
  - `Qdrant 400`: IDs inválidos (use UUID).
  - `Broker offline`: Sistema opera em modo degradado (sem tarefas de background).
  - `403 Forbidden`: Verifique se o usuário é admin ou tem consentimento.

---

## 9. Referências e Código

- Composição: [main.py](janus/app/main.py)
- LLM Manager: [llm_manager.py](janus/app/core/llm/llm_manager.py)
- Broker: [message_broker.py](janus/app/core/infrastructure/message_broker.py)
- Config: [config.py](janus/app/config.py)

---

## 10. Roadmap & Dívida Técnica

> *Última atualização: 14/01/2026 (Scientific & V1 Focus)*

### 🚨 V1 Critical Path (Launch Blockers)

#### Security & Enterprise Ready
- [ ] **Security Headers**: CSP, HSTS, X-Frame-Options.
- [ ] **Input Sanitization**: Validação estrita de inputs da API.
- [ ] **Rate Limiting (Cost-Based)**: Limitar por gasto ($), não apenas requests.
- [ ] **Audit Log Imutável**.

#### Frontend V1
- [ ] **UI Overhaul**: Migrar para estética SaaS (Shadcn/UI + Tailwind).
- [ ] **Complete UI Coverage**: Implementar telas faltantes (Tools, Workers).
- [ ] **Critical Bugs**: Corrigir stream de pensamento (SSE) e erros 500 na Autonomia.

#### Stability & Ops
- [ ] **Database Migration**: Finalizar Alembic.
- [ ] **Smart Model Routing**: Router baseado em complexidade da task.
- [ ] **Graceful Degradation**: Fallbacks claros para queda de serviços.

### 🧪 Scientific Frontier (Post-V1)
- **Self-Evolving Toolset**: Agente cria suas próprias ferramentas (`ToolSynthesizerAgent`).
- **Swarm Intelligence**: Handoffs dinâmicos entre agentes sem supervisor central.
- **Active Memory Management**: Agente gerencia sua janela de contexto como RAM.
