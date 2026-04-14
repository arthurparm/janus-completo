import random
from dataclasses import dataclass, field
from typing import Any, Callable

import structlog
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from prometheus_client import Counter, Gauge

from app.config import settings

from .factory import (
    _get_openai_http_client,
    _health_check_ollama,
    _validate_deepseek_key,
    _validate_gemini_key,
    _validate_openai_key,
    _validate_xai_key,
    create_ollama_llm,
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

logger = structlog.get_logger(__name__)

try:
    from langchain_openai import ChatOpenAI

    _LANGCHAIN_OPENAI_AVAILABLE = True
except Exception:
    _LANGCHAIN_OPENAI_AVAILABLE = False

    class ChatOpenAI:  # type: ignore[override]
        """Fallback type when langchain_openai is not installed."""

        pass

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


def _require_langchain_openai() -> None:
    if not _LANGCHAIN_OPENAI_AVAILABLE:
        raise RuntimeError(
            "langchain_openai is not installed. Install it to use OpenAI-compatible chat models."
        )


def _create_openai_compatible_chat(**kwargs):
    _require_langchain_openai()
    return ChatOpenAI(**kwargs)


def _normalize(values):
    if not values:
        return []
    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        return [1.0 for _ in values]
    return [(v - min_v) / (max_v - min_v) for v in values]


MODELS_WITHOUT_TEMPERATURE_SUPPORT = frozenset(
    {
        "o1",
        "o1-mini",
        "o1-preview",
        "o3",
        "o3-mini",
        "o3-mini-2025-01-31",
        "gpt-5",
    }
)


def _model_supports_temperature(model_name: str) -> bool:
    model_lower = model_name.lower()
    for no_temp_model in MODELS_WITHOUT_TEMPERATURE_SUPPORT:
        if model_lower == no_temp_model or model_lower.startswith(f"{no_temp_model}-"):
            return False
    return True


def _normalize_provider_key(provider: str | None) -> str | None:
    if not provider:
        return None
    key = str(provider).strip().lower()
    aliases = {
        "gemini": "google_gemini",
        "google": "google_gemini",
        "google_gemini": "google_gemini",
        "xai": "xai",
        "grok": "xai",
        "ollama": "ollama",
        "openai": "openai",
        "deepseek": "deepseek",
    }
    return aliases.get(key, key)


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _create_openai_model(
    model: str, temperature: float = 0, max_tokens: int | None = None
) -> ChatOpenAI:
    api_key = getattr(settings.OPENAI_API_KEY, "get_secret_value", lambda: None)()

    kwargs = {
        "model": model,
        "openai_api_key": api_key,
        "http_client": _get_openai_http_client(),
    }
    if _model_supports_temperature(model):
        kwargs["temperature"] = temperature
    else:
        logger.debug(
            "log_debug", message=f"Model {model} doesn't support temperature, omitting it"
        )
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    return _create_openai_compatible_chat(**kwargs)


@dataclass
class RouterSelection:
    role: ModelRole
    priority: ModelPriority
    cache_key: str = ""
    exclude_providers: list[str] = field(default_factory=list)
    explicit_provider: str | None = None
    explicit_model: str | None = None
    temperature_override: float | None = None
    max_tokens_override: int | None = None
    ollama_kwargs_override: dict[str, Any] = field(default_factory=dict)

    @property
    def pool_allowed(self) -> bool:
        return (
            self.temperature_override is None
            and self.max_tokens_override is None
            and not self.ollama_kwargs_override
        )


@dataclass(frozen=True)
class ModelCandidate:
    name: str
    provider_key: str
    model_name: str
    initializer_factory: Callable[[str], BaseChatModel]
    stats: ModelStats
    cost_per_1k: float


class LLMFactory:
    def __init__(self, selection: RouterSelection):
        self.selection = selection

    @property
    def local_model_name(self) -> str:
        model_map = {
            ModelRole.ORCHESTRATOR: settings.OLLAMA_ORCHESTRATOR_MODEL,
            ModelRole.CODE_GENERATOR: settings.OLLAMA_CODER_MODEL,
            ModelRole.KNOWLEDGE_CURATOR: settings.OLLAMA_CURATOR_MODEL,
            ModelRole.REASONER: settings.OLLAMA_CODER_MODEL,
        }
        local_model_name = model_map.get(self.selection.role, settings.OLLAMA_ORCHESTRATOR_MODEL)
        if self.selection.explicit_provider == "ollama" and self.selection.explicit_model:
            return self.selection.explicit_model
        return local_model_name

    @property
    def deepseek_temperature(self) -> float:
        deepseek_temp_by_role = getattr(settings, "DEEPSEEK_TEMPERATURE_BY_ROLE", {}) or {}
        default_temp = float(
            deepseek_temp_by_role.get(
                self.selection.role.value, getattr(settings, "DEEPSEEK_TEMPERATURE", 0.0)
            )
        )
        if self.selection.temperature_override is not None:
            return float(self.selection.temperature_override)
        return default_temp

    @property
    def default_temperature(self) -> float:
        if self.selection.temperature_override is not None:
            return float(self.selection.temperature_override)
        return 0.0

    def resolve_model_name(self, provider_key: str) -> str:
        if provider_key == "ollama":
            return self.selection.explicit_model or self.local_model_name
        if provider_key == "openai":
            return self.selection.explicit_model or settings.OPENAI_MODEL_NAME
        if provider_key == "google_gemini":
            return self.selection.explicit_model or settings.GEMINI_MODEL_NAME
        if provider_key == "deepseek":
            return self.selection.explicit_model or settings.DEEPSEEK_MODEL_NAME
        if provider_key == "xai":
            return self.selection.explicit_model or settings.XAI_MODEL_NAME
        raise RuntimeError(f"Unsupported provider override: {provider_key}")

    def get_pooled(self, provider_key: str, model_name: str) -> BaseChatModel | None:
        if not self.selection.pool_allowed:
            return None
        return _get_from_pool(provider_key, model_name)

    def remember(self, provider_key: str, model_name: str, llm: BaseChatModel) -> None:
        if self.selection.pool_allowed:
            _add_to_pool(provider_key, model_name, llm)

    def cloud_catalog(self) -> list[dict[str, Any]]:
        if self.selection.priority == ModelPriority.HIGH_QUALITY:
            provider_order = ["xAI", "OpenAI", "Google Gemini", "DeepSeek"]
        else:
            provider_order = ["DeepSeek", "Google Gemini", "xAI", "OpenAI"]

        cloud_providers = {
            "DeepSeek": {
                "name": "DeepSeek",
                "provider_key": "deepseek",
                "enabled": _validate_deepseek_key(
                    getattr(settings.DEEPSEEK_API_KEY, "get_secret_value", lambda: None)()
                ),
                "initializer_factory": lambda model: _create_openai_compatible_chat(
                    model=model,
                    temperature=self.deepseek_temperature,
                    api_key=getattr(
                        settings.DEEPSEEK_API_KEY, "get_secret_value", lambda: None
                    )(),
                    base_url=settings.DEEPSEEK_BASE_URL,
                    max_tokens=(
                        self.selection.max_tokens_override
                        if self.selection.max_tokens_override is not None
                        else (8000 if "reasoner" in model else None)
                    ),
                ),
                "models": (
                    settings.DEEPSEEK_MODELS
                    if getattr(settings, "DEEPSEEK_MODELS", None)
                    else [settings.DEEPSEEK_MODEL_NAME]
                ),
            },
            "Google Gemini": {
                "name": "Google Gemini",
                "provider_key": "google_gemini",
                "enabled": _validate_gemini_key(
                    getattr(settings.GEMINI_API_KEY, "get_secret_value", lambda: None)()
                ),
                "initializer_factory": lambda model: ChatGoogleGenerativeAI(
                    model=model,
                    temperature=self.default_temperature,
                    google_api_key=(
                        getattr(settings.GEMINI_API_KEY, "get_secret_value", lambda: None)()
                        or None
                    ),
                ),
                "models": (
                    settings.GEMINI_MODELS
                    if getattr(settings, "GEMINI_MODELS", None)
                    else [settings.GEMINI_MODEL_NAME]
                ),
            },
            "OpenAI": {
                "name": "OpenAI",
                "provider_key": "openai",
                "enabled": _validate_openai_key(
                    getattr(settings.OPENAI_API_KEY, "get_secret_value", lambda: None)()
                ),
                "initializer_factory": lambda model: _create_openai_model(
                    model,
                    temperature=self.default_temperature,
                    max_tokens=self.selection.max_tokens_override,
                ),
                "models": (
                    settings.OPENAI_MODELS
                    if getattr(settings, "OPENAI_MODELS", None)
                    else [settings.OPENAI_MODEL_NAME]
                ),
            },
            "xAI": {
                "name": "xAI Grok",
                "provider_key": "xai",
                "enabled": _validate_xai_key(
                    getattr(settings.XAI_API_KEY, "get_secret_value", lambda: None)()
                ),
                "initializer_factory": lambda model: _create_openai_compatible_chat(
                    model=model,
                    temperature=self.default_temperature,
                    api_key=getattr(settings.XAI_API_KEY, "get_secret_value", lambda: None)(),
                    base_url=settings.XAI_BASE_URL,
                    max_tokens=(
                        self.selection.max_tokens_override
                        if self.selection.max_tokens_override is not None
                        else 8000
                    ),
                ),
                "models": (
                    settings.XAI_MODELS
                    if getattr(settings, "XAI_MODELS", None)
                    else [settings.XAI_MODEL_NAME]
                ),
            },
        }
        return [cloud_providers[name] for name in provider_order if name in cloud_providers]

    def create(self, provider_key: str, model_name: str) -> BaseChatModel:
        if provider_key == "ollama":
            llm = create_ollama_llm(
                model_name,
                temperature=self.selection.temperature_override,
                model_kwargs=self.selection.ollama_kwargs_override,
            )
            if not _health_check_ollama(llm, timeout_s=settings.LLM_DEFAULT_TIMEOUT_SECONDS * 3):
                raise RuntimeError(f"Health check failed for model '{model_name}'")
            return llm

        for descriptor in self.cloud_catalog():
            if descriptor["provider_key"] == provider_key:
                return descriptor["initializer_factory"](model_name)

        raise RuntimeError(f"Unsupported provider override: {provider_key}")


class CandidateFilter:
    def __init__(self, selection: RouterSelection, factory: LLMFactory):
        self.selection = selection
        self.factory = factory

    async def ensure_explicit_provider_allowed(self, provider_key: str) -> None:
        if provider_key in self.selection.exclude_providers:
            raise RuntimeError(f"Explicit provider '{provider_key}' is excluded for selection.")
        if provider_key == "ollama":
            return

        descriptor = next(
            (
                item
                for item in self.factory.cloud_catalog()
                if item["provider_key"] == provider_key
            ),
            None,
        )
        if descriptor is None:
            raise RuntimeError(f"Unsupported provider override: {provider_key}")
        if not descriptor["enabled"]:
            raise RuntimeError(f"{provider_key} provider unavailable.")
        if not _circuit_closed(provider_key) or not await _budget_allows(provider_key):
            raise RuntimeError(f"{provider_key} provider unavailable.")

    def _role_candidates_map(self) -> dict[str, set[str]]:
        role_key = self.selection.role.value
        raw_role_candidates = getattr(settings, "LLM_CLOUD_MODEL_CANDIDATES", {}).get(role_key, [])
        role_candidates_map: dict[str, set[str]] = {}
        for spec in raw_role_candidates:
            try:
                provider_key, model_name = spec.split(":", 1)
                role_candidates_map.setdefault(provider_key.strip(), set()).add(model_name.strip())
            except Exception:
                logger.warning(
                    "log_warning",
                    message=f"Spec de candidato inválido: '{spec}' — esperado 'provider:model'",
                )
        return role_candidates_map

    async def cloud_candidates(self) -> list[ModelCandidate]:
        role_candidates_map = self._role_candidates_map()
        candidates: list[ModelCandidate] = []

        for descriptor in self.factory.cloud_catalog():
            provider_key = descriptor["provider_key"]
            if provider_key in self.selection.exclude_providers:
                continue
            if not descriptor["enabled"]:
                continue
            if not _circuit_closed(provider_key) or not await _budget_allows(provider_key):
                continue

            if role_candidates_map:
                if provider_key not in role_candidates_map:
                    continue
                model_list = list(role_candidates_map[provider_key])
            else:
                model_list = descriptor["models"]

            for model_name in model_list:
                rate_limiter = get_rate_limiter()
                if not rate_limiter.is_available(provider_key, model_name):
                    availability = rate_limiter.get_availability(provider_key, model_name)
                    logger.info(
                        "log_info",
                        message=(
                            f"Modelo {provider_key}:{model_name} indisponível por rate limit "
                            f"(uso={availability['usage_percent']:.1%})"
                        ),
                    )
                    continue

                pricing = _get_model_pricing(provider_key, model_name)
                stats = _model_stats.get(provider_key, {}).get(model_name, ModelStats())
                candidates.append(
                    ModelCandidate(
                        name=descriptor["name"],
                        provider_key=provider_key,
                        model_name=model_name,
                        initializer_factory=descriptor["initializer_factory"],
                        stats=stats,
                        cost_per_1k=pricing.input_per_1k_usd + pricing.output_per_1k_usd,
                    )
                )

        return candidates


class ModelRanker:
    def __init__(self, selection: RouterSelection):
        self.selection = selection

    def rank(self, candidates: list[ModelCandidate]) -> list[tuple[float, ModelCandidate]]:
        if not candidates:
            return []

        role_key = self.selection.role.value
        expected_k = float(
            _expected_k_ema_by_role.get(
                role_key,
                float(getattr(settings, "LLM_EXPECTED_KTOKENS_BY_ROLE", {}).get(role_key, 2.0)),
            )
        )
        max_cost = float(
            getattr(settings, "LLM_MAX_COST_PER_REQUEST_USD", {}).get(role_key, float("inf"))
        )

        filtered: list[ModelCandidate] = []
        for candidate in candidates:
            expected_cost = expected_k * candidate.cost_per_1k
            try:
                LLM_EXPECTED_COST_USD.labels(
                    priority=self.selection.priority.value,
                    provider=candidate.provider_key,
                    model=candidate.model_name,
                    role=role_key,
                ).set(expected_cost)
            except Exception:
                pass

            if expected_cost <= max_cost:
                filtered.append(candidate)
            else:
                logger.info(
                    "log_info",
                    message=(
                        f"Candidato filtrado por custo: {candidate.provider_key}:{candidate.model_name} "
                        f"(expected_cost={expected_cost:.4f} > max_cost={max_cost:.4f}, role={role_key})"
                    ),
                )

        active_candidates = filtered or candidates
        cost_norm = _normalize([candidate.cost_per_1k for candidate in active_candidates])
        lat_norm = _normalize(
            [
                candidate.stats.avg_latency if candidate.stats.total_requests > 0 else 1.0
                for candidate in active_candidates
            ]
        )
        success_rates = [
            candidate.stats.success_rate if candidate.stats.total_requests > 0 else 0.7
            for candidate in active_candidates
        ]

        econ = getattr(settings, "LLM_ECONOMY_POLICY", "balanced").lower()
        scored: list[tuple[float, ModelCandidate]] = []
        for idx, candidate in enumerate(active_candidates):
            penalty_factor = _model_penalty_factors.get(candidate.provider_key, {}).get(
                candidate.model_name, 1.0
            )
            if self.selection.priority == ModelPriority.FAST_AND_CHEAP:
                failure_penalty = 1.0 - success_rates[idx]
                if econ == "strict":
                    w_cost, w_lat, w_fail = 0.75, 0.20, 0.05
                elif econ == "quality":
                    w_cost, w_lat, w_fail = 0.45, 0.35, 0.20
                else:
                    w_cost, w_lat, w_fail = 0.60, 0.30, 0.10
                score = (
                    w_cost * cost_norm[idx]
                    + w_lat * lat_norm[idx]
                    + w_fail * failure_penalty
                )
                if penalty_factor > 1.0:
                    score = score / penalty_factor
            else:
                if econ == "strict":
                    alpha = 0.20
                elif econ == "quality":
                    alpha = 0.00
                else:
                    alpha = 0.10
                score = success_rates[idx] - 0.3 * lat_norm[idx] - alpha * cost_norm[idx]
                if penalty_factor > 1.0:
                    score = score / penalty_factor

            scored.append((score, candidate))
            LLM_SELECTION_SCORE.labels(
                priority=self.selection.priority.value,
                provider=candidate.provider_key,
            ).set(score)
            LLM_MODEL_SELECTION_SCORE.labels(
                priority=self.selection.priority.value,
                provider=candidate.provider_key,
                model=candidate.model_name,
            ).set(score)

        reverse = self.selection.priority == ModelPriority.HIGH_QUALITY
        scored.sort(key=lambda item: item[0], reverse=reverse)

        explore_p = float(getattr(settings, "LLM_EXPLORATION_PERCENT", 0.0) or 0.0)
        if explore_p > 0.0 and len(scored) > 1 and random.random() < explore_p:
            alt_idx = random.randint(1, len(scored) - 1)
            scored[0], scored[alt_idx] = scored[alt_idx], scored[0]
            try:
                LLM_EXPLORATION_DECISIONS.labels(
                    role=self.selection.role.value,
                    priority=self.selection.priority.value,
                ).inc()
            except Exception:
                pass
            logger.info(
                "log_info",
                message=(
                    f"Exploração ativada (p={explore_p:.2f}). "
                    f"Priorizando candidato alternativo index={alt_idx}."
                ),
            )

        return scored


def _build_selection(
    role: ModelRole,
    priority: ModelPriority,
    cache_key: str,
    exclude_providers: list[str] | None,
    config: dict[str, Any] | None,
) -> RouterSelection:
    selection = RouterSelection(
        role=role,
        priority=priority,
        cache_key=cache_key,
        exclude_providers=list(exclude_providers or []),
    )

    try:
        if config:
            if "priority" in config:
                selection.priority = ModelPriority(config["priority"])
            if "role" in config:
                selection.role = ModelRole(config["role"])
            if "exclude_providers" in config:
                config_exclude = config.get("exclude_providers")
                if isinstance(config_exclude, list):
                    selection.exclude_providers = list(
                        {*(selection.exclude_providers or []), *config_exclude}
                    )
                elif config_exclude:
                    selection.exclude_providers = [str(config_exclude)]
            if "provider" in config:
                selection.explicit_provider = _normalize_provider_key(config.get("provider"))
            if "model" in config and config.get("model") is not None:
                selection.explicit_model = str(config.get("model"))
            if "temperature" in config:
                selection.temperature_override = _coerce_float(config.get("temperature"))
            if "max_tokens" in config:
                selection.max_tokens_override = _coerce_int(config.get("max_tokens"))

            for key in ("num_ctx", "context", "context_window", "context_tokens"):
                if key in config:
                    ctx_val = _coerce_int(config.get(key))
                    if ctx_val is not None:
                        selection.ollama_kwargs_override["num_ctx"] = ctx_val

            if "num_thread" in config:
                thread_val = _coerce_int(config.get("num_thread"))
                if thread_val is not None:
                    selection.ollama_kwargs_override["num_thread"] = thread_val
            if "num_batch" in config:
                batch_val = _coerce_int(config.get("num_batch"))
                if batch_val is not None:
                    selection.ollama_kwargs_override["num_batch"] = batch_val
            for gpu_key in ("num_gpu", "gpu_layers", "gpu_layer"):
                if gpu_key not in config:
                    continue
                gpu_val = _coerce_int(config.get(gpu_key))
                if gpu_val is not None:
                    selection.ollama_kwargs_override["num_gpu"] = gpu_val
                    break
            if "keep_alive" in config and config.get("keep_alive") is not None:
                selection.ollama_kwargs_override["keep_alive"] = config.get("keep_alive")
    except Exception as e:
        logger.warning(
            "log_warning",
            message=f"Error applying LLM overrides from config: {e}",
            exc_info=True,
        )

    if not selection.cache_key:
        selection.cache_key = f"{selection.role.value}_{selection.priority.value}"
    return selection


async def _apply_budget_guardrail(selection: RouterSelection) -> RouterSelection:
    if selection.priority in (ModelPriority.LOCAL_ONLY, ModelPriority.HIGH_QUALITY):
        return selection
    if await is_total_budget_threshold_exceeded():
        logger.warning(
            "log_warning",
            message=(
                f"Budget guardrail activated! Forcing LOCAL_ONLY for role={selection.role.value}, "
                f"original_priority={selection.priority.value}"
            ),
        )
        selection.priority = ModelPriority.LOCAL_ONLY
    return selection


def _register_selection(
    role: ModelRole,
    priority: str,
    model_name: str,
    provider_key: str,
    llm: BaseChatModel,
    factory: LLMFactory,
) -> BaseChatModel:
    LLM_ROUTER_COUNTER.labels(role.value, priority, model_name, provider_key).inc()
    factory.remember(provider_key, model_name, llm)
    return llm


async def get_llm(
    role: ModelRole = ModelRole.ORCHESTRATOR,
    priority: ModelPriority = ModelPriority.LOCAL_ONLY,
    cache_key: str = "",
    exclude_providers: list[str] | None = None,
    config: dict[str, Any] | None = None,
) -> BaseChatModel:
    """Obtém uma instância de LLM preservando overrides, pooling e fallback existentes."""

    selection = _build_selection(role, priority, cache_key, exclude_providers, config)
    selection = await _apply_budget_guardrail(selection)
    factory = LLMFactory(selection)
    candidate_filter = CandidateFilter(selection, factory)
    ranker = ModelRanker(selection)

    if selection.explicit_model and not selection.explicit_provider:
        logger.warning("LLM config model override ignored (missing provider).")

    if selection.explicit_provider:
        if (
            selection.explicit_provider != "ollama"
            and selection.priority == ModelPriority.LOCAL_ONLY
        ):
            logger.warning(
                "Explicit provider override ignored due to LOCAL_ONLY priority.",
                extra={"provider": selection.explicit_provider},
            )
        else:
            try:
                await candidate_filter.ensure_explicit_provider_allowed(selection.explicit_provider)
                model_name = factory.resolve_model_name(selection.explicit_provider)
                pooled = factory.get_pooled(selection.explicit_provider, model_name)
                if pooled:
                    return pooled
                llm = factory.create(selection.explicit_provider, model_name)
                return _register_selection(
                    selection.role,
                    selection.priority.value,
                    model_name,
                    selection.explicit_provider,
                    llm,
                    factory,
                )
            except Exception:
                logger.warning(
                    "Explicit LLM override failed; falling back to selection.",
                    exc_info=True,
                )

    if selection.priority == ModelPriority.LOCAL_ONLY:
        try:
            if "ollama" in selection.exclude_providers:
                raise RuntimeError("Provedor local 'ollama' está excluído para esta seleção.")
            pooled_local = factory.get_pooled("ollama", factory.local_model_name)
            if pooled_local:
                return pooled_local
            llm = factory.create("ollama", factory.local_model_name)
            logger.info(
                "log_info",
                message=f"Modelo local '{factory.local_model_name}' inicializado com sucesso.",
            )
            return _register_selection(
                selection.role,
                selection.priority.value,
                factory.local_model_name,
                "ollama",
                llm,
                factory,
            )
        except Exception as e:
            logger.error(
                "log_error",
                message=f"Falha crítica ao carregar modelo local para LOCAL_ONLY: {e}",
                exc_info=True,
            )
            raise RuntimeError(f"Falha crítica ao carregar modelo local. Causa: {e}") from e

    candidates = await candidate_filter.cloud_candidates()
    for score, candidate in ranker.rank(candidates):
        logger.info(
            "log_info",
            message=(
                f"Estratégia {selection.priority.value}: Tentando "
                f"{candidate.provider_key}:{candidate.model_name} "
                f"(score={score:.3f}, cost_1k={candidate.cost_per_1k:.3f}, "
                f"avg_lat={candidate.stats.avg_latency:.3f})"
            ),
        )
        try:
            pooled = factory.get_pooled(candidate.provider_key, candidate.model_name)
            if pooled:
                return pooled
            llm = candidate.initializer_factory(candidate.model_name)
            logger.info(
                "log_info",
                message=(
                    f"LLM '{candidate.provider_key}:{candidate.model_name}' "
                    "inicializado com sucesso."
                ),
            )
            return _register_selection(
                selection.role,
                selection.priority.value,
                candidate.model_name,
                candidate.provider_key,
                llm,
                factory,
            )
        except Exception as e:
            logger.warning(
                "log_warning",
                message=(
                    f"Falha ao inicializar '{candidate.provider_key}:{candidate.model_name}' "
                    f"(score={score:.3f}): {e}"
                ),
                exc_info=True,
            )

    logger.warning("Estratégias de nuvem falharam ou desabilitadas. Recorrendo ao modelo local.")
    try:
        if "ollama" in selection.exclude_providers:
            raise RuntimeError("Fallback local desativado: 'ollama' está excluído.")
        llm = factory.create("ollama", factory.local_model_name)
        return _register_selection(
            selection.role,
            "fallback",
            factory.local_model_name,
            "ollama",
            llm,
            factory,
        )
    except Exception as e:
        logger.critical(
            "log_critical",
            message=(
                "FALHA CRÍTICA: Nenhum provedor de LLM pôde ser inicializado. "
                f"Erro final: {e}"
            ),
            exc_info=True,
        )
        raise RuntimeError("Sistema inoperável: nenhum LLM disponível.") from e
