import logging
from enum import Enum

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from prometheus_client import Counter

from app.config import settings

LLM_ROUTER_COUNTER = Counter(
    "llm_router_model_selected_total",
    "Contador para os modelos selecionados pelo roteador dinâmico",
    ["role", "priority", "model_name", "provider"]
)

logger = logging.getLogger(__name__)

# Cache para as instâncias de LLM
_llm_instances = {}


class ModelRole(Enum):
    """Define os papéis cognitivos para seleção do modelo apropriado."""
    ORCHESTRATOR = "orchestrator"
    CODE_GENERATOR = "code_generator"
    KNOWLEDGE_CURATOR = "knowledge_curator"


class ModelPriority(Enum):
    """Define a prioridade para o roteador de modelos, balanceando custo e performance."""
    LOCAL_ONLY = "local_only"  # Força o uso do cérebro soberano local (Ollama)
    FAST_AND_CHEAP = "fast_and_cheap"  # Prioriza APIs de nuvem de baixo custo para tarefas rápidas
    HIGH_QUALITY = "high_quality"  # Prioriza os modelos de nuvem mais poderosos (e caros)


def get_llm(
        role: ModelRole = ModelRole.ORCHESTRATOR,
        priority: ModelPriority = ModelPriority.LOCAL_ONLY
) -> BaseChatModel:
    """
    Obtém uma instância de um modelo de linguagem com base no papel e na prioridade,
    atuando como um roteador dinâmico de modelos.
    """
    cache_key = f"{role.value}_{priority.value}"
    if cache_key in _llm_instances:
        logger.debug(f"Retornando instância de LLM em cache para: {cache_key}")
        return _llm_instances[cache_key]

    # Mapeamento de papéis para modelos locais
    model_map = {
        ModelRole.ORCHESTRATOR: settings.OLLAMA_ORCHESTRATOR_MODEL,
        ModelRole.CODE_GENERATOR: settings.OLLAMA_CODER_MODEL,
        ModelRole.KNOWLEDGE_CURATOR: settings.OLLAMA_CURATOR_MODEL,
    }
    local_model_name = model_map.get(role, settings.OLLAMA_ORCHESTRATOR_MODEL)


    # Estratégia 1: Prioridade é o Cérebro Soberano Local
    if priority == ModelPriority.LOCAL_ONLY:
        try:
            logger.info(f"Estratégia LOCAL_ONLY: Tentando inicializar o modelo '{local_model_name}'...")
            llm = ChatOllama(base_url=settings.OLLAMA_HOST, model=local_model_name, temperature=0)
            llm.invoke("Confirme sua funcionalidade.")
            logger.info(f"Modelo local '{local_model_name}' inicializado com sucesso.")
            LLM_ROUTER_COUNTER.labels(role=role.value, priority=priority.value, model_name=local_model_name,
                                      provider="ollama").inc()
            _llm_instances[cache_key] = llm
            return llm
        except Exception as e:
            logger.warning(
                f"Falha ao inicializar o modelo local '{local_model_name}': {e}. Nenhuma outra estratégia será tentada para LOCAL_ONLY.")
            raise RuntimeError(f"Falha crítica ao tentar carregar o modelo local com prioridade LOCAL_ONLY.")

    # Provedores de Nuvem (ordenados por prioridade/custo)
    cloud_providers = [
        {
            "name": "Google Gemini",  # Frequentemente oferece um bom equilíbrio de custo/performance
            "enabled": getattr(settings, "GEMINI_API_KEY", None) and settings.GEMINI_API_KEY.get_secret_value(),
            "initializer": lambda: ChatGoogleGenerativeAI(model=settings.GEMINI_MODEL_NAME, temperature=0,
                                                          google_api_key=settings.GEMINI_API_KEY.get_secret_value())
        },
        {
            "name": "OpenAI",
            "enabled": getattr(settings, "OPENAI_API_KEY", None) and settings.OPENAI_API_KEY.get_secret_value(),
            "initializer": lambda: ChatOpenAI(model=settings.OPENAI_MODEL_NAME, temperature=0,
                                              api_key=settings.OPENAI_API_KEY.get_secret_value())
        }
    ]

    # Estratégia 2: Rápido e Barato (tentamos provedores de nuvem)
    if priority == ModelPriority.FAST_AND_CHEAP or priority == ModelPriority.HIGH_QUALITY:
        # A ordem em cloud_providers pode ser ajustada para refletir qual é o mais "barato"
        for provider in cloud_providers:
            if provider["enabled"]:
                logger.info(f"Estratégia {priority.value}: Tentando o provedor de nuvem: {provider['name']}")
                try:
                    llm = provider["initializer"]()
                    logger.info(f"LLM do provedor '{provider['name']}' inicializado com sucesso.")
                    model_name = settings.GEMINI_MODEL_NAME if provider[
                                                                   'name'] == 'Google Gemini' else settings.OPENAI_MODEL_NAME
                    LLM_ROUTER_COUNTER.labels(role=role.value, priority=priority.value, model_name=model_name,
                                              provider=provider['name'].lower()).inc()
                    _llm_instances[cache_key] = llm
                    return llm
                except Exception as e:
                    logger.warning(f"Falha ao inicializar o provedor '{provider['name']}': {e}.")

    # Fallback final para o modelo local se as estratégias de nuvem falharem
    logger.warning(f"Todas as estratégias de nuvem falharam. Recorrendo ao modelo local como fallback final.")
    try:
        llm = ChatOllama(base_url=settings.OLLAMA_HOST, model=local_model_name, temperature=0)
        llm.invoke("Confirme sua funcionalidade.")
        LLM_ROUTER_COUNTER.labels(role=role.value, priority="fallback", model_name=local_model_name,
                                  provider="ollama").inc()
        _llm_instances[cache_key] = llm
        return llm
    except Exception as e:
        raise RuntimeError(
            f"FALHA CRÍTICA: Nenhum provedor de LLM (nem nuvem, nem local) pôde ser inicializado. Erro final: {e}"
        )
