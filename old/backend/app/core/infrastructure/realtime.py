import time

import structlog

from app.config import settings
from app.core.infrastructure.firebase import get_firebase_service

logger = structlog.get_logger(__name__)


class RealtimeService:
    _instance = None

    def __init__(self):
        self._enabled = getattr(settings, "FIREBASE_ENABLED", False) and getattr(
            settings, "FIREBASE_DATABASE_URL", None
        )
        self._db = None
        if self._enabled:
            try:
                self._db = get_firebase_service().get_database()
            except Exception as e:
                logger.warning("log_warning", message=f"RealtimeService failed to get DB instance: {e}")
                self._enabled = False

    @staticmethod
    def get_instance():
        if RealtimeService._instance is None:
            RealtimeService._instance = RealtimeService()
        return RealtimeService._instance

    def broadcast_status(self, state: str, detail: str = ""):
        if not self._enabled or not self._db:
            return
        try:
            ref = self._db.child("autonomy/status")
            ref.set({"state": state, "detail": detail, "timestamp": int(time.time() * 1000)})
        except Exception as e:
            logger.error("log_error", message=f"Failed to broadcast status: {e}")

    def append_log(self, message: str, level: str = "info"):
        if not self._enabled or not self._db:
            return
        try:
            ref = self._db.child("autonomy/logs")
            # Keep only last 100 logs? RTDB can grow fast.
            # Using push() creates a unique ID
            ref.push({"message": message, "level": level, "timestamp": int(time.time() * 1000)})
        except Exception as e:
            logger.error("log_error", message=f"Failed to append log: {e}")

    def broadcast_metrics(self, cpu: float, memory: float):
        if not self._enabled or not self._db:
            return
        try:
            ref = self._db.child("system/metrics")
            ref.set({"cpu": cpu, "memory": memory, "timestamp": int(time.time() * 1000)})
        except Exception:
            # Metrics fail silently to avoid log spam
            pass


def get_realtime_service() -> RealtimeService:
    return RealtimeService.get_instance()
