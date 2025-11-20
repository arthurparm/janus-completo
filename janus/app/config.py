import json
from typing import Optional, Dict, List, Any

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra='ignore', env_file='app/.env', env_file_encoding='utf-8'
    )

    # App
    APP_NAME: str = "Janus"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    # Identidade
    AGENT_IDENTITY_NAME: str = "Janus"
    IDENTITY_ENFORCEMENT_ENABLED: bool = True

    # Feature flags / modos de execução
    DRY_RUN: bool = False
    PUBLIC_API_MINIMAL: bool = False  # Expor apenas chat/autonomy quando True

    # CORS
    # Lista de origens permitidas para chamadas ao backend (produção/desenvolvimento)
    # Pode ser configurada via variável de ambiente CORS_ALLOW_ORIGINS (JSON ou CSV)
    CORS_ALLOW_ORIGINS: List[str] = ["*"]

    # Neo4j
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: SecretStr = "password"

    # Qdrant
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[SecretStr] = None
    QDRANT_COLLECTION_EPISODIC: str = "janus_episodic_memory"

    # MySQL - Configuration-as-Data
    MYSQL_HOST: str = "mysql"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "janus"
    MYSQL_PASSWORD: SecretStr = "janus_pass"
    MYSQL_DATABASE: str = "janus_config"
    MYSQL_ROOT_PASSWORD: SecretStr = "janus_root"

    # LangSmith
    LANGCHAIN_TRACING_V2: str = "true"
    LANGCHAIN_API_KEY: Optional[SecretStr] = None

    # Memória
    MEMORY_SHORT_TTL_SECONDS: int = 600
    MEMORY_SHORT_MAX_ITEMS: int = 256
    MEMORY_SHORT_SCAN_MAX_ITEMS: int = 128
    MEMORY_MAX_CONTENT_CHARS: int = 20000
    MEMORY_QUOTA_WINDOW_SECONDS: int = 3600
    MEMORY_QUOTA_MAX_ITEMS_PER_ORIGIN: int = 200
    MEMORY_QUOTA_MAX_BYTES_PER_ORIGIN: int = 5_000_000
    MEMORY_ENCRYPTION_KEY: Optional[str] = None
    MEMORY_PII_REDACT: bool = True

    # Raciocínio
    REASONING_MAX_ITERATIONS: int = 3
    REASONING_MAX_SECONDS: int = 60
    REASONING_MAX_TOKENS: int = 8000

    # Meta-Agente
    META_AGENT_CYCLE_INTERVAL_SECONDS: int = 300
    META_AGENT_MAX_ITERATIONS: int = 3
    META_AGENT_MAX_SECONDS: int = 60

    # LLM
    LLM_DEFAULT_TIMEOUT_SECONDS: int = 60
    LLM_CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 3
    LLM_CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 30
    LLM_RETRY_MAX_ATTEMPTS: int = 3
    LLM_RETRY_INITIAL_BACKOFF_SECONDS: float = 0.5
    LLM_RETRY_MAX_BACKOFF_SECONDS: float = 5.0
    LLM_CACHE_TTL_SECONDS: int = 3600
    LLM_RESPONSE_CACHE_USE_MSGPACK: bool = False
    LLM_POOL_MAX_SIZE: int = 4
    LLM_POOL_TTL_SECONDS: int = 3600
    LLM_POOL_WARM_PROVIDERS: List[str] = []
    LLM_EXECUTOR_MAX_WORKERS: int = 4
    LLM_MAX_PROMPT_LENGTH: int = 100000
    # Política econômica e tetos de custo
    LLM_ECONOMY_POLICY: str = "balanced"  # strict | balanced | quality
    LLM_MAX_COST_PER_REQUEST_USD: Dict[str, float] = {
        "orchestrator": 0.02,
        "code_generator": 0.05,
        "knowledge_curator": 0.01,
    }
    # Tokens esperados (em milhares) por requisição por papel (input+output total)
    LLM_EXPECTED_KTOKENS_BY_ROLE: Dict[str, float] = {
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

    # Auto-tuning de timeouts
    TIMEOUT_AUTO_TUNE_ENABLED: bool = True
    TIMEOUT_AUTO_TUNE_PERCENTILE: float = 0.95
    TIMEOUT_AUTO_TUNE_PAD_SECONDS: float = 0.5
    TIMEOUT_MIN_SECONDS_MAP: Dict[str, float] = {
        "llm": 5.0,
        "qdrant_search": 3.0,
        "neo4j_query": 3.0,
        "rabbitmq_management": 2.0,
    }
    TIMEOUT_MAX_SECONDS_MAP: Dict[str, float] = {
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

    # LLM Providers
    OPENAI_API_KEY: Optional[SecretStr] = None
    OPENAI_MODEL_NAME: str = "gpt-4o"
    OPENAI_MODELS: List[str] = ["gpt-4o"]
    OPENAI_HTTP_MAX_CONNECTIONS: int = 100
    OPENAI_HTTP_MAX_KEEPALIVE: int = 20
    OPENAI_HTTP_TIMEOUT_SECONDS: float = 60.0
    GEMINI_API_KEY: Optional[SecretStr] = None
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    GEMINI_MODELS: List[str] = ["gemini-2.5-flash"]
    OLLAMA_HOST: str = "http://ollama:11434"
    OLLAMA_ORCHESTRATOR_MODEL: str = "llama3.1:8b"
    OLLAMA_CODER_MODEL: str = "llama3.1:8b"
    OLLAMA_CURATOR_MODEL: str = "llama3.1:8b"

    # P4 — Orçamentação e Preços por Provedor
    # Orçamentos mensais (USD) por provedor
    OPENAI_MONTHLY_BUDGET_USD: float = 50.0
    GEMINI_MONTHLY_BUDGET_USD: float = 25.0
    OLLAMA_MONTHLY_BUDGET_USD: float = 0.0

    # Preço por 1k tokens (USD) por provedor
    # Valores padrão podem ser ajustados via .env conforme necessidade
    OPENAI_COST_PER_1K_INPUT_USD: float = 5.0
    OPENAI_COST_PER_1K_OUTPUT_USD: float = 15.0
    GEMINI_COST_PER_1K_INPUT_USD: float = 0.5
    GEMINI_COST_PER_1K_OUTPUT_USD: float = 1.5
    OLLAMA_COST_PER_1K_INPUT_USD: float = 0.0
    OLLAMA_COST_PER_1K_OUTPUT_USD: float = 0.0
    # Tunáveis de desempenho do Ollama (opcionais, aplicados se definidos)
    OLLAMA_KEEP_ALIVE: Optional[str] = "30m"  # mantém modelos carregados para reduzir cold-start
    OLLAMA_NUM_CTX: Optional[int] = 4096  # contexto máximo por requisição
    OLLAMA_NUM_THREAD: Optional[int] = None  # threads CPU (auto se None)
    OLLAMA_NUM_BATCH: Optional[int] = None  # tamanho de batch de tokens
    OLLAMA_GPU_LAYERS: Optional[int] = None  # camadas na GPU (auto se None)

    # Modularidade: candidatos por papel (ex.: "orchestrator": ["openai:gpt-4o", "google_gemini:gemini-2.5-pro"]) 
    LLM_CLOUD_MODEL_CANDIDATES: Dict[str, List[str]] = {}

    # Tabelas de preço por modelo (se ausente, usa preço default do provedor)
    OPENAI_MODEL_PRICING: Dict[str, Dict[str, float]] = {
        "gpt-4o": {"input_per_1k_usd": 5.0, "output_per_1k_usd": 15.0},
        # Adicione aqui outros modelos (ex.: "gpt-4", "gpt-5")
    }
    GEMINI_MODEL_PRICING: Dict[str, Dict[str, float]] = {
        "gemini-2.5-flash": {"input_per_1k_usd": 0.5, "output_per_1k_usd": 1.5},
        # Adicione aqui outros modelos (ex.: "gemini-2.5-pro")
    }

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_IP_PER_MIN: int = 60

    # Estáticos
    SERVE_STATIC_FILES: bool = False
    STATIC_FILES_DIR: str = "front/janus-angular/public"

    # Timeouts de infraestrutura
    QDRANT_DEFAULT_TIMEOUT_SECONDS: int = 30
    NEO4J_DEFAULT_TIMEOUT_SECONDS: int = 30
    RATE_LIMIT_PER_KEY_PER_MIN: int = 300

    AUTH_JWT_SECRET: Optional[str] = None
    AUTH_JWT_EXPIRES_SECONDS: int = 3600

    # Sprint 1: RabbitMQ
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "janus"
    RABBITMQ_PASSWORD: str = "janus_pass"
    RABBITMQ_MANAGEMENT_PORT: int = 15672
    BROKER_USE_MSGPACK: bool = True
    RABBITMQ_QUEUE_CONFIG: Dict[str, Dict[str, int]] = {
        "janus.knowledge.consolidation": {
            "x-message-ttl": 86400000,
            "x-max-length": 10000
        },
        "janus.agent.tasks": {
            "x-message-ttl": 86400000,
            "x-max-length": 10000
        },
        "janus.neural.training": {
            "x-message-ttl": 86400000,
            "x-max-length": 10000
        },
        "janus.data.harvesting": {
            "x-message-ttl": 86400000,
            "x-max-length": 10000
        },
        "janus.meta_agent.cycle": {
            "x-message-ttl": 86400000,
            "x-max-length": 10000,
            "x-max-priority": 10
        },
        "janus.tasks.reflexion": {
            "x-message-ttl": 86400000,
            "x-max-length": 10000,
            "x-max-priority": 10
        },
        "janus.failure.detected": {
            "x-message-ttl": 86400000,
            "x-max-length": 10000,
            "x-max-priority": 10
        },
        "default": {
            "x-message-ttl": 86400000,
            "x-max-length": 10000
        }
    }

    # Sprint 2: Knowledge Consolidator
    KNOWLEDGE_CONSOLIDATOR_INTERVAL_SECONDS: int = 60
    KNOWLEDGE_MIN_CONFIDENCE: float = 0.6
    RAG_HYBRID_VECTOR_WEIGHT: float = 0.7
    RAG_HYBRID_GRAPH_WEIGHT: float = 0.3
    DOCS_MAX_FILE_SIZE_BYTES: int = 10_000_000
    DOCS_MAX_POINTS_PER_USER: int = 50000
    PRODUCTIVITY_DAILY_LIMITS: Dict[str, int] = {
        "calendar.write": 500,
        "mail.send": 100,
        "notes.write": 1000,
    }
    GOOGLE_OAUTH_CLIENT_ID: Optional[SecretStr] = None
    GOOGLE_OAUTH_CLIENT_SECRET: Optional[SecretStr] = None
    GOOGLE_OAUTH_REDIRECT_URI: Optional[str] = None
    TRAINING_GPU_BUDGET_PER_USER: Dict[str, float] = {}
    RABBITMQ_QUEUE_CONFIG: Dict[str, Dict[str, int]] = {
        "janus.neural.training": {"x-max-priority": 5, "x-message-ttl": 3600000},
        "janus.productivity.google": {"x-max-priority": 5, "x-message-ttl": 600000},
    }
    MIN_DEPLOY_ACCURACY: float = 0.7
    LLM_AB_EXPERIMENT_ID: Optional[int] = None

    # Sprint 3: Web Search
    TAVILY_API_KEY: Optional[SecretStr] = None
    CONTEXT_WEB_CACHE_TTL_SECONDS: int = 1800
    CONTEXT_WEB_CACHE_MAX_ITEMS: int = 512

    # Sprint 4: Python Sandbox (epicbox)
    SANDBOX_DOCKER_IMAGE: str = "python:3.11-slim"
    SANDBOX_TIMEOUT_SECONDS: int = 15
    SANDBOX_MEM_LIMIT_MB: int = 128
    SANDBOX_CPU_LIMIT: float = 0.5
    SANDBOX_MAX_OUTPUT_LENGTH: int = 25000

    # Sprint 5: Reflexion
    REFLEXION_MAX_ITERATIONS: int = 3
    REFLEXION_MAX_TIME_SECONDS: int = 180
    REFLEXION_SUCCESS_THRESHOLD: float = 0.8

    # Observabilidade
    OTEL_ENABLED: bool = False
    OTEL_OTLP_ENDPOINT: Optional[str] = None
    OTEL_SERVICE_NAME: Optional[str] = None
    LOG_SAMPLING_RATE: float = 1.0
    AUDIT_PURGE_INTERVAL_SECONDS: int = 3600
    AUDIT_RETENTION_DAYS: int = 30

    # Tailscale Serve Configuration
    TAILSCALE_SERVE_ENABLED: bool = False
    TAILSCALE_HOST: Optional[str] = None
    TAILSCALE_BACKEND_URL: Optional[str] = None
    TAILSCALE_FRONTEND_URL: Optional[str] = None
    
    # CORS para Tailscale - adicionar domínios Tailscale aos domínios permitidos
    @field_validator("CORS_ALLOW_ORIGINS", mode="before")
    def _add_tailscale_origins(cls, v: Any, info):
        # Se Tailscale estiver habilitado, adicionar origens Tailscale
        tailscale_enabled = info.data.get("TAILSCALE_SERVE_ENABLED", False)
        tailscale_host = info.data.get("TAILSCALE_HOST", "")
        
        # Parse existing origins
        if isinstance(v, str):
            if v.strip() == "*":
                origins = ["*"]
            else:
                origins = [x.strip() for x in v.split(",") if x.strip()]
        elif isinstance(v, list):
            origins = v
        else:
            origins = ["*"]
        
        # Adicionar origens Tailscale se habilitado
        if tailscale_enabled and tailscale_host:
            tailscale_origin = f"https://{tailscale_host}"
            if tailscale_origin not in origins and "*" not in origins:
                origins.append(tailscale_origin)
        
        return origins

    # ======= Validadores para variáveis de ambiente complexas =======

    @field_validator("OPENAI_MODELS", "GEMINI_MODELS", mode="before")
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
                parsed: Dict[str, List[str]] = {}
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

    @field_validator("OPENAI_MODEL_PRICING", "GEMINI_MODEL_PRICING", mode="before")
    def _parse_model_pricing(cls, v: Any):
        # Aceita JSON objeto {model: {input_per_1k_usd: float, output_per_1k_usd: float}}
        if isinstance(v, str):
            try:
                obj = json.loads(v)

                def coerce(d: Dict[str, Any]) -> Dict[str, float]:
                    return {
                        "input_per_1k_usd": float(d.get("input_per_1k_usd", 0.0)),
                        "output_per_1k_usd": float(d.get("output_per_1k_usd", 0.0)),
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
                parsed: Dict[str, float] = {}
                for k, val in obj.items():
                    try:
                        parsed[str(k)] = float(val)
                    except Exception:
                        parsed[str(k)] = 0.0
                return parsed
            except Exception:
                parsed: Dict[str, float] = {}
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

settings = AppSettings()
