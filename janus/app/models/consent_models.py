from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.sql import func
from app.models.config_models import Base

class Consent(Base):
    __tablename__ = "consents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False)
    scope = Column(String(100), nullable=False)
    resource = Column(String(200), nullable=True)
    granted = Column(String(5), default="True")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    revoked_at = Column(DateTime, nullable=True)
    __table_args__ = (
        Index("idx_consent_user_scope", "user_id", "scope"),
    )