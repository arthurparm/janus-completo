from __future__ import annotations

import os

from app.core.security.security_alerts import emit_security_alert
from fastapi import FastAPI

_FORBIDDEN_ENABLE_FLAGS = (
    "ENABLE_AUTO_EVOLUTION",
    "AUTO_EVOLUTION_ENABLED",
    "ENABLE_SELF_MODIFICATION",
    "DYNAMIC_TOOL_CREATION_ENABLED",
    "JANUS_DREAM_MODE",
)
_FORBIDDEN_ROUTE_FRAGMENTS = ("/sandbox", "/tools/create", "/evolution", "/dream")


def validate_autonomous_evolution_disabled(app: FastAPI) -> None:
    enabled_flags = [
        name
        for name in _FORBIDDEN_ENABLE_FLAGS
        if str(os.getenv(name, "")).strip().lower() in {"1", "true", "yes", "on"}
    ]
    forbidden_routes = [
        getattr(route, "path", "")
        for route in app.routes
        if any(fragment in getattr(route, "path", "").lower() for fragment in _FORBIDDEN_ROUTE_FRAGMENTS)
    ]
    if enabled_flags or forbidden_routes:
        emit_security_alert(
            "autonomous_evolution_reactivation_blocked",
            {"flags": enabled_flags, "routes": forbidden_routes},
        )
        raise RuntimeError("Autonomous code evolution is permanently disabled")
