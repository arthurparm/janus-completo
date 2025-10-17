import json
from typing import Optional, Dict, List, Any

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra='ignore', env_file='.env', env_file_encoding='utf-8'
    )

    # App
    APP_NAME: str = "Janus"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    # Identidade
    AGENT_IDENTITY_NAME: str = "Janus"
    IDENTITY_ENFORCEMENT_ENABLED: bool = True

    # Feature flags / modos de execução
    DRY_RUN: bool = True

    # Neo4j
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: SecretStr = "password"

    # Qdrant
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[SecretStr] = None
    QDRANT_COLLECTION_EPISODIC: str = "janus_episodic_memory"

    # LangSmith
    LANGCHAIN_TRACING_V2: str = "true"
    LANGCHAIN_API_KEY: Optional[SecretStr] = None

    # Memória
    MEMORY_SHORT_TTL_SECONDS: int = 600
    MEMORY_SHORT_MAX_ITEMS: int = 512
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
    GEMINI_API_KEY: Optional[SecretStr] = None
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    GEMINI_MODELS: List[str] = ["gemini-2.5-flash"]
    OLLAMA_HOST: str = "http://ollama:11434"
    OLLAMA_ORCHESTRATOR_MODEL: str = "llama3.1:8b"
    OLLAMA_CODER_MODEL: str = "codellama:7b"
    OLLAMA_CURATOR_MODEL: str = "phi3:mini"

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
    RATE_LIMIT_PER_KEY_PER_MIN: int = 300

    # Sprint 1: RabbitMQ
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "janus"
    RABBITMQ_PASSWORD: str = "janus_pass"
    RABBITMQ_MANAGEMENT_PORT: int = 15672
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
            "x-max-length": 10000
        },
        "default": {
            "x-message-ttl": 86400000,
            "x-max-length": 10000
        }
    }

    # Sprint 2: Knowledge Consolidator
    KNOWLEDGE_CONSOLIDATOR_INTERVAL_SECONDS: int = 60

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
