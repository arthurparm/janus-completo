import json
from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.security.cpf import is_valid_cpf, normalize_cpf

_LOCALHOST_ORIGINS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "http://localhost:4300",
    "http://127.0.0.1:4300",
]


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore", env_file="app/.env", env_file_encoding="utf-8"
    )

    # App
    APP_NAME: str = "Janus"
    APP_VERSION: str = "0.5.44"
    ENVIRONMENT: str = "development"
    # Identidade
    AGENT_IDENTITY_NAME: str = "Janus"
    IDENTITY_ENFORCEMENT_ENABLED: bool = True

    # Feature flags / modos de execução
    DRY_RUN: bool = False
    PUBLIC_API_MINIMAL: bool = False  # Expor apenas chat/autonomy quando True
    AUTO_INDEX_ON_STARTUP: bool = True  # Indexar automaticamente se o grafo estiver vazio
    INIT_MAS_AGENTS_ON_STARTUP: bool = True  # Inicializar agentes do MAS no startup
    START_ORCHESTRATOR_WORKERS_ON_STARTUP: bool = True  # Iniciar workers de fila no boot do API
    ENABLE_GOOGLE_PRODUCTIVITY_WORKER: bool = False  # Mantem worker opcional em modo disabled por padrao

    # CORS
    # Lista de origens permitidas para chamadas ao backend (produção/desenvolvimento)
    # Pode ser configurada via variável de ambiente CORS_ALLOW_ORIGINS (JSON ou CSV)
    CORS_ALLOW_ORIGINS: list[str] = Field(default_factory=list)

    # Neo4j
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: SecretStr = SecretStr("change_me_neo4j_password")

    # Qdrant
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_HTTPS: bool = False
    QDRANT_API_KEY: SecretStr | None = None
    QDRANT_COLLECTION_EPISODIC: str = "janus_episodic_memory"

    # PostgreSQL - Configuration-as-Data
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "janus"
    POSTGRES_PASSWORD: SecretStr = SecretStr("change_me_postgres_password")
    POSTGRES_DB: str = "janus_db"


    # Firebase
    FIREBASE_ENABLED: bool = False
    FIREBASE_CREDENTIALS_PATH: str | None = "/app/app/serviceAccountKey.json"
    FIREBASE_DATABASE_URL: str | None = None

    # LangSmith
    LANGCHAIN_TRACING_V2: str = "true"
    LANGCHAIN_API_KEY: SecretStr | None = None

    # Memória
    MEMORY_SHORT_TTL_SECONDS: int = 600
    MEMORY_SHORT_MAX_ITEMS: int = 1024
    MEMORY_SHORT_SCAN_MAX_ITEMS: int = 512
    MEMORY_MAX_CONTENT_CHARS: int = 50000
    MEMORY_QUOTA_WINDOW_SECONDS: int = 3600
    MEMORY_QUOTA_MAX_ITEMS_PER_ORIGIN: int = 200
    MEMORY_QUOTA_MAX_BYTES_PER_ORIGIN: int = 5_000_000
    MEMORY_ENCRYPTION_KEY: str | None = None
    MEMORY_PII_REDACT: bool = True

    # Raciocínio
    REASONING_MAX_ITERATIONS: int = 3
    REASONING_MAX_SECONDS: int = 60
    REASONING_MAX_TOKENS: int = 8000

    # Meta-Agente
    META_AGENT_CYCLE_INTERVAL_SECONDS: int = 300
    META_AGENT_MAX_ITERATIONS: int = 3
    META_AGENT_MAX_SECONDS: int = 60
    META_AGENT_MIN_CYCLE_INTERVAL_SECONDS: int = 30
    META_AGENT_TRIGGER_COOLDOWN_SECONDS: int = 20
    META_AGENT_FAILURE_DEBOUNCE_SECONDS: int = 30
    META_AGENT_SCHEDULED_PRIORITY: int = 2
    META_AGENT_FAILURE_BASE_PRIORITY: int = 6
    META_AGENT_SCHEDULER_PUBLISH_TO_QUEUE: bool = True

    # LLM
    LLM_DEFAULT_TIMEOUT_SECONDS: int = 120
    LLM_CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 3
    LLM_CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 30
    LLM_RETRY_MAX_ATTEMPTS: int = 3
    LLM_RETRY_INITIAL_BACKOFF_SECONDS: float = 0.5
    LLM_RETRY_MAX_BACKOFF_SECONDS: float = 5.0
    LLM_CACHE_TTL_SECONDS: int = 3600
    LLM_RESPONSE_CACHE_USE_MSGPACK: bool = False
    LLM_POOL_MAX_SIZE: int = 16
    LLM_POOL_TTL_SECONDS: int = 3600
    LLM_POOL_WARM_PROVIDERS: list[str] = []
    LLM_EXECUTOR_MAX_WORKERS: int = 32
    LLM_MAX_PROMPT_LENGTH: int = 100000
    # Política econômica e tetos de custo
    LLM_ECONOMY_POLICY: str = "balanced"  # strict | balanced | quality
    LLM_MAX_COST_PER_REQUEST_USD: dict[str, float] = {
        "orchestrator": 0.02,
        "code_generator": 0.05,
        "knowledge_curator": 0.01,
    }
    # Tokens esperados (em milhares) por requisição por papel (input+output total)
    LLM_EXPECTED_KTOKENS_BY_ROLE: dict[str, float] = {
        "orchestrator": 2.0,
        "code_generator": 3.0,
        "knowledge_curator": 1.5,
    }

    # Exploração e estimativa dinâmica
    LLM_EXPLORATION_PERCENT: float = 0.10  # fração de requisições para explorar candidatos
    LLM_DYNAMIC_EXPECTED_ALPHA: float = 0.20  # fator de suavização da EMA

    # Limites de geração de tokens
    LLM_MAX_GENERATION_TOKENS_CAP: int = 4096
    LLM_MIN_GENERATION_TOKENS: int = 64
    LLM_TASK_POLICY: dict[str, Any] = Field(default_factory=dict)

    # Auto-tuning de timeouts
    TIMEOUT_AUTO_TUNE_ENABLED: bool = True
    TIMEOUT_AUTO_TUNE_PERCENTILE: float = 0.95
    TIMEOUT_AUTO_TUNE_PAD_SECONDS: float = 0.5
    TIMEOUT_MIN_SECONDS_MAP: dict[str, float] = {
        "llm": 5.0,
        "qdrant_search": 3.0,
        "neo4j_query": 3.0,
        "rabbitmq_management": 2.0,
    }
    TIMEOUT_MAX_SECONDS_MAP: dict[str, float] = {
        "llm": 180.0,
        "qdrant_search": 120.0,
        "neo4j_query": 120.0,
        "rabbitmq_management": 30.0,
    }

    # Orçamentos diários multitenant (sem persistência)
    TENANT_USER_DAILY_BUDGET_USD: float = 1.00
    TENANT_PROJECT_DAILY_BUDGET_USD: float = 3.00

    # Penalização de custo para modelos que excedem tetos
    LLM_COST_PENALTY_INCREMENT: float = 0.25
    LLM_COST_PENALTY_MAX_FACTOR: float = 2.0

    # Auto-Healer - Database
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600
    DB_POOL_TIMEOUT: int = 30

    # LLM Providers
    OPENAI_API_KEY: SecretStr | None = None
    OPENAI_MODEL_NAME: str = "gpt-4o"
    OPENAI_MODELS: list[str] = ["gpt-4o"]
    OPENAI_HTTP_MAX_CONNECTIONS: int = 100
    OPENAI_HTTP_MAX_KEEPALIVE: int = 20
    OPENAI_HTTP_TIMEOUT_SECONDS: float = 60.0
    GEMINI_API_KEY: SecretStr | None = None
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    GEMINI_MODELS: list[str] = ["gemini-2.5-flash"]
    OLLAMA_HOST: str = "http://ollama:11434"
    OLLAMA_ORCHESTRATOR_MODEL: str = "qwen2.5:14b"
    OLLAMA_CODER_MODEL: str = "qwen2.5-coder:14b"
    OLLAMA_CURATOR_MODEL: str = "qwen2.5:14b"
    DEEPSEEK_API_KEY: SecretStr | None = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL_NAME: str = "deepseek-chat"
    DEEPSEEK_MODELS: list[str] = ["deepseek-chat", "deepseek-reasoner"]
    DEEPSEEK_TEMPERATURE: float = 0.0
    DEEPSEEK_TEMPERATURE_BY_ROLE: dict[str, float] = Field(
        default_factory=lambda: {
            # ConversaÇõÇœ/planejamento (mais criativo) e anÇ­lise leve
            "orchestrator": 1.0,
            # Coding/math deve ser determinÇ­stico
            "code_generator": 0.0,
            # Curadoria de conhecimento/RAG: baixa aleatoriedade
            "knowledge_curator": 0.3,
            # Auditoria/seguranÇõa: determinÇ­stico
            "security_auditor": 0.0,
            # Reasoning mais controlado (DeepSeek R1 muitas vezes ignora temp, mas fixamos baixo)
            "reasoner": 0.0,
        }
    )
    XAI_API_KEY: SecretStr | None = None
    XAI_BASE_URL: str = "https://api.x.ai/v1"
    XAI_MODEL_NAME: str = "grok-4-1-fast-reasoning"
    XAI_MODELS: list[str] = [
        "grok-4-1-fast-reasoning",
        "grok-4",
        "grok-3",
    ]
    OPENROUTER_API_KEY: SecretStr | None = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL_NAME: str = "deepseek/deepseek-r1-0528:free"
    EMBEDDINGS_OPENROUTER_MODEL_NAME: str = "qwen/qwen3-embedding-8b"
    OPENROUTER_MODELS: list[str] = [
        "deepseek/deepseek-r1-0528:free",
        "qwen/qwen3-coder:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.1-405b-instruct:free",
        "tngtech/deepseek-r1t-chimera:free",
    ]

    # P4 — Orçamentação e Preços por Provedor
    # Orçamentos mensais (USD) por provedor
    OPENAI_MONTHLY_BUDGET_USD: float = 10.0
    GEMINI_MONTHLY_BUDGET_USD: float = 10.0
    OLLAMA_MONTHLY_BUDGET_USD: float = 0.0
    DEEPSEEK_MONTHLY_BUDGET_USD: float = 10.0
    XAI_MONTHLY_BUDGET_USD: float = 10.0
    OPENROUTER_MONTHLY_BUDGET_USD: float = 5.0
    # Dynamic Budget Guardrail: Force LOCAL_ONLY when total cloud spend >= this % of total budget
    BUDGET_THRESHOLD_PERCENT: float = 0.90

    # Deep Self-Healing: CoderAgent retry loop settings
    # Maximum iterations for compiler error auto-correction (DeepSeek makes this affordable)
    CODER_MAX_SELF_HEALING_ITERATIONS: int = 20
    CODER_SELF_HEALING_ENABLED: bool = True

    # Reasoning RAG (HyDE & Re-Ranking)
    # HyDE: Generate hypothetical document before semantic search
    RAG_HYDE_ENABLED: bool = True
    # Re-Ranking: Use LLM to re-rank retrieved chunks
    RAG_RERANK_ENABLED: bool = True
    RAG_RERANK_TOP_K: int = 5
    RAG_RERANK_BACKEND: str = "cross_encoder"  # cross_encoder | heuristic
    RAG_RERANK_CROSS_ENCODER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RAG_RERANK_CROSS_ENCODER_WEIGHT: float = 0.75
    RAG_RERANK_BASE_SCORE_WEIGHT: float = 0.25
    RAG_RERANK_METADATA_WEIGHT: float = 0.10
    RAG_RERANK_RECENCY_WEIGHT: float = 0.05
    RAG_RERANK_HEURISTIC_TEXT_WEIGHT: float = 0.55
    RAG_RERANK_HEURISTIC_BASE_WEIGHT: float = 0.30
    RAG_RERANK_HEURISTIC_METADATA_WEIGHT: float = 0.10
    RAG_RERANK_HEURISTIC_RECENCY_WEIGHT: float = 0.05
    RAG_RERANK_CANDIDATE_MULTIPLIER: int = 3
    RAG_RERANK_MAX_CONTENT_CHARS: int = 1200

    # Preço por 1k tokens (USD) por provedor
    # Valores padrão conservadores para evitar fallback indevido por teto de custo.
    OPENAI_COST_PER_1K_INPUT_USD: float = 0.005
    OPENAI_COST_PER_1K_OUTPUT_USD: float = 0.015
    GEMINI_COST_PER_1K_INPUT_USD: float = 0.0005
    GEMINI_COST_PER_1K_OUTPUT_USD: float = 0.0015
    OLLAMA_COST_PER_1K_INPUT_USD: float = 0.0
    OLLAMA_COST_PER_1K_OUTPUT_USD: float = 0.0
    DEEPSEEK_COST_PER_1K_INPUT_USD: float = 0.00028
    DEEPSEEK_COST_PER_1K_OUTPUT_USD: float = 0.00042
    DEEPSEEK_COST_PER_1K_CACHE_READ_USD: float = 0.000028
    XAI_COST_PER_1K_INPUT_USD: float = 0.00020
    XAI_COST_PER_1K_OUTPUT_USD: float = 0.00050
    OPENROUTER_COST_PER_1K_INPUT_USD: float = 0.0
    OPENROUTER_COST_PER_1K_OUTPUT_USD: float = 0.0
    # Tunáveis de desempenho do Ollama (opcionais, aplicados se definidos)
    OLLAMA_KEEP_ALIVE: str | None = "30m"  # mantém modelos carregados para reduzir cold-start
    OLLAMA_NUM_CTX: int | None = 4096  # contexto máximo por requisição
    OLLAMA_NUM_THREAD: int | None = None  # threads CPU (auto se None)
    OLLAMA_NUM_BATCH: int | None = None  # tamanho de batch de tokens
    OLLAMA_GPU_LAYERS: int | None = None  # camadas na GPU (auto se None)

    # Modularidade: candidatos por papel
    # Estratégia padrão: prioriza provedores cloud compatíveis com o roteador atual.
    LLM_CLOUD_MODEL_CANDIDATES: dict[str, list[str]] = {
        "orchestrator": [
            "deepseek:deepseek-chat",
            "xai:grok-4-1-fast-reasoning",
            "openai:gpt-5-mini",
        ],
        "code_generator": [
            "deepseek:deepseek-reasoner",
            "openai:gpt-5-mini",
            "xai:grok-4-1-fast-reasoning",
        ],
        "knowledge_curator": [
            "deepseek:deepseek-chat",
            "openai:gpt-5-mini",
            "xai:grok-4-1-fast-reasoning",
        ]
    }

    # Tabelas de preço por modelo (se ausente, usa preço default do provedor)
    OPENAI_MODEL_PRICING: dict[str, dict[str, float]] = {
        "gpt-4o": {"input_per_1k_usd": 0.005, "output_per_1k_usd": 0.015},
        "gpt-5-mini": {"input_per_1k_usd": 0.00025, "output_per_1k_usd": 0.002},
    }
    GEMINI_MODEL_PRICING: dict[str, dict[str, float]] = {
        "gemini-2.5-flash": {"input_per_1k_usd": 0.0005, "output_per_1k_usd": 0.0015},
    }
    DEEPSEEK_MODEL_PRICING: dict[str, dict[str, float]] = {
        "deepseek-chat": {
            "input_per_1k_usd": 0.00028,
            "output_per_1k_usd": 0.00042,
            "cache_read_per_1k_usd": 0.000028,
        },
        "deepseek-reasoner": {
            "input_per_1k_usd": 0.00028,
            "output_per_1k_usd": 0.00042,
            "cache_read_per_1k_usd": 0.000028,
        },
    }
    XAI_MODEL_PRICING: dict[str, dict[str, float]] = {
        "grok-4.1-fast-reasoning": {
            "input_per_1k_usd": 0.00020,
            "output_per_1k_usd": 0.00050,
        },
        "grok-4.1-fast": {
            "input_per_1k_usd": 0.00020,
            "output_per_1k_usd": 0.00050,
        },
        "grok-4-1-fast-reasoning": {
            "input_per_1k_usd": 0.00020,
            "output_per_1k_usd": 0.00050,
        },
        "grok-4": {
            "input_per_1k_usd": 0.00030,
            "output_per_1k_usd": 0.00070,
        },
        "grok-3": {
            "input_per_1k_usd": 0.00025,
            "output_per_1k_usd": 0.00060,
        },
    }
    OPENROUTER_MODEL_PRICING: dict[str, dict[str, float]] = {
        "deepseek/deepseek-r1-0528:free": {"input_per_1k_usd": 0.0, "output_per_1k_usd": 0.0},
        "qwen/qwen3-coder:free": {"input_per_1k_usd": 0.0, "output_per_1k_usd": 0.0},
        "meta-llama/llama-3.3-70b-instruct:free": {"input_per_1k_usd": 0.0, "output_per_1k_usd": 0.0},
    }

    # Rate Limits por modelo (TPM=tokens/min, RPM=requests/min, TPD=tokens/day, RPD=requests/day)
    # Formato: {"provider:model": {"tpm": int, "rpm": int, "rpd": int, "tpd": int}}
    LLM_RATE_LIMITS: dict[str, dict[str, int]] = {}
    LLM_RATE_LIMIT_THRESHOLD: float = 0.80  # Começa a evitar modelo quando atinge 80% do limite
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_IP_PER_MIN: int = 60
    RATE_LIMIT_FAIL_CLOSED: bool = False

    # Estáticos
    SERVE_STATIC_FILES: bool = False
    STATIC_FILES_DIR: str = "frontend/dist/janus-angular/browser"

    # Timeouts de infraestrutura
    QDRANT_DEFAULT_TIMEOUT_SECONDS: int = 60
    NEO4J_DEFAULT_TIMEOUT_SECONDS: int = 30
    RATE_LIMIT_PER_KEY_PER_MIN: int = 300

    AUTH_JWT_SECRET: str | None = None
    AUTH_JWT_EXPIRES_SECONDS: int = 3600
    AUTH_RESET_TOKEN_TTL_SECONDS: int = 3600
    AUTH_RESET_RETURN_TOKEN: bool = False
    AUTH_TRUST_X_USER_ID_HEADER: bool = False
    AUTH_ADMIN_CPF_ALLOWLIST: list[str] = []
    AUTH_RATE_LIMIT_ENABLED: bool = True
    AUTH_RATE_LIMITS: dict[str, dict[str, int]] = {
        "auth.token": {"max_attempts": 20, "window_seconds": 60},
        "auth.local_login": {"max_attempts": 10, "window_seconds": 60},
        "auth.local_request_reset": {"max_attempts": 5, "window_seconds": 60},
        "auth.local_reset": {"max_attempts": 10, "window_seconds": 60},
    }
    AI_INTENT_ROUTING_ENABLED: bool = True
    AI_INTENT_RISK_ESCALATION_ENABLED: bool = True
    AI_INTENT_ROUTING_MIN_CONFIDENCE: float = 0.72
    AI_INTENT_ROUTING_ORCHESTRATOR_OVERRIDE_CONFIDENCE: float = 0.82
    AI_INTENT_ROUTING_URGENCY_OVERRIDE_CONFIDENCE: float = 0.76
    AI_ANOMALY_DETECTION_ENABLED: bool = True
    AI_ANOMALY_WINDOW_HOURS: int = 6
    AI_ANOMALY_BUCKET_MINUTES: int = 10
    AI_ANOMALY_MIN_EVENTS: int = 30
    AI_ANOMALY_ZSCORE_THRESHOLD: float = 2.5
    AI_ANOMALY_BACKLOG_THRESHOLD: int = 200
    AI_ANOMALY_QUEUE_NAMES: list[str] = [
        "janus.knowledge.consolidation",
        "janus.agent.tasks",
        "janus.neural.training",
        "janus.meta_agent.cycle",
        "janus.tasks.router",
    ]
    AI_DOC_ENRICHMENT_ENABLED: bool = True
    AI_DOC_ENRICHMENT_MAX_TEXT_CHARS: int = 12000
    AI_DOC_ENRICHMENT_MAX_ENTITIES_PER_TYPE: int = 8
    AI_DOC_ENRICHMENT_SUMMARY_MAX_CHARS: int = 280
    SYSTEM_USER_EMAIL: str | None = None
    SYSTEM_USER_USERNAME: str | None = None
    SYSTEM_USER_DISPLAY_NAME: str | None = "Janus"
    SYSTEM_USER_PASSWORD: SecretStr | None = None
    SYSTEM_USER_ROLE: str = "SYSTEM"

    # RabbitMQ
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "janus"
    RABBITMQ_PASSWORD: SecretStr = SecretStr("change_me_rabbitmq_password")
    RABBITMQ_MANAGEMENT_PORT: int = 15672
    BROKER_USE_MSGPACK: bool = True

    # Tooling safety
    LAUNCH_APP_ALLOWED_APPS: list[str] = []

    # Redis
    REDIS_ENABLED: bool = False
    REDIS_URL: str = "redis://redis:6379"

    RABBITMQ_QUEUE_CONFIG: dict[str, dict[str, Any]] = {
        "janus.knowledge.consolidation": {
            "x-message-ttl": 86400000,
            "x-max-length": 10000,
            "x-dead-letter-exchange": "janus.dlx",
        },
        "janus.agent.tasks": {
            "x-message-ttl": 86400000,
            "x-max-length": 10000,
            "x-dead-letter-exchange": "janus.dlx",
        },
        "janus.neural.training": {
            "x-message-ttl": 3600000,
            "x-max-length": 10000,
            "x-max-priority": 5,
            "x-dead-letter-exchange": "janus.dlx",
        },
        "janus.data.harvesting": {
            "x-message-ttl": 86400000,
            "x-max-length": 10000,
            "x-dead-letter-exchange": "janus.dlx",
        },
        "janus.meta_agent.cycle": {
            "x-message-ttl": 86400000,
            "x-max-length": 10000,
            "x-max-priority": 10,
            "x-dead-letter-exchange": "janus.dlx",
        },
        "janus.tasks.codex": {
            "x-message-ttl": 86400000,
            "x-max-length": 10000,
            "x-max-priority": 10,
            "x-dead-letter-exchange": "janus.dlx",
        },
        "janus.tasks.reflexion": {
            "x-message-ttl": 86400000,
            "x-max-length": 10000,
            "x-max-priority": 10,
            "x-dead-letter-exchange": "janus.dlx",
        },
        "janus.productivity.google": {
            "x-message-ttl": 600000,
            "x-max-length": 10000,
            "x-max-priority": 5,
            "x-dead-letter-exchange": "janus.dlx",
        },
        "janus.failure.detected": {
            "x-message-ttl": 86400000,
            "x-max-length": 10000,
            "x-max-priority": 10,
            "x-dead-letter-exchange": "janus.dlx",
        },
        "janus.dlq": {
            "x-message-ttl": 604800000,  # 7 days retention for dead letters
            "x-max-length": 10000,
        },
        "default": {
            "x-message-ttl": 86400000,
            "x-max-length": 10000,
            "x-dead-letter-exchange": "janus.dlx",
        },
    }

    # Sprint 2: Knowledge Consolidator
    KNOWLEDGE_CONSOLIDATOR_INTERVAL_SECONDS: int = 60
    KNOWLEDGE_MIN_CONFIDENCE: float = 0.6
    RAG_HYBRID_VECTOR_WEIGHT: float = 0.7
    RAG_HYBRID_GRAPH_WEIGHT: float = 0.3
    DOCS_MAX_FILE_SIZE_BYTES: int = 100_000_000
    DOCS_MAX_POINTS_PER_USER: int = 50000
    PRODUCTIVITY_DAILY_LIMITS: dict[str, int] = {
        "calendar.write": 500,
        "mail.send": 100,
        "notes.write": 1000,
    }
    PRODUCTIVITY_UNLIMITED_USERS: list[str] = []
    GOOGLE_OAUTH_CLIENT_ID: SecretStr | None = None
    GOOGLE_OAUTH_CLIENT_SECRET: SecretStr | None = None
    GOOGLE_OAUTH_REDIRECT_URI: str | None = None
    TRAINING_GPU_BUDGET_PER_USER: dict[str, float] = {}
    # CLI externo (Codex/Jules)
    EXTERNAL_CLI_ENABLED: bool = True
    EXTERNAL_CLI_TIMEOUT_SECONDS: int = 600
    EXTERNAL_CLI_MAX_OUTPUT_CHARS: int = 20000
    TOOL_DAILY_QUOTAS: dict[str, int] = {
        "codex_exec": 10,
        "codex_review": 10,
        "jules_new": 5,
        "jules_pull": 10,
    }
    MIN_DEPLOY_ACCURACY: float = 0.7
    LLM_AB_EXPERIMENT_ID: int | None = None

    # Sprint 3: Web Search
    TAVILY_API_KEY: SecretStr | None = None
    CONTEXT_WEB_CACHE_TTL_SECONDS: int = 1800
    CONTEXT_WEB_CACHE_MAX_ITEMS: int = 512

    # Sprint 4: Python Sandbox (epicbox)
    SANDBOX_MODE: str = "auto"
    SANDBOX_DOCKER_IMAGE: str = "python:3.11-slim"
    SANDBOX_TIMEOUT_SECONDS: int = 15
    SANDBOX_MEM_LIMIT_MB: int = 16384
    SANDBOX_CPU_LIMIT: float = 8.0
    SANDBOX_MAX_OUTPUT_LENGTH: int = 25000

    # Sprint 5: Reflexion
    REFLEXION_MAX_ITERATIONS: int = 3
    REFLEXION_MAX_TIME_SECONDS: int = 180
    REFLEXION_SUCCESS_THRESHOLD: float = 0.8

    # Observabilidade
    OTEL_ENABLED: bool = False
    OTEL_OTLP_ENDPOINT: str | None = None
    OTEL_SERVICE_NAME: str | None = None
    LOG_SAMPLING_RATE: float = 1.0
    AUDIT_PURGE_INTERVAL_SECONDS: int = 3600
    AUDIT_RETENTION_DAYS: int = 30
    OQ_SLO_WINDOW_MINUTES: int = 15
    OQ_SLO_MIN_EVENTS_PER_DOMAIN: int = 20
    OQ_SLO_CHAT_MAX_ERROR_RATE_PCT: float = 5.0
    OQ_SLO_CHAT_MAX_P95_LATENCY_MS: float = 3500.0
    OQ_SLO_RAG_MAX_ERROR_RATE_PCT: float = 5.0
    OQ_SLO_RAG_MAX_P95_LATENCY_MS: float = 4500.0
    OQ_SLO_TOOLS_MAX_ERROR_RATE_PCT: float = 3.0
    OQ_SLO_TOOLS_MAX_P95_LATENCY_MS: float = 2500.0
    OQ_SLO_WORKERS_MAX_ERROR_RATE_PCT: float = 3.0
    OQ_SLO_WORKERS_MAX_P95_LATENCY_MS: float = 4000.0
    CHAT_SSE_MAX_CHAT_STREAMS_PER_USER: int = 2
    CHAT_SSE_MAX_AGENT_EVENT_STREAMS_PER_USER: int = 2
    CHAT_SSE_MAX_CONNECTIONS_PER_USER: int = 4
    CHAT_SSE_MAX_GLOBAL_CONNECTIONS: int = 250

    # Tailscale Serve Configuration
    TAILSCALE_SERVE_ENABLED: bool = False
    TAILSCALE_HOST: str | None = None
    TAILSCALE_BACKEND_URL: str | None = None
    TAILSCALE_FRONTEND_URL: str | None = None

    # CORS para Tailscale - adicionar domínios Tailscale aos domínios permitidos
    @field_validator("CORS_ALLOW_ORIGINS", mode="before")
    def _add_tailscale_origins(cls, v: Any, info):
        # Se Tailscale estiver habilitado, adicionar origens Tailscale
        tailscale_enabled = info.data.get("TAILSCALE_SERVE_ENABLED", False)
        tailscale_host = info.data.get("TAILSCALE_HOST", "")
        environment = str(info.data.get("ENVIRONMENT", "development")).strip().lower()
        is_prod = environment == "production"

        # Parse existing origins
        if isinstance(v, str):
            s = v.strip()
            if not s:
                origins = []
            elif s == "*":
                origins = ["*"]
            elif s.startswith("["):
                try:
                    parsed = json.loads(s)
                    origins = [str(x).strip() for x in parsed if str(x).strip()]
                except Exception:
                    origins = [x.strip() for x in s.split(",") if x.strip()]
            else:
                origins = [x.strip() for x in s.split(",") if x.strip()]
        elif isinstance(v, list):
            origins = [str(x).strip() for x in v if str(x).strip()]
        else:
            origins = []

        if not origins and not is_prod:
            # Default seguro para desenvolvimento local.
            origins = list(_LOCALHOST_ORIGINS)

        if is_prod and "*" in origins:
            raise ValueError(
                "CORS_ALLOW_ORIGINS não pode conter '*' em produção. Defina domínios explícitos."
            )

        # Adicionar origens Tailscale se habilitado
        if tailscale_enabled and tailscale_host:
            tailscale_origin = f"https://{tailscale_host}"
            if tailscale_origin not in origins and "*" not in origins:
                origins.append(tailscale_origin)

        return origins

    @field_validator("PRODUCTIVITY_UNLIMITED_USERS", mode="before")
    def _parse_productivity_unlimited_users(cls, v: Any):
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            if s.startswith("["):
                try:
                    arr = json.loads(s)
                    return [str(x).strip().lower() for x in arr if str(x).strip()]
                except Exception:
                    pass
            return [x.strip().lower() for x in s.split(",") if x.strip()]
        if isinstance(v, list):
            return [str(x).strip().lower() for x in v if str(x).strip()]
        return []

    @field_validator("AUTH_ADMIN_CPF_ALLOWLIST", mode="before")
    def _parse_auth_admin_cpf_allowlist(cls, v: Any):
        items: list[str] = []
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            if s.startswith("["):
                try:
                    arr = json.loads(s)
                    items = [str(x).strip() for x in arr if str(x).strip()]
                except Exception:
                    items = [x.strip() for x in s.split(",") if x.strip()]
            else:
                items = [x.strip() for x in s.split(",") if x.strip()]
        elif isinstance(v, list):
            items = [str(x).strip() for x in v if str(x).strip()]
        else:
            return []

        normalized = [normalize_cpf(item) for item in items]
        return [cpf for cpf in normalized if is_valid_cpf(cpf)]

    # ======= Validadores para variáveis de ambiente complexas =======

    @field_validator(
        "OPENAI_MODELS", "GEMINI_MODELS", "DEEPSEEK_MODELS", "XAI_MODELS", mode="before"
    )
    def _parse_models_list(cls, v: Any):
        # Aceita JSON array ou lista separada por vírgulas
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("["):
                try:
                    arr = json.loads(s)
                    return [str(x).strip() for x in arr]
                except Exception:
                    pass
            return [x.strip() for x in s.split(",") if x.strip()]
        return v

    @field_validator("LLM_CLOUD_MODEL_CANDIDATES", mode="before")
    def _parse_candidates(cls, v: Any):
        # Aceita JSON objeto {role: ["provider:model", ...]} ou string separada por vírgulas como default para orchestrator
        if isinstance(v, str):
            s = v.strip()
            try:
                obj = json.loads(s)
                parsed: dict[str, list[str]] = {}
                for k, val in obj.items():
                    if isinstance(val, list):
                        parsed[k] = [str(x).strip() for x in val if str(x).strip()]
                    elif isinstance(val, str):
                        parsed[k] = [val.strip()] if val.strip() else []
                return parsed
            except Exception:
                items = [x.strip() for x in s.split(",") if x.strip()]
                return {"orchestrator": items} if items else {}
        return v or {}

    @field_validator("TOOL_DAILY_QUOTAS", mode="before")
    def _parse_tool_daily_quotas(cls, v: Any):
        # Aceita JSON objeto {tool: int} ou string "tool=10,tool2=5"
        if isinstance(v, str):
            s = v.strip()
            try:
                obj = json.loads(s)
                if isinstance(obj, dict):
                    parsed: dict[str, int] = {}
                    for k, val in obj.items():
                        try:
                            parsed[str(k)] = int(val)
                        except Exception:
                            parsed[str(k)] = 0
                    return parsed
            except Exception:
                parsed: dict[str, int] = {}
                parts = [x.strip() for x in s.split(",") if x.strip()]
                for p in parts:
                    if "=" in p:
                        k, v_str = p.split("=", 1)
                        try:
                            parsed[k.strip()] = int(v_str.strip())
                        except Exception:
                            parsed[k.strip()] = 0
                return parsed
        if isinstance(v, dict):
            parsed = {}
            for k, val in v.items():
                try:
                    parsed[str(k)] = int(val)
                except Exception:
                    parsed[str(k)] = 0
            return parsed
        return {}

    @field_validator("LLM_TASK_POLICY", mode="before")
    def _parse_llm_task_policy(cls, v: Any):
        # Accept JSON object or dict for task routing policy.
        if isinstance(v, str):
            s = v.strip()
            try:
                obj = json.loads(s)
                return obj if isinstance(obj, dict) else {}
            except Exception:
                return {}
        return v or {}

    @field_validator(
        "OPENAI_MODEL_PRICING",
        "GEMINI_MODEL_PRICING",
        "DEEPSEEK_MODEL_PRICING",
        "XAI_MODEL_PRICING",
        "OPENROUTER_MODEL_PRICING",
        mode="before",
    )
    def _parse_model_pricing(cls, v: Any):
        # Aceita JSON objeto {model: {input_per_1k_usd: float, output_per_1k_usd: float}}
        if isinstance(v, str):
            try:
                obj = json.loads(v)

                def coerce(d: dict[str, Any]) -> dict[str, float]:
                    return {
                        "input_per_1k_usd": float(d.get("input_per_1k_usd", 0.0)),
                        "output_per_1k_usd": float(d.get("output_per_1k_usd", 0.0)),
                        "cache_read_per_1k_usd": float(d.get("cache_read_per_1k_usd", 0.0)),
                    }

                return {str(k): coerce(val) for k, val in obj.items() if isinstance(val, dict)}
            except Exception:
                return {}
        return v or {}

    @field_validator("LLM_MAX_COST_PER_REQUEST_USD", "LLM_EXPECTED_KTOKENS_BY_ROLE", mode="before")
    def _parse_role_float_maps(cls, v: Any):
        # Aceita JSON objeto {role: float} ou string "role=value,role2=value2"
        if isinstance(v, str):
            s = v.strip()
            try:
                obj = json.loads(s)
                parsed: dict[str, float] = {}
                for k, val in obj.items():
                    try:
                        parsed[str(k)] = float(val)
                    except Exception:
                        parsed[str(k)] = 0.0
                return parsed
            except Exception:
                parsed: dict[str, float] = {}
                parts = [x.strip() for x in s.split(",") if x.strip()]
                for p in parts:
                    if "=" in p:
                        k, v_str = p.split("=", 1)
                        try:
                            parsed[k.strip()] = float(v_str.strip())
                        except Exception:
                            parsed[k.strip()] = 0.0
                return parsed
        return v or {}

    @field_validator("LLM_RATE_LIMITS", mode="before")
    def _parse_rate_limits(cls, v: Any):
        # Aceita JSON objeto {"provider:model": {"tpm": int, "rpm": int, ...}}
        if isinstance(v, str):
            try:
                obj = json.loads(v)
                parsed: dict[str, dict[str, int]] = {}
                for model_key, limits in obj.items():
                    if isinstance(limits, dict):
                        parsed[str(model_key)] = {
                            k: int(val) for k, val in limits.items() if val is not None
                        }
                return parsed
            except Exception:
                return {}
        return v or {}

    # Workspace e File System
    WORKSPACE_ROOT: str = "/app/workspace"

    def update(self, new_values: dict[str, Any]):
        """Atualiza as configurações em tempo de execução."""
        for key, value in new_values.items():
            if hasattr(self, key):
                # Helper simples para conversão de tipos básicos se necessário
                # Em um cenário ideal, recriaríamos o modelo, mas aqui queremos atualizar o singleton
                try:
                    current_val = getattr(self, key)
                    if isinstance(current_val, bool) and not isinstance(value, bool):
                        if str(value).lower() in ("true", "1", "yes"):
                            value = True
                        elif str(value).lower() in ("false", "0", "no"):
                            value = False
                    elif isinstance(current_val, int) and not isinstance(value, int):
                        value = int(value)
                    elif isinstance(current_val, float) and not isinstance(value, float):
                        value = float(value)

                    setattr(self, key, value)
                except Exception:
                    # Se falhar conversão, tenta setar direto ou ignora
                    setattr(self, key, value)


settings = AppSettings()
