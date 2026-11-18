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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.config_models import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=True)
    display_name = Column(String(100), nullable=True)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
    profiles = relationship("Profile", back_populates="user")
    roles = relationship("UserRole", back_populates="user")
    external_identities = relationship(
        "ExternalIdentity", back_populates="user", cascade="all, delete-orphan"
    )
    __table_args__ = (
        Index("idx_user_lookup", "email"),
        UniqueConstraint("email", name="unique_user_email"),
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
    __table_args__ = (UniqueConstraint("user_id", name="unique_profile_user"),)


class ExternalIdentity(Base):
    __tablename__ = "external_identities"
    id = Column(Integer, primary_key=True, autoincrement=True)
    issuer = Column(String(512), nullable=False)
    subject = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    email_at_link = Column(String(255), nullable=True)
    email_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=func.current_timestamp(), nullable=False)
    last_seen_at = Column(DateTime, default=func.current_timestamp(), nullable=False)
    user = relationship("User", back_populates="external_identities")
    __table_args__ = (
        UniqueConstraint("issuer", "subject", name="unique_external_identity"),
        Index("idx_external_identity_user", "user_id"),
    )


class ExternalIdentityEvent(Base):
    __tablename__ = "external_identity_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    identity_id = Column(
        Integer, ForeignKey("external_identities.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False)
    admin_group_authorized = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=func.current_timestamp(), nullable=False)
    __table_args__ = (Index("idx_external_identity_event_user", "user_id", "created_at"),)


class ServicePrincipal(Base):
    __tablename__ = "service_principals"
    id = Column(Integer, primary_key=True, autoincrement=True)
    issuer = Column(String(512), nullable=False)
    subject = Column(String(255), nullable=False)
    client_id = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
    scopes = relationship(
        "ServicePrincipalScope", back_populates="principal", cascade="all, delete-orphan"
    )
    __table_args__ = (
        UniqueConstraint("issuer", "subject", name="unique_service_principal_subject"),
        UniqueConstraint("issuer", "client_id", name="unique_service_principal_client"),
    )


class ServicePrincipalScope(Base):
    __tablename__ = "service_principal_scopes"
    principal_id = Column(
        Integer, ForeignKey("service_principals.id", ondelete="CASCADE"), primary_key=True
    )
    scope = Column(String(100), primary_key=True)
    created_at = Column(DateTime, default=func.current_timestamp(), nullable=False)
    principal = relationship("ServicePrincipal", back_populates="scopes")


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
    knowledge_space_id = Column(String(255), nullable=True)
    mode_used = Column(String(64), nullable=True)
    base_used = Column(String(64), nullable=True)
    citations_json = Column(JSONB, nullable=True)
    citation_status_json = Column(JSONB, nullable=True)
    ui_json = Column(JSONB, nullable=True)
    source_scope_json = Column(JSONB, nullable=True)
    gaps_or_conflicts_json = Column(JSONB, nullable=True)
    understanding_json = Column(JSONB, nullable=True)
    confirmation_json = Column(JSONB, nullable=True)
    agent_state_json = Column(JSONB, nullable=True)
    delivery_status = Column(String(32), nullable=True)
    failure_classification = Column(String(32), nullable=True)
    provider = Column(String(100), nullable=True)
    model = Column(String(120), nullable=True)
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
