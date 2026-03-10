from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from app.db import db
from app.models.document_models import DocumentManifest


class DocumentManifestRepositoryError(Exception):
    pass


class DocumentManifestRepository:
    def create_manifest(
        self,
        *,
        doc_id: str,
        user_id: str,
        conversation_id: str | None,
        file_name: str,
        content_type: str | None,
        file_size_bytes: int = 0,
        status: str = "queued",
        storage_path: str | None = None,
    ) -> dict[str, Any]:
        session = db.get_session_direct()
        try:
            row = DocumentManifest(
                doc_id=doc_id,
                user_id=str(user_id),
                conversation_id=str(conversation_id) if conversation_id is not None else None,
                file_name=file_name,
                content_type=content_type,
                file_size_bytes=int(file_size_bytes or 0),
                status=status,
                storage_path=storage_path,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._serialize(row)
        except Exception as e:
            session.rollback()
            raise DocumentManifestRepositoryError(f"Falha ao criar manifesto: {e}") from e
        finally:
            session.close()

    def get_manifest(self, doc_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        session = db.get_session_direct()
        try:
            query = session.query(DocumentManifest).filter(DocumentManifest.doc_id == str(doc_id))
            if user_id is not None:
                query = query.filter(DocumentManifest.user_id == str(user_id))
            row = query.first()
            return self._serialize(row) if row is not None else None
        finally:
            session.close()

    def list_manifests(
        self,
        *,
        user_id: str,
        conversation_id: str | None = None,
        limit: int = 100,
        statuses: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        session = db.get_session_direct()
        try:
            query = session.query(DocumentManifest).filter(DocumentManifest.user_id == str(user_id))
            if conversation_id is not None:
                query = query.filter(DocumentManifest.conversation_id == str(conversation_id))
            if statuses:
                query = query.filter(DocumentManifest.status.in_([str(s) for s in statuses]))
            rows = (
                query.order_by(DocumentManifest.created_at.desc(), DocumentManifest.id.desc())
                .limit(max(1, int(limit)))
                .all()
            )
            return [self._serialize(row) for row in rows]
        finally:
            session.close()

    def update_manifest(self, doc_id: str, **fields: Any) -> dict[str, Any] | None:
        session = db.get_session_direct()
        try:
            row = session.query(DocumentManifest).filter(DocumentManifest.doc_id == str(doc_id)).first()
            if row is None:
                return None
            for key, value in fields.items():
                if not hasattr(row, key):
                    continue
                setattr(row, key, value)
            session.commit()
            session.refresh(row)
            return self._serialize(row)
        except Exception as e:
            session.rollback()
            raise DocumentManifestRepositoryError(f"Falha ao atualizar manifesto: {e}") from e
        finally:
            session.close()

    def delete_manifest(self, doc_id: str, user_id: str | None = None) -> bool:
        session = db.get_session_direct()
        try:
            query = session.query(DocumentManifest).filter(DocumentManifest.doc_id == str(doc_id))
            if user_id is not None:
                query = query.filter(DocumentManifest.user_id == str(user_id))
            row = query.first()
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise DocumentManifestRepositoryError(f"Falha ao excluir manifesto: {e}") from e
        finally:
            session.close()

    def mark_processing(self, doc_id: str) -> dict[str, Any] | None:
        return self.update_manifest(
            doc_id,
            status="processing",
            started_at=datetime.utcnow(),
            error_code=None,
            error_message=None,
        )

    def mark_completed(
        self,
        doc_id: str,
        *,
        chunks_total: int,
        chunks_indexed: int,
        semantic_doc_type: str | None,
        semantic_summary: str | None,
        semantic_confidence: float | None,
    ) -> dict[str, Any] | None:
        return self.update_manifest(
            doc_id,
            status="indexed",
            chunks_total=int(chunks_total),
            chunks_indexed=int(chunks_indexed),
            semantic_doc_type=semantic_doc_type,
            semantic_summary=semantic_summary,
            semantic_confidence=str(semantic_confidence) if semantic_confidence is not None else None,
            completed_at=datetime.utcnow(),
            error_code=None,
            error_message=None,
        )

    def mark_failed(
        self,
        doc_id: str,
        *,
        status: str,
        error_code: str | None = None,
        error_message: str | None = None,
        chunks_total: int | None = None,
        chunks_indexed: int | None = None,
        file_size_bytes: int | None = None,
    ) -> dict[str, Any] | None:
        fields: dict[str, Any] = {
            "status": status,
            "error_code": error_code,
            "error_message": error_message,
            "completed_at": datetime.utcnow(),
        }
        if chunks_total is not None:
            fields["chunks_total"] = int(chunks_total)
        if chunks_indexed is not None:
            fields["chunks_indexed"] = int(chunks_indexed)
        if file_size_bytes is not None:
            fields["file_size_bytes"] = int(file_size_bytes)
        return self.update_manifest(doc_id, **fields)

    def update_progress(
        self,
        doc_id: str,
        *,
        chunks_total: int,
        chunks_indexed: int,
        file_size_bytes: int | None = None,
        semantic_doc_type: str | None = None,
        semantic_summary: str | None = None,
        semantic_confidence: float | None = None,
    ) -> dict[str, Any] | None:
        fields: dict[str, Any] = {
            "chunks_total": int(chunks_total),
            "chunks_indexed": int(chunks_indexed),
        }
        if file_size_bytes is not None:
            fields["file_size_bytes"] = int(file_size_bytes)
        if semantic_doc_type is not None:
            fields["semantic_doc_type"] = semantic_doc_type
        if semantic_summary is not None:
            fields["semantic_summary"] = semantic_summary
        if semantic_confidence is not None:
            fields["semantic_confidence"] = str(semantic_confidence)
        return self.update_manifest(doc_id, **fields)

    def _serialize(self, row: DocumentManifest) -> dict[str, Any]:
        return {
            "id": int(row.id),
            "doc_id": str(row.doc_id),
            "user_id": str(row.user_id),
            "conversation_id": str(row.conversation_id) if row.conversation_id is not None else None,
            "file_name": row.file_name,
            "content_type": row.content_type,
            "file_size_bytes": int(row.file_size_bytes or 0),
            "status": row.status,
            "error_code": row.error_code,
            "error_message": row.error_message,
            "chunks_total": int(row.chunks_total or 0),
            "chunks_indexed": int(row.chunks_indexed or 0),
            "semantic_doc_type": row.semantic_doc_type,
            "semantic_summary": row.semantic_summary,
            "semantic_confidence": (
                float(row.semantic_confidence)
                if row.semantic_confidence not in (None, "")
                else None
            ),
            "storage_path": row.storage_path,
            "created_at": row.created_at.isoformat() if row.created_at is not None else None,
            "started_at": row.started_at.isoformat() if row.started_at is not None else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at is not None else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at is not None else None,
        }
