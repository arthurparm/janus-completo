import os
import platform
import threading
import time
from datetime import UTC, datetime
from typing import Any

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class SystemStatusService:
    """
    Camada de serviço para obter o status e a saúde geral da aplicação.
    """

    _START_TS = time.time()
    _PID = os.getpid()

    def get_system_status(self) -> dict[str, Any]:
        """
        Coleta e retorna informações de status da aplicação.

        No futuro, pode ser expandido para incluir health checks de dependências.
        """
        logger.info("Coletando status do sistema.")
        now = datetime.now(UTC)
        uptime_s = max(0.0, time.time() - self._START_TS)

        # Info de sistema
        sys_info = {
            "platform": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "architecture": platform.architecture()[0],
            "python_version": platform.python_version(),
        }

        # Info de processo
        proc_info: dict[str, Any] = {
            "pid": self._PID,
            "threads": threading.active_count(),
        }
        # Tenta incluir memória RSS via psutil, se disponível
        try:
            import psutil  # type: ignore

            p = psutil.Process(self._PID)
            rss_mb = float(p.memory_info().rss) / (1024 * 1024)
            proc_info["rss_mb"] = round(rss_mb, 2)
        except Exception as e:
            logger.debug("log_debug", message=f"Failed to get process info: {e}")

        # Métricas de performance (CPU/Memória), se psutil disponível
        perf: dict[str, float | None] = {}
        try:
            import psutil  # type: ignore

            perf["cpu_percent"] = float(psutil.cpu_percent(interval=0.0))
            perf["memory_percent"] = float(psutil.virtual_memory().percent)
        except Exception as e:
            logger.debug("log_debug", message=f"Failed to get system performance metrics: {e}")
            perf["cpu_percent"] = None
            perf["memory_percent"] = None

        # Configs relevantes
        cfg = {
            "identity_name": getattr(settings, "AGENT_IDENTITY_NAME", None) or settings.APP_NAME,
            "identity_enforcement": bool(getattr(settings, "IDENTITY_ENFORCEMENT_ENABLED", False)),
        }
        try:
            providers_cfg = getattr(settings, "LLM_PROVIDERS", {})
            cfg["providers_configured"] = (
                len(providers_cfg) if isinstance(providers_cfg, dict) else 0
            )
        except Exception as e:
            logger.debug("log_debug", message=f"Failed to read providers config: {e}")
            cfg["providers_configured"] = 0

        return {
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "status": "OPERATIONAL",
            "timestamp": now.isoformat(),
            "uptime_seconds": round(uptime_s, 2),
            "system": sys_info,
            "process": proc_info,
            "performance": perf,
            "config": cfg,
        }


# Instância única do serviço
system_status_service = SystemStatusService()
