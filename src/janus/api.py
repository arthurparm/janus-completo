"""API que o cliente de supervisão chama."""

from __future__ import annotations

from janus.loop import Runtime
from janus.state import Pending, PendingStatus
from janus.util.codec import JanusError, as_object


def interrupt_run(runtime: Runtime, run_id: str) -> dict[str, object]:
    checkpoint = runtime.interrupt(run_id)
    return {
        "run_id": checkpoint.run_id,
        "status": checkpoint.status,
        "stop_reason": checkpoint.stop_reason,
    }


def list_pending(runtime: Runtime, run_id: str) -> tuple[dict[str, object], ...]:
    return tuple(item.to_json() for item in runtime.pending_of(run_id))


def approve_pending(runtime: Runtime, value: object) -> dict[str, object]:
    return _settle_pending(runtime, value, "aprovada")


def deny_pending(runtime: Runtime, value: object) -> dict[str, object]:
    return _settle_pending(runtime, value, "negada")


def require_pending(value: object) -> dict[str, object]:
    _require_effect_and_risk(value)
    return Pending.from_json(value).to_json()


def _settle_pending(runtime: Runtime, value: object, status: PendingStatus) -> dict[str, object]:
    _require_effect_and_risk(value)
    return runtime.settle_pending(Pending.from_json(value), status).to_json()


def _require_effect_and_risk(value: object) -> None:
    raw = as_object(value, "pending")
    effect = raw.get("effect")
    risk_class = raw.get("risk_class")
    if (
        not isinstance(effect, str)
        or effect.strip() == ""
        or not isinstance(risk_class, str)
        or risk_class.strip() == ""
    ):
        raise JanusError("pendência sem efeito ou classe de risco")
