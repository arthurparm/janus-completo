import contextvars
import logging
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
from typing import Any

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
SESSION_ID: contextvars.ContextVar[str] = contextvars.ContextVar("session_id", default="-")
CONVERSATION_ID: contextvars.ContextVar[str] = contextvars.ContextVar(
    "conversation_id", default="-"
)
PROJECT_ID: contextvars.ContextVar[str] = contextvars.ContextVar("project_id", default="-")


class _SamplingProcessor:
    """Drop noisy logs probabilistically. sampling in [0,1]."""

    def __init__(self, sampling: float = 1.0):
        self.sampling = max(0.0, min(1.0, sampling))

    def __call__(self, logger: Any, method_name: str, event_dict: dict[str, Any]):
        if self.sampling >= 1.0:
            return event_dict
        # Always keep warnings and above
        level = event_dict.get("level", "info").lower()
        if level in ("warning", "error", "critical"):
            return event_dict
        if random.random() <= self.sampling:
            return event_dict
        raise structlog.DropEvent


_LEGACY_LOG_EVENTS = {"log_debug", "log_info", "log_warning", "log_error"}


def _normalize_legacy_structlog_event(_, __, event_dict: dict[str, Any]):
    """Normalize legacy structlog calls using event='log_*' and message='...'.

    Legacy pattern found across the codebase:
      logger.info("log_info", message="...")

    This processor rewrites it into a standard event message while preserving
    the original marker in `legacy_event` for migration observability.
    """
    event = event_dict.get("event")
    message = event_dict.get("message")

    # Some callsites pass a structured dict as the positional event:
    #   logger.info({"event": "...", "foo": "bar"})
    # structlog stores that dict under event_dict["event"].
    # Normalize it by flattening into the top-level event payload.
    if isinstance(event, dict):
        nested = event
        nested_event = nested.get("event")
        for key, value in nested.items():
            if key == "event":
                continue
            event_dict.setdefault(str(key), value)
        if isinstance(nested_event, str) and nested_event.strip():
            event_dict["event"] = nested_event
        else:
            event_dict["event"] = "structured_log_event"
        event = event_dict.get("event")

    if isinstance(event, str) and event in _LEGACY_LOG_EVENTS:
        if message is not None:
            event_dict["event"] = str(message)
            event_dict["legacy_event"] = str(event)
            event_dict.pop("message", None)
        else:
            event_dict["legacy_event"] = str(event)
    return event_dict


def _add_trace_correlation(_, __, event_dict: dict[str, Any]):
    event_dict["trace_id"] = TRACE_ID.get()
    event_dict["user_id"] = USER_ID.get()
    event_dict["session_id"] = SESSION_ID.get()
    event_dict["conversation_id"] = CONVERSATION_ID.get()
    event_dict["project_id"] = PROJECT_ID.get()
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


def _redact_secrets(_, __, event_dict: dict[str, Any]):
    def _mask(value: Any) -> Any:
        s = str(value)
        if len(s) <= 8:
            return "***"
        return s[:2] + "***" + s[-2:]

    # First pass: Redact known sensitive keys
    for k in list(event_dict.keys()):
        lk = str(k).lower()
        if any(sk in lk for sk in _SENSITIVE_KEYS):
            event_dict[k] = _mask(event_dict[k])
    
    # Second pass: Apply PII redaction to message and string values
    # We apply this to 'event' (the message) and other string fields
    # Be careful not to over-redact structured data if it's not a string
    
    try:
        from app.core.memory.security import redact_pii_text_only
        
        # Redact the main log message
        if "event" in event_dict and isinstance(event_dict["event"], str):
            event_dict["event"] = redact_pii_text_only(event_dict["event"])
            
        # Redact other string values (optional, can be expensive)
        # for k, v in event_dict.items():
        #     if isinstance(v, str) and k != "event":
        #         event_dict[k] = redact_pii_text_only(v)
    except Exception:
        # Fail safe: if redaction fails, don't crash, but keep original
        pass
            
    return event_dict


class _LevelFilter(logging.Filter):
    """Optional per-module level overrides."""

    def __init__(self, module_levels: dict[str, int] | None = None):
        super().__init__()
        self.module_levels = module_levels or {}

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - simple pass-through
        lvl = self.module_levels.get(record.name)
        if lvl is not None and record.levelno < lvl:
            return False
        return True


def setup_logging(
    level: int = logging.INFO,
    module_levels: dict[str, int] | None = None,
    sampling: float = 1.0,
    log_file: str | None = "janus.log",
    error_log_file: str | None = None,
):
    """Configure structlog to emit JSON with correlation and safety.

    Args:
        level: Root logging level.
        module_levels: Optional per-module level overrides.
        sampling: Probability [0..1] to keep info/debug logs (warnings+ are always kept).
        log_file: Path to the log file (default: "janus.log").
        error_log_file: Path to the error-only log file. If omitted and log_file is
            set, defaults to a sibling `janus-errors.log`.
    """
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.addFilter(_LevelFilter(module_levels))

    root = logging.getLogger()
    root.handlers = [handler]

    if error_log_file is None and log_file:
        log_dir = os.path.dirname(log_file)
        error_log_file = os.path.join(log_dir, "janus-errors.log") if log_dir else "janus-errors.log"

    if log_file:
        try:
            # Ensure directory exists if path has one
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            max_bytes = int(getattr(settings, "LOG_FILE_MAX_BYTES", 10 * 1024 * 1024))
            backup_count = int(getattr(settings, "LOG_FILE_BACKUP_COUNT", 5))
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max(1, max_bytes),
                backupCount=max(1, backup_count),
                encoding="utf-8",
            )
            file_handler.setFormatter(logging.Formatter("%(message)s"))
            file_handler.addFilter(_LevelFilter(module_levels))
            root.addHandler(file_handler)
        except Exception:
            # Fallback to stderr if file logging fails, but don't crash
            print(f"Failed to setup file logging to {log_file}", file=sys.stderr)

    if error_log_file:
        try:
            error_log_dir = os.path.dirname(error_log_file)
            if error_log_dir and not os.path.exists(error_log_dir):
                os.makedirs(error_log_dir, exist_ok=True)

            max_bytes = int(getattr(settings, "LOG_FILE_MAX_BYTES", 10 * 1024 * 1024))
            backup_count = int(getattr(settings, "LOG_FILE_BACKUP_COUNT", 5))
            error_file_handler = RotatingFileHandler(
                error_log_file,
                maxBytes=max(1, max_bytes),
                backupCount=max(1, backup_count),
                encoding="utf-8",
            )
            error_file_handler.setFormatter(logging.Formatter("%(message)s"))
            error_file_handler.addFilter(_LevelFilter(module_levels))
            error_file_handler.setLevel(logging.ERROR)
            root.addHandler(error_file_handler)
        except Exception:
            print(f"Failed to setup error file logging to {error_log_file}", file=sys.stderr)

    root.setLevel(level)

    sampling_value = float(getattr(settings, "LOG_SAMPLING_RATE", sampling))
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        _normalize_legacy_structlog_event,
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


def cleanup_rotated_log_files(log_file: str, retention_days: int) -> dict[str, Any]:
    """Delete rotated log files older than `retention_days`.

    Keeps the active log file untouched and removes only rotated siblings
    (e.g. janus.log.1, janus.log.2...).
    """
    if retention_days <= 0:
        raise ValueError("retention_days must be greater than zero.")
    if not log_file:
        return {"removed": 0, "scanned": 0}

    base_path = os.path.abspath(log_file)
    base_dir = os.path.dirname(base_path) or "."
    base_name = os.path.basename(base_path)
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    scanned = 0
    removed = 0
    for name in os.listdir(base_dir):
        if not name.startswith(base_name):
            continue
        full_path = os.path.join(base_dir, name)
        if full_path == base_path or not os.path.isfile(full_path):
            continue
        scanned += 1
        try:
            modified = datetime.fromtimestamp(os.path.getmtime(full_path), tz=timezone.utc)
            if modified < cutoff:
                os.remove(full_path)
                removed += 1
        except FileNotFoundError:
            continue

    return {"removed": removed, "scanned": scanned}


def setup_tracing(app=None):
    try:
        if not getattr(settings, "OTEL_ENABLED", False):
            return
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

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
