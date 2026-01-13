import logging
import random
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from prometheus_client import Counter, Gauge

from app.config import settings

from .factory import (
    _get_openai_http_client,
    _health_check_ollama,
    _validate_deepseek_key,
    _validate_gemini_key,
    _validate_openai_key,
)
from .pricing import (
    ModelStats,
    _budget_allows,
    _expected_k_ema_by_role,
    _get_model_pricing,
    _model_penalty_factors,
    _model_stats,
    is_total_budget_threshold_exceeded,
)
from .rate_limiter import get_rate_limiter
from .resilience import _add_to_pool, _circuit_closed, _get_from_pool
from .types import ModelPriority, ModelRole

logger = logging.getLogger(__name__)

# Metrics
LLM_ROUTER_COUNTER = Counter(
    "llm_router_model_selected_total",
    "Contador para os modelos selecionados pelo roteador dinâmico",
    ["role", "priority", "model_name", "provider"],
)
LLM_SELECTION_SCORE = Gauge(
    "llm_selection_score",
    "Score de seleção adaptativa por provedor",
    ["priority", "provider"],
)
LLM_MODEL_SELECTION_SCORE = Gauge(
    "llm_model_selection_score",
    "Score de seleção adaptativa por modelo",
    ["priority", "provider", "model"],
)
LLM_EXPECTED_COST_USD = Gauge(
    "llm_expected_cost_usd",
    "Custo esperado (USD) por candidato antes da seleção",
    ["priority", "provider", "model", "role"],
)
LLM_EXPLORATION_DECISIONS = Counter(
    "llm_exploration_decisions_total",
    "Contagem de decisões de exploração na seleção",
    ["role", "priority"],
)


def _normalize(values):
    # Evita divisão por zero; retorna lista de valores normalizados [0..1]
    if not values:
        return []
    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        return [1.0 for _ in values]
    return [(v - min_v) / (max_v - min_v) for v in values]


# Models that don't support temperature parameter (o1, o3 series)
MODELS_WITHOUT_TEMPERATURE_SUPPORT = frozenset(
    {"o1", "o1-mini", "o1-preview", "o3", "o3-mini", "o3-mini-2025-01-31"}
)


def _model_supports_temperature(model_name: str) -> bool:
    """Check if a model supports the temperature parameter."""
    model_lower = model_name.lower()
    for no_temp_model in MODELS_WITHOUT_TEMPERATURE_SUPPORT:
        if model_lower == no_temp_model or model_lower.startswith(f"{no_temp_model}-"):
            return False
    return True


def _create_openai_model(model: str, temperature: float = 0) -> ChatOpenAI:
    """Create OpenAI model with temperature awareness for o1/o3 models."""
    api_key = getattr(settings.OPENAI_API_KEY, "get_secret_value", lambda: None)()

    if _model_supports_temperature(model):
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            openai_api_key=api_key,
            http_client=_get_openai_http_client(),
        )
    else:
        logger.debug(f"Model {model} doesn't support temperature, omitting it")
        return ChatOpenAI(
            model=model, openai_api_key=api_key, http_client=_get_openai_http_client()
        )


async def get_llm(
    role: ModelRole = ModelRole.ORCHESTRATOR,
    priority: ModelPriority = ModelPriority.LOCAL_ONLY,
    cache_key: str = "",
    exclude_providers: list[str] | None = None,
    config: dict[str, Any] | None = None,
) -> BaseChatModel:
    """Obtém uma instância de um modelo de linguagem com base no papel e na prioridade.
    Suporta overrides via configuração (provider/model/temperature/exclude_providers/priority).
    """
    # Overrides por configuração dinâmica
    except Exception as e:
        logger.warning(f"Error applying LLM overrides from config: {e}", exc_info=True)
        # Continue to default selection logic

    # Dynamic Budget Guardrail: Force LOCAL_ONLY when total cloud spending exceeds threshold
    # Except for HIGH_QUALITY priority (critical tasks that need cloud models)
    if priority != ModelPriority.LOCAL_ONLY and priority != ModelPriority.HIGH_QUALITY:
        if await is_total_budget_threshold_exceeded():
            logger.warning(
                f"Budget guardrail activated! Forcing LOCAL_ONLY for role={role.value}, "
                f"original_priority={priority.value}"
            )
            priority = ModelPriority.LOCAL_ONLY

    if not cache_key:
        cache_key = f"{role.value}_{priority.value}"

    # Define nome do modelo local
    model_map = {
        ModelRole.ORCHESTRATOR: settings.OLLAMA_ORCHESTRATOR_MODEL,
        ModelRole.CODE_GENERATOR: settings.OLLAMA_CODER_MODEL,
        ModelRole.KNOWLEDGE_CURATOR: settings.OLLAMA_CURATOR_MODEL,
        ModelRole.REASONER: settings.OLLAMA_CODER_MODEL, # Fallback local para reasoner
    }
    local_model_name = model_map.get(role, settings.OLLAMA_ORCHESTRATOR_MODEL)

    pooled_local = (
        _get_from_pool("ollama", local_model_name) if priority == ModelPriority.LOCAL_ONLY else None
    )
    if pooled_local:
        return pooled_local

    # Estratégia 1: Prioridade é o Cérebro Soberano Local
    if priority == ModelPriority.LOCAL_ONLY:
        try:
            # Bloqueia se provedor local estiver excluído
            if exclude_providers and "ollama" in exclude_providers:
                raise RuntimeError("Provedor local 'ollama' está excluído para esta seleção.")
            # Model kwargs para tunar desempenho do OllaM
            model_kwargs: dict[str, Any] = {}
            if settings.OLLAMA_NUM_CTX:
                model_kwargs["num_ctx"] = settings.OLLAMA_NUM_CTX
            if settings.OLLAMA_NUM_THREAD:
                model_kwargs["num_thread"] = settings.OLLAMA_NUM_THREAD
            if settings.OLLAMA_NUM_BATCH:
                model_kwargs["num_batch"] = settings.OLLAMA_NUM_BATCH
            if settings.OLLAMA_GPU_LAYERS:
                model_kwargs["gpu_layer"] = settings.OLLAMA_GPU_LAYERS
            if settings.OLLAMA_KEEP_ALIVE:
                model_kwargs["keep_alive"] = settings.OLLAMA_KEEP_ALIVE

            llm = ChatOllama(
                base_url=settings.OLLAMA_HOST,
                model=local_model_name,
                temperature=0,
                model_kwargs=model_kwargs,
            )
            # Primeiro uso pode exigir carregar o modelo; aumentamos o timeout para reduzir falsos negativos
            if not _health_check_ollama(llm, timeout_s=settings.LLM_DEFAULT_TIMEOUT_SECONDS * 3):
                raise RuntimeError(f"Health check falhou para modelo '{local_model_name}'")

            logger.info(f"Modelo local '{local_model_name}' inicializado com sucesso.")
            LLM_ROUTER_COUNTER.labels(role.value, priority.value, local_model_name, "ollama").inc()
            _add_to_pool("ollama", local_model_name, llm)
            return llm
        except Exception as e:
            logger.error(
                f"Falha crítica ao carregar modelo local para LOCAL_ONLY: {e}", exc_info=True
            )
            raise RuntimeError(f"Falha crítica ao carregar modelo local. Causa: {e}") from e

    # Provedores de Nuvem (catálogo com factories por modelo)
    # DeepSeek é listado primeiro para ter prioridade em FAST_AND_CHEAP
    cloud_catalog = [
        {
            "name": "DeepSeek",
            "provider_key": "deepseek",
            "enabled": _validate_deepseek_key(
                getattr(settings.DEEPSEEK_API_KEY, "get_secret_value", lambda: None)()
            ),
            # DeepSeek R1 (reasoner) does not support temperature in some contexts or requires specific handling.
            # However, standard ChatOpenAI params usually work but 'deepseek-reasoner' might ignore temp.
            # We keep it standard but ensure base_url is correct.
            "initializer_factory": lambda model: ChatOpenAI(
                model=model,
                temperature=0, # DeepSeek Reasoner generally ignores this or prefers 0/null
                api_key=getattr(settings.DEEPSEEK_API_KEY, "get_secret_value", lambda: None)(),
                base_url=settings.DEEPSEEK_BASE_URL,
                max_tokens=8000 if "reasoner" in model else None, # R1 needs room for thinking
            ),
            "models": settings.DEEPSEEK_MODELS
            if getattr(settings, "DEEPSEEK_MODELS", None)
            else [settings.DEEPSEEK_MODEL_NAME],
        },
        {
            "name": "Google Gemini",
            "provider_key": "google_gemini",
            "enabled": _validate_gemini_key(
                getattr(settings.GEMINI_API_KEY, "get_secret_value", lambda: None)()
            ),
            "initializer_factory": lambda model: ChatGoogleGenerativeAI(
                model=model,
                temperature=0,
                google_api_key=(
                    getattr(settings.GEMINI_API_KEY, "get_secret_value", lambda: None)() or None
                ),
            ),
            "models": settings.GEMINI_MODELS
            if getattr(settings, "GEMINI_MODELS", None)
            else [settings.GEMINI_MODEL_NAME],
        },
        {
            "name": "OpenAI",
            "provider_key": "openai",
            "enabled": _validate_openai_key(
                getattr(settings.OPENAI_API_KEY, "get_secret_value", lambda: None)()
            ),
            "initializer_factory": lambda model: _create_openai_model(model),
            "models": settings.OPENAI_MODELS
            if getattr(settings, "OPENAI_MODELS", None)
            else [settings.OPENAI_MODEL_NAME],
        },
    ]

    # Estratégia 2: Rápido e Barato ou Alta Qualidade
    if priority in [ModelPriority.FAST_AND_CHEAP, ModelPriority.HIGH_QUALITY]:
        # Seleção adaptativa por modelo considerando orçamento, circuito e métricas observadas
        # Se houver candidatos por papel definidos, usa-os; caso contrário, usa listas de modelos por provedor
        role_key = role.value
        raw_role_candidates = getattr(settings, "LLM_CLOUD_MODEL_CANDIDATES", {}).get(role_key, [])

        # Mapa provider->set(models) derivado de LLM_CLOUD_MODEL_CANDIDATES
        role_candidates_map: dict[str, set] = {}
        for spec in raw_role_candidates:
            try:
                provider_key, model_name = spec.split(":", 1)
                role_candidates_map.setdefault(provider_key.strip(), set()).add(model_name.strip())
            except Exception:
                logger.warning(f"Spec de candidato inválido: '{spec}' — esperado 'provider:model'")

        candidates = []
        for p in cloud_catalog:
            provider_key = p["provider_key"]
            if exclude_providers and provider_key in exclude_providers:
                continue
            if not (
                p["enabled"] and _circuit_closed(provider_key) and await _budget_allows(provider_key)
            ):
                continue

            # Lista de modelos elegíveis para este papel
            # Se LLM_CLOUD_MODEL_CANDIDATES define candidatos para este papel,
            # usar APENAS os provedores/modelos especificados (não usar modelos padrão de outros provedores)
            if role_candidates_map:
                # Há candidatos específicos definidos - usar apenas provedores nele
                if provider_key not in role_candidates_map:
                    continue  # Pula provedores não listados nos candidatos
                model_list = list(role_candidates_map[provider_key])
            else:
                # Sem candidatos específicos - usar todos os modelos do provedor
                model_list = p["models"]

            for model_name in model_list:
                # Verifica disponibilidade de rate limit antes de adicionar candidato
                rate_limiter = get_rate_limiter()
                if not rate_limiter.is_available(provider_key, model_name):
                    availability = rate_limiter.get_availability(provider_key, model_name)
                    logger.info(
                        f"Modelo {provider_key}:{model_name} indisponível por rate limit "
                        f"(uso={availability['usage_percent']:.1%})"
                    )
                    continue

                pricing = _get_model_pricing(provider_key, model_name)
                cost_per_1k = pricing.input_per_1k_usd + pricing.output_per_1k_usd

                # Fetch stats from pricing module (or rather, the shared state)
                stats = _model_stats.get(provider_key, {}).get(model_name, ModelStats())

                candidates.append(
                    {
                        "name": p["name"],
                        "provider_key": provider_key,
                        "model_name": model_name,
                        "initializer_factory": p["initializer_factory"],
                        "pricing": pricing,
                        "stats": stats,
                        "cost_per_1k": cost_per_1k,
                    }
                )

        if candidates:
            role_key = role.value
            # Filtra por teto de custo estimado por papel (usa EMA dinâmica)
            expected_k = float(
                _expected_k_ema_by_role.get(
                    role_key,
                    float(getattr(settings, "LLM_EXPECTED_KTOKENS_BY_ROLE", {}).get(role_key, 2.0)),
                )
            )
            max_cost = float(
                getattr(settings, "LLM_MAX_COST_PER_REQUEST_USD", {}).get(role_key, float("inf"))
            )
            filtered = []
            for c in candidates:
                expected_cost = expected_k * c["cost_per_1k"]
                try:
                    LLM_EXPECTED_COST_USD.labels(
                        priority=priority.value,
                        provider=c["provider_key"],
                        model=c["model_name"],
                        role=role_key,
                    ).set(expected_cost)
                except Exception:
                    pass
                if expected_cost <= max_cost:
                    filtered.append(c)
                else:
                    logger.info(
                        f"Candidato filtrado por custo: {c['provider_key']}:{c['model_name']} (expected_cost={expected_cost:.4f} > max_cost={max_cost:.4f}, role={role_key})"
                    )

            candidates = (
                filtered or candidates
            )  # se todos foram filtrados, usa originais para evitar vazio
            # Normalizações para scoring
            cost_norm = _normalize([c["cost_per_1k"] for c in candidates])
            latencies = [
                c["stats"].avg_latency if c["stats"].total_requests > 0 else 1.0 for c in candidates
            ]
            lat_norm = _normalize(latencies)
            success_rates = [
                c["stats"].success_rate if c["stats"].total_requests > 0 else 0.7
                for c in candidates
            ]

            scored = []
            for idx, c in enumerate(candidates):
                econ = getattr(settings, "LLM_ECONOMY_POLICY", "balanced").lower()
                if priority == ModelPriority.FAST_AND_CHEAP:
                    failure_penalty = 1.0 - success_rates[idx]
                    if econ == "strict":
                        w_cost, w_lat, w_fail = 0.75, 0.20, 0.05
                    elif econ == "quality":
                        w_cost, w_lat, w_fail = 0.45, 0.35, 0.20
                    else:  # balanced
                        w_cost, w_lat, w_fail = 0.60, 0.30, 0.10
                    score = (
                        w_cost * cost_norm[idx] + w_lat * lat_norm[idx] + w_fail * failure_penalty
                    )
                    # Aplica penalização pós-execução acumulada ao score
                    pf = _model_penalty_factors.get(c["provider_key"], {}).get(c["model_name"], 1.0)
                    if pf > 1.0:
                        score = score / pf
                    scored.append((score, c))
                    LLM_SELECTION_SCORE.labels(
                        priority=priority.value, provider=c["provider_key"]
                    ).set(score)
                    LLM_MODEL_SELECTION_SCORE.labels(
                        priority=priority.value, provider=c["provider_key"], model=c["model_name"]
                    ).set(score)
                else:  # HIGH_QUALITY
                    if econ == "strict":
                        alpha = 0.20
                    elif econ == "quality":
                        alpha = 0.00
                    else:  # balanced
                        alpha = 0.10
                    score = success_rates[idx] - 0.3 * lat_norm[idx] - alpha * cost_norm[idx]
                    # Aplica penalização ao score
                    pf = _model_penalty_factors.get(c["provider_key"], {}).get(c["model_name"], 1.0)
                    if pf > 1.0:
                        score = score / pf
                    scored.append((score, c))
                    LLM_SELECTION_SCORE.labels(
                        priority=priority.value, provider=c["provider_key"]
                    ).set(score)
                    LLM_MODEL_SELECTION_SCORE.labels(
                        priority=priority.value, provider=c["provider_key"], model=c["model_name"]
                    ).set(score)

            # Ordenação por score
            if priority == ModelPriority.FAST_AND_CHEAP:
                scored.sort(key=lambda x: x[0])  # menor é melhor
            else:
                scored.sort(key=lambda x: x[0], reverse=True)  # maior é melhor
            # Exploração ocasional: escolhe candidato alternativo
            explore_p = float(getattr(settings, "LLM_EXPLORATION_PERCENT", 0.0) or 0.0)
            if explore_p > 0.0 and len(scored) > 1 and random.random() < explore_p:
                alt_idx = random.randint(1, len(scored) - 1)
                scored[0], scored[alt_idx] = scored[alt_idx], scored[0]
                try:
                    LLM_EXPLORATION_DECISIONS.labels(role=role.value, priority=priority.value).inc()
                except Exception:
                    pass
                logger.info(
                    f"Exploração ativada (p={explore_p:.2f}). Priorizando candidato alternativo index={alt_idx}."
                )

            for score, cand in scored:
                logger.info(
                    f"Estratégia {priority.value}: Tentando {cand['provider_key']}:{cand['model_name']} (score={score:.3f}, cost_1k={cand['cost_per_1k']:.3f}, avg_lat={cand['stats'].avg_latency:.3f})"
                )
                try:
                    llm = cand["initializer_factory"](cand["model_name"])
                    logger.info(
                        f"LLM '{cand['provider_key']}:{cand['model_name']}' inicializado com sucesso."
                    )
                    LLM_ROUTER_COUNTER.labels(
                        role.value, priority.value, cand["model_name"], cand["provider_key"]
                    ).inc()
                    _add_to_pool(cand["provider_key"], cand["model_name"], llm)
                    return llm
                except Exception as e:
                    logger.warning(
                        f"Falha ao inicializar '{cand['provider_key']}:{cand['model_name']}' (score={score:.3f}): {e}",
                        exc_info=True,
                    )

    # Fallback final para o modelo local
    logger.warning("Estratégias de nuvem falharam ou desabilitadas. Recorrendo ao modelo local.")
    try:
        if exclude_providers and "ollama" in exclude_providers:
            raise RuntimeError("Fallback local desativado: 'ollama' está excluído.")

        # Recalcular model kwargs localmente ou pegar de constants
        # Para simplificar aqui, assumimos defaults ou hardcoded similares
        model_kwargs: dict[str, Any] = {}
        if settings.OLLAMA_NUM_CTX:
            model_kwargs["num_ctx"] = settings.OLLAMA_NUM_CTX
        if settings.OLLAMA_NUM_THREAD:
            model_kwargs["num_thread"] = settings.OLLAMA_NUM_THREAD
        if settings.OLLAMA_NUM_BATCH:
            model_kwargs["num_batch"] = settings.OLLAMA_NUM_BATCH
        if settings.OLLAMA_GPU_LAYERS:
            model_kwargs["gpu_layer"] = settings.OLLAMA_GPU_LAYERS
        if settings.OLLAMA_KEEP_ALIVE:
            model_kwargs["keep_alive"] = settings.OLLAMA_KEEP_ALIVE

        llm = ChatOllama(
            base_url=settings.OLLAMA_HOST,
            model=local_model_name,
            temperature=0,
            model_kwargs=model_kwargs,
        )
        if not _health_check_ollama(llm, timeout_s=settings.LLM_DEFAULT_TIMEOUT_SECONDS * 3):
            raise RuntimeError(
                f"Health check falhou para modelo local '{local_model_name}' no fallback"
            )

        LLM_ROUTER_COUNTER.labels(role.value, "fallback", local_model_name, "ollama").inc()
        _add_to_pool("ollama", local_model_name, llm)
        return llm
    except Exception as e:
        logger.critical(
            f"FALHA CRÍTICA: Nenhum provedor de LLM pôde ser inicializado. Erro final: {e}",
            exc_info=True,
        )
        raise RuntimeError("Sistema inoperável: nenhum LLM disponível.") from e




