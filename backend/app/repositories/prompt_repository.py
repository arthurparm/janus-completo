"""
Repositório para gerenciar prompts dinâmicos.
Permite que o Meta-Agent atualize prompts baseado em análises de performance.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import db
from app.models.config_models import Prompt


class PromptRepository:
    """Repositório para operações CRUD em prompts."""

    def __init__(self, session: Session | AsyncSession | None = None):
        self._session: Session | AsyncSession | None = None
        self._async_session: AsyncSession | None = None
        if session is None:
            return
        if isinstance(session, AsyncSession):
            self._async_session = session
        else:
            self._session = session

    def _get_session_sync(self) -> Session:
        """Get a sync database session."""
        if self._session is not None:
            if isinstance(self._session, AsyncSession):
                raise RuntimeError(
                    "PromptRepository has an AsyncSession injected. Use async methods."
                )
            return self._session
        return db.get_session_direct()

    async def _get_session_async(self) -> AsyncSession:
        """Get an async database session."""
        if self._async_session is not None:
            return self._async_session
        if isinstance(self._session, AsyncSession):
            return self._session
        # Creating ad-hoc async sessions must be done by the caller.
        raise RuntimeError(
            "PromptRepository requires an injected AsyncSession. "
            "Use 'async with postgres_db.get_session_async() as session:' "
            "and pass the session to the repository."
        )

    async def get_active_prompt(
        self,
        prompt_name: str,
        namespace: str = "default",
        language: str = "en",
        model_target: str = "general",
    ) -> Prompt | None:
        """Obtém o prompt ativo para um nome específico."""
        session = await self._get_session_async()
        
        # Async query
        stmt = (
            select(Prompt)
            .filter(
                and_(
                    Prompt.prompt_name == prompt_name,
                    Prompt.namespace == namespace,
                    Prompt.language == language,
                    Prompt.model_target == model_target,
                    Prompt.is_active,
                )
            )
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    def get_active_prompt_sync(
        self,
        prompt_name: str,
        namespace: str = "default",
        language: str = "en",
        model_target: str = "general",
    ) -> Prompt | None:
        """Get the active prompt using a sync session."""
        session = self._get_session_sync()
        owns_session = self._session is None
        try:
            return (
                session.query(Prompt)
                .filter(
                    and_(
                        Prompt.prompt_name == prompt_name,
                        Prompt.namespace == namespace,
                        Prompt.language == language,
                        Prompt.model_target == model_target,
                        Prompt.is_active,
                    )
                )
                .first()
            )
        finally:
            if owns_session:
                session.close()

    def get_prompt_by_id(self, prompt_id: int) -> Prompt | None:
        """Obtém prompt por ID."""
        session = self._get_session_sync()
        owns_session = self._session is None
        try:
            return session.query(Prompt).filter(Prompt.id == prompt_id).first()
        finally:
            if owns_session:
                session.close()

    def get_prompt_versions(self, prompt_name: str, namespace: str = "default") -> list[Prompt]:
        """Obtém todas as versões de um prompt."""
        session = self._get_session_sync()
        owns_session = self._session is None
        try:
            return (
                session.query(Prompt)
                .filter(and_(Prompt.prompt_name == prompt_name, Prompt.namespace == namespace))
                .order_by(desc(Prompt.created_at))
                .all()
            )
        finally:
            if owns_session:
                session.close()

    def create_prompt_version(
        self,
        prompt_name: str,
        prompt_text: str,
        version: str,
        namespace: str = "default",
        language: str = "en",
        model_target: str = "general",
        created_by: str = "meta-agent",
        activate: bool = False,
    ) -> Prompt:
        """Cria uma nova versão de prompt."""
        session = self._get_session_sync()
        owns_session = self._session is None
        try:
            # Se ativar, desativar versão anterior
            if activate:
                self._deactivate_prompt(session, prompt_name, namespace, language, model_target)

            new_prompt = Prompt(
                prompt_name=prompt_name,
                prompt_version=version,
                prompt_text=prompt_text,
                is_active=activate,
                namespace=namespace,
                language=language,
                model_target=model_target,
                created_by=created_by,
            )

            session.add(new_prompt)
            session.commit()
            session.refresh(new_prompt)
            return new_prompt
        finally:
            if owns_session:
                session.close()

    def activate_prompt_version(self, prompt_id: int) -> bool:
        """Ativa uma versão específica de prompt."""
        session = self._get_session_sync()
        owns_session = self._session is None
        try:
            prompt = session.query(Prompt).filter(Prompt.id == prompt_id).first()
            if not prompt:
                return False

            # Desativar versão atual
            self._deactivate_prompt(
                session, prompt.prompt_name, prompt.namespace, prompt.language, prompt.model_target
            )

            # Ativar nova versão
            prompt.is_active = True
            prompt.updated_at = datetime.utcnow()
            session.commit()
            return True
        finally:
            if owns_session:
                session.close()

    def _deactivate_prompt(
        self, session: Session, prompt_name: str, namespace: str, language: str, model_target: str
    ):
        """Desativa prompt ativo atual."""
        current_active = (
            session.query(Prompt)
            .filter(
                and_(
                    Prompt.prompt_name == prompt_name,
                    Prompt.namespace == namespace,
                    Prompt.language == language,
                    Prompt.model_target == model_target,
                    Prompt.is_active,
                )
            )
            .first()
        )

        if current_active:
            current_active.is_active = False
            current_active.updated_at = datetime.utcnow()

    def search_prompts(
        self,
        name_pattern: str | None = None,
        namespace: str | None = None,
        active_only: bool = True,
    ) -> list[Prompt]:
        """Busca prompts por padrão."""
        session = self._get_session_sync()
        owns_session = self._session is None
        try:
            query = session.query(Prompt)

            if name_pattern:
                query = query.filter(Prompt.prompt_name.like(f"%{name_pattern}%"))

            if namespace:
                query = query.filter(Prompt.namespace == namespace)

            if active_only:
                query = query.filter(Prompt.is_active)

            return query.order_by(desc(Prompt.updated_at)).all()
        finally:
            if owns_session:
                session.close()

    def get_prompt_stats(self) -> dict[str, Any]:
        """Obtém estatísticas dos prompts."""
        session = self._get_session_sync()
        owns_session = self._session is None
        try:
            total_prompts = session.query(Prompt).count()
            active_prompts = session.query(Prompt).filter(Prompt.is_active).count()
            namespaces = session.query(Prompt.namespace).distinct().count()

            return {
                "total_prompts": total_prompts,
                "active_prompts": active_prompts,
                "namespaces": namespaces,
                "inactive_prompts": total_prompts - active_prompts,
            }
        finally:
            if owns_session:
                session.close()
