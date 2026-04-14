from __future__ import annotations

from typing import Any

from qdrant_client import models

from app.core.embeddings.embedding_manager import aembed_text
from app.db.vector_store import (
    aget_or_create_collection,
    async_count_points,
    build_user_chat_collection_name,
    build_user_docs_collection_name,
    build_user_memory_collection_name,
    get_async_qdrant_client,
)


class QdrantKnowledgeAdapter:
    async def search_documents(
        self,
        *,
        query: str,
        user_id: str,
        doc_id: str | None,
        knowledge_space_id: str | None,
        limit: int,
        min_score: float | None,
        collection_suffix: str | None = None,
    ) -> list[dict[str, Any]]:
        vec = await aembed_text(query)
        client = get_async_qdrant_client()
        base_collection = build_user_docs_collection_name(user_id)
        if collection_suffix:
            base_collection = f"{base_collection}{collection_suffix}"
        collection_name = await aget_or_create_collection(base_collection)
        must: list[models.FieldCondition] = [
            models.FieldCondition(key="metadata.type", match=models.MatchValue(value="doc_chunk"))
        ]
        if doc_id:
            must.append(
                models.FieldCondition(key="metadata.doc_id", match=models.MatchValue(value=doc_id))
            )
        if knowledge_space_id:
            must.append(
                models.FieldCondition(
                    key="metadata.knowledge_space_id",
                    match=models.MatchValue(value=knowledge_space_id),
                )
            )
        res = await client.query_points(
            collection_name=collection_name,
            query=vec,
            limit=limit,
            with_payload=True,
            query_filter=models.Filter(must=must),
            score_threshold=min_score if isinstance(min_score, float) else None,
        )
        points = getattr(res, "points", res) or []
        results: list[dict[str, Any]] = []
        for point in points:
            payload = point.payload or {}
            meta = payload.get("metadata", {})
            results.append(
                {
                    "id": point.id,
                    "score": point.score,
                    "doc_id": meta.get("doc_id"),
                    "file_name": meta.get("file_name"),
                    "index": meta.get("index"),
                    "timestamp": meta.get("timestamp"),
                    "knowledge_space_id": meta.get("knowledge_space_id"),
                    "section_title": meta.get("section_title"),
                }
            )
        return results

    async def delete_document(self, *, doc_id: str, user_id: str) -> None:
        client = get_async_qdrant_client()
        coll = await aget_or_create_collection(build_user_docs_collection_name(user_id))
        qfilter = models.Filter(
            must=[
                models.FieldCondition(key="metadata.type", match=models.MatchValue(value="doc_chunk")),
                models.FieldCondition(key="metadata.doc_id", match=models.MatchValue(value=doc_id)),
            ]
        )
        await client.delete(collection_name=coll, points_selector=models.FilterSelector(filter=qfilter))

    async def get_document_points(self, *, doc_id: str, user_id: str, limit: int = 10) -> tuple[list[Any], int]:
        client = get_async_qdrant_client()
        coll = await aget_or_create_collection(build_user_docs_collection_name(user_id))
        qfilter = models.Filter(
            must=[models.FieldCondition(key="metadata.doc_id", match=models.MatchValue(value=doc_id))]
        )
        res = await client.query_points(
            collection_name=coll,
            query=[0.0] * 1536,
            limit=limit,
            with_payload=True,
            query_filter=qfilter,
        )
        points = list(getattr(res, "points", res) or [])
        total = await async_count_points(client, coll, qfilter, exact=True)
        return points, total

    async def search_user_chat(
        self,
        *,
        query: str,
        user_id: str,
        session_id: str | None,
        role: str | None,
        limit: int,
        min_score: float | None,
        start_ts: int | None = None,
        end_ts: int | None = None,
        exclude_duplicate: bool = False,
    ) -> list[Any]:
        collection_name = await aget_or_create_collection(build_user_chat_collection_name(user_id))
        vec = await aembed_text(query)
        must: list[models.FieldCondition] = []
        if session_id:
            must.append(
                models.FieldCondition(key="metadata.session_id", match=models.MatchValue(value=session_id))
            )
        if role:
            must.append(models.FieldCondition(key="metadata.role", match=models.MatchValue(value=role)))
        if start_ts is not None or end_ts is not None:
            bounds: dict[str, int] = {}
            if start_ts is not None:
                bounds["gte"] = start_ts
            if end_ts is not None:
                bounds["lte"] = end_ts
            must.append(models.FieldCondition(key="metadata.timestamp", range=models.Range(**bounds)))
        must_not = None
        if exclude_duplicate:
            must_not = [
                models.FieldCondition(
                    key="metadata.status", match=models.MatchValue(value="duplicate")
                )
            ]
        client = get_async_qdrant_client()
        res = await client.query_points(
            collection_name=collection_name,
            query=vec,
            limit=limit,
            with_payload=True,
            query_filter=models.Filter(must=must, must_not=must_not) if (must or must_not) else None,
            score_threshold=min_score if isinstance(min_score, float) else None,
        )
        return list(getattr(res, "points", res) or [])

    async def search_user_memory(
        self,
        *,
        query: str,
        user_id: str,
        limit: int,
        min_score: float | None,
        memory_type: str | None = None,
        origin: str | None = None,
        exclude_duplicate: bool = False,
    ) -> list[Any]:
        coll = await aget_or_create_collection(build_user_memory_collection_name(user_id))
        vec = await aembed_text(query)
        must: list[models.FieldCondition] = []
        if memory_type:
            must.append(models.FieldCondition(key="metadata.type", match=models.MatchValue(value=memory_type)))
        if origin:
            must.append(models.FieldCondition(key="metadata.origin", match=models.MatchValue(value=origin)))
        must_not = None
        if exclude_duplicate:
            must_not = [
                models.FieldCondition(
                    key="metadata.status", match=models.MatchValue(value="duplicate")
                )
            ]
        client = get_async_qdrant_client()
        res = await client.query_points(
            collection_name=coll,
            query=vec,
            limit=limit,
            with_payload=True,
            query_filter=models.Filter(must=must, must_not=must_not) if (must or must_not) else None,
            score_threshold=min_score if isinstance(min_score, float) else None,
        )
        return list(getattr(res, "points", res) or [])

    async def index_memory_event(
        self,
        *,
        user_id: str,
        content: str,
        point_id: str,
        payload: dict[str, Any],
    ) -> None:
        client = get_async_qdrant_client()
        coll = await aget_or_create_collection(build_user_memory_collection_name(user_id))
        vec = await aembed_text(content)
        point = models.PointStruct(id=point_id, vector=vec, payload=payload)
        await client.upsert(collection_name=coll, points=[point])

    async def load_user_timeline_points(
        self,
        *,
        user_id: str,
        conversation_id: str | None,
        query: str | None,
        start_ts: int | None,
        end_ts: int | None,
        limit: int,
    ) -> list[Any]:
        client = get_async_qdrant_client()
        vector = await aembed_text(query) if query else None
        points: list[Any] = []
        for collection_name in (
            build_user_memory_collection_name(user_id),
            build_user_chat_collection_name(user_id),
            build_user_docs_collection_name(user_id),
        ):
            coll = await aget_or_create_collection(collection_name)
            must: list[models.FieldCondition] = []
            if start_ts is not None or end_ts is not None:
                must.append(
                    models.FieldCondition(key="metadata.timestamp", range=models.Range(gte=start_ts, lte=end_ts))
                )
            qfilter = models.Filter(must=must) if must else None
            if vector is not None:
                res = await client.query_points(
                    collection_name=coll,
                    query=vector,
                    limit=limit,
                    with_payload=True,
                    query_filter=qfilter,
                )
                coll_points = list(getattr(res, "points", res) or [])
            else:
                coll_points, _ = await client.scroll(
                    collection_name=coll,
                    scroll_filter=qfilter,
                    limit=limit,
                    with_payload=True,
                )
            if conversation_id:
                coll_points = [
                    point
                    for point in coll_points
                    if _matches_conversation_scope(point, conversation_id)
                ]
            points.extend(coll_points)
        return points


class GraphKnowledgeAdapter:
    async def health_snapshot(self, service: Any) -> dict[str, Any]:
        return await service.get_health_status()


def _matches_conversation_scope(point: Any, conversation_id: str) -> bool:
    payload = getattr(point, "payload", None) or {}
    metadata = payload.get("metadata") or {}
    target = str(conversation_id or "").strip()
    if not target:
        return True
    candidates = [
        metadata.get("conversation_id"),
        metadata.get("session_id"),
        metadata.get("thread_id"),
        metadata.get("task_id"),
        payload.get("composite_id"),
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        value = str(candidate).strip()
        if value == target:
            return True
        if candidate == payload.get("composite_id"):
            parts = [part.strip() for part in value.replace("/", ":").replace("|", ":").split(":")]
            if target in [part for part in parts if part]:
                return True
    return False
