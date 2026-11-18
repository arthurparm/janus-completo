import asyncio
import time
from typing import Any

import structlog
from app.repositories.observability_repository import record_audit_event_direct

logger = structlog.get_logger(__name__)

try:
    from prometheus_client import Counter
    AUTONOMY_WATCHDOG_CHECKS = Counter(
        "autonomy_watchdog_checks_total",
        "Total autonomy watchdog checks executed"
    )
    AUTONOMY_WATCHDOG_RECOVERIES = Counter(
        "autonomy_watchdog_recoveries_total",
        "Total autonomy watchdog recovery actions performed",
        ["action"]
    )
except ImportError:
    AUTONOMY_WATCHDOG_CHECKS = None
    AUTONOMY_WATCHDOG_RECOVERIES = None


class AutonomyWatchdog:
    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None
        self._autonomy_service: Any = None
        self._domain_cb: Any = None
        self._lock_service: Any = None
        self._cost_tracker: Any = None

    def configure(
        self,
        autonomy_service=None,
        domain_cb=None,
        lock_service=None,
        cost_tracker=None,
    ) -> None:
        self._autonomy_service = autonomy_service
        self._domain_cb = domain_cb
        self._lock_service = lock_service
        self._cost_tracker = cost_tracker

    async def start(self, interval: int = 60) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(interval))
        logger.info("autonomy_watchdog_started", interval=interval)

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("autonomy_watchdog_stopped")

    async def _loop(self, interval: int) -> None:
        while self._running:
            try:
                await self._check()
            except Exception as exc:
                logger.error("autonomy_watchdog_error", error=str(exc))
            await asyncio.sleep(interval)

    async def _check(self) -> None:
        if AUTONOMY_WATCHDOG_CHECKS is not None:
            AUTONOMY_WATCHDOG_CHECKS.inc()

        # 1. Circuit breaker check
        if self._domain_cb is not None:
            health = self._domain_cb.get_domain_health()
            for domain, state in health.items():
                if state.get("is_open") and state.get("open_since", 0) > 0:
                    duration = time.time() - state["open_since"]
                    if duration > 300:
                        logger.warning("watchdog_force_close_cb", domain=domain, duration_sec=duration)
                        self._domain_cb.record_success(domain)
                        record_audit_event_direct(
                            endpoint="autonomy_watchdog",
                            action="watchdog_forced_cb_close",
                            status="success",
                            details_json={"domain": domain, "duration_sec": int(duration)},
                        )
                        if AUTONOMY_WATCHDOG_RECOVERIES is not None:
                            AUTONOMY_WATCHDOG_RECOVERIES.labels(action="force_close_cb").inc()

        # 2. Budget check
        if self._cost_tracker is not None:
            if self._cost_tracker.budget_exhausted():
                logger.warning("watchdog_budget_exhausted")
            elif self._cost_tracker.budget_warning():
                logger.warning("watchdog_budget_warning", remaining=self._cost_tracker.budget_remaining())

        # 3. Loop active check
        if self._autonomy_service is not None:
            status = {}
            try:
                status_method = getattr(self._autonomy_service, 'get_status', None)
                if status_method:
                    status = status_method()
                last_cycle = status.get("last_cycle_at")
                active = status.get("active", False)
                if active and last_cycle:
                    elapsed = time.time() - float(last_cycle)
                    if elapsed > 600 and getattr(self._autonomy_service, '_config', None) is not None:
                        config = self._autonomy_service._config
                        auto_restart = getattr(config, 'auto_restart', False) if config else False
                        if auto_restart:
                            logger.warning("watchdog_auto_restart", idle_seconds=int(elapsed))
                            restart_method = getattr(self._autonomy_service, 'restart', None)
                            if restart_method:
                                await restart_method()
                                record_audit_event_direct(
                                    endpoint="autonomy_watchdog",
                                    action="watchdog_auto_restart",
                                    status="success",
                                    details_json={"idle_seconds": int(elapsed)},
                                )
                                if AUTONOMY_WATCHDOG_RECOVERIES is not None:
                                    AUTONOMY_WATCHDOG_RECOVERIES.labels(action="auto_restart").inc()
            except Exception as exc:
                logger.error("watchdog_loop_check_error", error=str(exc))

        # 4. Lease check
        if self._lock_service is not None:
            pass

        record_audit_event_direct(
            endpoint="autonomy_watchdog",
            action="watchdog_check_completed",
            status="success",
            details_json={},
        )


autonomy_watchdog = AutonomyWatchdog()
