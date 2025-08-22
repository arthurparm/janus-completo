from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    """
    Carrega e valida as configurações da aplicação a partir de variáveis de ambiente.
    """
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    APP_NAME: str = "Janus"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"

# Instância única das configurações para ser importada em outros módulos
settings = AppSettings()
