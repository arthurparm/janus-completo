"""
Rate Limit Tracker - Gerencia limites de taxa por modelo LLM.

Permite verificação proativa de disponibilidade antes de selecionar um modelo,
evitando erros 429 e distribuindo carga entre modelos.
"""
import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuração de limites de taxa para um modelo."""
    tpm: Optional[int] = None  # Tokens Per Minute
    rpm: Optional[int] = None  # Requests Per Minute
    rpd: Optional[int] = None  # Requests Per Day
    tpd: Optional[int] = None  # Tokens Per Day
    
    def has_limits(self) -> bool:
        return any([self.tpm, self.rpm, self.rpd, self.tpd])


@dataclass
class UsageWindow:
    """Janela de uso com reset automático."""
    tokens: int = 0
    requests: int = 0
    window_start: float = field(default_factory=time.time)
    window_duration_seconds: float = 60.0  # 1 minuto por padrão
    
    def reset_if_expired(self) -> bool:
        """Reseta contadores se a janela expirou. Retorna True se resetou."""
        now = time.time()
        if now - self.window_start >= self.window_duration_seconds:
            self.tokens = 0
            self.requests = 0
            self.window_start = now
            return True
        return False
    
    def add_usage(self, tokens: int = 0, requests: int = 1):
        """Adiciona uso à janela."""
        self.reset_if_expired()
        self.tokens += tokens
        self.requests += requests


class ModelUsageTracker:
    """
    Rastreia uso de tokens e requests por modelo com múltiplas janelas.
    
    Suporta:
    - Janela por minuto (TPM/RPM)
    - Janela por dia (TPD/RPD)
    - Threshold de alerta (ex: 80%)
    """
    
    def __init__(self, threshold: float = 0.80):
        self._threshold = threshold  # Limite para considerar "chegando no limite"
        self._lock = threading.RLock()
        
        # Contadores por modelo: {provider:model -> {minute: UsageWindow, day: UsageWindow}}
        self._usage: Dict[str, Dict[str, UsageWindow]] = {}
        
        # Limites configurados por modelo
        self._limits: Dict[str, RateLimitConfig] = {}
        
        # Último reset diário (timestamp)
        self._last_daily_reset: float = self._start_of_day()
        
        # Modelos explicitamente marcados como esgotados para o dia (via erro 429 externo)
        self._daily_exhausted: set[str] = set()
    
    def _start_of_day(self) -> float:
        """Retorna timestamp do início do dia atual (UTC)."""
        now = datetime.now(timezone.utc)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start.timestamp()
    
    def _get_model_key(self, provider: str, model: str) -> str:
        return f"{provider}:{model}"
    
    def configure_limits(self, provider: str, model: str, config: RateLimitConfig):
        """Configura limites para um modelo específico."""
        key = self._get_model_key(provider, model)
        with self._lock:
            self._limits[key] = config
            if key not in self._usage:
                self._usage[key] = {
                    "minute": UsageWindow(window_duration_seconds=60.0),
                    "day": UsageWindow(window_duration_seconds=86400.0),
                }
    
    def configure_limits_bulk(self, limits: Dict[str, Dict[str, Any]]):
        """Configura limites em lote a partir de um dicionário."""
        for model_spec, limit_dict in limits.items():
            try:
                if ":" in model_spec:
                    provider, model = model_spec.split(":", 1)
                else:
                    # Assume OpenAI se não especificado
                    provider, model = "openai", model_spec
                
                config = RateLimitConfig(
                    tpm=limit_dict.get("tpm"),
                    rpm=limit_dict.get("rpm"),
                    rpd=limit_dict.get("rpd"),
                    tpd=limit_dict.get("tpd"),
                )
                self.configure_limits(provider.strip(), model.strip(), config)
            except Exception as e:
                logger.warning(f"Erro ao configurar limite para '{model_spec}': {e}")
    
    def _check_daily_reset(self):
        """Reseta contadores diários se passou da meia-noite."""
        now = time.time()
        start_of_today = self._start_of_day()
        if start_of_today > self._last_daily_reset:
            # Novo dia - resetar contadores diários
            for model_key in self._usage:
                if "day" in self._usage[model_key]:
                    self._usage[model_key]["day"].tokens = 0
                    self._usage[model_key]["day"].requests = 0
                    self._usage[model_key]["day"].window_start = start_of_today
            # Limpar modelos marcados como esgotados (novo dia = nova chance)
            self._daily_exhausted.clear()
            self._last_daily_reset = start_of_today
            logger.info("Contadores diários de rate limit resetados. Modelos esgotados liberados.")
    
    def mark_exhausted_for_day(self, provider: str, model: str):
        """
        Marca um modelo como esgotado (cota diária atingida) até a meia-noite.
        
        Use quando receber um erro 429 com 'quota exceeded' ou 'FreeTier' na mensagem.
        Isso evita que o sistema fique tentando o modelo repetidamente.
        """
        key = self._get_model_key(provider, model)
        with self._lock:
            self._daily_exhausted.add(key)
            logger.warning(f"Modelo {key} marcado como ESGOTADO para o dia. Será liberado à meia-noite UTC.")
    
    def register_usage(self, provider: str, model: str, tokens: int = 0, requests: int = 1):
        """Registra uso de tokens/requests para um modelo."""
        key = self._get_model_key(provider, model)
        with self._lock:
            self._check_daily_reset()
            
            if key not in self._usage:
                self._usage[key] = {
                    "minute": UsageWindow(window_duration_seconds=60.0),
                    "day": UsageWindow(window_duration_seconds=86400.0),
                }
            
            # Atualiza janela por minuto
            self._usage[key]["minute"].reset_if_expired()
            self._usage[key]["minute"].add_usage(tokens, requests)
            
            # Atualiza janela diária
            self._usage[key]["day"].add_usage(tokens, requests)
    
    def get_availability(self, provider: str, model: str) -> Dict[str, Any]:
        """
        Retorna disponibilidade do modelo com base nos limites e uso atual.
        
        Returns:
            {
                "available": bool,  # True se está disponível para uso
                "usage_percent": float,  # Maior percentual de uso entre os limites
                "details": {...}  # Detalhes por tipo de limite
            }
        """
        key = self._get_model_key(provider, model)
        with self._lock:
            self._check_daily_reset()
            
            # Verifica se foi explicitamente marcado como esgotado (por erro 429 externo)
            if key in self._daily_exhausted:
                return {
                    "available": False, 
                    "usage_percent": 1.0, 
                    "details": {"exhausted": "Marked as exhausted for the day due to quota error"}
                }
            
            limits = self._limits.get(key)
            if not limits or not limits.has_limits():
                # Sem limites configurados = sempre disponível
                return {"available": True, "usage_percent": 0.0, "details": {}}
            
            usage = self._usage.get(key)
            if not usage:
                return {"available": True, "usage_percent": 0.0, "details": {}}
            
            # Atualiza janela por minuto
            usage["minute"].reset_if_expired()
            
            details = {}
            max_percent = 0.0
            
            # Verificar TPM
            if limits.tpm and limits.tpm > 0:
                current = usage["minute"].tokens
                percent = current / limits.tpm
                details["tpm"] = {"current": current, "limit": limits.tpm, "percent": percent}
                max_percent = max(max_percent, percent)
            
            # Verificar RPM
            if limits.rpm and limits.rpm > 0:
                current = usage["minute"].requests
                percent = current / limits.rpm
                details["rpm"] = {"current": current, "limit": limits.rpm, "percent": percent}
                max_percent = max(max_percent, percent)
            
            # Verificar TPD
            if limits.tpd and limits.tpd > 0:
                current = usage["day"].tokens
                percent = current / limits.tpd
                details["tpd"] = {"current": current, "limit": limits.tpd, "percent": percent}
                max_percent = max(max_percent, percent)
            
            # Verificar RPD
            if limits.rpd and limits.rpd > 0:
                current = usage["day"].requests
                percent = current / limits.rpd
                details["rpd"] = {"current": current, "limit": limits.rpd, "percent": percent}
                max_percent = max(max_percent, percent)
            
            # Disponível se abaixo do threshold
            available = max_percent < self._threshold
            
            return {
                "available": available,
                "usage_percent": max_percent,
                "details": details,
            }
    
    def is_available(self, provider: str, model: str) -> bool:
        """Verifica rapidamente se um modelo está disponível."""
        return self.get_availability(provider, model)["available"]
    
    def get_all_usage_stats(self) -> Dict[str, Dict[str, Any]]:
        """Retorna estatísticas de uso de todos os modelos."""
        with self._lock:
            self._check_daily_reset()
            stats = {}
            for key in self._limits:
                provider, model = key.split(":", 1) if ":" in key else ("unknown", key)
                stats[key] = self.get_availability(provider, model)
            return stats
    
    def set_threshold(self, threshold: float):
        """Atualiza o threshold de disponibilidade (0.0 a 1.0)."""
        self._threshold = max(0.0, min(1.0, threshold))


# Instância global singleton
_rate_limiter: Optional[ModelUsageTracker] = None
_rate_limiter_lock = threading.Lock()


def get_rate_limiter() -> ModelUsageTracker:
    """Retorna instância singleton do rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        with _rate_limiter_lock:
            if _rate_limiter is None:
                _rate_limiter = ModelUsageTracker()
    return _rate_limiter


def configure_rate_limits_from_settings(settings_dict: Dict[str, Dict[str, Any]], threshold: float = 0.80):
    """
    Configura rate limits a partir do dicionário de settings.
    
    Args:
        settings_dict: {"provider:model": {"tpm": int, "rpm": int, "rpd": int, "tpd": int}}
        threshold: Percentual do limite a partir do qual considera indisponível (0.0-1.0)
    """
    limiter = get_rate_limiter()
    limiter.set_threshold(threshold)
    limiter.configure_limits_bulk(settings_dict)
    logger.info(f"Rate limits configurados para {len(settings_dict)} modelos (threshold={threshold})")
