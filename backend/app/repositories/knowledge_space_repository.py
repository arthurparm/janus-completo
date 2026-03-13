from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from app.db import db
from app.models.knowledge_space_models import KnowledgeSpace


class KnowledgeSpaceRepositoryError(Exception):
    pass


class KnowledgeSpaceRepository:
    def create_space(
        self,
        *,
        knowledge_space_id: str,
        user_id: str,
        name: str,
        source_type: str,
        source_id: str | None = None,
        edition_or_version: str | None = None,
        language: str | None = None,
        parent_collection_id: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        session = db.get_session_direct()
        try:
            row = KnowledgeSpace(
                knowledge_space_id=str(knowledge_space_id),
                user_id=str(user_id),
                name=str(name),
                source_type=str(source_type or "documentation"),
                source_id=str(source_id) if source_id else None,
                edition_or_version=str(edition_or_version) if edition_or_version else None,
                language=str(language) if language else None,
                parent_collection_id=str(parent_collection_id) if parent_collection_id else None,
                description=description,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._serialize(row)
        except Exception as exc:
            session.rollback()
            raise KnowledgeSpaceRepositoryError(f"Falha ao criar knowledge space: {exc}") from exc
        finally:
            session.close()

    def get_space(self, knowledge_space_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        session = db.get_session_direct()
        try:
            query = session.query(KnowledgeSpace).filter(
                KnowledgeSpace.knowledge_space_id == str(knowledge_space_id)
            )
            if user_id is not None:
                query = query.filter(KnowledgeSpace.user_id == str(user_id))
            row = query.first()
            return self._serialize(row) if row is not None else None
        finally:
            session.close()

    def list_spaces(
        self,
        *,
        user_id: str,
        statuses: Iterable[str] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        session = db.get_session_direct()
        try:
            query = session.query(KnowledgeSpace).filter(KnowledgeSpace.user_id == str(user_id))
            if statuses:
                query = query.filter(KnowledgeSpace.consolidation_status.in_([str(item) for item in statuses]))
            rows = (
                query.order_by(KnowledgeSpace.updated_at.desc(), KnowledgeSpace.id.desc())
                .limit(max(1, int(limit)))
                .all()
            )
            return [self._serialize(row) for row in rows]
        finally:
            session.close()

    def update_space(self, knowledge_space_id: str, **fields: Any) -> dict[str, Any] | None:
        session = db.get_session_direct()
        try:
            row = session.query(KnowledgeSpace).filter(
                KnowledgeSpace.knowledge_space_id == str(knowledge_space_id)
            ).first()
            if row is None:
                return None
            for key, value in fields.items():
                if not hasattr(row, key):
                    continue
                setattr(row, key, value)
            session.commit()
            session.refresh(row)
            return self._serialize(row)
        except Exception as exc:
            session.rollback()
            raise KnowledgeSpaceRepositoryError(f"Falha ao atualizar knowledge space: {exc}") from exc
        finally:
            session.close()

    def mark_consolidation(
        self,
        knowledge_space_id: str,
        *,
        status: str,
        summary: str | None = None,
        last_consolidated_at: datetime | None = None,
    ) -> dict[str, Any] | None:
        fields: dict[str, Any] = {"consolidation_status": str(status)}
        if summary is not None:
            fields["consolidation_summary"] = summary
        if last_consolidated_at is not None:
            fields["last_consolidated_at"] = last_consolidated_at
        return self.update_space(knowledge_space_id, **fields)

    def _serialize(self, row: KnowledgeSpace) -> dict[str, Any]:
        return {
            "id": int(row.id),
            "knowledge_space_id": str(row.knowledge_space_id),
            "user_id": str(row.user_id),
            "name": row.name,
            "source_type": row.source_type,
            "source_id": row.source_id,
            "edition_or_version": row.edition_or_version,
            "language": row.language,
            "parent_collection_id": row.parent_collection_id,
            "description": row.description,
            "consolidation_status": row.consolidation_status,
            "consolidation_summary": row.consolidation_summary,
            "last_consolidated_at": (
                row.last_consolidated_at.isoformat() if row.last_consolidated_at is not None else None
            ),
            "created_at": row.created_at.isoformat() if row.created_at is not None else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at is not None else None,
        }
