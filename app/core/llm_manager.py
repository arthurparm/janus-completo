# app/core/llm_manager.py
import logging
from app.config import settings

# LangChain tem integrações para todos os principais fornecedores
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama

logger = logging.getLogger(__name__)

# Cache para a instância do LLM para evitar recriações desnecessárias
_llm_instance = None


def get_llm():
    """
    Obtém uma instância de um modelo de linguagem, implementando uma estratégia
    de fallback hierárquica para garantir máxima resiliência.
    A ordem de preferência é: OpenAI -> Google Gemini -> Ollama (local).
    """
    global _llm_instance
    if _llm_instance:
        return _llm_instance

    # 1ª Tentativa: OpenAI (Prioridade Máxima)
    try:
        if getattr(settings, "OPENAI_API_KEY", None) and settings.OPENAI_API_KEY.get_secret_value() != "sk-your_openai_api_key":
            logger.info("Tentando inicializar o LLM com o provedor: OpenAI")
            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL_NAME,
                temperature=0,
                api_key=settings.OPENAI_API_KEY.get_secret_value()
            )
            logger.info("LLM da OpenAI inicializado com sucesso.")
            _llm_instance = llm
            return _llm_instance
        else:
            logger.warning("Chave da API da OpenAI não configurada. Pulando para o próximo provedor.")
    except Exception as e:
        logger.error(f"Falha ao inicializar o LLM da OpenAI: {e}. Tentando o próximo provedor.", exc_info=True)

    # 2ª Tentativa: Google Gemini (Fallback 1)
    try:
        if getattr(settings, "GEMINI_API_KEY", None) and settings.GEMINI_API_KEY.get_secret_value() != "your_gemini_api_key":
            logger.info("Tentando inicializar o LLM com o provedor: Google Gemini")
            llm = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL_NAME,
                temperature=0,
                google_api_key=settings.GEMINI_API_KEY.get_secret_value()
            )
            logger.info("LLM do Google Gemini inicializado com sucesso.")
            _llm_instance = llm
            return _llm_instance
        else:
            logger.warning("Chave da API do Gemini não configurada. Pulando para o próximo provedor.")
    except Exception as e:
        logger.error(f"Falha ao inicializar o LLM do Google Gemini: {e}. Tentando o próximo provedor.", exc_info=True)
        
    # 3ª Tentativa: Ollama (Fallback Final - Local)
    try:
        logger.info(f"Tentando inicializar o LLM com o provedor local: Ollama (Host: {settings.OLLAMA_HOST})")
        llm = ChatOllama(
            base_url=settings.OLLAMA_HOST,
            model=settings.OLLAMA_MODEL_NAME,
            temperature=0
        )
        # Testa a conexão para garantir que o Ollama está a responder
        llm.invoke("Teste de conexão")
        logger.info("LLM do Ollama inicializado com sucesso.")
        _llm_instance = llm
        return _llm_instance
    except Exception as e:
        logger.critical(f"FALHA CRÍTICA: Não foi possível inicializar nenhum provedor de LLM. Ollama falhou: {e}", exc_info=True)
        raise RuntimeError("Nenhum provedor de LLM está disponível.") from e
        
    # Se nenhuma chave estiver configurada
    raise RuntimeError("Nenhum provedor de LLM foi configurado. Por favor, defina pelo menos uma chave de API (OPENAI_API_KEY, GEMINI_API_KEY) ou garanta que o OLLAMA_HOST esteja acessível.")
