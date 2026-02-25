from __future__ import annotations

from typing import Any, Iterable

import structlog

from app.repositories.observability_repository import record_audit_event_direct

logger = structlog.get_logger(__name__)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def confidence_from_scores(scores: Iterable[Any]) -> float:
    normalized = [_safe_float(s, default=-1.0) for s in scores]
    valid = [max(0.0, min(1.0, s)) for s in normalized if s >= 0.0]
    if not valid:
        return 0.0
    return max(valid)


def build_step_telemetry(
    *,
    step: str,
    source: str,
    db: str,
    latency_ms: int | float,
    confidence: float | None,
    error_code: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "step": str(step),
        "source": str(source),
        "db": str(db),
        "latency_ms": int(max(0.0, _safe_float(latency_ms, 0.0))),
        "confidence": max(0.0, min(1.0, _safe_float(confidence, 0.0))),
        "error_code": (str(error_code) if error_code else None),
    }
    if extra:
        payload["extra"] = extra
    return payload


def emit_step_telemetry(
    *,
    endpoint: str,
    step: str,
    source: str,
    db: str,
    latency_ms: int | float,
    confidence: float | None,
    error_code: str | None = None,
    extra: dict[str, Any] | None = None,
    user_id: str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    payload = build_step_telemetry(
        step=step,
        source=source,
        db=db,
        latency_ms=latency_ms,
        confidence=confidence,
        error_code=error_code,
        extra=extra,
    )

    log_fields: dict[str, Any] = {
        "endpoint": endpoint,
        "step": payload["step"],
        "source": payload["source"],
        "db": payload["db"],
        "latency_ms": payload["latency_ms"],
        "confidence": payload["confidence"],
        "error_code": payload["error_code"],
    }
    if extra:
        for key, value in extra.items():
            if isinstance(key, str) and key:
                log_fields[key] = value

    logger.info("rag_step_telemetry", **log_fields)

    try:
        record_audit_event_direct(
            {
                "user_id": user_id,
                "endpoint": endpoint,
                "action": "rag_step_telemetry",
                "tool": "rag_pipeline",
                "status": "error" if payload["error_code"] else "success",
                "latency_ms": payload["latency_ms"],
                "trace_id": trace_id,
                "detail": payload,
            }
        )
    except Exception:
        logger.debug("rag_step_telemetry_audit_failed", endpoint=endpoint, step=payload["step"])

    return payload
