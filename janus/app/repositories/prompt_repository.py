"""
Repositório para gerenciar prompts dinâmicos.
Permite que o Meta-Agent atualize prompts baseado em análises de performance.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.models.config_models import Prompt
from app.db.mysql_config import mysql_db


class PromptRepository:
    """Repositório para operações CRUD em prompts."""

    def __init__(self, session: Optional[Session] = None):
        self._session = session

    def _get_session(self) -> Session:
        """Obtém sessão do banco de dados."""
        if self._session:
            return self._session
        return mysql_db.get_session_direct()

    def get_active_prompt(
            self,
            prompt_name: str,
            namespace: str = "default",
            language: str = "pt-BR",
            model_target: str = "general"
    ) -> Optional[Prompt]:
        """Obtém o prompt ativo para um nome específico."""
        session = self._get_session()
        try:
            return session.query(Prompt).filter(
                and_(
                    Prompt.prompt_name == prompt_name,
                    Prompt.namespace == namespace,
                    Prompt.language == language,
                    Prompt.model_target == model_target,
                    Prompt.is_active == True
                )
            ).first()
        finally:
            if not self._session:
                session.close()

    def get_prompt_by_id(self, prompt_id: int) -> Optional[Prompt]:
        """Obtém prompt por ID."""
        session = self._get_session()
        try:
            return session.query(Prompt).filter(Prompt.id == prompt_id).first()
        finally:
            if not self._session:
                session.close()

    def get_prompt_versions(self, prompt_name: str, namespace: str = "default") -> List[Prompt]:
        """Obtém todas as versões de um prompt."""
        session = self._get_session()
        try:
            return session.query(Prompt).filter(
                and_(
                    Prompt.prompt_name == prompt_name,
                    Prompt.namespace == namespace
                )
            ).order_by(desc(Prompt.created_at)).all()
        finally:
            if not self._session:
                session.close()

    def create_prompt_version(
            self,
            prompt_name: str,
            prompt_text: str,
            version: str,
            namespace: str = "default",
            language: str = "pt-BR",
            model_target: str = "general",
            created_by: str = "meta-agent",
            activate: bool = False
    ) -> Prompt:
        """Cria uma nova versão de prompt."""
        session = self._get_session()
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
                created_by=created_by
            )

            session.add(new_prompt)
            session.commit()
            session.refresh(new_prompt)
            return new_prompt
        finally:
            if not self._session:
                session.close()

    def activate_prompt_version(self, prompt_id: int) -> bool:
        """Ativa uma versão específica de prompt."""
        session = self._get_session()
        try:
            prompt = session.query(Prompt).filter(Prompt.id == prompt_id).first()
            if not prompt:
                return False

            # Desativar versão atual
            self._deactivate_prompt(
                session,
                prompt.prompt_name,
                prompt.namespace,
                prompt.language,
                prompt.model_target
            )

            # Ativar nova versão
            prompt.is_active = True
            prompt.updated_at = datetime.utcnow()
            session.commit()
            return True
        finally:
            if not self._session:
                session.close()

    def _deactivate_prompt(
            self,
            session: Session,
            prompt_name: str,
            namespace: str,
            language: str,
            model_target: str
    ):
        """Desativa prompt ativo atual."""
        current_active = session.query(Prompt).filter(
            and_(
                Prompt.prompt_name == prompt_name,
                Prompt.namespace == namespace,
                Prompt.language == language,
                Prompt.model_target == model_target,
                Prompt.is_active == True
            )
        ).first()

        if current_active:
            current_active.is_active = False
            current_active.updated_at = datetime.utcnow()

    def search_prompts(
            self,
            name_pattern: Optional[str] = None,
            namespace: Optional[str] = None,
            active_only: bool = True
    ) -> List[Prompt]:
        """Busca prompts por padrão."""
        session = self._get_session()
        try:
            query = session.query(Prompt)

            if name_pattern:
                query = query.filter(Prompt.prompt_name.like(f"%{name_pattern}%"))

            if namespace:
                query = query.filter(Prompt.namespace == namespace)

            if active_only:
                query = query.filter(Prompt.is_active == True)

            return query.order_by(desc(Prompt.updated_at)).all()
        finally:
            if not self._session:
                session.close()

    def get_prompt_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas dos prompts."""
        session = self._get_session()
        try:
            total_prompts = session.query(Prompt).count()
            active_prompts = session.query(Prompt).filter(Prompt.is_active == True).count()
            namespaces = session.query(Prompt.namespace).distinct().count()

            return {
                "total_prompts": total_prompts,
                "active_prompts": active_prompts,
                "namespaces": namespaces,
                "inactive_prompts": total_prompts - active_prompts
            }
        finally:
            if not self._session:
                session.close()
