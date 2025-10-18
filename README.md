# Janus AI Architect

Versão: `0.2.0` • Status: Ativo • Plataforma: API/Workers • Observabilidade: Prometheus/Grafana

Janus AI Architect é um sistema de arquitetura cognitiva para aplicações IA resilientes, com API unificada, roteamento dinâmico de LLMs, memória semântica, ferramentas dinâmicas, fluxo de aprendizagem e observabilidade completa. O design prioriza confiabilidade, desempenho e custo, operando com circuit breakers, orçamentos, caches, métricas e um meta-agente que otimiza a operação com feedback em ciclo fechado.

- Repositório e documentação detalhada:
  - `doc/Architecture.md` — arquitetura completa e referências de código
  - `doc/Configuration.md` — variáveis e opções de configuração (Pydantic)
  - `doc/Usage.md` — guia prático de uso (local/Docker) e cURL
  - `doc/Examples.md` — exemplos Python/cURL para ferramentas, treino e LLMs
  - `doc/Troubleshooting.md` — diagnóstico e resolução de problemas
  - Histórico/Referência: `doc/DOCUMENTACAO JANUS.md`


## 1. Visão Geral do Sistema

- Objetivo principal: prover um sistema cognitivo modular com API unificada que:
  - Gerencie e roteie LLMs dinamicamente por custo/latência/qualidade
  - Crie e execute ferramentas (dinâmicas) dentro de contexto seguro
  - Construa e utilize memória semântica (Neo4j + Qdrant)
  - Orquestre fluxos de aprendizado (harvesting, treino, avaliação, métricas)
  - Forneça observabilidade em tempo real com métricas, logs e dashboards
- Funcionalidades chave:
  - API REST consistente com versionamento (`/api/v1`) e health checks
  - Roteamento dinâmico de LLMs, budgets, circuit breakers e cache
  - Ferramentas dinâmicas criadas via função/API com categorias, permissões e tags
  - Memória: grafo semântico (Neo4j) + vetor (Qdrant) para contexto e recuperação
  - Aprendizagem: fila (RabbitMQ), workers assíncronos, treino e avaliação
  - Meta-agente: monitoramento, recomendações, otimização contínua
  - Observabilidade: Prometheus endpoints e dashboards Grafana
- Tecnologias:
  - Backend: `Python 3.11`, `FastAPI`, `Uvicorn`
  - Mensageria: `RabbitMQ`
  - Bancos: `Neo4j` (grafo), `Qdrant` (vetor)
  - LLMs: OpenAI, Google, Anthropic e `Ollama` (local), via roteador
  - Observabilidade: `Prometheus`, `Grafana`, integração `LangSmith`
  - Empacotamento: `Docker`, `docker-compose`


## 2. Requisitos do Sistema

- Sistema operacional: Windows, macOS ou Linux
- Requisitos mínimos:
  - Docker e Docker Compose (recomendado) ou Python `3.11` + `pip`
  - Acesso às chaves dos provedores de LLM (opcionais e configuráveis)
  - Serviços: `RabbitMQ`, `Neo4j`, `Qdrant` (fornecidos por `docker-compose.yml`)
- Dependências Python: conforme `requirements.txt`
- GPU (opcional): suporte a `Ollama` com GPU NVIDIA se disponível
- Configuração por `.env`:
  - Consulte `doc/Configuration.md` para lista completa e validações
  - Exemplo mínimo:
```
APP_ENV=development
APP_VERSION=0.2.0
APP_PORT=8000
NEO4J_URL=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4jpassword
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
LLM_PROVIDER_PRIORITIES=openai,gemini,anthropic,ollama
OPENAI_API_KEY=
GEMINI_API_KEY=
ANTHROPIC_API_KEY=
OLLAMA_BASE_URL=http://ollama:11434
```


## 3. Guia de Instalação

- Via Docker Compose (recomendado):
  1) Crie `.env` na raiz conforme exemplo e ajuste chaves/custos/roteamento
  2) Inicie serviços: `docker-compose up -d`
  3) Aguarde readiness:
     - API: `http://localhost:8000/readyz`
     - Neo4j UI: `http://localhost:7474` (user: `neo4j`)
     - Qdrant UI: `http://localhost:6333/dashboard`
     - RabbitMQ UI: `http://localhost:15672` (user: `guest`)
     - Grafana: `http://localhost:3000` (user: `admin` / `admin`)
  4) (Opcional) Baixe modelos no `Ollama`:
     - Execute `./init-ollama.sh` (Linux/macOS) ou adicione modelos manualmente via API
  5) Verifique API: `http://localhost:8000/docs` e `http://localhost:8000/metrics`
  6) Logs: `docker-compose logs -f janus-api` (ou via Grafana)

- Instalação local (sem Docker):
  1) Garantir serviços externos (`RabbitMQ`, `Neo4j`, `Qdrant`) rodando
  2) Python 3.11: `py -3.11 -m venv .venv && .venv\Scripts\activate`
  3) Instalar deps: `pip install -r requirements.txt`
  4) Configurar `.env` e variáveis de provedores
  5) Executar API: `uvicorn app.main:app --host 0.0.0.0 --port 8000`


## 4. Estrutura do Projeto

```
janus-1.0/
├── app/                  # Código da aplicação (API, serviços, core)
│   ├── api/              # Endpoints e handlers
│   ├── config.py         # Configuração (Pydantic), validações
│   ├── core/             # Núcleo: llm, memory, tools, workers, infra
│   ├── db/               # Conectores Neo4j e Qdrant
│   ├── services/         # Regras de negócio e orquestração
│   ├── web/              # Rotas web e templates (visões rápidas)
│   └── main.py           # FastAPI app (inclui /healthz, /readyz)
├── http/                 # Coleções HTTP (exercícios e testes)
├── grafana/              # Dashboards (JSON) para importação
├── doc/                  # Documentação detalhada
├── docker-compose.yml    # Orquestração de serviços
├── requirements.txt      # Dependências Python
├── pyproject.toml        # Configuração de build/ferramentas
└── tests/                # Testes (unit/integration)
```

- Diretórios principais:
  - `app/api/v1/...`: endpoints REST e problem details
  - `app/core/...`: mecanismos de LLM, memória, ferramentas, workers
  - `app/services/...`: serviços de domínio (learning, knowledge, llm, etc.)
  - `app/db/...`: camadas de acesso a Neo4j e Qdrant
  - `app/web/...`: páginas de preview (overview, console)
  - `grafana/dashboards`: dashboards prontos para importação
  - `http/`: requests cURL/HTTP para testes de endpoints


## 5. Funcionalidades Detalhadas

- Roteamento e Gestão de LLMs:
  - Prioridades configuráveis (`LLM_PROVIDER_PRIORITIES`) e budgets por provider/modelo
  - Circuit breakers, retries, timeouts e cache para resiliência e eficiência
  - Fallback para LLM local (`Ollama`) quando provedores externos falham ou excedem custo
- Ferramentas Dinâmicas (Tools):
  - Criação a partir de função nativa ou API HTTP externa
  - Metadados: categorias, tags, permissões; controle de uso e rate limit
  - Execução contextualizada com integração à memória e trilhas de auditoria
- Memória Semântica:
  - Grafo (`Neo4j`) com entidades e relações (consolidação e análise)
  - Vetor (`Qdrant`) para embeddings e recuperação contextual
  - Políticas de retenção, TTL e curadoria (via serviços e workers)
- Aprendizagem (Learning):
  - Harvesting, agendamento de treino, monitoramento de status
  - Avaliações e comparação de modelos; registro de experimentos
  - Pipelines assíncronas via `RabbitMQ` e workers dedicados
- Meta-Agente:
  - Monitoramento de métricas, análise de incidentes e recomendações de otimização
  - Gatilhos de reconfiguração e ajustes dinâmicos para desempenho/custo
- Observabilidade:
  - Endpoints `/metrics`, logs estruturados, dashboards Grafana
  - Integração `LangSmith` para traces de execução de LLMs
- Web Preview:
  - Rotas simples para visão do sistema e console de operações (`app/web`)


## 6. Fluxos de Trabalho

- Criação e uso de Ferramentas:
  1) Criar ferramenta a partir de função/API com metadados
  2) Registrar e habilitar categorias/permissões
  3) Executar em contexto com auditoria e memória
  4) Coletar métricas, analisar uso e otimizar

- Treino e Avaliação (Learning):
  1) Ingerir dados (harvest), montar dataset e versão
  2) Agendar treino via API, worker consome fila `RabbitMQ`
  3) Registrar status, métricas e resultados
  4) Avaliar modelo e comparar com baseline (experimentos)

- Memória e Conhecimento:
  1) Consolidar entidades/relacionamentos no grafo (Neo4j)
  2) Gerar embeddings e indexar no Qdrant
  3) Consultar e recuperar contexto (RAG) para agentes/LLMs

- Solicitação LLM (resumo ASCII):
```
[Request] -> [Router] -> [CB/Cache/Budget] -> [Provider] -> [Result]
                  |           |                 \-> Fallback (Ollama)
               Observability  +----> Metrics/Logs -> Grafana
```


## 7. Exemplos de Uso

- Listar ferramentas:
```
curl -s http://localhost:8000/api/v1/tools
```

- Criar ferramenta (API externa):
```
curl -X POST http://localhost:8000/api/v1/tools \
  -H "Content-Type: application/json" \
  -d '{
    "name": "weather",
    "type": "http",
    "endpoint": "https://api.weather.com/v1/forecast",
    "category": "utilities",
    "permissions": ["network"],
    "tags": ["weather","forecast"]
  }'
```

- Agendar treino:
```
curl -X POST http://localhost:8000/api/v1/learning/train \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "ds-2024-10", "model": "custom-bert", "epochs": 3}'
```

- Checar status de treino:
```
curl -s http://localhost:8000/api/v1/learning/train/status?job_id=12345
```

- Mais exemplos: consulte `doc/Examples.md` e as coleções em `http/`


## 8. Documentação da API

- Descoberta: `http://localhost:8000/docs` e `http://localhost:8000/openapi.json`
- Health/Status:
  - `GET /healthz` — checagem de vida do processo
  - `GET /readyz` — readiness (dependências e serviços)
  - `GET /api/v1/system/status` — visão consolidada de serviços
- Tools:
  - `GET /api/v1/tools` — listar ferramentas registradas
  - `GET /api/v1/tools/{tool_id}` — detalhes de uma ferramenta
  - `POST /api/v1/tools` — criar ferramenta (função/API)
  - `DELETE /api/v1/tools/{tool_id}` — remover ferramenta
  - `GET /api/v1/tools/categories` — listar categorias
  - `GET /api/v1/tools/permissions` — listar permissões
- Learning:
  - `POST /api/v1/learning/harvest` — ingestão/harvest de dados
  - `POST /api/v1/learning/train` — agendar treinamento
  - `GET /api/v1/learning/train/status` — status de job de treinamento
  - `GET /api/v1/learning/models` — modelos disponíveis
  - `POST /api/v1/learning/evaluate` — avaliar modelo
  - `GET /api/v1/learning/experiments` — listar experimentos
- Knowledge:
  - `GET /api/v1/knowledge/nodes` — listar nós do grafo
  - `GET /api/v1/knowledge/relations` — listar relações
  - `POST /api/v1/knowledge/consolidate` — consolidar conhecimento
  - `GET /api/v1/knowledge/query` — consultar conhecimento
- LLM:
  - `GET /api/v1/llm/health` — saúde do subsistema de LLMs
  - `GET /api/v1/llm/providers` — provedores disponíveis e prioridades
  - `GET /api/v1/llm/cache/status` — status do cache
  - `POST /api/v1/llm/cache/invalidate` — invalidar entradas de cache
  - `GET /api/v1/llm/circuit-breakers` — estado dos circuit breakers
- Observabilidade:
  - `GET /metrics` — métricas Prometheus para dashboards

Observações:
- Modelos de request/response seguem `pydantic` em `app/models/schemas.py`
- Tratamento de erros via `app/api/problem_details.py` e `exception_handlers.py`


## 9. Guia de Contribuição

- Pré-requisitos:
  - Python 3.11, Docker/Compose, `.env` configurado
  - Consulte `doc/Configuration.md` e `.aiassistant/rules/diretrizes de codigo.md`
- Fluxo de contribuição:
  - Abra uma issue descrevendo claramente motivação, escopo e impacto
  - Faça um fork/branch (`feature/xyz`, `fix/abc`), mantenha commits pequenos e claros
  - Siga o estilo do projeto e mantenha mudanças focadas (cirúrgicas)
  - Cubra com testes quando aplicável (`pytest`) e valide API localmente
  - Abra um PR com descrição técnica, screenshots (se aplicável) e checklist:
    - [ ] Passa em testes locais
    - [ ] Mantém compatibilidade com `docker-compose`
    - [ ] Atualiza docs quando necessário (README, `doc/*`)
- Padrões e qualidade:
  - Logs estruturados, mensagens claras e métricas quando relevante
  - Evite refatorações amplas não solicitadas; preserve estilo e contratos
  - Respeite validações Pydantic em `app/config.py`
- Comunicação:
  - Use Issues/PRs para decisões; inclua links a código/arquitetura


## 10. Licença e Créditos

- Licença: MIT (adicione/consulte arquivo `LICENSE` quando disponível)
- Créditos:
  - Arquitetura e desenvolvimento: time Janus
  - Terceiros: OpenAI, Google, Anthropic, Ollama, FastAPI, Neo4j, Qdrant, RabbitMQ, Prometheus, Grafana, LangChain/LangGraph e comunidade OSS


## Observabilidade e Screenshots

- Dashboards disponíveis em `grafana/dashboards/*.json` (importe no Grafana)
- Recomenda-se criar capturas de tela para:
  - Visão Geral (latência, taxa de erro, throughput)
  - Desempenho de LLMs (latência, custo, acertos por tarefa)
- Como capturar:
  - Acesse `http://localhost:3000`, abra o dashboard e salve capturas como `grafana/screenshots/*.png`


## Manutenção e Atualizações

- Versão atual: `0.2.0` (atualize `APP_VERSION` em `.env` e docs quando necessário)
- Para detalhes de arquitetura, configuração, exemplos e troubleshooting:
  - Veja `doc/Architecture.md`, `doc/Configuration.md`, `doc/Usage.md`, `doc/Examples.md`, `doc/Troubleshooting.md`


## Notas finais

- Endpoints de Conhecimento e demais coleções de teste estão disponíveis em `http/`
- Sprints históricos foram descontinuados como documentação; preferir os docs centrais (`doc/*`) e coleções HTTP
- Em caso de dúvida operacional, consulte primeiro `doc/Troubleshooting.md`
