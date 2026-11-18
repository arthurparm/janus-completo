from __future__ import annotations

from typing import Any

import structlog

from app.core.infrastructure.logging_config import TRACE_ID
from app.core.infrastructure.vault_client import vault_client
from app.repositories.observability_repository import record_audit_event_direct

logger = structlog.get_logger(__name__)


class VaultTransitRotationService:
    def rotate(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        try:
            result = vault_client.transit_rotate()
        except Exception as exc:
            try:
                record_audit_event_direct(
                    user_id=None,
                    endpoint="vault",
                    action="vault_transit_rotate",
                    tool="vault_transit",
                    status="error",
                    trace_id=TRACE_ID.get(),
                    details_json={"error": str(exc)},
                )
            except Exception:
                pass
            raise

        try:
            record_audit_event_direct(
                user_id=None,
                endpoint="vault",
                action="vault_transit_rotate",
                tool="vault_transit",
                status="success",
                trace_id=TRACE_ID.get(),
                details_json=result,
            )
        except Exception:
            pass

        return result


vault_transit_rotation_service = VaultTransitRotationService()

