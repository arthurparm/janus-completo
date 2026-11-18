from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from app.db import db
from app.db.graph import get_graph_db
from app.db.vector_store import (
    aget_or_create_collection,
    build_user_chat_collection_name,
    build_user_docs_collection_name,
    build_user_secret_collection_name,
    delete_points_by_filter,
    delete_points_by_ids,
    get_async_qdrant_client,
    get_user_collection_names,
)
from app.models.user_models import Message
from app.models.user_models import Session as ChatSession
from app.repositories.data_governance_repository import DataGovernanceRepository
from app.repositories.document_manifest_repository import DocumentManifestRepository
from app.repositories.observability_repository import record_audit_event_direct
from qdrant_client import models as qdrant_models

logger = structlog.get_logger(__name__)


class DataPurgeServiceError(Exception):
    pass


class DataPurgeService:
    def __init__(
        self,
        *,
        gov_repo: DataGovernanceRepository | None = None,
        manifest_repo: DocumentManifestRepository | None = None,
    ):
        self._gov_repo = gov_repo or DataGovernanceRepository()
        self._manifest_repo = manifest_repo or DocumentManifestRepository()

    @staticmethod
    def _job_id() -> str:
        return uuid.uuid4().hex

    @staticmethod
    def _cleanup_storage_path(storage_path: str | None) -> bool:
        if not storage_path:
            return False
        try:
            path = Path(str(storage_path))
            if path.exists():
                path.unlink()
            parent = path.parent
            while parent != parent.parent and parent.exists():
                try:
                    parent.rmdir()
                except OSError:
                    break
                parent = parent.parent
            return True
        except Exception:
            return False

    async def run_expired_purge(self, *, limit: int = 250) -> dict[str, Any]:
        job_id = self._job_id()
        now = datetime.now(timezone.utc)
        counters: dict[str, int] = {
            "records_scanned": 0,
            "records_purged": 0,
            "postgres_deleted_sessions": 0,
            "postgres_deleted_messages": 0,
            "postgres_deleted_document_manifests": 0,
            "qdrant_deleted_chat_points": 0,
            "qdrant_deleted_doc_points": 0,
            "qdrant_deleted_memory_points": 0,
            "qdrant_deactivated_secrets": 0,
            "neo4j_deleted_expired": 0,
            "errors": 0,
        }

        record_audit_event_direct(
            user_id=None,
            endpoint="data_purge",
            action="purge_run_start",
            tool="data_purge",
            status="started",
            details_json={"job_id": job_id, "now": now.isoformat(), "limit": int(limit)},
        )

        expired = self._gov_repo.list_expired(now=now, limit=limit)
        counters["records_scanned"] = len(expired)

        for item in expired:
            try:
                await self._purge_one(item=item, job_id=job_id, counters=counters)
                self._gov_repo.mark_purged(record_id=int(item.id), purge_job_id=job_id, purged_at=now)
                counters["records_purged"] += 1
            except Exception as exc:
                counters["errors"] += 1
                record_audit_event_direct(
                    user_id=item.user_id,
                    endpoint="data_purge",
                    action="purge_item_failed",
                    tool="data_purge",
                    status="error",
                    details_json={
                        "job_id": job_id,
                        "record_id": int(item.id),
                        "resource_type": item.resource_type,
                        "resource_id": item.resource_id,
                        "error": str(exc),
                    },
                )

        counters["neo4j_deleted_expired"] += await self._purge_expired_neo4j(job_id=job_id)

        record_audit_event_direct(
            user_id=None,
            endpoint="data_purge",
            action="purge_run_end",
            tool="data_purge",
            status="completed" if counters["errors"] == 0 else "completed_with_errors",
            details_json={"job_id": job_id, "counters": counters},
        )
        return {"job_id": job_id, "counters": counters}

    async def _purge_one(self, *, item: Any, job_id: str, counters: dict[str, int]) -> None:
        resource_type = str(getattr(item, "resource_type", "") or "")
        resource_id = str(getattr(item, "resource_id", "") or "")

        if resource_type == "chat_session":
            deleted = self._delete_chat_session(session_id=resource_id)
            counters["postgres_deleted_sessions"] += int(deleted)
            await self._delete_chat_points(session_id=resource_id)
            record_audit_event_direct(
                user_id=item.user_id,
                endpoint="data_purge",
                action="purge_chat_session",
                tool="data_purge",
                status="success",
                details_json={"job_id": job_id, "session_id": resource_id},
            )
            return

        if resource_type == "chat_message":
            deleted = self._delete_chat_message(message_id=resource_id)
            counters["postgres_deleted_messages"] += int(deleted)
            record_audit_event_direct(
                user_id=item.user_id,
                endpoint="data_purge",
                action="purge_chat_message",
                tool="data_purge",
                status="success",
                details_json={"job_id": job_id, "message_id": resource_id},
            )
            return

        if resource_type == "document_manifest":
            ok = await self._purge_document(doc_id=resource_id, user_id=item.user_id)
            counters["postgres_deleted_document_manifests"] += 1 if ok else 0
            record_audit_event_direct(
                user_id=item.user_id,
                endpoint="data_purge",
                action="purge_document",
                tool="data_purge",
                status="success" if ok else "skipped",
                details_json={"job_id": job_id, "doc_id": resource_id},
            )
            return

        if resource_type == "knowledge_space":
            ok = await self._purge_knowledge_space(
                knowledge_space_id=resource_id,
                user_id=item.user_id,
            )
            record_audit_event_direct(
                user_id=item.user_id,
                endpoint="data_purge",
                action="purge_knowledge_space",
                tool="data_purge",
                status="success" if ok else "skipped",
                details_json={"job_id": job_id, "knowledge_space_id": resource_id},
            )
            return

        if resource_type == "memory_point":
            await self._delete_memory_point(point_id=resource_id)
            counters["qdrant_deleted_memory_points"] += 1
            record_audit_event_direct(
                user_id=item.user_id,
                endpoint="data_purge",
                action="purge_memory_point",
                tool="data_purge",
                status="success",
                details_json={"job_id": job_id, "point_id": resource_id},
            )
            return

        if resource_type == "secret":
            changed = await self._deactivate_secret(item=item)
            counters["qdrant_deactivated_secrets"] += 1 if changed else 0
            record_audit_event_direct(
                user_id=item.user_id,
                endpoint="data_purge",
                action="purge_secret",
                tool="data_purge",
                status="success" if changed else "skipped",
                details_json={"job_id": job_id, "secret_id": resource_id},
            )
            return

        raise DataPurgeServiceError(f"resource_type não suportado: {resource_type}")

    def _delete_chat_session(self, *, session_id: str) -> bool:
        s = db.get_session_direct()
        try:
            row = s.query(ChatSession).filter(ChatSession.id == int(session_id)).first()
            if row is None:
                return False
            s.delete(row)
            s.commit()
            return True
        finally:
            s.close()

    def _delete_chat_message(self, *, message_id: str) -> bool:
        s = db.get_session_direct()
        try:
            row = s.query(Message).filter(Message.id == int(message_id)).first()
            if row is None:
                return False
            s.delete(row)
            s.commit()
            return True
        finally:
            s.close()

    async def _delete_chat_points(self, *, session_id: str) -> None:
        collection_name = await aget_or_create_collection(build_user_chat_collection_name())
        await delete_points_by_filter(collection_name=collection_name, filter_conditions={"metadata.session_id": str(session_id)})

    async def _delete_memory_point(self, *, point_id: str) -> None:
        collection_name = await aget_or_create_collection(build_user_chat_collection_name())
        await delete_points_by_ids(collection_name=collection_name, point_ids=[str(point_id)])

    async def _purge_document(self, *, doc_id: str, user_id: int | None) -> bool:
        manifest = None
        if user_id is not None:
            manifest = self._manifest_repo.get_manifest(doc_id, str(user_id))
        if manifest is None:
            manifest = self._manifest_repo.get_manifest(doc_id)
        if manifest is None:
            return False

        storage_path = str(manifest.get("storage_path") or "")
        collection_name = await aget_or_create_collection(build_user_docs_collection_name("system"))
        await delete_points_by_filter(
            collection_name=collection_name,
            filter_conditions={"metadata.user_id": "system", "metadata.doc_id": str(doc_id)},
        )
        self._cleanup_storage_path(storage_path)
        self._manifest_repo.delete_manifest(str(doc_id))
        return True

    async def _purge_knowledge_space(self, *, knowledge_space_id: str, user_id: int | None) -> bool:
        ks_id = str(knowledge_space_id)
        if not ks_id:
            return False

        try:
            base_collections = set(get_user_collection_names().values())
            episodic_collection = "janus_episodic_memory"
            try:
                from app.config import settings

                episodic_collection = str(
                    getattr(settings, "QDRANT_COLLECTION_EPISODIC", episodic_collection)
                )
            except Exception:
                episodic_collection = "janus_episodic_memory"
            target_collections = sorted({*base_collections, episodic_collection})
            for col in target_collections:
                try:
                    await delete_points_by_filter(
                        collection_name=col,
                        filter_conditions={"metadata.knowledge_space_id": ks_id},
                    )
                except Exception:
                    continue
        except Exception:
            pass

        try:
            graph = await get_graph_db()
            await graph.execute(
                "MATCH (ks:KnowledgeSpace {id: $knowledge_space_id}) DETACH DELETE ks",
                params={"knowledge_space_id": ks_id},
                operation="purge_knowledge_space_root",
            )
            await graph.execute(
                "MATCH (n) WHERE n.knowledge_space_id = $knowledge_space_id DETACH DELETE n",
                params={"knowledge_space_id": ks_id},
                operation="purge_knowledge_space_nodes",
            )
        except Exception:
            pass

        try:
            s = db.get_session_direct()
            try:
                from app.models.knowledge_space_models import KnowledgeSpace

                q = s.query(KnowledgeSpace).filter(KnowledgeSpace.knowledge_space_id == ks_id)
                if user_id is not None:
                    q = q.filter(KnowledgeSpace.user_id == str(user_id))
                row = q.first()
                if row is not None:
                    s.delete(row)
                    s.commit()
            finally:
                s.close()
        except Exception:
            pass

        return True

    async def _deactivate_secret(self, *, item: Any) -> bool:
        user_id = getattr(item, "user_id", None)
        metadata = getattr(item, "metadata_json", None) or {}
        secret_label = metadata.get("secret_label")
        secret_type = metadata.get("secret_type")
        if user_id is None or not secret_label or not secret_type:
            return False

        collection_name = await aget_or_create_collection(build_user_secret_collection_name(str(user_id)))
        client = get_async_qdrant_client()
        qfilter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="metadata.owner_user_id",
                    match=qdrant_models.MatchValue(value=str(user_id)),
                ),
                qdrant_models.FieldCondition(
                    key="metadata.secret_label",
                    match=qdrant_models.MatchValue(value=str(secret_label)),
                ),
                qdrant_models.FieldCondition(
                    key="metadata.secret_type",
                    match=qdrant_models.MatchValue(value=str(secret_type)),
                ),
            ]
        )
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        points, _next = await client.scroll(
            collection_name=collection_name,
            scroll_filter=qfilter,
            limit=50,
            with_payload=True,
            with_vectors=False,
        )
        changed = False
        for point in points or []:
            pid = str(getattr(point, "id", "") or "")
            payload = getattr(point, "payload", {}) or {}
            metadata_payload = dict((payload or {}).get("metadata") or {})
            if metadata_payload.get("active") is False:
                continue
            metadata_payload["active"] = False
            metadata_payload["purged_at"] = now_ms
            await client.set_payload(
                collection_name=collection_name,
                payload={"metadata": metadata_payload},
                points=[pid],
            )
            changed = True
        return changed

    async def _purge_expired_neo4j(self, *, job_id: str) -> int:
        try:
            g = await get_graph_db()
            rows = await g.query(
                "MATCH (n) WHERE exists(n.valid_to) AND datetime(n.valid_to) < datetime() RETURN count(n) AS total",
                operation="purge_neo4j_count_expired",
            )
            total = int((rows[0].get("total") if rows else 0) or 0)
            if total <= 0:
                return 0
            await g.execute(
                "MATCH (n) WHERE exists(n.valid_to) AND datetime(n.valid_to) < datetime() DETACH DELETE n",
                operation="purge_neo4j_delete_expired",
            )
            record_audit_event_direct(
                user_id=None,
                endpoint="data_purge",
                action="purge_neo4j_expired",
                tool="data_purge",
                status="success",
                details_json={"job_id": job_id, "deleted": total},
            )
            return total
        except Exception as exc:
            record_audit_event_direct(
                user_id=None,
                endpoint="data_purge",
                action="purge_neo4j_expired_failed",
                tool="data_purge",
                status="error",
                details_json={"job_id": job_id, "error": str(exc)},
            )
            return 0


data_purge_service = DataPurgeService()
