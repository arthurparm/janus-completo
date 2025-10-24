"""
Repositório para gerenciar configurações dinâmicas de agentes.
Permite que o Meta-Agent otimize configurações baseado em performance.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.models.config_models import AgentConfiguration, PriorityLevel
from app.db.mysql_config import mysql_db


class AgentConfigRepository:
    """Repositório para operações CRUD em configurações de agentes."""

    def __init__(self, session: Optional[Session] = None):
        self._session = session

    def _get_session(self) -> Session:
        """Obtém sessão do banco de dados."""
        if self._session:
            return self._session
        return mysql_db.get_session_direct()

    def get_active_config(self, agent_name: str, agent_role: str) -> Optional[AgentConfiguration]:
        """Obtém a configuração ativa para um agente específico."""
        session = self._get_session()
        try:
            return session.query(AgentConfiguration).filter(
                and_(
                    AgentConfiguration.agent_name == agent_name,
                    AgentConfiguration.agent_role == agent_role,
                    AgentConfiguration.is_active == True
                )
            ).first()
        finally:
            if not self._session:
                session.close()

    def get_config_by_id(self, config_id: int) -> Optional[AgentConfiguration]:
        """Obtém configuração por ID."""
        session = self._get_session()
        try:
            return session.query(AgentConfiguration).filter(
                AgentConfiguration.id == config_id
            ).first()
        finally:
            if not self._session:
                session.close()

    def get_configs_by_role(self, agent_role: str, active_only: bool = True) -> List[AgentConfiguration]:
        """Obtém todas as configurações para um papel específico."""
        session = self._get_session()
        try:
            query = session.query(AgentConfiguration).filter(
                AgentConfiguration.agent_role == agent_role
            )

            if active_only:
                query = query.filter(AgentConfiguration.is_active == True)

            return query.order_by(desc(AgentConfiguration.updated_at)).all()
        finally:
            if not self._session:
                session.close()

    def get_configs_by_provider(self, llm_provider: str, active_only: bool = True) -> List[AgentConfiguration]:
        """Obtém configurações por provedor LLM."""
        session = self._get_session()
        try:
            query = session.query(AgentConfiguration).filter(
                AgentConfiguration.llm_provider == llm_provider
            )

            if active_only:
                query = query.filter(AgentConfiguration.is_active == True)

            return query.order_by(desc(AgentConfiguration.updated_at)).all()
        finally:
            if not self._session:
                session.close()

    def create_config(
            self,
            agent_name: str,
            agent_role: str,
            llm_provider: str,
            llm_model: str,
            prompt_id: Optional[int] = None,
            max_retries: int = 3,
            timeout_seconds: int = 60,
            temperature: Decimal = Decimal("0.7"),
            max_tokens: int = 4096,
            priority_level: PriorityLevel = PriorityLevel.MEDIUM,
            cost_budget_usd: Decimal = Decimal("0.05"),
            performance_threshold: Decimal = Decimal("0.8"),
            created_by: str = "meta-agent",
            activate: bool = False
    ) -> AgentConfiguration:
        """Cria uma nova configuração de agente."""
        session = self._get_session()
        try:
            # Se ativar, desativar configuração anterior
            if activate:
                self._deactivate_config(session, agent_name, agent_role)

            new_config = AgentConfiguration(
                agent_name=agent_name,
                agent_role=agent_role,
                llm_provider=llm_provider,
                llm_model=llm_model,
                prompt_id=prompt_id,
                max_retries=max_retries,
                timeout_seconds=timeout_seconds,
                temperature=temperature,
                max_tokens=max_tokens,
                is_active=activate,
                priority_level=priority_level,
                cost_budget_usd=cost_budget_usd,
                performance_threshold=performance_threshold,
                created_by=created_by
            )

            session.add(new_config)
            session.commit()
            session.refresh(new_config)
            return new_config
        finally:
            if not self._session:
                session.close()

    def update_config(
            self,
            config_id: int,
            updates: Dict[str, Any],
            updated_by: str = "meta-agent"
    ) -> Optional[AgentConfiguration]:
        """Atualiza uma configuração existente."""
        session = self._get_session()
        try:
            config = session.query(AgentConfiguration).filter(
                AgentConfiguration.id == config_id
            ).first()

            if not config:
                return None

            # Aplicar atualizações
            for field, value in updates.items():
                if hasattr(config, field):
                    setattr(config, field, value)

            config.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(config)
            return config
        finally:
            if not self._session:
                session.close()

    def activate_config(self, config_id: int) -> bool:
        """Ativa uma configuração específica."""
        session = self._get_session()
        try:
            config = session.query(AgentConfiguration).filter(
                AgentConfiguration.id == config_id
            ).first()

            if not config:
                return False

            # Desativar configuração atual
            self._deactivate_config(session, config.agent_name, config.agent_role)

            # Ativar nova configuração
            config.is_active = True
            config.updated_at = datetime.utcnow()
            session.commit()
            return True
        finally:
            if not self._session:
                session.close()

    def _deactivate_config(self, session: Session, agent_name: str, agent_role: str):
        """Desativa configuração ativa atual."""
        current_active = session.query(AgentConfiguration).filter(
            and_(
                AgentConfiguration.agent_name == agent_name,
                AgentConfiguration.agent_role == agent_role,
                AgentConfiguration.is_active == True
            )
        ).first()

        if current_active:
            current_active.is_active = False
            current_active.updated_at = datetime.utcnow()

    def get_low_performance_configs(self, threshold: float = 0.7) -> List[AgentConfiguration]:
        """Obtém configurações com performance abaixo do limiar."""
        session = self._get_session()
        try:
            return session.query(AgentConfiguration).filter(
                and_(
                    AgentConfiguration.is_active == True,
                    AgentConfiguration.performance_threshold < threshold
                )
            ).all()
        finally:
            if not self._session:
                session.close()

    def get_high_cost_configs(self, cost_limit: Decimal = Decimal("0.10")) -> List[AgentConfiguration]:
        """Obtém configurações com custo acima do limite."""
        session = self._get_session()
        try:
            return session.query(AgentConfiguration).filter(
                and_(
                    AgentConfiguration.is_active == True,
                    AgentConfiguration.cost_budget_usd > cost_limit
                )
            ).all()
        finally:
            if not self._session:
                session.close()

    def get_config_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas das configurações."""
        session = self._get_session()
        try:
            total_configs = session.query(AgentConfiguration).count()
            active_configs = session.query(AgentConfiguration).filter(
                AgentConfiguration.is_active == True
            ).count()

            providers = session.query(AgentConfiguration.llm_provider).distinct().all()
            roles = session.query(AgentConfiguration.agent_role).distinct().all()

            avg_cost = session.query(AgentConfiguration.cost_budget_usd).filter(
                AgentConfiguration.is_active == True
            ).all()

            avg_cost_value = sum(float(c.cost_budget_usd) for c in avg_cost) / len(avg_cost) if avg_cost else 0

            return {
                "total_configs": total_configs,
                "active_configs": active_configs,
                "inactive_configs": total_configs - active_configs,
                "providers": [p[0] for p in providers],
                "roles": [r[0] for r in roles],
                "average_cost_usd": round(avg_cost_value, 4)
            }
        finally:
            if not self._session:
                session.close()
