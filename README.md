# Janus AI Architect

**Janus** é uma Arquitetura Cognitiva Resiliente (ACR) projetada para orquestração de agentes autônomos, memória híbrida (vetor + grafo) e desenvolvimento assistido por IA.

O projeto combina um backend em **Python (FastAPI + LangGraph)** e um frontend em **Angular 20**, operando sobre uma infraestrutura local robusta (Docker, Neo4j, Qdrant, RabbitMQ).

---

## 🚀 Quick Start

### Pré-requisitos
- **Docker** & **Docker Compose**
- (Opcional) Node.js 20+ (para desenvolvimento frontend local)
- (Opcional) Python 3.11+ (para desenvolvimento backend local)

### Rodando com Docker (Recomendado)

O repositório traz um `docker-compose.yml` que sobe **backend + frontend + dependências** em uma rede única.

1. **Configuração**:
   Verifique o arquivo `janus/app/config.py` para as variáveis de ambiente necessárias. Crie um arquivo `janus/app/.env` (se não existir) e configure suas chaves (ex: `OPENAI_API_KEY`, `NEO4J_PASSWORD`, etc.).

2. **Start**:
   Na raiz do projeto:
   ```bash
   docker compose up -d --build
   ```

3. **Acessar**:
   - **Frontend**: http://localhost:4300
   - **API Docs**: http://localhost:8000/docs
   - **Grafana**: http://localhost:3000
   - **Neo4j**: http://localhost:7474
   - **RabbitMQ**: http://localhost:15672

---

## 📖 Visão Geral

### Objetivos e Princípios

O Janus foi projetado como uma **Arquitetura Cognitiva Resiliente (ACR)**: um sistema que não apenas responde, mas mantém contexto, aprende com o uso e se protege de falhas inevitáveis.

**Pilares fundamentais:**
- **Autonomia supervisionada**: Meta-Agente que inspeciona a saúde do sistema.
- **Memória híbrida**: Vetor (Qdrant) + Grafo (Neo4j) + Cache LRU/TTL.
- **Eficiência de custo**: Roteamento dinâmico de LLMs (Local vs Cloud).
- **Resiliência por design**: Circuit breakers, retries, modo degradado.
- **Contratos estáveis**: API unificada (`/api/v1`).

### Topologia e Arquitetura

```text
   [Frontend Angular] --HTTP--> [FastAPI /api/v1]
      |                          |-- Services (LLM, Memory, Autonomy)
      |                          |-- Repos (Neo4j, Qdrant, RabbitMQ)
      |                          |-- Core (Router, Resilience, Monitoring)
      |                          |-- Workers (Consolidator, Harvester)
      \--> /metrics ----> Prometheus ----> Grafana
```

---

## 🏗️ Estrutura do Projeto

```
/ (raiz)
├─ README.md                      # Documentação Central
├─ docker-compose.yml             # Orquestração
├─ front/                         # Aplicação Angular (UI)
├─ janus/                         # Backend (FastAPI, serviços, workers)
│  ├─ app/                        # Código da aplicação
│  │  ├─ api/                     # Endpoints REST (/api/v1)
│  │  ├─ core/                    # LLM, memória, infra, tools
│  │  ├─ services/                # Orquestração e regras de negócio
│  │  ├─ config.py                # Configurações
│  │  └─ main.py                  # Lifecycle
│  ├─ tests/                      # Testes
│  └─ docker/                     # Dockerfiles
├─ docs/                          # Guias específicos (Guides)
└─ scripts/                       # Utilitários
```

---

## ⚙️ Processos Ponta a Ponta

### 1. Conversas e LLM Routing
O **LLMRouter** decide dinamicamente qual modelo usar baseado em:
- **Priority**: `FAST_AND_CHEAP` (Modelos locais/Flash) vs `HIGH_QUALITY` (GPT-4/DeepSeek).
- **Custo e Latência**: Seleção adaptativa.
- **Saúde**: Circuit Breaker automático em caso de falhas.

### 2. Memória Híbrida (Hot/Cold Path)
- **Hot Path**: Interação salva imediatamente no **Qdrant** (Episódio) para recuperação rápida.
- **Cold Path**: Worker (`KnowledgeConsolidator`) extrai entidades e relações para o **Neo4j** (Grafo) assincronamente.

### 3. Autonomia e Meta-Agente
O Meta-Agente implementa um loop **OODA** (Observe, Orient, Decide, Act) com Reflexão:
1. **Monitor**: Coleta métricas.
2. **Diagnose**: Identifica problemas.
3. **Plan**: Propõe correções.
4. **Reflect**: Critica o plano antes da execução.
5. **Execute**: Aplica ações seguras.

### 4. Parlamento de Agentes
Pipeline de multi-agentes via RabbitMQ:
- **Router** -> **Coder** (Gera código) -> **Professor** (Revisa) -> **Sandbox** (Executa).

---

## 🔌 API de Backend

A API é exposta em `/api/v1` e inclui:
- **Chat**: `/api/v1/chat` (REST e Streaming SSE).
- **Memória**: `/api/v1/memory` e `/api/v1/rag` (Busca Híbrida).
- **Autonomia**: `/api/v1/autonomy` (Controle do Meta-Agente).
- **Ferramentas**: `/api/v1/tools` e `/api/v1/sandbox`.
- **Observabilidade**: `/api/v1/metrics` e `/api/v1/system/health`.

---

## 💻 Frontend (Site)

O frontend em Angular 20 fornece:
- **Chat Interface**: Com streaming de tokens e eventos.
- **HUD de Agentes**: Visualização do pensamento e ações do sistema.
- **Gestão de Conhecimento**: Upload de documentos e visualização de memória.

Para rodar localmente (sem Docker):
```bash
cd front
npm install
npm start
# Acessar em http://localhost:4200 (Proxy para backend na porta 8000)
```

---

## 🛡️ Segurança e Governança

- **Policy Engine**: Valida execução de ferramentas com base em perfis de risco (`conservative`, `balanced`, `aggressive`).
- **Human-in-the-Loop**: Ações perigosas podem gerar "Pending Actions" para aprovação manual.
- **Sanitização**: PII Redaction e limpeza de inputs.

---

## 🗺️ Roadmap & Status

*(Baseado no planejamento V1 Launch e Scientific Foundation)*

### ✅ Concluído
- Hybrid Agent Architecture (LangGraph + PydanticAI).
- Native GraphRAG (Neo4j).
- Centralized HITL (Human-in-the-loop).
- Observabilidade Completa (Prometheus/Grafana).
- Secure Sandbox (Docker-based).

### 🚧 Em Progresso / Backlog V1
- **Security**: Security Headers, Input Sanitization, Rate Limiting (Cost-Based).
- **Frontend V1**: UI Overhaul (Shadcn/UI + Tailwind), Testes E2E.
- **Ops**: Database Migration Pipeline (Alembic).

### 🧪 Fronteira Científica (Post-V1)
- **Self-Evolving Toolset**: Agente cria suas próprias ferramentas.
- **Swarm Intelligence**: Dynamic Handoffs entre agentes.
- **Active Memory Management**: Gestão de contexto nível SO (paginação/esquecimento).

---

## 🔧 Troubleshooting

### Checklist Rápido
1. API está viva? `GET /healthz`
2. Serviços saudáveis? `GET /api/v1/system/health/services`
3. Filas travadas? Verifique RabbitMQ UI (`localhost:15672`).

### Problemas Comuns
- **Broker Offline**: O sistema entra em modo degradado (sem consolidação de memória).
- **Qdrant 400**: Verifique se IDs são UUIDs válidos.
- **Circuit Breaker Aberto**: Aguarde o tempo de recovery ou resete via API.

---

## 📚 Guias Adicionais

Consulte a pasta `docs/guides/` para guias específicos:
- [Tailscale Security Comparison](docs/guides/tailscale-security-comparison.md)
- [Tailscale Serve Setup](docs/guides/tailscale-serve-setup.md)
- [Tailscale Windows GUI Guide](docs/guides/tailscale-windows-gui-guide.md)

---

> *Este README consolida a documentação do projeto. Para detalhes de código, consulte os docstrings e a estrutura interna dos diretórios `janus/` e `front/`.*
