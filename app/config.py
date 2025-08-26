# app/config.py

from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra='ignore', env_file='.env', env_file_encoding='utf-8'
    )

    # App
    APP_NAME: str = "Janus"
    APP_VERSION: str = "0.2.0"
    ENVIRONMENT: str = "development"

    # ... (Configurações de Neo4j e ChromaDB inalteradas) ...
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: SecretStr = "password"

    CHROMA_HOST: str = "chroma"
    CHROMA_PORT: int = 8000

    LANGCHAIN_TRACING_V2: str = "true"
    LANGCHAIN_API_KEY: Optional[SecretStr] = None

    # --- ARQUITETURA COGNITIVA DE MODELOS ---

    # 1. CO-PROCESSADOR DE ELITE (Nuvem - Fallback Estratégico)
    OPENAI_API_KEY: Optional[SecretStr] = None
    OPENAI_MODEL_NAME: str = "gpt-4o"

    GEMINI_API_KEY: Optional[SecretStr] = None
    GEMINI_MODEL_NAME: str = "gemini-1.5-pro-latest"

    # 2. CÉREBRO / SISTEMA NERVOSO CENTRAL (Local via Ollama - Primário)
    OLLAMA_HOST: str = "http://ollama:11434"

    # Modelo para o Córtex Pré-Frontal (Orquestração e Raciocínio Geral)
    OLLAMA_ORCHESTRATOR_MODEL: str = "llama3.2:3b"

    # Modelo para o Cerebelo (Geração e Análise de Código)
    OLLAMA_CODER_MODEL: str = "codellama:7b"

    # Modelo para o Lobo Temporal (Análise, Sumarização e Validação de Conhecimento)
    OLLAMA_CURATOR_MODEL: str = "phi3:mini"


settings = AppSettings()