# app/config.py

from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class AppSettings(BaseSettings):
    # A configuração do model_config foi ajustada para carregar explicitamente do .env
    model_config = SettingsConfigDict(
        extra='ignore', env_file='.env', env_file_encoding='utf-8'
    )

    # App
    APP_NAME: str = "Janus"
    APP_VERSION: str = "0.2.0"
    ENVIRONMENT: str = "development"

    # Neo4j
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: SecretStr = "password"

    # ChromaDB
    CHROMA_HOST: str = "chroma"
    CHROMA_PORT: int = 8000

    # LangChain
    LANGCHAIN_TRACING_V2: str = "true"
    # LANGCHAIN_API_KEY é mantido como opcional, mas pode ser obrigatório dependendo do seu uso
    LANGCHAIN_API_KEY: Optional[SecretStr] = None

    # --- CORREÇÃO PRINCIPAL SPRINT 10 ---
    # As chaves de API agora são opcionais. Isso permite que a aplicação inicie
    # mesmo que uma ou mais chaves não estejam definidas no ambiente, o que é
    # essencial para a lógica de fallback do LLMManager.

    # OpenAI (Provedor 1)
    OPENAI_API_KEY: Optional[SecretStr] = None
    OPENAI_MODEL_NAME: str = "gpt-4o"

    # Google Gemini (Provedor 2)
    GEMINI_API_KEY: Optional[SecretStr] = None
    GEMINI_MODEL_NAME: str = "gemini-1.5-pro-latest"

    # Grok (Provedor 3)
    GROK_API_KEY: Optional[SecretStr] = None
    GROK_MODEL_NAME: str = "llama3-8b-8192"

    # Ollama (Provedor 4 - Fallback Local)
    OLLAMA_HOST: str = "http://ollama:11434"
    OLLAMA_MODEL_NAME: str = "llama3"


settings = AppSettings()