import json
from contextlib import nullcontext
from typing import Any

import structlog

from app.config import settings
from app.core.infrastructure.logging_config import TRACE_ID, USER_ID
from app.core.llm.factory import _validate_gemini_key, _validate_openai_key, warm_llm_pool
from app.core.llm.response_cache import entries as rc_entries
from app.core.llm.response_cache import get as rc_get
from app.core.llm.response_cache import invalidate as rc_invalidate
from app.core.llm.response_cache import put as rc_put

try:
    from opentelemetry import trace  # type: ignore

    _OTEL = True
    _tracer = trace.get_tracer(__name__)
except Exception:
    _OTEL = False
    _tracer = None

from app.core.llm import (
    LLMClient,
    ModelPriority,
    ModelRole,
    get_circuit_breaker_snapshot,
    get_llm,
    get_llm_client,
    get_llm_pool_snapshot,
    get_llm_pool_summary,
    invalidate_cache,
    reset_provider_circuit_breaker,
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

    async def invoke_llm(
        self,
        prompt: str,
        role: ModelRole,
        priority: ModelPriority,
        timeout_seconds: int | None,
        user_id: str | None = None,
        project_id: str | None = None,
        llm_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        logger.debug("Invocando LLM via repositório", role=role.value, priority=priority.value)
        client = None
        span_cm = _tracer.start_as_current_span("llm.invoke") if _OTEL else nullcontext()
        try:
            with span_cm as span:
                if _OTEL and span is not None:
                    try:
                        span.set_attribute("llm.role", role.value)
                        span.set_attribute("llm.priority", priority.value)
                        sid = user_id or USER_ID.get()
                        tid = TRACE_ID.get()
                        if sid and sid != "-":
                            span.set_attribute("janus.user_id", sid)
                        if tid and tid != "-":
                            span.set_attribute("janus.trace_id", tid)
                    except Exception:
                        pass
            explicit_provider = None
            explicit_model = None
            strict_provider = False
            disable_failover = False
            disable_response_cache = False
            if isinstance(llm_config, dict):
                explicit_provider = llm_config.get("provider")
                explicit_model = llm_config.get("model")
                strict_provider = bool(llm_config.get("strict_provider"))
                disable_failover = bool(llm_config.get("disable_failover")) or strict_provider
                disable_response_cache = bool(llm_config.get("disable_response_cache")) or strict_provider

            # Cache de resposta: tentativa de hit antes de chamar provedor
            cached = None if disable_response_cache else rc_get(prompt, role.value, priority.value)
            if cached and strict_provider:
                cached_provider = cached.get("provider")
                cached_model = cached.get("model")
                if explicit_provider and str(cached_provider or "").strip().lower() != str(explicit_provider).strip().lower():
                    cached = None
                elif explicit_model and str(cached_model or "").strip() != str(explicit_model).strip():
                    cached = None
            if cached:
                logger.info("Resposta retornada do cache de prompts/respostas.")
                if _OTEL and span is not None:
                    try:
                        span.set_attribute("llm.cache_hit", True)
                        span.set_attribute("llm.provider", cached.get("provider", "unknown"))
                        span.set_attribute("llm.model", cached.get("model", "unknown"))
                    except Exception:
                        pass
                return {
                    "response": cached["response"],
                    "provider": cached.get("provider", "unknown"),
                    "model": cached.get("model", "unknown"),
                    "role": role.value,
                    "input_tokens": cached.get("input_tokens"),
                    "output_tokens": cached.get("output_tokens"),
                    "cost_usd": cached.get("cost_usd"),
                }

            client = None
            try:
                if (
                    user_id
                    and getattr(settings, "LLM_AB_EXPERIMENT_ID", None)
                    and not (explicit_provider or explicit_model)
                ):
                    from app.repositories.ab_experiment_repository import ABExperimentRepository

                    abr = ABExperimentRepository()
                    exp_id = int(settings.LLM_AB_EXPERIMENT_ID)
                    asg = abr.get_assignment(exp_id, str(user_id))
                    if not asg:
                        asg = abr.assign_user(exp_id, str(user_id))
                    arm_id = asg.arm_id
                    # Busca spec do braço
                    from app.models.ab_experiment_models import ExperimentArm

                    s = abr._get_session()
                    try:
                        arm = s.query(ExperimentArm).filter(ExperimentArm.id == arm_id).first()
                        if arm and arm.model_spec and ":" in arm.model_spec:
                            provider, model = arm.model_spec.split(":", 1)
                            ab_config = dict(llm_config or {})
                            ab_config["provider"] = provider
                            ab_config["model"] = model
                            llm = await get_llm(
                                role=role,
                                priority=priority,
                                cache_key=f"ab_{provider}_{model}_{role.value}",
                                config=ab_config,
                            )
                            client = LLMClient(
                                llm,
                                provider,
                                model,
                                role,
                                f"ab_{provider}_{model}_{role.value}",
                                user_id=user_id,
                                project_id=project_id,
                            )
                    finally:
                        if not abr._session:
                            s.close()
            except Exception:
                client = None
            if client is None:
                client = await get_llm_client(
                    role=role,
                    priority=priority,
                    user_id=user_id,
                    project_id=project_id,
                    config=llm_config,
                )
            if _OTEL and span is not None:
                try:
                    span.set_attribute("llm.cache_hit", False)
                    span.set_attribute("llm.provider", getattr(client, "provider", "unknown"))
                    span.set_attribute("llm.model", getattr(client, "model", "unknown"))
                except Exception:
                    pass
            import time as _t

            _start = _t.time()
            enriched = await client.send_enriched(prompt, timeout_s=timeout_seconds)

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
            try:
                from app.repositories.observability_repository import record_audit_event_direct

                detail = {
                    "provider": client.provider,
                    "model": client.model,
                    "role": role.value,
                    "input_tokens": enriched.get("input_tokens"),
                    "output_tokens": enriched.get("output_tokens"),
                    "cost_usd": enriched.get("cost_usd"),
                    "reasoning": enriched.get("reasoning"),
                }
                record_audit_event_direct(
                    {
                        "user_id": int(user_id) if user_id is not None else None,
                        "endpoint": "llm",
                        "action": "invoke",
                        "tool": client.provider,
                        "status": "ok",
                        "latency_ms": int((_t.time() - _start) * 1000),
                        "trace_id": TRACE_ID.get(),
                        "details_json": json.dumps(detail),
                    }
                )
            except Exception:
                pass

            return enriched
        except Exception as e:
            if disable_failover:
                raise
            logger.warning(
                "Falha na invocação inicial; tentando failover por provedor.", exc_info=True
            )
            # Failover: tenta outro provedor excluindo o atual
            try:
                failed_provider = getattr(client, "provider", "unknown") if client else None
                exclude = [failed_provider] if failed_provider else None
                fb_config = dict(llm_config or {})
                if "provider" in fb_config:
                    fb_config.pop("provider", None)
                if "model" in fb_config:
                    fb_config.pop("model", None)
                if not fb_config:
                    fb_config = None
                client_fb = await get_llm_client(
                    role=role,
                    priority=priority,
                    user_id=user_id,
                    project_id=project_id,
                    exclude_providers=exclude,
                    config=fb_config,
                )
                # Se não houver mudança de provedor, repropaga
                if client and getattr(client_fb, "provider", None) == getattr(
                    client, "provider", None
                ):
                    raise e
                enriched_fb = await client_fb.send_enriched(prompt, timeout_s=timeout_seconds)
                if _OTEL and _tracer is not None:
                    try:
                        with _tracer.start_as_current_span("llm.invoke.failover") as span_fb:
                            span_fb.set_attribute(
                                "llm.failed_provider", failed_provider or "unknown"
                            )
                            span_fb.set_attribute(
                                "llm.provider", getattr(client_fb, "provider", "unknown")
                            )
                            span_fb.set_attribute(
                                "llm.model", getattr(client_fb, "model", "unknown")
                            )
                            sid = user_id or USER_ID.get()
                            tid = TRACE_ID.get()
                            if sid and sid != "-":
                                span_fb.set_attribute("janus.user_id", sid)
                            if tid and tid != "-":
                                span_fb.set_attribute("janus.trace_id", tid)
                    except Exception:
                        pass
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
                logger.error(
                    "Erro no repositório ao invocar LLM (failover também falhou)", exc_info=True
                )
                raise LLMRepositoryError(f"Falha ao invocar LLM: {e2}") from e2

    def get_cache_entries(self) -> list[dict[str, Any]]:
        logger.debug("Buscando entradas do pool de LLMs no repositório.")
        entries = []
        pool_snapshot = get_llm_pool_snapshot()
        for key, items in pool_snapshot.items():
            try:
                provider, model = key.split(":", 1)
            except Exception:
                provider, model = "unknown", key
            entries.append(
                {
                    "pool_key": key,
                    "provider": provider,
                    "model": model,
                    "size": len(items),
                }
            )
            for it in items:
                entries.append(
                    {
                        "pool_key": key,
                        "provider": it.get("provider"),
                        "model": it.get("model"),
                        "consecutive_failures": it.get("consecutive_failures"),
                        "created_at": it.get("created_at"),
                    }
                )
        # Acrescenta entradas do cache de respostas
        try:
            entries.extend([{**e, "kind": "response"} for e in rc_entries()])
        except Exception:
            pass
        return entries

    def invalidate_cache(self, provider: str | None = None) -> int:
        logger.debug("Invalidando pool de LLMs via repositório", provider=provider)
        invalidate_cache(provider=provider)
        return get_llm_pool_summary()["pool_total_instances"]

    def warm_pool(self, specs: list[str] | None = None) -> dict[str, int]:
        logger.debug("Pré-aquecendo pool de LLMs via repositório.")
        return warm_llm_pool(specs or getattr(settings, "LLM_POOL_WARM_PROVIDERS", []) or [])

    def invalidate_response_cache(
        self, prompt: str | None = None, role: str | None = None, priority: str | None = None
    ) -> int:
        logger.debug(
            "Invalidando cache de respostas via repositório",
            prompt=bool(prompt),
            role=role,
            priority=priority,
        )
        return rc_invalidate(prompt=prompt, role=role, priority=priority)

    def get_circuit_breakers(self) -> list[dict[str, Any]]:
        logger.debug("Buscando status dos circuit breakers no repositório.")
        statuses = []
        for provider, cb in get_circuit_breaker_snapshot().items():
            statuses.append(
                {
                    "provider": provider,
                    "state": cb.get("state"),
                    "failure_count": cb.get("failure_count"),
                    "last_failure_time": cb.get("last_failure_time"),
                }
            )
        return statuses

    def reset_circuit_breaker(self, provider: str):
        logger.debug("Resetando circuit breaker via repositório", provider=provider)
        if not reset_provider_circuit_breaker(provider):
            raise LLMRepositoryError(f"Provedor '{provider}' não encontrado.")

    def list_providers(self) -> list[dict[str, Any]]:
        """Lista provedores configurados com status de habilitação e modelos padrão."""
        logger.debug("Listando provedores de LLMs via repositório.")

        # Recupera chaves (podem ser SecretStr) e valida
        openai_key = getattr(settings.OPENAI_API_KEY, "get_secret_value", lambda: None)()
        gemini_key = getattr(settings.GEMINI_API_KEY, "get_secret_value", lambda: None)()

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
