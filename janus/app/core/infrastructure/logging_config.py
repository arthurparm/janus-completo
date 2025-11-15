import contextvars
import logging
import random
import sys
from typing import Any, Dict, Optional

import structlog
from app.config import settings

try:
    # Optional OpenTelemetry correlation
    from opentelemetry import trace  # type: ignore

    _OTEL = True
except Exception:  # pragma: no cover
    _OTEL = False

# Correlation: trace_id for all logs via contextvar
TRACE_ID: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")
USER_ID: contextvars.ContextVar[str] = contextvars.ContextVar("user_id", default="-")


class _SamplingProcessor:
    """Drop noisy logs probabilistically. sampling in [0,1]."""

    def __init__(self, sampling: float = 1.0):
        self.sampling = max(0.0, min(1.0, sampling))

    def __call__(self, logger: Any, method_name: str, event_dict: Dict[str, Any]):
        if self.sampling >= 1.0:
            return event_dict
        # Always keep warnings and above
        level = event_dict.get("level", "info").lower()
        if level in ("warning", "error", "critical"):
            return event_dict
        if random.random() <= self.sampling:
            return event_dict
        raise structlog.DropEvent


def _add_trace_correlation(_, __, event_dict: Dict[str, Any]):
    event_dict["trace_id"] = TRACE_ID.get()
    event_dict["user_id"] = USER_ID.get()
    if _OTEL:
        try:
            span = trace.get_current_span()
            span_ctx = span.get_span_context()
            if span_ctx and span_ctx.is_valid:
                event_dict["otel_trace_id"] = format(span_ctx.trace_id, "032x")
                event_dict["otel_span_id"] = format(span_ctx.span_id, "016x")
        except Exception:
            pass
    return event_dict


_SENSITIVE_KEYS = ("api_key", "apikey", "password", "secret", "token", "authorization")


def _redact_secrets(_, __, event_dict: Dict[str, Any]):
    def _mask(value: Any) -> Any:
        s = str(value)
        if len(s) <= 8:
            return "***"
        return s[:2] + "***" + s[-2:]

    for k in list(event_dict.keys()):
        lk = str(k).lower()
        if any(sk in lk for sk in _SENSITIVE_KEYS):
            event_dict[k] = _mask(event_dict[k])
    return event_dict


class _LevelFilter(logging.Filter):
    """Optional per-module level overrides."""

    def __init__(self, module_levels: Optional[Dict[str, int]] = None):
        super().__init__()
        self.module_levels = module_levels or {}

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - simple pass-through
        lvl = self.module_levels.get(record.name)
        if lvl is not None and record.levelno < lvl:
            return False
        return True


def setup_logging(level: int = logging.INFO, module_levels: Optional[Dict[str, int]] = None, sampling: float = 1.0):
    """Configure structlog to emit JSON with correlation and safety.

    Args:
        level: Root logging level.
        module_levels: Optional per-module level overrides.
        sampling: Probability [0..1] to keep info/debug logs (warnings+ are always kept).
    """
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.addFilter(_LevelFilter(module_levels))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    sampling_value = float(getattr(settings, "LOG_SAMPLING_RATE", sampling))
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        _add_trace_correlation,
        _redact_secrets,
        _SamplingProcessor(sampling_value),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def setup_tracing(app=None):
    try:
        if not getattr(settings, "OTEL_ENABLED", False):
            return
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry import trace
        service_name = getattr(settings, "OTEL_SERVICE_NAME", settings.APP_NAME)
        endpoint = getattr(settings, "OTEL_OTLP_ENDPOINT", None)
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        if endpoint:
            exporter = OTLPSpanExporter(endpoint=endpoint)
            processor = BatchSpanProcessor(exporter)
            provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        if app is not None:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            FastAPIInstrumentor.instrument_app(app)
    except Exception:
        pass
