from __future__ import annotations
import structlog
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.core.infrastructure.redis_manager import RedisManager, redis_manager

logger = structlog.get_logger(__name__)


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

    def _objective_key(self, objective_id: str, date: Optional[str] = None) -> str:
        d = date or self._today_str()
        return f"usage:llm:objective:{objective_id}:{d}:spend"

    def _sliding_window_key(self, kind: str, tool_name: str, id_: str) -> str:
        return f"usage:tool:{tool_name}:{kind}:{id_}:window"

    async def get_provider_spend(self, provider: str) -> float:
        try:
            client = self.manager.client
            key = self._provider_key(provider)
            raw = await client.get(key)
            if raw is None:
                return 0.0
            return float(raw)
        except Exception as e:
            if _is_event_loop_runtime_error(e):
                logger.warning(
                    "Provider spend read skipped due to event-loop mismatch",
                    extra={"provider": provider},
                )
            else:
                logger.error("log_error", message=f"Failed to get provider spend for {provider}: {e}", exc_info=True)
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
            logger.error("log_error", message=f"Failed to increment provider spend for {provider}: {e}", exc_info=True)
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
            if _is_event_loop_runtime_error(e):
                logger.warning(
                    "Tenant spend read skipped due to event-loop mismatch",
                    extra={"kind": kind, "id": id_},
                )
            else:
                logger.error("log_error", message=f"Failed to get tenant spend for {kind}:{id_}: {e}", exc_info=True)
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
            logger.error("log_error", message=f"Failed to increment tenant spend for {kind}:{id_}: {e}", exc_info=True)
            return await self.get_tenant_spend(kind, id_, date)

    async def get_objective_spend(self, objective_id: str, date: Optional[str] = None) -> float:
        if not objective_id:
            return 0.0
        try:
            client = self.manager.client
            key = self._objective_key(objective_id, date)
            raw = await client.get(key)
            if raw is None:
                return 0.0
            return float(raw)
        except Exception as e:
            if _is_event_loop_runtime_error(e):
                logger.warning(
                    "Objective spend read skipped due to event-loop mismatch",
                    extra={"objective_id": objective_id},
                )
            else:
                logger.error(
                    "log_error",
                    message=f"Failed to get objective spend for {objective_id}: {e}",
                    exc_info=True,
                )
            return 0.0

    async def increment_objective_spend(
        self, objective_id: str, cost_usd: float, date: Optional[str] = None
    ) -> float:
        if not objective_id:
            return 0.0
        amount = max(0.0, float(cost_usd))
        if amount == 0.0:
            return await self.get_objective_spend(objective_id, date)
        try:
            client = self.manager.client
            key = self._objective_key(objective_id, date)
            value = await client.incrbyfloat(key, amount)
            if not date:
                await client.expire(key, 60 * 60 * 24 * 45)
            return float(value)
        except Exception as e:
            if _is_event_loop_runtime_error(e):
                logger.warning(
                    "Objective spend increment skipped due to event-loop mismatch",
                    extra={"objective_id": objective_id},
                )
                return await self.get_objective_spend(objective_id, date)
            logger.error(
                "log_error",
                message=f"Failed to increment objective spend for {objective_id}: {e}",
                exc_info=True,
            )
            return await self.get_objective_spend(objective_id, date)

    async def sliding_window_check_and_increment(
        self,
        *,
        kind: str,
        tool_name: str,
        id_: str,
        limit: int,
        window_seconds: int,
        now_ts: Optional[float] = None,
    ) -> tuple[bool, int, int, int]:
        if not id_ or limit <= 0 or window_seconds <= 0:
            return True, 0, limit, window_seconds
        now = float(now_ts or datetime.now(timezone.utc).timestamp())
        window_start = now - float(window_seconds)
        member = f"{now:.6f}"
        try:
            client = self.manager.client
            key = self._sliding_window_key(kind, tool_name, id_)
            pipe = client.pipeline()
            await pipe.zremrangebyscore(key, "-inf", window_start)
            await pipe.zcard(key)
            _, current_count = await pipe.execute()
            current_count = int(current_count or 0)
            if current_count >= limit:
                await client.expire(key, max(window_seconds * 2, 60))
                return False, current_count, limit, window_seconds

            pipe = client.pipeline()
            await pipe.zadd(key, {member: now})
            await pipe.expire(key, max(window_seconds * 2, 60))
            await pipe.zcard(key)
            _, _, updated_count = await pipe.execute()
            return True, int(updated_count or (current_count + 1)), limit, window_seconds
        except Exception as e:
            if _is_event_loop_runtime_error(e):
                logger.warning(
                    "Sliding window quota skipped due to event-loop mismatch",
                    extra={"kind": kind, "tool_name": tool_name, "id": id_},
                )
            else:
                logger.error(
                    "log_error",
                    message=(
                        f"Failed to check sliding window quota for "
                        f"{kind}:{tool_name}:{id_}: {e}"
                    ),
                    exc_info=True,
                )
            return True, 0, limit, window_seconds


def get_redis_usage_tracker() -> Optional[RedisUsageTracker]:
    if redis_manager._client:
        return RedisUsageTracker(manager=redis_manager)
    return None
