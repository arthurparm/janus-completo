from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.core.infrastructure.redis_manager import RedisManager, redis_manager

logger = logging.getLogger(__name__)


def _is_event_loop_runtime_error(error: Exception) -> bool:
    msg = str(error).lower()
    return "different loop" in msg or "event loop is closed" in msg


@dataclass
class RedisUsageTracker:
    manager: RedisManager

    def _today_str(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _provider_key(self, provider: str) -> str:
        return f"usage:llm:provider:{provider}:spend"

    def _tenant_key(self, kind: str, id_: str, date: Optional[str] = None) -> str:
        d = date or self._today_str()
        return f"usage:llm:tenant:{kind}:{id_}:{d}:spend"

    async def get_provider_spend(self, provider: str) -> float:
        try:
            client = self.manager.client
            key = self._provider_key(provider)
            raw = await client.get(key)
            if raw is None:
                return 0.0
            return float(raw)
        except Exception as e:
            logger.error(f"Failed to get provider spend for {provider}: {e}", exc_info=True)
            return 0.0

    async def increment_provider_spend(self, provider: str, cost_usd: float) -> float:
        amount = max(0.0, float(cost_usd))
        if amount == 0.0:
            return await self.get_provider_spend(provider)

        try:
            client = self.manager.client
            key = self._provider_key(provider)
            value = await client.incrbyfloat(key, amount)
            return float(value)
        except Exception as e:
            if _is_event_loop_runtime_error(e):
                logger.warning(
                    "Provider spend increment skipped due to event-loop mismatch",
                    extra={"provider": provider},
                )
                return await self.get_provider_spend(provider)
            logger.error(f"Failed to increment provider spend for {provider}: {e}", exc_info=True)
            return await self.get_provider_spend(provider)

    async def get_tenant_spend(self, kind: str, id_: str, date: Optional[str] = None) -> float:
        if not id_:
            return 0.0
        try:
            client = self.manager.client
            key = self._tenant_key(kind, id_, date)
            raw = await client.get(key)
            if raw is None:
                return 0.0
            return float(raw)
        except Exception as e:
            logger.error(f"Failed to get tenant spend for {kind}:{id_}: {e}", exc_info=True)
            return 0.0

    async def increment_tenant_spend(
        self, kind: str, id_: str, cost_usd: float, date: Optional[str] = None
    ) -> float:
        if not id_:
            return 0.0
        amount = max(0.0, float(cost_usd))
        if amount == 0.0:
            return await self.get_tenant_spend(kind, id_, date)

        try:
            client = self.manager.client
            key = self._tenant_key(kind, id_, date)
            value = await client.incrbyfloat(key, amount)
            if not date:
                await client.expire(key, 60 * 60 * 24 * 45)
            return float(value)
        except Exception as e:
            if _is_event_loop_runtime_error(e):
                logger.warning(
                    "Tenant spend increment skipped due to event-loop mismatch",
                    extra={"kind": kind, "id": id_},
                )
                return await self.get_tenant_spend(kind, id_, date)
            logger.error(f"Failed to increment tenant spend for {kind}:{id_}: {e}", exc_info=True)
            return await self.get_tenant_spend(kind, id_, date)


def get_redis_usage_tracker() -> Optional[RedisUsageTracker]:
    if redis_manager._client:
        return RedisUsageTracker(manager=redis_manager)
    return None
