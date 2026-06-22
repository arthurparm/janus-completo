from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import db
from app.models.audit_ledger_models import AuditLedgerEvent

logger = structlog.get_logger(__name__)


def _canonical_json(payload: Any) -> str:
    try:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    except Exception:
        return json.dumps(str(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _get_hmac_key() -> bytes:
    key = getattr(settings, "AUDIT_LEDGER_HMAC_KEY", None)
    if key is not None:
        try:
            return key.get_secret_value().encode("utf-8")  # type: ignore[attr-defined]
        except Exception:
            return str(key).encode("utf-8")
    if str(getattr(settings, "ENVIRONMENT", "") or "").lower() != "production":
        legacy = getattr(settings, "AUTH_JWT_SECRET", None)
        if legacy:
            return str(legacy).encode("utf-8")
    raise RuntimeError("AUDIT_LEDGER_HMAC_KEY is not configured.")


class AuditLedgerRepository:
    """
    Ledger append-only com hash-chain e assinatura HMAC.

    A proteção contra UPDATE/DELETE é aplicada no banco (Postgres triggers).
    O hash-chain é aplicado na aplicação com lock transacional para consistência.
    """

    def _get_session(self) -> Session:
        return db.get_session_direct()

    def append(
        self,
        *,
        actor_user_id: int | None,
        endpoint: str,
        action: str,
        tool: str | None,
        status: str,
        trace_id: str | None,
        payload_json: dict[str, Any] | None,
    ) -> int | None:
        if not bool(getattr(settings, "AUDIT_LEDGER_ENABLED", True)):
            return None

        s = self._get_session()
        try:
            dialect = str(getattr(s.get_bind().dialect, "name", "") or "").lower()
            if dialect in ("postgresql", "postgres"):
                s.execute(text("SELECT pg_advisory_xact_lock(98122731)"))

            last = (
                s.query(AuditLedgerEvent)
                .order_by(AuditLedgerEvent.id.desc())
                .limit(1)
                .first()
            )
            prev_hash = str(last.entry_hash) if last else None

            payload = payload_json or {}
            canonical = _canonical_json(
                {
                    "actor_user_id": actor_user_id,
                    "endpoint": endpoint,
                    "action": action,
                    "tool": tool,
                    "status": status,
                    "trace_id": trace_id,
                    "payload": payload,
                }
            )
            payload_hash = _sha256_hex(canonical)
            chain_base = f"{prev_hash or ''}|{payload_hash}"
            entry_hash = _sha256_hex(chain_base)
            signature = hmac.new(_get_hmac_key(), entry_hash.encode("utf-8"), hashlib.sha256).hexdigest()

            row = AuditLedgerEvent(
                actor_user_id=actor_user_id,
                endpoint=str(endpoint),
                action=str(action),
                tool=str(tool) if tool is not None else None,
                status=str(status),
                trace_id=str(trace_id) if trace_id else None,
                payload_json=payload,
                prev_hash=prev_hash,
                entry_hash=entry_hash,
                signature=signature,
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            return int(row.id)
        except Exception as exc:
            try:
                s.rollback()
            except Exception:
                pass
            logger.warning("audit_ledger_append_failed", error=str(exc))
            return None
        finally:
            s.close()

    def list_events(
        self,
        *,
        user_id: int | None,
        tool: str | None,
        status: str | None,
        endpoint: str | None,
        start_ts: float | None,
        end_ts: float | None,
        limit: int,
        offset: int,
    ) -> list[AuditLedgerEvent]:
        s = self._get_session()
        try:
            q = s.query(AuditLedgerEvent)
            if user_id is not None:
                q = q.filter(AuditLedgerEvent.actor_user_id == int(user_id))
            if tool is not None:
                q = q.filter(AuditLedgerEvent.tool == str(tool))
            if status is not None:
                q = q.filter(AuditLedgerEvent.status == str(status))
            if endpoint is not None:
                q = q.filter(AuditLedgerEvent.endpoint == str(endpoint))
            if start_ts is not None:
                from datetime import datetime

                q = q.filter(AuditLedgerEvent.created_at >= datetime.fromtimestamp(float(start_ts)))
            if end_ts is not None:
                from datetime import datetime

                q = q.filter(AuditLedgerEvent.created_at <= datetime.fromtimestamp(float(end_ts)))
            q = q.order_by(AuditLedgerEvent.created_at.desc()).offset(int(offset)).limit(int(limit))
            return list(q.all())
        finally:
            s.close()

    def count_events(
        self,
        *,
        user_id: int | None,
        tool: str | None,
        status: str | None,
        endpoint: str | None,
        start_ts: float | None,
        end_ts: float | None,
    ) -> int:
        s = self._get_session()
        try:
            q = s.query(AuditLedgerEvent)
            if user_id is not None:
                q = q.filter(AuditLedgerEvent.actor_user_id == int(user_id))
            if tool is not None:
                q = q.filter(AuditLedgerEvent.tool == str(tool))
            if status is not None:
                q = q.filter(AuditLedgerEvent.status == str(status))
            if endpoint is not None:
                q = q.filter(AuditLedgerEvent.endpoint == str(endpoint))
            if start_ts is not None:
                from datetime import datetime

                q = q.filter(AuditLedgerEvent.created_at >= datetime.fromtimestamp(float(start_ts)))
            if end_ts is not None:
                from datetime import datetime

                q = q.filter(AuditLedgerEvent.created_at <= datetime.fromtimestamp(float(end_ts)))
            return int(q.count())
        finally:
            s.close()

    def list_events_by_trace_id(self, *, trace_id: str, limit: int, offset: int) -> list[AuditLedgerEvent]:
        s = self._get_session()
        try:
            q = (
                s.query(AuditLedgerEvent)
                .filter(AuditLedgerEvent.trace_id == str(trace_id))
                .order_by(AuditLedgerEvent.created_at.asc())
                .offset(int(offset))
                .limit(int(limit))
            )
            return list(q.all())
        finally:
            s.close()

    def verify_integrity(self, *, max_errors: int = 25) -> dict[str, Any]:
        s = self._get_session()
        try:
            dialect = str(getattr(s.get_bind().dialect, "name", "") or "").lower()
            if dialect in ("postgresql", "postgres"):
                s.execute(text("SELECT pg_advisory_xact_lock(98122732)"))

            rows = s.query(AuditLedgerEvent).order_by(AuditLedgerEvent.id.asc()).all()
            errors: list[dict[str, Any]] = []
            prev_hash: str | None = None
            key = _get_hmac_key()

            for row in rows:
                payload = row.payload_json or {}
                canonical = _canonical_json(
                    {
                        "actor_user_id": row.actor_user_id,
                        "endpoint": row.endpoint,
                        "action": row.action,
                        "tool": row.tool,
                        "status": row.status,
                        "trace_id": row.trace_id,
                        "payload": payload,
                    }
                )
                payload_hash = _sha256_hex(canonical)
                expected_entry_hash = _sha256_hex(f"{prev_hash or ''}|{payload_hash}")
                expected_sig = hmac.new(key, expected_entry_hash.encode("utf-8"), hashlib.sha256).hexdigest()

                if row.prev_hash != prev_hash:
                    errors.append(
                        {
                            "id": row.id,
                            "kind": "prev_hash_mismatch",
                            "expected": prev_hash,
                            "actual": row.prev_hash,
                        }
                    )
                if row.entry_hash != expected_entry_hash:
                    errors.append(
                        {
                            "id": row.id,
                            "kind": "entry_hash_mismatch",
                            "expected": expected_entry_hash,
                            "actual": row.entry_hash,
                        }
                    )
                if row.signature != expected_sig:
                    errors.append(
                        {
                            "id": row.id,
                            "kind": "signature_mismatch",
                            "expected": expected_sig,
                            "actual": row.signature,
                        }
                    )

                prev_hash = row.entry_hash
                if len(errors) >= max_errors:
                    break

            ok = len(errors) == 0
            return {
                "ok": ok,
                "checked": len(rows),
                "errors": errors,
                "errors_total": len(errors),
                "last_entry_hash": prev_hash,
            }
        finally:
            s.close()


audit_ledger_repository = AuditLedgerRepository()
