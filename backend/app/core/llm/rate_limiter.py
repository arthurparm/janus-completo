"""
Rate Limit Tracker - Gerencia limites de taxa por modelo LLM.

Permite verificação proativa de disponibilidade antes de selecionar um modelo,
evitando erros 429 e distribuindo carga entre modelos.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuração de limites de taxa para um modelo."""

    tpm: int | None = None  # Tokens Per Minute
    rpm: int | None = None  # Requests Per Minute
    rpd: int | None = None  # Requests Per Day
    tpd: int | None = None  # Tokens Per Day

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
        self._usage: dict[str, dict[str, UsageWindow]] = {}

        # Limites configurados por modelo
        self._limits: dict[str, RateLimitConfig] = {}

        # Último reset diário (timestamp)
        self._last_daily_reset: float = self._start_of_day()

        # Modelos explicitamente marcados como esgotados para o dia (via erro 429 externo)
        self._daily_exhausted: set[str] = set()

        # Tenta carregar do Firebase se habilitado
        if getattr(settings, "FIREBASE_ENABLED", False):
            self.load_limits_from_firebase()

    def _start_of_day(self) -> float:
        """Retorna timestamp do início do dia atual (UTC)."""
        now = datetime.now(UTC)
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

    def configure_limits_bulk(self, limits: dict[str, dict[str, Any]]):
        """Configura limites em lote (ex: do settings)."""
        for key_str, config_dict in limits.items():
            try:
                if ":" in key_str:
                    provider, model = key_str.split(":", 1)
                else:
                    provider = key_str
                    model = "*"

                cfg = RateLimitConfig(
                    tpm=config_dict.get("tpm"),
                    rpm=config_dict.get("rpm"),
                    rpd=config_dict.get("rpd"),
                    tpd=config_dict.get("tpd"),
                )
                self.configure_limits(provider, model, cfg)
            except Exception as e:
                logger.error(f"Erro ao configurar limite para {key_str}: {e}")

    def load_limits_from_firebase(self):
        """Carrega limites do Firebase Realtime Database."""
        if not getattr(settings, "FIREBASE_ENABLED", False):
            return

        try:
            from app.core.infrastructure.firebase import get_firebase_service

            db = get_firebase_service().get_database()
            ref = db.child("config").child("rate_limits")
            remote_limits = ref.get()

            if remote_limits and isinstance(remote_limits, dict):
                logger.info(f"Carregando {len(remote_limits)} configurações de limite do Firebase.")
                self.configure_limits_bulk(remote_limits)
        except Exception as e:
            logger.warning(f"Falha ao carregar limites do Firebase: {e}")

    def save_limit_to_firebase(self, key: str, config: RateLimitConfig):
        """Salva um limite específico no Firebase."""
        if not getattr(settings, "FIREBASE_ENABLED", False):
            return

        try:
            from app.core.infrastructure.firebase import get_firebase_service

            db = get_firebase_service().get_database()
            ref = db.child("config").child("rate_limits").child(key)

            data = {"rpm": config.rpm, "tpm": config.tpm, "rpd": config.rpd, "tpd": config.tpd}
            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}

            ref.set(data)
            logger.debug(f"Limite para {key} salvo no Firebase.")
        except Exception as e:
            logger.error(f"Falha ao salvar limite {key} no Firebase: {e}")

    def update_limits_from_headers(self, provider: str, model: str, headers: dict[str, Any]):
        """
        Atualiza limites e uso baseado em headers de resposta da API (ex: OpenAI).
        Captura 'x-ratelimit-limit-*' e 'x-ratelimit-remaining-*'.
        """
        key = self._get_model_key(provider, model)

        # Normaliza headers para lowercase
        h = {k.lower(): v for k, v in headers.items()}

        limit_req = h.get("x-ratelimit-limit-requests")
        rem_req = h.get("x-ratelimit-remaining-requests")
        limit_tok = h.get("x-ratelimit-limit-tokens")
        rem_tok = h.get("x-ratelimit-remaining-tokens")

        if not any([limit_req, rem_req, limit_tok, rem_tok]):
            return

        with self._lock:
            # Garante existência da config/usage se ainda não houver
            if key not in self._limits:
                self._limits[key] = RateLimitConfig()
            if key not in self._usage:
                self._usage[key] = {
                    "minute": UsageWindow(window_duration_seconds=60.0),
                    "day": UsageWindow(window_duration_seconds=86400.0),
                }

            cfg = self._limits[key]
            minute_window = self._usage[key]["minute"]

            # Atualiza Configuração (Max Limits)
            updated = False
            if limit_req:
                try:
                    val = int(limit_req)
                    if cfg.rpm != val:
                        cfg.rpm = val
                        updated = True
                except Exception as e:
                    logger.debug(f"Failed to parse x-ratelimit-limit-requests: {e}")

            if limit_tok:
                try:
                    val = int(limit_tok)
                    if cfg.tpm != val:
                        cfg.tpm = val
                        updated = True
                except Exception as e:
                    logger.debug(f"Failed to parse x-ratelimit-limit-tokens: {e}")

            # Persiste no Firebase se houve alteração na configuração de limites
            if updated and getattr(settings, "FIREBASE_ENABLED", False):
                self.save_limit_to_firebase(key, cfg)

            # Atualiza Uso (Remaining)
            # Se a API diz que restam X, ajustamos nosso contador interno para (Limit - X)
            # Isso sincroniza nosso estado local com a realidade do servidor
            if rem_req and cfg.rpm:
                try:
                    rem = int(rem_req)
                    used = max(0, cfg.rpm - rem)
                    # Se o reset for curto, assumimos que é janela de minuto
                    minute_window.requests = used
                    # Atualiza timestamp para evitar reset imediato incorreto
                    minute_window.window_start = time.time()
                except Exception as e:
                    logger.debug(f"Failed to parse x-ratelimit-remaining-requests: {e}")

            if rem_tok and cfg.tpm:
                try:
                    rem = int(rem_tok)
                    used = max(0, cfg.tpm - rem)
                    minute_window.tokens = used
                    minute_window.window_start = time.time()
                except Exception as e:
                    logger.debug(f"Failed to parse x-ratelimit-remaining-tokens: {e}")

            # Atualiza Uso (Sincronização com Servidor)
            # Usage = Limit - Remaining
            if limit_req and rem_req:
                try:
                    l_r = int(limit_req)
                    r_r = int(rem_req)
                    if l_r > 0:
                        used_r = max(0, l_r - r_r)
                        # Atualiza janela de minuto
                        minute_window.requests = used_r
                        # Como é uma snapshot do servidor, assumimos que isso reflete o estado atual
                        # Resetamos o window_start para agora para evitar reset imediato
                        minute_window.window_start = time.time()
                except Exception as e:
                    logger.debug(f"Failed to calculate request usage from headers: {e}")

            if limit_tok and rem_tok:
                try:
                    l_t = int(limit_tok)
                    r_t = int(rem_tok)
                    if l_t > 0:
                        used_t = max(0, l_t - r_t)
                        minute_window.tokens = used_t
                        minute_window.window_start = time.time()
                except Exception as e:
                    logger.debug(f"Failed to calculate token usage from headers: {e}")

            logger.debug(
                f"RateLimit atualizado via headers para {key}: RPM={cfg.rpm}, TPM={cfg.tpm}, UsedReq={minute_window.requests}, UsedTok={minute_window.tokens}"
            )

    def _check_daily_reset(self):
        """Reseta contadores diários se passou da meia-noite."""
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
            logger.warning(
                f"Modelo {key} marcado como ESGOTADO para o dia. Será liberado à meia-noite UTC."
            )

    def update_model_limits(
        self,
        provider: str,
        model: str,
        rpm: int | None = None,
        rpd: int | None = None,
        tpm: int | None = None,
        tpd: int | None = None,
    ):
        """Atualiza limites configurados para um modelo manualmente."""
        key = self._get_model_key(provider, model)
        with self._lock:
            if key not in self._limits:
                self._limits[key] = RateLimitConfig()

            cfg = self._limits[key]
            updated = False

            if rpm is not None and cfg.rpm != rpm:
                cfg.rpm = rpm
                updated = True
            if rpd is not None and cfg.rpd != rpd:
                cfg.rpd = rpd
                updated = True
            if tpm is not None and cfg.tpm != tpm:
                cfg.tpm = tpm
                updated = True
            if tpd is not None and cfg.tpd != tpd:
                cfg.tpd = tpd
                updated = True

            if updated:
                logger.info(f"Limites atualizados manualmente para {key}: {cfg}")
                if getattr(settings, "FIREBASE_ENABLED", False):
                    self.save_limit_to_firebase(key, cfg)

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

    def get_availability(self, provider: str, model: str) -> dict[str, Any]:
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
                    "details": {"exhausted": "Marked as exhausted for the day due to quota error"},
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

    def get_all_usage_stats(self) -> dict[str, dict[str, Any]]:
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
_rate_limiter: ModelUsageTracker | None = None
_rate_limiter_lock = threading.Lock()


def get_rate_limiter() -> ModelUsageTracker:
    """Retorna instância singleton do rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        with _rate_limiter_lock:
            if _rate_limiter is None:
                _rate_limiter = ModelUsageTracker()
    return _rate_limiter


def configure_rate_limits_from_settings(
    settings_dict: dict[str, dict[str, Any]], threshold: float = 0.80
):
    """
    Configura rate limits a partir do dicionário de settings.

    Args:
        settings_dict: {"provider:model": {"tpm": int, "rpm": int, "rpd": int, "tpd": int}}
        threshold: Percentual do limite a partir do qual considera indisponível (0.0-1.0)
    """
    limiter = get_rate_limiter()
    limiter.set_threshold(threshold)
    limiter.configure_limits_bulk(settings_dict)
    logger.info(
        f"Rate limits configurados para {len(settings_dict)} modelos (threshold={threshold})"
    )
