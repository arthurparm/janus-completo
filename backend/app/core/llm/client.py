import structlog
import time
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from prometheus_client import Counter, Histogram

from app.config import settings
from app.core.infrastructure.resilience import CircuitBreaker, CircuitOpenError, resilient
from app.core.monitoring.health_monitor import get_timeout_recommendation

from . import response_cache  # Import cache module

# New Modules
from .adapters import get_adapter
from .factory import _health_check_ollama, _infer_model_name, _infer_provider
from .pricing import _budget_remaining, _get_model_pricing, _tenant_budget_remaining, register_usage
from .rate_limiter import get_rate_limiter
from .resilience import _llm_pool, _pool_key, _provider_circuit_breakers
from .router import get_llm
from .sanitizer import ContentSanitizer
from .types import ModelPriority, ModelRole

logger = structlog.get_logger(__name__)

try:
    from langchain_ollama import ChatOllama

    _OLLAMA_AVAILABLE = True
except Exception:
    _OLLAMA_AVAILABLE = False
    ChatOllama = None  # type: ignore[assignment]

# Metrics
LLM_REQUESTS = Counter(
    "llm_requests_total",
    "Total de requisições ao provedor LLM",
    ["provider", "model", "role", "outcome", "exception_type"],
)
LLM_LATENCY = Histogram(
    "llm_request_latency_seconds",
    "Latência por requisição LLM",
    ["provider", "model", "role", "outcome"],
)
LLM_TOKENS = Counter(
    "llm_tokens_total",
    "Tokens contabilizados (aprox.) por direção",
    ["provider", "model", "role", "direction"],
)


class LLMClient:
    """Cliente unificado para invocar LLMs com métricas, timeouts e resiliência.

    Refatorado para usar Adaptadores e Sanitizadores independentes.
    """

    def __init__(
        self,
        base: BaseChatModel,
        provider: str,
        model: str,
        role: ModelRole,
        cache_key: str,
        user_id: str | None = None,
        project_id: str | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        config: Any = None,
    ):
        self.base = base
        self.provider = provider
        self.model = model
        self.role = role
        self.cache_key = cache_key
        self.user_id = user_id
        self.project_id = project_id
        self.settings = config if config is not None else settings
        self.circuit_breaker = circuit_breaker

        # Delegates
        self.adapter = get_adapter(base, provider)
        self.sanitizer = ContentSanitizer(self.settings)

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def _validate_prompt(self, prompt: str):
        if not prompt or not prompt.strip():
            raise ValueError("Prompt não pode ser vazio.")
        if len(prompt) > self.settings.LLM_MAX_PROMPT_LENGTH:
            raise ValueError(
                f"Prompt excede o tamanho máximo de {self.settings.LLM_MAX_PROMPT_LENGTH} caracteres."
            )

    def _invoke(self, prompt: str) -> Any:
        return self.adapter.invoke(prompt)

    async def _compute_output_limit(self, prompt: str) -> int:
        pricing = _get_model_pricing(self.provider, self.model)
        tokens_in = self._estimate_tokens(prompt)
        role_key = self.role.value
        max_req_cost = float(
            getattr(self.settings, "LLM_MAX_COST_PER_REQUEST_USD", {}).get(role_key, float("inf"))
        )
        cap = int(getattr(self.settings, "LLM_MAX_GENERATION_TOKENS_CAP", 0) or 0)
        min_tokens = int(getattr(self.settings, "LLM_MIN_GENERATION_TOKENS", 0) or 0)

        input_cost_usd = (tokens_in / 1000.0) * pricing.input_per_1k_usd
        remaining_req_usd = (
            max(0.0, (max_req_cost - input_cost_usd))
            if max_req_cost < float("inf")
            else float("inf")
        )
        remaining_provider_usd = await _budget_remaining(self.provider)
        remaining_user_usd = await _tenant_budget_remaining("user", self.user_id)
        remaining_project_usd = await _tenant_budget_remaining("project", self.project_id)

        def usd_to_out_tokens(usd: float) -> int:
            if usd == float("inf"):
                return 10**9
            try:
                return int((usd / max(1e-12, pricing.output_per_1k_usd)) * 1000)
            except Exception:
                return 0

        allowances = [
            usd_to_out_tokens(remaining_req_usd),
            usd_to_out_tokens(remaining_provider_usd),
            usd_to_out_tokens(remaining_user_usd),
            usd_to_out_tokens(remaining_project_usd),
        ]

        allowed = min([a for a in allowances if a >= 0]) if allowances else 0
        if cap and cap > 0:
            allowed = min(allowed, cap)
        if allowed < min_tokens and self.provider != "ollama":
            return allowed
        return max(allowed, min_tokens)

    def _handle_rate_limit_error(self, error: Exception):
        try:
            is_quota = False
            err_str = str(error).lower()
            err_type = str(type(error))

            # Detectar erros de cota/rate limit
            if "ResourceExhausted" in err_type or "429" in err_str or "quota" in err_str:
                is_quota = True

            if is_quota:
                logger.warning("log_warning", message=f"Quota Exceeded for {self.provider}/{self.model}. Marking as exhausted for day."
                )
                get_rate_limiter().mark_exhausted_for_day(self.provider, self.model)
        except Exception as e:
            logger.error("log_error", message=f"Error handling rate limit: {e}", exc_info=True)

    def _run_async(self, coro):
        import asyncio
        import concurrent.futures

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # Thread sem loop: executa a coro no loop principal do Redis quando disponível
            # para evitar uso de conexões async em event loops diferentes.
            try:
                from app.core.infrastructure.redis_manager import get_redis_manager

                bridge_loop = get_redis_manager().event_loop
            except Exception:
                bridge_loop = None

            if bridge_loop and bridge_loop.is_running():
                return asyncio.run_coroutine_threadsafe(coro, bridge_loop).result()
            return asyncio.run(coro)
        # Loop já está em execução: executa em um thread separado para evitar nested loop.
        def _runner():
            return asyncio.run(coro)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(_runner).result()

    async def asend(self, prompt: str, timeout_s: int | None = None) -> str:
        """Envia um prompt para o LLM de forma assíncrona."""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.send, prompt, timeout_s)

    def send(self, prompt: str, timeout_s: int | None = None) -> str:
        """Envia um prompt para o LLM com resiliência, observabilidade e cache."""
        # 1. Check cache first
        # Extract priority from cache_key or just use a derived one.
        priority_val = "unknown"
        if "_" in self.cache_key:
            priority_val = self.cache_key.split("_", 1)[1]

        cached_entry = response_cache.get(prompt, self.role.value, priority_val)
        if cached_entry:
            logger.info("log_info", message=f"LLM Cache HIT for {self.provider}/{self.model}")
            return cached_entry["response"]

        self._validate_prompt(prompt)

        operation = f"llm_send_{self.provider}"
        base_timeout = timeout_s or self.settings.LLM_DEFAULT_TIMEOUT_SECONDS
        timeout = get_timeout_recommendation(f"llm_{self.provider}", float(base_timeout))

        # Use injected CB or fallback to global provider mapping
        if self.circuit_breaker:
            circuit_breaker = self.circuit_breaker
        else:
            circuit_breaker = _provider_circuit_breakers.get(
                self.provider, _provider_circuit_breakers["unknown"]
            )

        try:
            circuit_breaker.update_params(recovery_timeout=int(max(1, timeout)))
        except Exception as e:
            logger.warning("log_warning", message=f"Failed to update circuit breaker params: {e}")

        # Decorate the adapter-based invoke
        decorated_invoke = resilient(
            max_attempts=self.settings.LLM_RETRY_MAX_ATTEMPTS,
            initial_backoff=self.settings.LLM_RETRY_INITIAL_BACKOFF_SECONDS,
            max_backoff=self.settings.LLM_RETRY_MAX_BACKOFF_SECONDS,
            circuit_breaker=circuit_breaker,
            retry_on=(Exception,),
            operation_name=operation,
        )(self._invoke)

        start = time.perf_counter()
        pricing = _get_model_pricing(self.provider, self.model)

        try:
            LLM_REQUESTS.labels(self.provider, self.model, self.role.value, "attempt", "").inc()

            allowed_out = self._run_async(self._compute_output_limit(prompt))
            if allowed_out < 1:
                logger.warning("log_warning", message=f"Orçamento insuficiente para {self.provider} (tokens={allowed_out}). Acionando fallback."
                )
                raise RuntimeError(f"Orçamento insuficiente ou esgotado para {self.provider}.")

            # Use Adapter for limit application
            self.adapter.apply_output_limit(allowed_out)

            # NOTE: self._invoke is likely wrapping a sync call (langchain invoke).
            # If we want true async, we should use ainvoke if available, or run_in_executor.
            # However, resilient decorator might expect sync? checking...
            # resilient decorator in python is usually sync or async aware.
            # Assuming _invoke is sync (calls adapter.invoke).
            # Ideally we should use adapter.ainvoke if possible.
            # For now, we wrap the resilient decorated call in executor if explicit async needed,
            # BUT resilient decorator usually handles retry logic.
            # If resilient is sync, we must run it in thread pool.

            result = decorated_invoke(prompt)

            elapsed = time.perf_counter() - start
            LLM_LATENCY.labels(self.provider, self.model, self.role.value, "success").observe(
                elapsed
            )
            LLM_REQUESTS.labels(self.provider, self.model, self.role.value, "success", "").inc()

            key = _pool_key(self.provider, self.model)
            for item in _llm_pool.get(key, []):
                if item.instance is self.base:
                    item.consecutive_failures = 0
                    break

            output_text = getattr(result, "content", None) or str(result)

            # Use Sanitizer
            sanitized_text = self.sanitizer.sanitize(output_text)

            # 2. Store in cache & Calc Cost
            try:
                # Tenta extrair uso real da resposta (LangChain standard or provider specific)
                input_tokens = 0
                output_tokens = 0
                cache_read_tokens = 0
                usage_found = False

                # 1. Tenta usage_metadata (LangChain 0.2+)
                def _safe_int(value, default: int = 0) -> int:
                    try:
                        return int(value)
                    except Exception:
                        return default

                usage_meta = getattr(result, "usage_metadata", None)
                if isinstance(usage_meta, dict):
                    input_tokens = _safe_int(usage_meta.get("input_tokens", 0))
                    output_tokens = _safe_int(usage_meta.get("output_tokens", 0))
                    # Verifica detalhes de cache (DeepSeek/OpenAI pattern)
                    # DeepSeek injects directly into openai response object, accessed via response_metadata
                    usage_found = True

                # 2. Se não achou ou quer detalhes extras (cache), olha response_metadata
                resp_meta = getattr(result, "response_metadata", {})
                if not usage_found and isinstance(resp_meta, dict) and "token_usage" in resp_meta:
                    tu = resp_meta["token_usage"] or {}
                    if isinstance(tu, dict):
                        input_tokens = _safe_int(tu.get("prompt_tokens", 0))
                        output_tokens = _safe_int(tu.get("completion_tokens", 0))
                    usage_found = True

                # Tenta extrair cache hits específico do DeepSeek/OpenAI
                # DeepSeek: usage.prompt_tokens_details.cached_tokens
                if isinstance(resp_meta, dict):
                    tu = resp_meta.get("token_usage", {})
                    ptd = tu.get("prompt_tokens_details") if isinstance(tu, dict) else None
                    if isinstance(ptd, dict):
                        cache_read_tokens = _safe_int(ptd.get("cached_tokens", 0))

                # Fallback se não encontrou nada
                if not usage_found:
                    input_tokens = self._estimate_tokens(prompt)
                    output_tokens = self._estimate_tokens(sanitized_text)
                    cache_read_tokens = 0

                # Cálculo de custo (com suporte a cache pricing)
                # Nota: input_tokens geralmente inclui o cached. Pricing aplica ao "miss" e "hit" separadamente.
                # DeepSeek logic: Total Input = Cache Miss + Cache Hit.
                # Cost = (Input - Hit)*PriceIn + Hit*PriceCache + Output*PriceOut

                # Garantir que não subtraímos mais do que o total (sanity check)
                cache_read_tokens = min(cache_read_tokens, input_tokens)
                non_cached_input = input_tokens - cache_read_tokens

                cost = (
                    (non_cached_input / 1000.0) * pricing.input_per_1k_usd
                    + (cache_read_tokens / 1000.0) * pricing.cache_read_per_1k_usd
                    + (output_tokens / 1000.0) * pricing.output_per_1k_usd
                )

                response_cache.put(
                    prompt=prompt,
                    role=self.role.value,
                    priority=priority_val,
                    response=sanitized_text,
                    provider=self.provider,
                    model=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost,
                )

                tokens_in_est = input_tokens
                tokens_out_est = output_tokens
                try:
                    register_usage(self.provider, self.user_id, self.project_id, cost)
                except Exception as e:
                    logger.warning("log_warning", message=f"Failed to register LLM usage cost: {e}")
            except Exception as e:
                logger.warning("log_warning", message=f"Failed to cache LLM response: {e}")

            # 3. Register usage with rate limiter
            try:
                tokens_total = tokens_in_est + tokens_out_est
                get_rate_limiter().register_usage(
                    self.provider, self.model, tokens=tokens_total, requests=1
                )
            except Exception as e:
                logger.debug("log_debug", message=f"Failed to register rate limit usage: {e}")

            return sanitized_text

        except (TimeoutError, CircuitOpenError, FuturesTimeoutError, Exception) as e:
            # Handle Rate Limits
            self._handle_rate_limit_error(e)

            # Update pool failure count
            key = _pool_key(self.provider, self.model)
            for item in _llm_pool.get(key, []):
                if item.instance is self.base:
                    item.consecutive_failures += 1
                    break

            # Record failure metric
            LLM_REQUESTS.labels(
                self.provider, self.model, self.role.value, "failure", type(e).__name__
            ).inc()
            logger.warning("log_warning", message=f"Erro ao enviar prompt para LLM ({type(e).__name__}): {e}")

            # Fallback to Ollama if configured and current provider is not already Ollama
            should_fallback = (
                self.provider != "ollama"
                and not isinstance(e, ValueError)
                and getattr(self.settings, "LLM_FALLBACK_ENABLED", True)
            )

            if should_fallback:
                try:
                    if not _OLLAMA_AVAILABLE or ChatOllama is None:
                        logger.warning(
                            "Fallback Ollama requested but langchain_ollama is not installed."
                        )
                        raise RuntimeError("langchain_ollama is not installed.")

                    logger.info("Tentando fallback para Ollama...")
                    fallback_model = getattr(
                        self.settings,
                        "OLLAMA_ORCHESTRATOR_MODEL",
                        getattr(self.settings, "OLLAMA_MODEL", "llama3"),
                    )

                    # Setup Ollama params reusing factory logic
                    mk: dict[str, Any] = {}
                    if getattr(self.settings, "OLLAMA_NUM_CTX", None):
                        mk["num_ctx"] = self.settings.OLLAMA_NUM_CTX
                    if getattr(self.settings, "OLLAMA_NUM_THREAD", None):
                        mk["num_thread"] = self.settings.OLLAMA_NUM_THREAD
                    if getattr(self.settings, "OLLAMA_NUM_BATCH", None):
                        mk["num_batch"] = self.settings.OLLAMA_NUM_BATCH
                    if getattr(self.settings, "OLLAMA_GPU_LAYERS", None):
                        mk["num_gpu"] = self.settings.OLLAMA_GPU_LAYERS
                    if getattr(self.settings, "OLLAMA_KEEP_ALIVE", None):
                        mk["keep_alive"] = self.settings.OLLAMA_KEEP_ALIVE

                    fallback_llm = ChatOllama(
                        base_url=getattr(self.settings, "OLLAMA_HOST", "http://localhost:11434"),
                        model=fallback_model,
                        temperature=0,
                        model_kwargs=mk,
                    )

                    # Quick health check
                    # _health_check_ollama is sync, run in thread
                    # For simplicity, just run it sync as fallback is rare
                    if _health_check_ollama(fallback_llm, timeout_s=120):
                        logger.info("log_info", message=f"Fallback Ollama ({fallback_model}) saudável. Invocando...")
                        result = fallback_llm.invoke(prompt)

                        # Process success equivalent to main flow
                        output_text = getattr(result, "content", None) or str(result)
                        # Use Sanitizer for fallback too
                        sanitized_text = self.sanitizer.sanitize(output_text)

                        LLM_REQUESTS.labels(
                            "ollama", fallback_model, self.role.value, "fallback_success", ""
                        ).inc()
                        return sanitized_text
                    else:
                        logger.warning("Fallback Ollama falhou no health check.")

                except Exception as fb_err:
                    logger.error("log_error", message=f"Falha crítica no fallback Ollama: {fb_err}")

            # If fallback didn't return, re-raise original exception
            raise
        finally:
            pass

    async def send_enriched(self, prompt: str, timeout_s: int | None = None) -> dict[str, Any]:
        """Versão enriquecida que retorna metadados além da resposta."""
        text = await self.asend(prompt, timeout_s)

        # Tenta recuperar o objeto result original do adapter ou cache se possivel
        # Como send() retorna str, precisamos de uma forma de acessar o objeto completo se quisermos reasoning que não está no texto.
        # PORÉM, LLMClient.send() atualmente engole o objeto result.
        # Refatoração necessária: send() deve persistir metadados temporariamente ou send_enriched deve chamar logica interna.
        # Para evitar reescrever tudo, vamos assumir que o reasoning pode vir no texto (Ollama) ou vamos alterar o send() levemente.
        # Melhor abordagem: O send() já faz o invoke e pega o content.
        # Vamos fazer um "hack" limpo: se o adapter tiver suporte a capturar o ultimo resultado, ou melhor:
        # Vamos alterar o _invoke para retornar o objeto completo e o send() tratar.
        # Mas send() tem decorators de resiliencia.
        #
        # SOLUÇÃO IMEDIATA: Parsing de <think> tags se presente no texto (comum em Ollama/DeepSeek destilado)
        # Parsing de <think> tags se presente no texto (DeepSeek/Ollama)
        import re

        reasoning = None

        # Padrão 1: <think> content </think>
        match = re.search(r"<think>(.*?)</think>", text, re.DOTALL)
        if match:
            reasoning = match.group(1).strip()

        return {
            "response": text,
            "provider": self.provider,
            "model": self.model,
            "role": self.role.value,
            "reasoning": reasoning,
            # Placeholder para usage
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }


async def get_llm_client(
    role: ModelRole = ModelRole.ORCHESTRATOR,
    priority: ModelPriority = ModelPriority.LOCAL_ONLY,
    user_id: str | None = None,
    project_id: str | None = None,
    exclude_providers: list[str] | None = None,
    config: dict[str, Any] | None = None,
) -> LLMClient:
    """Retorna um cliente unificado (LLMClient) a partir do roteador de modelos."""
    cache_key = f"{role.value}_{priority.value}"
    llm = await get_llm(
        role=role,
        priority=priority,
        cache_key=cache_key,
        exclude_providers=exclude_providers,
        config=config,
    )
    provider = _infer_provider(llm)
    model_name = _infer_model_name(llm)
    return LLMClient(
        llm, provider, model_name, role, cache_key, user_id=user_id, project_id=project_id
    )
