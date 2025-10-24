import structlog
from typing import Dict, Any, List, Optional
from app.config import settings
from app.core.llm.llm_manager import _provider_circuit_breakers  # type: ignore
from app.core.llm.llm_manager import _llm_cache as llm_cache  # type: ignore
from app.core.llm.llm_manager import _validate_openai_key, _validate_gemini_key  # type: ignore
from app.core.llm.response_cache import get as rc_get, put as rc_put, entries as rc_entries, invalidate as rc_invalidate

from app.core.llm import (
    get_llm_client,
    ModelRole,
    ModelPriority,
    invalidate_cache,
    _llm_cache,
    _provider_circuit_breakers
)

logger = structlog.get_logger(__name__)

class LLMRepositoryError(Exception):
    """Base exception for LLM repository errors."""
    pass

class LLMRepository:
    """
    Camada de Repositório para o Cérebro Híbrido (LLMs).
    Abstrai todas as interações diretas com a infraestrutura de LLMs.
    """

    def invoke_llm(
            self,
            prompt: str,
            role: ModelRole,
            priority: ModelPriority,
            timeout_seconds: Optional[int],
            user_id: Optional[str] = None,
            project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        logger.debug("Invocando LLM via repositório", role=role.value, priority=priority.value)
        client = None
        try:
            # Cache de resposta: tentativa de hit antes de chamar provedor
            cached = rc_get(prompt, role.value, priority.value)
            if cached:
                logger.info("Resposta retornada do cache de prompts/respostas.")
                return {
                    "response": cached["response"],
                    "provider": cached.get("provider", "unknown"),
                    "model": cached.get("model", "unknown"),
                    "role": role.value,
                    "input_tokens": cached.get("input_tokens"),
                    "output_tokens": cached.get("output_tokens"),
                    "cost_usd": cached.get("cost_usd"),
                }

            client = get_llm_client(role=role, priority=priority, user_id=user_id, project_id=project_id)
            enriched = client.send_enriched(prompt, timeout_s=timeout_seconds)

            # Armazena no cache de resposta
            try:
                rc_put(
                    prompt,
                    role.value,
                    priority.value,
                    enriched.get("response", ""),
                    client.provider,
                    client.model,
                    input_tokens=enriched.get("input_tokens"),
                    output_tokens=enriched.get("output_tokens"),
                    cost_usd=enriched.get("cost_usd"),
                )
            except Exception:
                pass

            return enriched
        except Exception as e:
            logger.warning("Falha na invocação inicial; tentando failover por provedor.", exc_info=True)
            # Failover: tenta outro provedor excluindo o atual
            try:
                failed_provider = getattr(client, "provider", "unknown") if client else None
                exclude = [failed_provider] if failed_provider else None
                client_fb = get_llm_client(role=role, priority=priority, user_id=user_id, project_id=project_id,
                                           exclude_providers=exclude)
                # Se não houver mudança de provedor, repropaga
                if client and getattr(client_fb, "provider", None) == getattr(client, "provider", None):
                    raise e
                enriched_fb = client_fb.send_enriched(prompt, timeout_s=timeout_seconds)
                try:
                    rc_put(
                        prompt,
                        role.value,
                        priority.value,
                        enriched_fb.get("response", ""),
                        client_fb.provider,
                        client_fb.model,
                        input_tokens=enriched_fb.get("input_tokens"),
                        output_tokens=enriched_fb.get("output_tokens"),
                        cost_usd=enriched_fb.get("cost_usd"),
                    )
                except Exception:
                    pass
                return enriched_fb
            except Exception as e2:
                logger.error("Erro no repositório ao invocar LLM (failover também falhou)", exc_info=True)
                raise LLMRepositoryError(f"Falha ao invocar LLM: {e2}") from e2

    def get_cache_entries(self) -> List[Dict[str, Any]]:
        logger.debug("Buscando entradas do cache de LLMs no repositório.")
        entries = []
        for key, cached in _llm_cache.items():
            entries.append({
                "cache_key": key,
                "provider": cached.provider,
                "consecutive_failures": cached.consecutive_failures,
                "created_at": cached.created_at.isoformat(),
            })
        # Acrescenta entradas do cache de respostas
        try:
            entries.extend([{**e, "kind": "response"} for e in rc_entries()])
        except Exception:
            pass
        return entries

    def invalidate_cache(self, provider: Optional[str] = None) -> int:
        logger.debug("Invalidando cache de LLMs via repositório", provider=provider)
        invalidate_cache(provider=provider)
        return len(_llm_cache)

    def invalidate_response_cache(self, prompt: Optional[str] = None, role: Optional[str] = None,
                                  priority: Optional[str] = None) -> int:
        logger.debug("Invalidando cache de respostas via repositório", prompt=bool(prompt), role=role, priority=priority)
        return rc_invalidate(prompt=prompt, role=role, priority=priority)

    def get_circuit_breakers(self) -> List[Dict[str, Any]]:
        logger.debug("Buscando status dos circuit breakers no repositório.")
        statuses = []
        for provider, cb in _provider_circuit_breakers.items():
            statuses.append({
                "provider": provider,
                "state": cb.state.value,
                "failure_count": cb.failure_count,
                "last_failure_time": cb.last_failure_time
            })
        return statuses

    def reset_circuit_breaker(self, provider: str):
        logger.debug("Resetando circuit breaker via repositório", provider=provider)
        if provider not in _provider_circuit_breakers:
            raise LLMRepositoryError(f"Provedor '{provider}' não encontrado.")
        cb = _provider_circuit_breakers[provider]
        cb.reset()

    def list_providers(self) -> List[Dict[str, Any]]:
        """Lista provedores configurados com status de habilitação e modelos padrão."""
        logger.debug("Listando provedores de LLMs via repositório.")

        # Recupera chaves (podem ser SecretStr) e valida
        openai_key = getattr(settings.OPENAI_API_KEY, 'get_secret_value', lambda: None)()
        gemini_key = getattr(settings.GEMINI_API_KEY, 'get_secret_value', lambda: None)()

        providers = [
            {
                "provider": "ollama",
                "name": "Ollama",
                "enabled": True,
                "host": settings.OLLAMA_HOST,
                "models": {
                    "orchestrator": settings.OLLAMA_ORCHESTRATOR_MODEL,
                    "code_generator": settings.OLLAMA_CODER_MODEL,
                    "knowledge_curator": settings.OLLAMA_CURATOR_MODEL,
                },
            },
            {
                "provider": "openai",
                "name": "OpenAI",
                "enabled": _validate_openai_key(openai_key),
                "model_default": settings.OPENAI_MODEL_NAME,
            },
            {
                "provider": "google_gemini",
                "name": "Google Gemini",
                "enabled": _validate_gemini_key(gemini_key),
                "model_default": settings.GEMINI_MODEL_NAME,
            },
        ]

        return providers


# Padrão de Injeção de Dependência: Getter para o repositório
def get_llm_repository() -> LLMRepository:
    return LLMRepository()
