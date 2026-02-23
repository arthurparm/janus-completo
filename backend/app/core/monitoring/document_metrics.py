"""
Document metrics recording with graceful degradation.
Centralizes metric recording to eliminate scattered try/except blocks.
"""

import structlog

logger = structlog.get_logger(__name__)

try:
    from prometheus_client import Counter, Histogram

    _METRICS_AVAILABLE = True
except Exception:
    _METRICS_AVAILABLE = False


class DocumentMetricsRecorder:
    """
    Records document ingestion and parsing metrics with graceful degradation.
    Never throws exceptions - all failures are logged.
    """

    def __init__(self):
        if _METRICS_AVAILABLE:
            self._parse_total = Counter(
                "doc_parse_total", "Document parse operations", ["type", "outcome"]
            )
            self._parse_latency = Histogram(
                "doc_parse_latency_seconds", "Parse latency by type", ["type", "outcome"]
            )
            self._ingest_latency = Histogram(
                "doc_ingest_latency_seconds", "Document ingestion latency"
            )
            self._ingest_chunks = Histogram("doc_ingest_chunks_count", "Chunks per ingestion")
            self._ingest_points = Counter("doc_ingest_points_total", "Points indexed", ["outcome"])
            self._ingest_files = Counter("doc_ingest_files_total", "Files ingested", ["status"])
            self._ingest_points_user = Counter(
                "doc_ingest_points_user_total", "Points per user", ["user_id"]
            )
            self._ingest_files_user = Counter(
                "doc_ingest_files_user_total", "Files per user", ["user_id", "status"]
            )
        else:
            # No-op fallbacks
            self._parse_total = None
            self._parse_latency = None
            self._ingest_latency = None
            self._ingest_chunks = None
            self._ingest_points = None
            self._ingest_files = None
            self._ingest_points_user = None
            self._ingest_files_user = None

    def record_parse(self, doc_type: str, outcome: str, latency: float):
        """Record parsing metrics (never throws)."""
        if not _METRICS_AVAILABLE:
            return

        try:
            self._parse_total.labels(doc_type, outcome).inc()
            self._parse_latency.labels(doc_type, outcome).observe(max(0.0, latency))
        except Exception as e:
            logger.debug(
                "metric_recording_failed",
                metric_type="parse",
                doc_type=doc_type,
                error=str(e),
            )

    def record_ingest_latency(self, latency: float):
        """Record ingestion latency (never throws)."""
        if not _METRICS_AVAILABLE:
            return

        try:
            self._ingest_latency.observe(max(0.0, latency))
        except Exception as e:
            logger.debug("metric_recording_failed", metric_type="ingest_latency", error=str(e))

    def record_chunks_count(self, count: int):
        """Record chunk count distribution (never throws)."""
        if not _METRICS_AVAILABLE:
            return

        try:
            self._ingest_chunks.observe(float(count))
        except Exception as e:
            logger.debug("metric_recording_failed", metric_type="chunks_count", error=str(e))

    def record_ingest_success(self, status: str, points_count: int, user_id: str):
        """Record successful ingestion (never throws)."""
        if not _METRICS_AVAILABLE:
            return

        try:
            self._ingest_points.labels("success").inc(points_count)
            self._ingest_files.labels(status).inc()
            self._ingest_points_user.labels(str(user_id)).inc(points_count)
            self._ingest_files_user.labels(str(user_id), status).inc()
        except Exception as e:
            logger.debug(
                "metric_recording_failed",
                metric_type="ingest_success",
                user_id=user_id,
                error=str(e),
            )

    def record_ingest_status(self, status: str, user_id: str):
        """Record ingestion status (empty/quota/etc) (never throws)."""
        if not _METRICS_AVAILABLE:
            return

        try:
            self._ingest_files.labels(status).inc()
            self._ingest_files_user.labels(str(user_id), status).inc()
        except Exception as e:
            logger.debug(
                "metric_recording_failed",
                metric_type="ingest_status",
                status=status,
                error=str(e),
            )


# Global singleton instance
_metrics_recorder = DocumentMetricsRecorder()


def get_metrics_recorder() -> DocumentMetricsRecorder:
    """Get global metrics recorder instance."""
    return _metrics_recorder
