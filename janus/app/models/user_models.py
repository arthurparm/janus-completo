from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.config_models import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    display_name = Column(String(100), nullable=True)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    profiles = relationship("Profile", back_populates="user")
    roles = relationship("UserRole", back_populates="user")
    __table_args__ = (
        Index("idx_user_lookup", "email", "external_id"),
    )

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    timezone = Column(String(50), nullable=True)
    language = Column(String(10), default="pt-BR")
    style_prefs = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    user = relationship("User", back_populates="profiles")
    __table_args__ = (
        Index("idx_profile_user", "user_id"),
    )

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    __table_args__ = (
        UniqueConstraint("name", name="unique_role_name"),
    )

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
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    summary = Column(Text, nullable=True)
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    __table_args__ = (
        Index("idx_session_user", "user_id", "updated_at"),
    )

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, default=func.current_timestamp())
    role = Column(String(20), nullable=False)
    text = Column(Text, nullable=False)
    session = relationship("Session", back_populates="messages")
    __table_args__ = (
        Index("idx_message_session_ts", "session_id", "timestamp"),
    )


class Consent(Base):
    __tablename__ = "consents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    scope = Column(String(100), nullable=False)
    granted = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    expires_at = Column(DateTime, nullable=True)
    __table_args__ = (
        UniqueConstraint("user_id", "scope", name="unique_user_scope_consent"),
        Index("idx_consent_user_scope", "user_id", "scope"),
    )