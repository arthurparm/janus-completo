"""
Modelos SQLAlchemy para Configuration-as-Data.
Permite que o Meta-Agent modifique prompts e configurações dinamicamente.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer,
    Numeric, String, Text, UniqueConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class PriorityLevel(str, Enum):
    """Níveis de prioridade para configurações de agentes."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class OptimizationType(str, Enum):
    """Tipos de otimização realizadas pelo Meta-Agent."""
    PROMPT_UPDATE = "PROMPT_UPDATE"
    CONFIG_UPDATE = "CONFIG_UPDATE"
    MODEL_CHANGE = "MODEL_CHANGE"


class TargetType(str, Enum):
    """Tipos de alvo para otimizações."""
    AGENT = "AGENT"
    PROMPT = "PROMPT"


class Prompt(Base):
    """
    Modelo para armazenar prompts versionados.
    Permite que o Meta-Agent atualize prompts dinamicamente.
    """
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_name = Column(String(100), nullable=False)
    prompt_version = Column(String(20), nullable=False, default="1.0")
    prompt_text = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    namespace = Column(String(50), default="default")
    language = Column(String(10), default="pt-BR")
    model_target = Column(String(50), default="general")
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    created_by = Column(String(100), default="system")

    # Relacionamentos
    agent_configurations = relationship("AgentConfiguration", back_populates="prompt")

    # Índices
    __table_args__ = (
        Index('idx_prompt_lookup', 'prompt_name', 'namespace', 'is_active'),
        Index('idx_prompt_version', 'prompt_name', 'prompt_version'),
        Index('idx_active_prompts', 'is_active', 'namespace'),
        UniqueConstraint('prompt_name', 'namespace', 'is_active', 'language', 'model_target',
                         name='unique_active_prompt'),
    )

    def __repr__(self):
        return f"<Prompt(name='{self.prompt_name}', version='{self.prompt_version}', active={self.is_active})>"


class AgentConfiguration(Base):
    """
    Modelo para configurações dinâmicas de agentes.
    Permite que o Meta-Agent otimize configurações baseado em performance.
    """
    __tablename__ = "agent_configurations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String(100), nullable=False)
    agent_role = Column(String(50), nullable=False)
    llm_provider = Column(String(50), nullable=False)
    llm_model = Column(String(100), nullable=False)
    prompt_id = Column(Integer, ForeignKey("prompts.id", ondelete="SET NULL"), nullable=True)
    max_retries = Column(Integer, default=3)
    timeout_seconds = Column(Integer, default=60)
    temperature = Column(Numeric(3, 2), default=Decimal("0.7"))
    max_tokens = Column(Integer, default=4096)
    is_active = Column(Boolean, nullable=False, default=False)
    priority_level = Column(SQLEnum(PriorityLevel), default=PriorityLevel.MEDIUM)
    cost_budget_usd = Column(Numeric(10, 4), default=Decimal("0.05"))
    performance_threshold = Column(Numeric(3, 2), default=Decimal("0.8"))
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    created_by = Column(String(100), default="system")

    # Relacionamentos
    prompt = relationship("Prompt", back_populates="agent_configurations")

    # Índices
    __table_args__ = (
        Index('idx_agent_lookup', 'agent_name', 'agent_role', 'is_active'),
        Index('idx_agent_provider', 'llm_provider', 'llm_model'),
        Index('idx_active_configs', 'is_active', 'agent_role'),
        UniqueConstraint('agent_name', 'agent_role', 'is_active', name='unique_active_agent'),
    )

    def __repr__(self):
        return f"<AgentConfiguration(name='{self.agent_name}', role='{self.agent_role}', active={self.is_active})>"


class OptimizationHistory(Base):
    """
    Modelo para rastrear otimizações realizadas pelo Meta-Agent.
    Permite análise de impacto e rollback se necessário.
    """
    __tablename__ = "optimization_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    optimization_type = Column(SQLEnum(OptimizationType), nullable=False)
    target_type = Column(SQLEnum(TargetType), nullable=False)
    target_id = Column(Integer, nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    performance_before = Column(Numeric(3, 2), nullable=True)
    performance_after = Column(Numeric(3, 2), nullable=True)
    cost_impact_usd = Column(Numeric(10, 4), nullable=True)
    success = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    created_by = Column(String(100), default="meta-agent")

    # Índices
    __table_args__ = (
        Index('idx_optimization_type', 'optimization_type', 'created_at'),
        Index('idx_target_history', 'target_type', 'target_id', 'created_at'),
        Index('idx_performance_tracking', 'performance_before', 'performance_after'),
    )

    def __repr__(self):
        return f"<OptimizationHistory(type='{self.optimization_type}', target='{self.target_type}:{self.target_id}')>"
