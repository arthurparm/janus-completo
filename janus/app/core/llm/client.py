import time
from typing import Optional, Any, Dict
from concurrent.futures import TimeoutError as FuturesTimeoutError
import logging

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from prometheus_client import Counter, Histogram

from app.config import settings
from app.core.infrastructure.resilience import resilient, CircuitOpenError, CircuitBreaker
from app.core.monitoring.health_monitor import get_timeout_recommendation
from .types import ModelRole, ModelPriority
from .pricing import (
    _get_model_pricing, _budget_remaining, _tenant_budget_remaining, 
)
from .resilience import (
    _pool_key, _llm_pool, _provider_circuit_breakers
)
from .factory import _get_executor, _infer_provider, _infer_model_name, _health_check_ollama
from .router import get_llm
from .rate_limiter import get_rate_limiter
from . import response_cache  # Import cache module

# New Modules
from .adapters import get_adapter
from .sanitizer import ContentSanitizer

logger = logging.getLogger(__name__)

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

    def __init__(self, base: BaseChatModel, provider: str, model: str, role: ModelRole, cache_key: str,
                 user_id: Optional[str] = None, project_id: Optional[str] = None,
                 circuit_breaker: Optional[CircuitBreaker] = None, config: Any = None):
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
            raise ValueError(f"Prompt excede o tamanho máximo de {self.settings.LLM_MAX_PROMPT_LENGTH} caracteres.")

    def _invoke(self, prompt: str) -> Any:
        return self.adapter.invoke(prompt)

    def _compute_output_limit(self, prompt: str) -> int:
        pricing = _get_model_pricing(self.provider, self.model)
        tokens_in = self._estimate_tokens(prompt)
        role_key = self.role.value
        max_req_cost = float(getattr(self.settings, "LLM_MAX_COST_PER_REQUEST_USD", {}).get(role_key, float("inf")))
        cap = int(getattr(self.settings, "LLM_MAX_GENERATION_TOKENS_CAP", 0) or 0)
        min_tokens = int(getattr(self.settings, "LLM_MIN_GENERATION_TOKENS", 0) or 0)

        input_cost_usd = (tokens_in / 1000.0) * pricing.input_per_1k_usd
        remaining_req_usd = max(0.0, (max_req_cost - input_cost_usd)) if max_req_cost < float("inf") else float("inf")
        remaining_provider_usd = _budget_remaining(self.provider)
        remaining_user_usd = _tenant_budget_remaining("user", self.user_id)
        remaining_project_usd = _tenant_budget_remaining("project", self.project_id)

        def usd_to_out_tokens(usd: float) -> int:
            if usd == float("inf"):
                return 10 ** 9
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
                logger.warning(f"Quota Exceeded for {self.provider}/{self.model}. Marking as exhausted for day.")
                get_rate_limiter().mark_exhausted_for_day(self.provider, self.model)
        except Exception as e:
            logger.error(f"Error handling rate limit: {e}", exc_info=True)

    async def asend(self, prompt: str, timeout_s: Optional[int] = None) -> str:
        """Envia um prompt para o LLM de forma assíncrona."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.send, prompt, timeout_s)

    def send(self, prompt: str, timeout_s: Optional[int] = None) -> str:
        """Envia um prompt para o LLM com resiliência, observabilidade e cache."""
        # 1. Check cache first
        # Extract priority from cache_key or just use a derived one.
        priority_val = "unknown"
        if "_" in self.cache_key:
             priority_val = self.cache_key.split("_", 1)[1]
             
        cached_entry = response_cache.get(prompt, self.role.value, priority_val)
        if cached_entry:
            logger.info(f"LLM Cache HIT for {self.provider}/{self.model}")
            return cached_entry["response"]

        self._validate_prompt(prompt)

        operation = f"llm_send_{self.provider}"
        base_timeout = timeout_s or self.settings.LLM_DEFAULT_TIMEOUT_SECONDS
        timeout = get_timeout_recommendation(f"llm_{self.provider}", float(base_timeout))
        
        # Use injected CB or fallback to global provider mapping
        if self.circuit_breaker:
            circuit_breaker = self.circuit_breaker
        else:
            circuit_breaker = _provider_circuit_breakers.get(self.provider, _provider_circuit_breakers["unknown"])
            
        try:
            circuit_breaker.update_params(recovery_timeout=int(max(1, timeout)))
        except Exception as e:
            logger.warning(f"Failed to update circuit breaker params: {e}")

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

            allowed_out = self._compute_output_limit(prompt)
            if allowed_out < 1:
                logger.warning(f"Orçamento insuficiente para {self.provider} (tokens={allowed_out}). Acionando fallback.")
                raise RuntimeError(f"Orçamento insuficiente ou esgotado para {self.provider}.")

            # Use Adapter for limit application
            self.adapter.apply_output_limit(allowed_out)
            
            if timeout > 0:
                future = _get_executor(self.provider).submit(decorated_invoke, prompt)
                result = future.result(timeout=timeout)
            else:
                result = decorated_invoke(prompt)

            elapsed = time.perf_counter() - start
            LLM_LATENCY.labels(self.provider, self.model, self.role.value, "success").observe(elapsed)
            LLM_REQUESTS.labels(self.provider, self.model, self.role.value, "success", "").inc()

            key = _pool_key(self.provider, self.model)
            for item in _llm_pool.get(key, []):
                if item.instance is self.base:
                    item.consecutive_failures = 0
                    break

            output_text = getattr(result, "content", None) or str(result)
            
            # Use Sanitizer
            sanitized_text = self.sanitizer.sanitize(output_text)
            
            # 2. Store in cache
            try:
                tokens_in_est = self._estimate_tokens(prompt)
                tokens_out_est = self._estimate_tokens(sanitized_text)
                cost = (tokens_in_est / 1000.0) * pricing.input_per_1k_usd + (tokens_out_est / 1000.0) * pricing.output_per_1k_usd
                
                response_cache.put(
                    prompt=prompt,
                    role=self.role.value,
                    priority=priority_val,
                    response=sanitized_text,
                    provider=self.provider,
                    model=self.model,
                    input_tokens=tokens_in_est,
                    output_tokens=tokens_out_est,
                    cost_usd=cost
                )
            except Exception as e:
                logger.warning(f"Failed to cache LLM response: {e}")

            # 3. Register usage with rate limiter
            try:
                tokens_total = tokens_in_est + tokens_out_est
                get_rate_limiter().register_usage(self.provider, self.model, tokens=tokens_total, requests=1)
            except Exception as e:
                logger.debug(f"Failed to register rate limit usage: {e}")

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
            LLM_REQUESTS.labels(self.provider, self.model, self.role.value, "failure", type(e).__name__).inc()
            logger.warning(f"Erro ao enviar prompt para LLM ({type(e).__name__}): {e}")

            # Fallback to Ollama if configured and current provider is not already Ollama
            should_fallback = (
                self.provider != "ollama" 
                and not isinstance(e, ValueError)
                and getattr(self.settings, "LLM_FALLBACK_ENABLED", True)
            )
            
            if should_fallback:
                try:
                    logger.info("Tentando fallback para Ollama...")
                    fallback_model = getattr(self.settings, "OLLAMA_ORCHESTRATOR_MODEL", 
                                             getattr(self.settings, "OLLAMA_MODEL", "llama3"))
                    
                    # Setup Ollama params reusing factory logic
                    mk: Dict[str, Any] = {}
                    if getattr(self.settings, "OLLAMA_NUM_CTX", None): mk["num_ctx"] = self.settings.OLLAMA_NUM_CTX
                    if getattr(self.settings, "OLLAMA_NUM_THREAD", None): mk["num_thread"] = self.settings.OLLAMA_NUM_THREAD
                    if getattr(self.settings, "OLLAMA_KEEP_ALIVE", None): mk["keep_alive"] = self.settings.OLLAMA_KEEP_ALIVE
                    
                    fallback_llm = ChatOllama(
                        base_url=getattr(self.settings, "OLLAMA_HOST", "http://localhost:11434"),
                        model=fallback_model,
                        temperature=0,
                        model_kwargs=mk
                    )
                    
                    # Quick health check
                    if _health_check_ollama(fallback_llm, timeout_s=120):
                        logger.info(f"Fallback Ollama ({fallback_model}) saudável. Invocando...")
                        result = fallback_llm.invoke(prompt)
                        
                        # Process success equivalent to main flow
                        output_text = getattr(result, "content", None) or str(result)
                        # Use Sanitizer for fallback too
                        sanitized_text = self.sanitizer.sanitize(output_text)
                        
                        LLM_REQUESTS.labels("ollama", fallback_model, self.role.value, "fallback_success", "").inc()
                        return sanitized_text
                    else:
                        logger.warning("Fallback Ollama falhou no health check.")
                
                except Exception as fb_err:
                    logger.error(f"Falha crítica no fallback Ollama: {fb_err}")
            
            # If fallback didn't return, re-raise original exception
            raise
        finally:
            pass

    def send_enriched(self, prompt: str, timeout_s: Optional[int] = None) -> Dict[str, Any]:
        """Versão enriquecida que retorna metadados além da resposta."""
        text = self.send(prompt, timeout_s)
        return {
            "response": text,
            "provider": self.provider,
            "model": self.model,
            "role": self.role.value,
            # Placeholder para usage, já que send() não retorna
            "usage": {"input_tokens": 0, "output_tokens": 0}
        }
            
def get_llm_client(
        role: ModelRole = ModelRole.ORCHESTRATOR,
        priority: ModelPriority = ModelPriority.LOCAL_ONLY,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        exclude_providers: Optional[list[str]] = None,
) -> LLMClient:
    """Retorna um cliente unificado, mantendo compatibilidade com get_llm()."""
    cache_key = f"{role.value}_{priority.value}"
    llm = get_llm(role=role, priority=priority, cache_key=cache_key, exclude_providers=exclude_providers)
    provider = _infer_provider(llm)
    model_name = _infer_model_name(llm)
    return LLMClient(llm, provider, model_name, role, cache_key, user_id=user_id, project_id=project_id)
