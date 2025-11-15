## Sumário Executivo
- Janus é um sistema cognitivo modular com API unificada, multi-LLM com roteamento por custo/latência/qualidade, memória semântica (Neo4j/Qdrant), ferramentas dinâmicas, fluxo de aprendizagem e observabilidade (Prometheus/Grafana). Versão atual 1.0.0 ativa.

## 1. Objetivos e Benefícios
- Problema: integrar capacidades de IA de forma confiável e eficiente, controlando custos e oferecendo memória/observabilidade.
- Benefícios: roteamento dinâmico de LLMs com budgets e circuit breakers; memória dual grafo+vetor; autonomia com metas; ferramentas seguras; métricas e dashboards prontos.

## 2. Escopo Funcional
- Funcionalidades: API REST v1 (health, LLM, tools, knowledge, learning, autonomy, observability, workers); meta-agente e reflexion; workers assíncronos (harvest, consolidation, training).
- Tecnologias: Backend Python 3.11, FastAPI, Uvicorn; LangChain; Neo4j, Qdrant; RabbitMQ; Prometheus/Grafana; Frontend Angular 20.
- Dependências: ver `janus/requirements.txt` e `front/package.json`; configuração via `.env` (Pydantic `app/config.py`).

## 3. Arquitetura e Componentes
- Backend: composição de serviços/repositórios inicializados no `lifespan` (API, LLM, memory, knowledge, autonomy, observability, workers). Fluxos com mensageria e cache.
- Frontend: Angular com páginas de documentação, arquitetura, sprints e features de chat e observabilidade básica.
- ASCII (alto nível):
```
[Frontend Angular] -> [FastAPI /api/v1]
   |                  |-- LLM Router (cache/CB/budget)
   |                  |-- Services (LLM, Memory, Knowledge, Autonomy)
   |                  |-- Repos (Neo4j, Qdrant, RabbitMQ)
   |                  |-- Workers (Consolidator, Harvester, Training)
   |                  \-- Metrics (/metrics) -> Prometheus -> Grafana
```

## 4. Stakeholders
- Product Owner: prioridades de metas e roadmap.
- Arquiteto/Tech Lead: decisões de arquitetura, budgets de LLM, observabilidade.
- Backend Eng.: APIs, workers, memória, repositórios.
- Frontend Eng.: UI Angular, integração com APIs.
- DevOps/SRE: Docker, Compose, ambientes, Grafana/Prometheus, segurança.
- QA: cenários .http, testes unitários/integrados e carga.

## 5. Status Atual
- Fase: 1.0.0 estável, com API e observabilidade; workers unificados; consolidação de conhecimento e meta-agente.
- Marcos: endpoints workers start/stop; consolidação batch; Configuration-as-Data (MySQL); métricas ampliadas.
- Desafios: consistência de IDs Qdrant; otimização de timeouts/executores LLM; locks assíncronos; batching Neo4j.

## 6. Documentação
- Disponível: `docs/Architecture.md`, `Configuration.md`, `Usage.md`, `Examples.md`, `Troubleshooting.md`, `Release-Notes-1.0.0.md`, README.
- Lacunas: mapa de stakeholders e RACI; catálogo completo de KPIs e limites alvo; guia de deploy do backend (CI/CD); diagramas visuais persistentes; playbooks de incidentes.

## 7. Métricas e KPIs
- LLM: `llm_requests_total`, `llm_request_latency_seconds`, `llm_provider_spend_usd_total`, `llm_provider_budget_remaining_usd`, `llm_selection_score`.
- Chat: `chat_messages_total`, `chat_message_latency_seconds`, `chat_spend_usd_total`.
- Broker: `broker_messages_published_total`, validações de fila.
- KPIs sugeridos: p95/p99 latência por rota; taxa de erro <1%; custo médio por requisição LLM; utilização de orçamento mensal; throughput de consolidação.

## Referências de Código (amostra)
- Composição e startup: `janus/app/main.py:69-76,140-176,240-256`
- Status do sistema: `janus/app/api/v1/endpoints/system_status.py:43-54,56-135`
- LLM manager e métricas: `janus/app/core/llm/llm_manager.py:23-43,144-169,539-864,1005-1166`
- Broker e filas: `janus/app/core/infrastructure/message_broker.py:19-22,69-123,258-335`
- Configuração: `janus/app/config.py:74-114,135-183,197-241`
- Autonomy: `janus/app/api/v1/endpoints/autonomy.py:116-172,190-234`

## Ambientes
- Desenvolvimento: `docker-compose.yml` (API, Neo4j, Qdrant, RabbitMQ, Prometheus, Grafana, MySQL, Ollama).
- Produção: Frontend CI deploy via FTP com `BACKEND_API_URL`; backend provável via Compose/nuvem (documentar pipeline).

## Plano de Validação e Entregáveis
1) Entrevistas rápidas (30–45 min cada): PO, Arquiteto, Backend, DevOps, QA para preencher RACI, KPIs alvo e pipeline de deploy.
2) Coleta e baseline: capturar /metrics, exportar p95/p99, custos e budgets atuais; validar dashboards Grafana carregados.
3) Documentação: adicionar seção Stakeholders/RACI, KPIs e metas, diagrama ASCII consolidado e links para dashboards.
4) Ambientes: registrar guia de deploy do backend (Compose/Cloud), variáveis, secrets e segurança (API key, CORS).
5) Observabilidade: checklist de alertas e metas por KPI; playbook de incidentes (resumo).

Confirma este plano? Após confirmação, entrego o documento final (Markdown) com a análise estruturada, referências de código e KPIs, mais checklist de validação em ambientes.