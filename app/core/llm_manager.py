# app/core/llm_manager.py
import logging
from enum import Enum

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# Cache para as instâncias de LLM
_llm_instances = {}


class ModelRole(Enum):
    """Define os papéis cognitivos para seleção do modelo apropriado."""
    ORCHESTRATOR = "orchestrator"
    CODE_GENERATOR = "code_generator"
    KNOWLEDGE_CURATOR = "knowledge_curator"


def get_llm(role: ModelRole = ModelRole.ORCHESTRATOR) -> BaseChatModel:
    """
    Obtém uma instância de um modelo de linguagem com base no papel cognitivo
    requerido, implementando uma estratégia de roteamento e fallback.
    """
    if role in _llm_instances:
        logger.debug(f"Retornando instância de LLM em cache para o papel: {role.value}")
        return _llm_instances[role]

    # 1. Seleciona o modelo local primário com base no papel
    model_map = {
        ModelRole.ORCHESTRATOR: settings.OLLAMA_ORCHESTRATOR_MODEL,
        ModelRole.CODE_GENERATOR: settings.OLLAMA_CODER_MODEL,
        ModelRole.KNOWLEDGE_CURATOR: settings.OLLAMA_CURATOR_MODEL,
    }
    local_model_name = model_map.get(role, settings.OLLAMA_ORCHESTRATOR_MODEL)

    # 2. Tenta inicializar o modelo local primeiro (Soberania do Janus)
    try:
        logger.info(f"Tentando inicializar o modelo local '{local_model_name}' para o papel '{role.value}'...")
        llm = ChatOllama(
            base_url=settings.OLLAMA_HOST,
            model=local_model_name,
            temperature=0
        )
        llm.invoke("Confirme sua funcionalidade.")
        logger.info(f"Modelo local '{local_model_name}' inicializado com sucesso.")
        _llm_instances[role] = llm
        return llm
    except Exception as e:
        logger.warning(
            f"Falha ao inicializar o modelo local '{local_model_name}': {e}. "
            "Iniciando fallback para provedores de nuvem..."
        )

    # 3. Lógica de Fallback para a Nuvem (Co-processador de Elite)
    cloud_providers = [
        {
            "name": "OpenAI",
            "enabled": getattr(settings, "OPENAI_API_KEY", None) and settings.OPENAI_API_KEY.get_secret_value(),
            "initializer": lambda: ChatOpenAI(
                model=settings.OPENAI_MODEL_NAME,
                temperature=0,
                api_key=settings.OPENAI_API_KEY.get_secret_value()
            )
        },
        {
            "name": "Google Gemini",
            "enabled": getattr(settings, "GEMINI_API_KEY", None) and settings.GEMINI_API_KEY.get_secret_value(),
            "initializer": lambda: ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL_NAME,
                temperature=0,
                google_api_key=settings.GEMINI_API_KEY.get_secret_value()
            )
        }
    ]

    for provider in cloud_providers:
        if provider["enabled"]:
            logger.info(f"Tentando fallback com o provedor de nuvem: {provider['name']}")
            try:
                llm = provider["initializer"]()
                logger.info(f"LLM do provedor '{provider['name']}' inicializado com sucesso.")
                _llm_instances[role] = llm  # Cacheia mesmo no fallback
                return llm
            except Exception as e:
                logger.warning(f"Falha ao inicializar o provedor '{provider['name']}': {e}.")

    # 4. Falha Crítica
    raise RuntimeError(
        "FALHA CRÍTICA: Nenhum provedor de LLM (local ou nuvem) pôde ser inicializado. "
        "Verifique a conexão com o Ollama e as chaves de API."
    )
