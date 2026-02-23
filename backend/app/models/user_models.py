from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.config_models import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(100), nullable=True)
    username = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    display_name = Column(String(100), nullable=True)
    password_hash = Column(Text, nullable=True)
    password_reset_token_hash = Column(String(128), nullable=True)
    password_reset_expires_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
    profiles = relationship("Profile", back_populates="user")
    roles = relationship("UserRole", back_populates="user")
    __table_args__ = (
        Index("idx_user_lookup", "email", "external_id"),
        UniqueConstraint("email", name="unique_user_email"),
        UniqueConstraint("username", name="unique_user_username"),
        UniqueConstraint("external_id", name="unique_user_external_id"),
    )


class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    timezone = Column(String(50), nullable=True)
    language = Column(String(10), default="pt-BR")
    style_prefs = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
    user = relationship("User", back_populates="profiles")
    __table_args__ = (Index("idx_profile_user", "user_id"),)


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    __table_args__ = (UniqueConstraint("name", name="unique_role_name"),)


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    user = relationship("User", back_populates="roles")
    role = relationship("Role")


class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    persona = Column(String(50), nullable=True)
    project_id = Column(String(100), nullable=True)
    title = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
    summary = Column(Text, nullable=True)
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    __table_args__ = (Index("idx_session_user", "user_id", "updated_at"),)


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, default=func.current_timestamp())
    role = Column(String(20), nullable=False)
    text = Column(Text, nullable=False)
    session = relationship("Session", back_populates="messages")
    __table_args__ = (Index("idx_message_session_ts", "session_id", "timestamp"),)


class Consent(Base):
    __tablename__ = "user_privacy_consents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    scope = Column(String(100), nullable=False)
    granted = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    expires_at = Column(DateTime, nullable=True)
    __table_args__ = (
        UniqueConstraint("user_id", "scope", name="unique_user_privacy_scope_consent"),
        Index("idx_privacy_consent_user_scope", "user_id", "scope"),
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    endpoint = Column(String(200), nullable=False)
    action = Column(String(100), nullable=False)
    tool = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False)
    latency_ms = Column(Integer, nullable=True)
    trace_id = Column(String(64), nullable=True)
    justification = Column(Text, nullable=True)
    details_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    __table_args__ = (
        Index("idx_audit_user_ts", "user_id", "created_at"),
        Index("idx_audit_trace", "trace_id"),
        Index("idx_audit_endpoint", "endpoint"),
        Index("idx_audit_action", "action"),
    )


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="unique_user_provider_token"),
        Index("idx_oauth_user_provider", "user_id", "provider"),
    )
