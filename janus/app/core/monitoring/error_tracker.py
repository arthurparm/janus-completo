import threading
import time
from collections import deque
from datetime import datetime


class GlobalErrorTracker:
    """
    Rastreador global de erros e exceções do sistema.
    Thread-safe e projetado para ser chamado de loggers ou blocos except.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._error_counts = 0
        self._recent_errors = deque(maxlen=20)
        self._start_time = time.time()
        self._last_error_time = 0.0

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = GlobalErrorTracker()
        return cls._instance

    def record_error(self, error_msg: str, source: str = "unknown"):
        """Registra um erro ocorrido."""
        now = time.time()
        with self._lock:
            self._error_counts += 1
            self._last_error_time = now
            self._recent_errors.append(
                {
                    "timestamp": datetime.fromtimestamp(now).isoformat(),
                    "message": str(error_msg)[:500],
                    "source": source,
                }
            )

    def get_stats(self) -> dict:
        """Retorna estatísticas atuais."""
        with self._lock:
            return {
                "total_errors": self._error_counts,
                "recent_errors": list(self._recent_errors),
                "last_error_seconds_ago": (
                    time.time() - self._last_error_time if self._last_error_time > 0 else -1
                ),
                "errors_per_hour": self._error_counts
                / (max(1, time.time() - self._start_time) / 3600),
            }


def track_exception(e: Exception, source: str = "unknown"):
    """Helper para registrar exceção facilmente."""
    GlobalErrorTracker.get_instance().record_error(str(e), source)
