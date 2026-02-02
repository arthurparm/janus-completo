"""
Modelos para persistência de itens em quarentena do GraphGuardian.
"""

from enum import Enum

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models.config_models import Base


class QuarantineStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PROCESSED = "PROCESSED"


class QuarantineItem(Base):
    """
    Armazena itens (entidades ou relações) que foram rejeitados pelo GraphGuardian
    para revisão posterior ou auditoria.
    """

    __tablename__ = "quarantine_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_type = Column(String(50), nullable=False)  # 'entity' ou 'relationship'
    source_id = Column(String(100), nullable=True)  # ID da origem (experience_id, doc_id)
    content = Column(JSON, nullable=False)  # O conteúdo original em JSON
    reason = Column(Text, nullable=False)  # Motivo da quarentena
    status = Column(String(20), default=QuarantineStatus.PENDING.value)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(String(100), nullable=True)

    def __repr__(self):
        return f"<QuarantineItem(id={self.id}, type={self.item_type}, reason='{self.reason}')>"
