
from typing import Optional

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra='ignore', env_file='.env', env_file_encoding='utf-8'
    )

    # App
    APP_NAME: str = "Janus"
    APP_VERSION: str = "0.2.0"
    ENVIRONMENT: str = "development"

    # Feature flags / modos de execução
    DRY_RUN: bool = True  # Modo simulado: substitui operações destrutivas por no-ops com logs

    # ... (Configurações de Neo4j inalteradas) ...
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: SecretStr = "password"

    # Qdrant
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[SecretStr] = None  # Para Qdrant Cloud (opcional)
    QDRANT_COLLECTION_EPISODIC: str = "janus_episodic_memory"

    LANGCHAIN_TRACING_V2: str = "true"
    LANGCHAIN_API_KEY: Optional[SecretStr] = None

    # Memória (short/long-term)
    MEMORY_SHORT_TTL_SECONDS: int = 600  # TTL para memória de curto prazo
    MEMORY_SHORT_MAX_ITEMS: int = 512    # Capacidade LRU para curto prazo
    MEMORY_MAX_CONTENT_CHARS: int = 20000
    MEMORY_QUOTA_WINDOW_SECONDS: int = 3600
    MEMORY_QUOTA_MAX_ITEMS_PER_ORIGIN: int = 200
    MEMORY_QUOTA_MAX_BYTES_PER_ORIGIN: int = 5_000_000
    MEMORY_ENCRYPTION_KEY: Optional[str] = None  # Opcional: chave de "criptografia" simples
    MEMORY_PII_REDACT: bool = True  # Se verdadeiro, redige PII detectada

    # Núcleo de Raciocínio
    REASONING_MAX_ITERATIONS: int = 3
    REASONING_MAX_SECONDS: int = 60
    REASONING_MAX_TOKENS: int = 8000

    # Meta-Agente (ciclo)
    META_AGENT_CYCLE_INTERVAL_SECONDS: int = 300
    META_AGENT_MAX_ITERATIONS: int = 3
    META_AGENT_MAX_SECONDS: int = 60

    # LLM Resilience & Timeouts
    LLM_DEFAULT_TIMEOUT_SECONDS: int = 60
    LLM_CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 3
    LLM_CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 30
    LLM_RETRY_MAX_ATTEMPTS: int = 3
    LLM_RETRY_INITIAL_BACKOFF_SECONDS: float = 0.5
    LLM_RETRY_MAX_BACKOFF_SECONDS: float = 5.0
    LLM_CACHE_TTL_SECONDS: int = 3600
    LLM_MAX_PROMPT_LENGTH: int = 100000

    # 1. CO-PROCESSADOR DE ELITE (Nuvem - Fallback Estratégico)
    OPENAI_API_KEY: Optional[SecretStr] = None
    OPENAI_MODEL_NAME: str = "gpt-4o"

    # API - Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_IP_PER_MIN: int = 60
    RATE_LIMIT_PER_KEY_PER_MIN: int = 300

    GEMINI_API_KEY: Optional[SecretStr] = None
    GEMINI_MODEL_NAME: str = "gemini-1.5-pro-latest"

    # 2. CÉREBRO / SISTEMA NERVOSO CENTRAL (Local via Ollama - Primário)
    OLLAMA_HOST: str = "http://ollama:11434"

    # Modelo para o Córtex Pré-Frontal (Orquestração e Raciocínio Geral)
    OLLAMA_ORCHESTRATOR_MODEL: str = "llama3.1:8b"

    # Modelo para o Cerebelo (Geração e Análise de Código)
    OLLAMA_CODER_MODEL: str = "codellama:7b"

    # Modelo para o Lobo Temporal (Análise, Sumarização e Validação de Conhecimento)
    OLLAMA_CURATOR_MODEL: str = "phi3:mini"

    # Sprint 1: RabbitMQ (Message Broker)
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "janus"
    RABBITMQ_PASSWORD: str = "janus_pass"
    RABBITMQ_MANAGEMENT_PORT: int = 15672


settings = AppSettings()
