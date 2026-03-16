from typing import Any

import structlog
from fastapi import Request

from app.config import settings
from app.core.llm import ModelPriority, ModelRole
from app.core.llm.task_policy import resolve_llm_task_policy
from app.core.infrastructure.prompt_loader import get_formatted_prompt
from app.core.monitoring.health_monitor import check_llm_router_health
from app.services.prompt_service import PromptService

try:
    from app.repositories.llm_repository import LLMRepository, LLMRepositoryError
except Exception:
    class LLMRepositoryError(Exception):
        pass

    class LLMRepository:  # type: ignore[override]
        pass

logger = structlog.get_logger(__name__)

# --- Custom Service-Layer Exceptions ---


class LLMServiceError(Exception):
    """Base exception for LLM service errors."""

    pass


class LLMInvocationError(LLMServiceError):
    """Raised on failure to invoke an LLM."""

    pass


class LLMTimeoutError(LLMServiceError):
    """Raised on LLM invocation timeout."""

    pass


# --- LLM Service ---


class LLMService:
    """
    Camada de serviço para gerenciamento do Cérebro Híbrido (LLMs).
    Orquestra a lógica de negócio, recebendo suas dependências via DI.
    """

    def __init__(self, repo: LLMRepository, prompt_service: PromptService | None = None):
        self._repo = repo
        self._prompt_service = prompt_service

    async def invoke_llm(
        self,
        prompt: str,
        role: ModelRole,
        priority: ModelPriority,
        timeout_seconds: int | None,
        task_type: str | None = None,
        complexity: str | None = None,
        policy_overrides: dict[str, Any] | None = None,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        policy = resolve_llm_task_policy(task_type, complexity, policy_overrides)
        llm_config: dict[str, Any] | None = None

        if isinstance(policy, dict) and policy:
            role_override = policy.get("role")
            if role_override:
                try:
                    role = (
                        role_override
                        if isinstance(role_override, ModelRole)
                        else ModelRole(role_override)
                    )
                except Exception:
                    logger.warning("Invalid policy role override ignored", role=str(role_override))

            priority_override = policy.get("priority")
            if priority_override:
                try:
                    priority = (
                        priority_override
                        if isinstance(priority_override, ModelPriority)
                        else ModelPriority(priority_override)
                    )
                except Exception:
                    logger.warning(
                        "Invalid policy priority override ignored", priority=str(priority_override)
                    )

            timeout_override = policy.get("timeout_seconds", policy.get("timeout"))
            if timeout_override is not None:
                try:
                    timeout_seconds = int(timeout_override)
                except Exception:
                    logger.warning(
                        "Invalid policy timeout override ignored", timeout=str(timeout_override)
                    )

            llm_config = {}
            direct_config = policy.get("llm_config")
            if isinstance(direct_config, dict):
                llm_config.update(direct_config)

            for key in (
                "provider",
                "model",
                "temperature",
                "max_tokens",
                "exclude_providers",
                "strict_provider",
                "disable_failover",
                "disable_response_cache",
                "num_ctx",
                "num_thread",
                "num_batch",
                "gpu_layer",
                "keep_alive",
            ):
                if key in policy:
                    llm_config[key] = policy[key]

            if not llm_config:
                llm_config = None

        logger.info(
            "Orquestrando invocação de LLM via serviço", role=role.value, priority=priority.value
        )
        try:
            # Aplica cabeçalho de identidade para reforçar que o assistente é Janus
            if getattr(settings, "IDENTITY_ENFORCEMENT_ENABLED", True):
                identity = getattr(settings, "AGENT_IDENTITY_NAME", None) or getattr(
                    settings, "APP_NAME", "Janus"
                )

                identity_header = ""
                try:
                    identity_header = await get_formatted_prompt(
                        "system_identity_enforcement",
                        identity=identity,
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to fetch identity prompt",
                        error=str(e),
                        prompt_name="system_identity_enforcement",
                    )

                if identity_header:
                    prompt = f"{identity_header}\n\n{prompt}"

            return await self._repo.invoke_llm(
                prompt,
                role,
                priority,
                timeout_seconds,
                user_id=user_id,
                project_id=project_id,
                llm_config=llm_config,
            )
        except TimeoutError as e:
            logger.error("Timeout no serviço de LLM", exc_info=e)
            raise LLMTimeoutError(str(e)) from e
        except LLMRepositoryError as e:
            logger.error("Erro no repositório de LLM", exc_info=e)
            raise LLMInvocationError(f"Falha ao invocar LLM: {e}") from e

    def get_cache_status(self) -> list[dict[str, Any]]:
        logger.info("Buscando status do cache de LLMs via serviço.")
        return self._repo.get_cache_entries()

    def invalidate_cache(self, provider: str | None = None) -> int:
        logger.info("Orquestrando invalidação de cache de LLMs via serviço", provider=provider)
        return self._repo.invalidate_cache(provider)

    # --- Response cache specific controls ---
    def get_response_cache_status(self) -> list[dict[str, Any]]:
        """Retorna apenas entradas do cache de respostas (prompts/respostas)."""
        logger.info("Buscando status do cache de respostas via serviço.")
        try:
            entries = self._repo.get_cache_entries()
            return [e for e in entries if e.get("kind") == "response"]
        except LLMRepositoryError as e:
            logger.error("Erro no repositório ao obter status do cache de respostas", exc_info=e)
            raise LLMServiceError("Falha ao obter status do cache de respostas.") from e

    def invalidate_response_cache(
        self, prompt: str | None = None, role: str | None = None, priority: str | None = None
    ) -> int:
        """Invalida entradas do cache de respostas por filtro (prompt/role/priority) ou completas se não informado."""
        logger.info(
            "Invalidando cache de respostas via serviço",
            prompt=bool(prompt),
            role=role,
            priority=priority,
        )
        try:
            return self._repo.invalidate_response_cache(prompt=prompt, role=role, priority=priority)
        except LLMRepositoryError as e:
            logger.error("Erro no repositório ao invalidar cache de respostas", exc_info=e)
            raise LLMServiceError("Falha ao invalidar cache de respostas.") from e

    def get_circuit_breaker_statuses(self) -> list[dict[str, Any]]:
        logger.info("Buscando status dos circuit breakers via serviço.")
        return self._repo.get_circuit_breakers()

    def reset_circuit_breaker(self, provider: str) -> str:
        logger.info("Orquestrando reset de circuit breaker via serviço", provider=provider)
        try:
            self._repo.reset_circuit_breaker(provider)
            breakers = self._repo.get_circuit_breakers()
            for cb in breakers:
                if cb["provider"] == provider:
                    return cb["state"]
            return "unknown"
        except LLMRepositoryError as e:
            raise LLMServiceError(str(e)) from e

    def get_providers(self) -> list[dict[str, Any]]:
        logger.info("Listando provedores de LLMs via serviço.")
        return self._repo.list_providers()

    def warm_pool(self, specs: list[str] | None = None) -> dict[str, int]:
        logger.info("Pré-aquecendo pool de LLMs via serviço.")
        return self._repo.warm_pool(specs)

    async def get_health_status(self) -> dict[str, Any]:
        logger.info("Verificando saúde do sistema de LLMs via serviço.")
        # Usa health monitor central para consolidar o estado dos circuit breakers e cache
        return await check_llm_router_health()

    # --- Provider selection and CB state ---
    async def select_provider(
        self,
        role: ModelRole,
        priority: ModelPriority,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Seleciona provider/modelo antecipadamente sem invocar o LLM."""
        from app.core.llm import get_llm_client

        client = await get_llm_client(
            role=role, priority=priority, user_id=user_id, project_id=project_id
        )
        return {
            "provider": getattr(client, "provider", "unknown"),
            "model": getattr(client, "model", "unknown"),
        }

    def is_provider_open(self, provider: str) -> bool:
        """Retorna True se o circuit breaker do provider estiver aberto (bloqueado)."""
        try:
            breakers = self._repo.get_circuit_breakers()
            for cb in breakers:
                if cb.get("provider") == provider and cb.get("state") == "open":
                    return True
            return False
        except Exception as e:
            logger.debug("log_debug", message=f"Failed to check provider status: {e}")
            return False


# Padrão de Injeção de Dependência: Getter para o serviço
def get_llm_service(request: Request) -> LLMService:
    return request.app.state.llm_service
