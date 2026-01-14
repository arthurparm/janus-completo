"""
Repositório para gerenciar configurações dinâmicas de agentes.
Permite que o Meta-Agent otimize configurações baseado em performance.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, desc, select
# from sqlalchemy.orm import Session # Removido, usando AsyncSession

from app.db import db
from app.models.config_models import AgentConfiguration, PriorityLevel


class AgentConfigRepository:
    """Repositório para operações CRUD em configurações de agentes (Async)."""

    def __init__(self, session: AsyncSession | None = None):
        self._session = session

    async def _get_session(self) -> AsyncSession:
        """Obtém sessão do banco de dados (Async)."""
        if self._session:
            return self._session
        # Em contexto async, não podemos criar sessão síncrona on-the-fly.
        # Deve ser injetada via get_db_session() ou passada no construtor.
        raise RuntimeError("AgentConfigRepository requires an injected AsyncSession")

    async def get_active_config(self, agent_name: str, agent_role: str) -> AgentConfiguration | None:
        """Obtém a configuração ativa para um agente específico."""
        session = await self._get_session()
        # Nota: Como _get_session agora levanta erro se não houver sessão,
        # assumimos que quem chama injetou a sessão corretamente.
        
        stmt = (
            select(AgentConfiguration)
            .filter(
                and_(
                    AgentConfiguration.agent_name == agent_name,
                    AgentConfiguration.agent_role == agent_role,
                    AgentConfiguration.is_active,
                )
            )
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def get_config_by_id(self, config_id: int) -> AgentConfiguration | None:
        """Obtém configuração por ID."""
        session = await self._get_session()
        stmt = select(AgentConfiguration).filter(AgentConfiguration.id == config_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def get_configs_by_role(
        self, agent_role: str, active_only: bool = True
    ) -> list[AgentConfiguration]:
        """Obtém todas as configurações para um papel específico."""
        session = await self._get_session()
        
        query = select(AgentConfiguration).filter(
            AgentConfiguration.agent_role == agent_role
        )

        if active_only:
            query = query.filter(AgentConfiguration.is_active)

        query = query.order_by(desc(AgentConfiguration.updated_at))
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_configs_by_provider(
        self, llm_provider: str, active_only: bool = True
    ) -> list[AgentConfiguration]:
        """Obtém configurações por provedor LLM."""
        session = await self._get_session()
        
        query = select(AgentConfiguration).filter(
            AgentConfiguration.llm_provider == llm_provider
        )

        if active_only:
            query = query.filter(AgentConfiguration.is_active)

        query = query.order_by(desc(AgentConfiguration.updated_at))
        result = await session.execute(query)
        return list(result.scalars().all())

    async def create_config(
        self,
        agent_name: str,
        agent_role: str,
        llm_provider: str,
        llm_model: str,
        prompt_id: int | None = None,
        max_retries: int = 3,
        timeout_seconds: int = 60,
        temperature: Decimal = Decimal("0.7"),
        max_tokens: int = 4096,
        priority_level: PriorityLevel = PriorityLevel.MEDIUM,
        cost_budget_usd: Decimal = Decimal("0.05"),
        performance_threshold: Decimal = Decimal("0.8"),
        created_by: str = "meta-agent",
        activate: bool = False,
    ) -> AgentConfiguration:
        """Cria uma nova configuração de agente."""
        session = await self._get_session()
        
        # Se ativar, desativar configuração anterior
        if activate:
            await self._deactivate_config(session, agent_name, agent_role)

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
            created_by=created_by,
        )

        session.add(new_config)
        await session.commit()
        await session.refresh(new_config)
        return new_config

    async def update_config(
        self, config_id: int, updates: dict[str, Any], updated_by: str = "meta-agent"
    ) -> AgentConfiguration | None:
        """Atualiza uma configuração existente."""
        session = await self._get_session()
        
        stmt = select(AgentConfiguration).filter(AgentConfiguration.id == config_id)
        result = await session.execute(stmt)
        config = result.scalars().first()

        if not config:
            return None

        # Aplicar atualizações
        for field, value in updates.items():
            if hasattr(config, field):
                setattr(config, field, value)

        config.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(config)
        return config

    async def activate_config(self, config_id: int) -> bool:
        """Ativa uma configuração específica."""
        session = await self._get_session()
        
        stmt = select(AgentConfiguration).filter(AgentConfiguration.id == config_id)
        result = await session.execute(stmt)
        config = result.scalars().first()

        if not config:
            return False

        # Desativar configuração atual
        await self._deactivate_config(session, config.agent_name, config.agent_role)

        # Ativar nova configuração
        config.is_active = True
        config.updated_at = datetime.utcnow()
        await session.commit()
        return True

    async def _deactivate_config(self, session: AsyncSession, agent_name: str, agent_role: str):
        """Desativa configuração ativa atual."""
        stmt = (
            select(AgentConfiguration)
            .filter(
                and_(
                    AgentConfiguration.agent_name == agent_name,
                    AgentConfiguration.agent_role == agent_role,
                    AgentConfiguration.is_active,
                )
            )
        )
        result = await session.execute(stmt)
        current_active = result.scalars().first()

        if current_active:
            current_active.is_active = False
            current_active.updated_at = datetime.utcnow()

    async def get_low_performance_configs(self, threshold: float = 0.7) -> list[AgentConfiguration]:
        """Obtém configurações com performance abaixo do limiar."""
        session = await self._get_session()
        
        query = select(AgentConfiguration).filter(
            and_(
                AgentConfiguration.is_active,
                AgentConfiguration.performance_threshold < threshold,
            )
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_high_cost_configs(
        self, cost_limit: Decimal = Decimal("0.10")
    ) -> list[AgentConfiguration]:
        """Obtém configurações com custo acima do limite."""
        session = await self._get_session()
        
        query = select(AgentConfiguration).filter(
            and_(
                AgentConfiguration.is_active,
                AgentConfiguration.cost_budget_usd > cost_limit,
            )
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_config_stats(self) -> dict[str, Any]:
        """Obtém estatísticas das configurações."""
        session = await self._get_session()
        
        # Total configs
        result = await session.execute(select(AgentConfiguration))
        all_configs = result.scalars().all()
        total_configs = len(all_configs)
        
        # Active configs
        active_configs_list = [c for c in all_configs if c.is_active]
        active_configs = len(active_configs_list)

        # Distinct providers & roles (using python set for simplicity with async results)
        providers = list({c.llm_provider for c in all_configs if c.llm_provider})
        roles = list({c.agent_role for c in all_configs if c.agent_role})

        # Average cost
        costs = [float(c.cost_budget_usd) for c in active_configs_list if c.cost_budget_usd is not None]
        avg_cost_value = sum(costs) / len(costs) if costs else 0

        return {
            "total_configs": total_configs,
            "active_configs": active_configs,
            "inactive_configs": total_configs - active_configs,
            "providers": providers,
            "roles": roles,
            "average_cost_usd": round(avg_cost_value, 4),
        }
