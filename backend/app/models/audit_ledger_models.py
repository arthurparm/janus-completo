from __future__ import annotations

from sqlalchemy import Column, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.config_models import Base


class AuditLedgerEvent(Base):
    """
    Ledger imutável (append-only) para auditoria.

    A imutabilidade é reforçada por:
    - tabela dedicada + triggers que bloqueiam UPDATE/DELETE (Postgres);
    - hash-chain (prev_hash -> entry_hash) + assinatura HMAC.
    """

    __tablename__ = "audit_ledger_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_user_id = Column(Integer, nullable=True)
    endpoint = Column(String(200), nullable=False)
    action = Column(String(100), nullable=False)
    tool = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False)
    trace_id = Column(String(64), nullable=True)

    payload_json = Column(JSONB, nullable=True)

    prev_hash = Column(String(64), nullable=True)
    entry_hash = Column(String(64), nullable=False)
    signature = Column(String(64), nullable=False)

    created_at = Column(DateTime, default=func.current_timestamp())

    __table_args__ = (
        Index("idx_audit_ledger_ts", "created_at"),
        Index("idx_audit_ledger_trace", "trace_id"),
        Index("idx_audit_ledger_actor", "actor_user_id", "created_at"),
        Index("idx_audit_ledger_action", "action", "created_at"),
    )

