# app/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(extra='ignore')

    # App
    APP_NAME: str = "Janus"
    APP_VERSION: str = "0.2.0"
    ENVIRONMENT: str = "development"

    # Neo4j
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str

    # ChromaDB
    CHROMA_HOST: str
    CHROMA_PORT: int

# A instância continua a mesma
settings = AppSettings()