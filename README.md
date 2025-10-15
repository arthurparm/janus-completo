# Janus AI Architect

[![Python Version](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Janus é uma aplicação de arquitetura de software de IA autônoma e modular. O sistema analisa bases de código, constrói
conhecimento e executa tarefas de forma proativa usando:

- Grafo de Conhecimento (Neo4j)
- Memória Vetorial (Qdrant)
- Agentes de IA especializados (LangChain) com acesso a ferramentas
- Observabilidade profunda com métricas Prometheus e dashboards Grafana

## Visão Geral do Stack

- Linguagem: Python 3.11
- Framework Web: FastAPI (totalmente assíncrono)
- Servidor ASGI: Uvicorn
- Gerenciador de pacotes: pip (requirements.txt)
- Orquestração local: Docker e Docker Compose
- Vetor/embedding: sentence-transformers, Qdrant
- Grafo: Neo4j 5 Community (com plugin APOC)
- LLM Router e Integrações: LangChain (OpenAI, Google Gemini, Groq, Ollama)
- Observabilidade: prometheus-fastapi-instrumentator + dashboard Grafana

Pontos de entrada:

- ASGI app: app.main:app
- API base: http://localhost:8000 (Swagger em /docs)

## Principais Funcionalidades

- **Arquitetura Altamente Robusta:** Sistema projetado para produção, com 9 arquivos críticos otimizados para alta
  confiabilidade.
- **Padrões de Resiliência:** Implementação nativa de Circuit Breakers, retries com backoff exponencial e timeouts em
  todos os componentes críticos (LLMs, Agentes, Banco de Dados).
- **API Totalmente Assíncrona:** Endpoints de alta performance que não bloqueiam o event loop, garantindo máxima
  concorrência.
- **Agentes de IA Especializados:** Múltiplos agentes com papéis distintos (Orchestrator, Tool User, Meta-Agent) e
  princípio do menor privilégio.
- **Ciclo de Auto-Otimização (Meta-Agente):** Um agente supervisor que monitora a saúde do sistema, analisa falhas e
  propõe correções de forma autônoma.
- **Roteador Dinâmico de LLMs:** Gerenciamento inteligente de modelos (Ollama, Gemini, OpenAI) com base em prioridade (
  custo vs. qualidade) e com fallback para o "Cérebro Soberano" local.
- **Observabilidade Profunda:** Métricas Prometheus detalhadas para latência, erros e estado de Circuit Breakers, com um
  dashboard Grafana pré-configurado.

## Requisitos

- Docker e Docker Compose (recomendado)
- OU Python 3.11 com pip para execução local

## 1. Configuração

Copie o arquivo `.env.example` para `.env` e ajuste as variáveis conforme necessário.

# App

APP_NAME=Janus
APP_VERSION=0.2.0
ENVIRONMENT=development
DRY_RUN=true

# Neo4j

NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Qdrant

QDRANT_HOST=qdrant
QDRANT_PORT=6333

# QDRANT_API_KEY= (opcional para Qdrant Cloud)

# LangSmith/Chain (opcional)

LANGCHAIN_TRACING_V2=true

# LANGCHAIN_API_KEY=

# Limites de taxa da API

RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_IP_PER_MIN=60
RATE_LIMIT_PER_KEY_PER_MIN=300

# Provedores LLM (preencha o que usar)

# OpenAI (nuvem)

# OPENAI_API_KEY=

OPENAI_MODEL_NAME=gpt-4o

# Google Gemini (nuvem)

# GEMINI_API_KEY=

GEMINI_MODEL_NAME=gemini-1.5-pro-latest

# Ollama (local)

OLLAMA_HOST=http://ollama:11434
OLLAMA_ORCHESTRATOR_MODEL=llama3.1:8b
OLLAMA_CODER_MODEL=codellama:7b
OLLAMA_CURATOR_MODEL=phi3:mini

Variáveis avançadas também suportadas via app/config.py (ajustes finos de memória e raciocínio):

- MEMORY_SHORT_TTL_SECONDS, MEMORY_SHORT_MAX_ITEMS, MEMORY_MAX_CONTENT_CHARS
- MEMORY_QUOTA_WINDOW_SECONDS, MEMORY_QUOTA_MAX_ITEMS_PER_ORIGIN, MEMORY_QUOTA_MAX_BYTES_PER_ORIGIN,
  MEMORY_ENCRYPTION_KEY, MEMORY_PII_REDACT
- REASONING_MAX_ITERATIONS, REASONING_MAX_SECONDS, REASONING_MAX_TOKENS
- META_AGENT_CYCLE_INTERVAL_SECONDS, META_AGENT_MAX_ITERATIONS, META_AGENT_MAX_SECONDS

## 2. Como Executar

Opção A) Docker Compose (recomendado)

Passo a passo (Docker):

1. Instale Docker Desktop (Windows/macOS) ou Docker Engine (Linux).
2. Copie `.env.example` para `.env` e preencha valores essenciais:
    - `NEO4J_USER` e `NEO4J_PASSWORD` (acesso ao Neo4j)
    - `OLLAMA_HOST=http://ollama:11434` (padrão já definido)
    - Chaves de provedores LLM caso use OpenAI/Gemini (opcional)
3. GPU (Ollama):
    - Se NÃO possuir GPU NVIDIA, remova o bloco abaixo do serviço `ollama` em `docker-compose.yml`:
      ```yaml
      deploy:
        resources:
          reservations:
            devices:
              - driver: nvidia
                count: all
                capabilities: [ gpu ]
      ```
    - Com GPU NVIDIA, mantenha para acelerar a execução dos modelos.
4. Suba os serviços:
    - `docker-compose up -d --build`
5. Aguarde os health checks (Neo4j, Qdrant, Ollama, RabbitMQ):
    - `docker compose ps`
    - `docker compose logs -f janus-api` até ver “Application startup complete”.
6. Acesse a API: `http://localhost:8000` (Swagger em `/docs`).
7. Verifique serviços auxiliares:
    - Neo4j Browser: `http://localhost:7474` (login `NEO4J_USER/NEO4J_PASSWORD`)
    - Qdrant health: `http://localhost:6333/healthz`
    - RabbitMQ UI: `http://localhost:15672` (credenciais de `.env`)
8. Modelos (Ollama):
    - O script `init-ollama.sh` puxa automaticamente os modelos: `llama3.1:8b`, `codellama:7b`, `phi3:mini` na primeira
      execução.
    - Opcional: puxe manualmente se necessário:
      ```sh
      docker-compose exec ollama ollama pull llama3.1:8b
      docker-compose exec ollama ollama pull codellama:7b
      docker-compose exec ollama ollama pull phi3:mini
      ```
9. Teste a prontidão:
    - Readiness: `GET http://localhost:8000/readyz`
    - Health da memória semântica: `GET http://localhost:8000/api/v1/knowledge/health`
10. Use os endpoints da Sprint 8:
    - Coleção `http/sprint/Sprint 8.http` possui exemplos prontos de:
        - `/knowledge/consolidate` (atenção: pode levar minutos conforme `limit`)
        - `/knowledge/query`, `/knowledge/concepts/related`, `/knowledge/entity/details`
        - `/knowledge/stats`, `/knowledge/node-types`, `/knowledge/health`, `/knowledge/clear`
11. Parar/Reiniciar:
    - Parar: `docker-compose down`
    - Reiniciar: `docker-compose up -d`
    - Reset completo (apaga dados): remova pastas em `data/*` e suba novamente.

Opção B) Local (sem Docker)

1. Python 3.11 instalado
2. pip install -r requirements.txt
3. Configure o .env (ver seção anterior)
4. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

### Primeira Execução (Ollama)

Na primeira execução com Docker, o script `init-ollama.sh` inicia o servidor Ollama e baixa automaticamente os modelos
necessários. Isso pode levar alguns minutos.

Caso prefira executar manualmente:

```sh
docker-compose exec ollama ollama pull llama3.1:8b
docker-compose exec ollama ollama pull codellama:7b
docker-compose exec ollama ollama pull phi3:mini
```

Dica: Em Windows, se make não estiver disponível, use os comandos diretos acima. Para quem tem Make, há alvos úteis (ver
próxima seção).

### Dicas e Troubleshooting (Docker)

- Portas em uso: ajuste mapeamentos no `docker-compose.yml` se houver conflito.
- Recursos do Docker Desktop: aumente memória/CPU se os serviços reiniciarem (Settings → Resources).
- Neo4j falhando ao iniciar: verifique `NEO4J_USER/NEO4J_PASSWORD` no `.env` e plugins APOC no compose.
- Sem GPU: remova o bloco `deploy.resources.reservations.devices` do serviço `ollama` (ver seção “GPU”).
- Logs úteis:
    - `docker compose logs -f janus-api`
    - `docker compose logs -f neo4j`
    - `docker compose logs -f qdrant`
    - `docker compose logs -f ollama`

## Scripts e Tarefas (Makefile)

- make run — inicia a API com autoreload
- make test — executa testes (pytest, se instalado)
- make lint — roda ruff/flake8/pyflakes (fallback: verificação de sintaxe)
- make format — formata com ruff/black
- make install-dev — instala ruff, black, pytest

Equivalentes diretos:

- uvicorn app.main:app --reload
- pytest (se existir suíte de testes)

## Endpoints úteis

- Saúde básica: GET /healthz
- Liveness: GET /livez
- Readiness: GET /readyz (verifica Neo4j, Qdrant e LLM best-effort)
- API v1 (prefixo): /api/v1
    - /system/status
    - /knowledge/index
    - /agent/execute
    - /memory/..., /learning/..., etc. (veja /docs)

Coleções HTTP para testes manuais: pasta http/ contém exemplos .http.

## Observabilidade

- Métricas Prometheus: /metrics na API
- Dashboard Grafana: Importe o arquivo `dashboards/janus_component_resilience_dashboard.json` para visualizar a
  latência (p95/p99), taxa de erros e o estado dos Circuit Breakers de cada componente.

## Estrutura do Projeto

.
├── app/ # Código-fonte
│ ├── api/ # Endpoints FastAPI (v1)
│ ├── core/ # Agentes, LLM manager, memória, prompts, resiliência, etc.
│ ├── db/ # Integrações Neo4j e Qdrant
│ ├── models/ # Schemas Pydantic
│ └── main.py # Ponto de entrada ASGI (uvicorn app.main:app)
├── dashboards/ # Dashboards Grafana
├── http/ # Requisições para testes (HTTP Client)
├── tests/ # Testes automatizados (atualmente vazio)
├── Dockerfile # Imagem da API
├── docker-compose.yml # Orquestração: API, Neo4j, Qdrant, Ollama
├── Makefile # Tarefas de dev
├── requirements.txt # Dependências Python
├── .env.example # Exemplo de arquivo de configuração
├── GEMINI.md # Guia de uso do co-processador Gemini (detalhado)
└── README.md # Este arquivo

Nota: volumes de dados (data/neo4j, data/qdrant, data/ollama) serão criados pelo Docker quando necessário.

## Testes

- Framework sugerido: pytest
- Estado atual: existe apenas um placeholder (tests/unit/.gitkeep)
- Como rodar:
    - pip install pytest ou make install-dev
    - pytest ou make test

TODO:

- Adicionar testes unitários de módulos core (LLM manager, agent_manager, graph_rag_core, etc.)
- Adicionar testes de API (FastAPI TestClient)
- Configurar cobertura (pytest-cov)

## Licença

Este projeto está licenciado sob a Licença MIT. Veja o arquivo `LICENSE` para mais detalhes. (TODO: Adicionar o arquivo
`LICENSE` ao repositório).

## Notas e TODOs

- Para uso de provedores em nuvem (OpenAI, Gemini), é necessário definir as chaves no .env. Veja também GEMINI.md para
  detalhes de ativação e estratégia de roteamento.
