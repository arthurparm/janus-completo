# Configuração

Este documento detalha as variáveis de ambiente e opções de configuração do Janus AI Architect, conforme definidas em `app/config.py`.

## Estrutura de Configuração

- Aplicativo: nome, versão, ambiente, `DRY_RUN`.
- Bancos: Neo4j (grafo) e Qdrant (vetores).
- Observabilidade: LangSmith/LangChain tracing (opcional).
- Memória: TTL, limites de itens/tamanho, quotas por origem, redaction de PII.
- Raciocínio: limites de iterações, tempo e tokens.
- Meta-Agente: ciclo de inspeção e limites.
- LLMs: provedores, modelos, prioridades, budgets e roteamento dinâmico.
- Rate limiting: por IP e por API key.
- Mensageria: RabbitMQ (host/vhost/credenciais/filas).

## Variáveis Principais (.env)

Aplicativo
- `APP_NAME`, `APP_VERSION`, `ENVIRONMENT` (`development|staging|production`)
- `DRY_RUN` (`true|false`) — modo de simulação para operações de risco

Neo4j
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`

Qdrant
- `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_API_KEY` (opcional)

LangSmith/LangChain (opcional)
- `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`

Memória
- `MEMORY_SHORT_TTL_SECONDS`, `MEMORY_SHORT_MAX_ITEMS`, `MEMORY_MAX_CONTENT_CHARS`
- `MEMORY_QUOTA_WINDOW_SECONDS`, `MEMORY_QUOTA_MAX_ITEMS_PER_ORIGIN`, `MEMORY_QUOTA_MAX_BYTES_PER_ORIGIN`
- `MEMORY_ENCRYPTION_KEY` (opcional), `MEMORY_PII_REDACT` (`true|false`)

Raciocínio
- `REASONING_MAX_ITERATIONS`, `REASONING_MAX_SECONDS`, `REASONING_MAX_TOKENS`

Meta-Agente
- `META_AGENT_CYCLE_INTERVAL_SECONDS`, `META_AGENT_MAX_ITERATIONS`, `META_AGENT_MAX_SECONDS`

LLMs e Roteamento
- OpenAI: `OPENAI_API_KEY`, `OPENAI_MODEL_NAME`
- Gemini: `GEMINI_API_KEY`, `GEMINI_MODEL_NAME`
- Ollama: `OLLAMA_HOST`, `OLLAMA_ORCHESTRATOR_MODEL`, `OLLAMA_CODER_MODEL`, `OLLAMA_CURATOR_MODEL`
- Budgets/Prioridades: `LLM_BUDGETS_JSON`, `LLM_PRIORITIES_JSON` (objeto JSON)

Rate Limiting
- `RATE_LIMIT_ENABLED`, `RATE_LIMIT_PER_IP_PER_MIN`, `RATE_LIMIT_PER_KEY_PER_MIN`

RabbitMQ
- `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `RABBITMQ_VHOST`
- Filas: `NEURAL_TRAINING` via Enum `QueueName.NEURAL_TRAINING = "janus.neural.training"`

## Exemplo de .env Mínimo

```
APP_NAME=Janus
APP_VERSION=1.0.0
ENVIRONMENT=development
DRY_RUN=true

NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

QDRANT_HOST=qdrant
QDRANT_PORT=6333

LANGCHAIN_TRACING_V2=true

RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_IP_PER_MIN=60
RATE_LIMIT_PER_KEY_PER_MIN=300

OLLAMA_HOST=http://ollama:11434
OLLAMA_ORCHESTRATOR_MODEL=llama3.1:8b
OLLAMA_CODER_MODEL=codellama:7b
OLLAMA_CURATOR_MODEL=phi3:mini
```

## Validações e Formatos

- `app/config.py` possui validadores Pydantic para listas, inteiros, decimais e objetos JSON.
- Chaves de provedores são validadas (`_validate_openai_key`, `_validate_gemini_key`).
- Budgets/prioridades podem ser definidos por `user_id`/`project_id`.

## Dicas

- Sempre versionar `.env.example` com chaves vazias para cloud.
- Usar `DRY_RUN=true` em desenvolvimento para operações de risco.
- Ajustar budgets e prioridades conforme custo/qualidade desejados.
- Habilitar tracing LangSmith apenas em ambientes controlados.