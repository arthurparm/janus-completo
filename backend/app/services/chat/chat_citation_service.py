from __future__ import annotations

import re
from typing import Any

from qdrant_client import models

from app.core.embeddings.embedding_manager import aembed_text
from app.db.vector_store import (
    aget_or_create_collection,
    build_user_docs_collection_name,
    get_async_qdrant_client,
)

MANDATORY_CITATION_GUARD_TEXT = (
    "Nao encontrei citacoes rastreaveis para essa resposta de documento/codigo. "
    "Envie mais contexto (arquivo, funcao ou documento) para eu responder com fonte."
)

_CITATION_REQUIRED_PATTERNS = (
    r"\bcodigo\b",
    r"\bcode\b",
    r"\bfuncao\b",
    r"\bfunction\b",
    r"\bclasse\b",
    r"\bclass\b",
    r"\barquivo\b",
    r"\bfile\b",
    r"\bdocumentacao\b",
    r"\bdocumentation\b",
    r"\bdocs?\b",
    r"\breadme\b",
    r"\bapi\b",
    r"\bendpoint\b",
    r"\.py\b",
    r"\.ts\b",
    r"\.js\b",
)

_UPLOADED_MATERIAL_PATTERNS = (
    r"\barquivo\b",
    r"\banexo\b",
    r"\bdocumento\b",
    r"\bupload\b",
    r"\benviei\b",
    r"\bmandei\b",
    r"\bte mandei\b",
    r"\battachment\b",
    r"\battached\b",
    r"\bsent\b",
)


def requires_mandatory_citations(message: str) -> bool:
    text = (message or "").lower()
    return any(re.search(pattern, text) for pattern in _CITATION_REQUIRED_PATTERNS)


def references_uploaded_material(message: str) -> bool:
    text = (message or "").lower()
    return any(re.search(pattern, text) for pattern in _UPLOADED_MATERIAL_PATTERNS)


def map_citation_hits(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    for item in items:
        meta = item.get("metadata") or {}
        payload = item.get("payload") or {}
        content = item.get("content") or payload.get("content") or item.get("page_content")
        line_start = (
            meta.get("line_start")
            or meta.get("start_line")
            or meta.get("line")
            or meta.get("line_no")
        )
        line_end = meta.get("line_end") or meta.get("end_line")
        source_type = meta.get("source_type") or meta.get("type") or "unknown"
        citations.append(
            {
                "id": item.get("id"),
                "title": meta.get("title"),
                "url": meta.get("url"),
                "doc_id": meta.get("doc_id"),
                "file_path": meta.get("file_path"),
                "source_type": source_type,
                # Legacy compat for frontend already reading `type`
                "type": source_type,
                "origin": meta.get("origin"),
                "line_start": line_start,
                "line_end": line_end,
                "line": line_start,
                "score": item.get("score"),
                "snippet": content,
            }
        )
    return citations


def build_citation_status(
    *,
    message: str,
    citations: list[dict[str, Any]],
    retrieval_failed: bool = False,
) -> dict[str, Any]:
    required = requires_mandatory_citations(message)
    mode = "required" if required else "optional"
    if retrieval_failed:
        return {
            "mode": mode,
            "status": "retrieval_failed",
            "count": len(citations),
            "reason": "retrieval_error",
        }
    if citations:
        return {
            "mode": mode,
            "status": "present",
            "count": len(citations),
            "reason": None,
        }
    if required:
        return {
            "mode": mode,
            "status": "missing_required",
            "count": 0,
            "reason": "no_retrievable_sources",
        }
    return {
        "mode": mode,
        "status": "not_applicable",
        "count": 0,
        "reason": None,
    }


def _dedupe_citations(citations: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    merged: list[dict[str, Any]] = []
    for citation in citations:
        key = (
            citation.get("doc_id"),
            citation.get("file_path"),
            citation.get("url"),
            citation.get("title"),
            citation.get("line_start"),
            citation.get("snippet"),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(citation)
        if len(merged) >= limit:
            break
    return merged


def _map_document_hits(points: list[Any]) -> list[dict[str, Any]]:
    mapped_hits: list[dict[str, Any]] = []
    for point in points:
        payload = getattr(point, "payload", {}) or {}
        metadata = dict(payload.get("metadata") or {})
        file_name = str(metadata.get("file_name") or metadata.get("doc_id") or "Documento").strip()
        metadata.setdefault("title", file_name)
        metadata.setdefault("file_path", file_name)
        metadata.setdefault("source_type", "document")
        metadata.setdefault("type", "document")
        mapped_hits.append(
            {
                "id": getattr(point, "id", None),
                "score": float(getattr(point, "score", 0.0) or 0.0),
                "payload": payload,
                "metadata": metadata,
                "content": payload.get("content"),
            }
        )
    return map_citation_hits(mapped_hits)


async def _query_document_citations(
    *,
    message: str,
    user_id: str,
    conversation_id: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    client = get_async_qdrant_client()
    collection_name = await aget_or_create_collection(build_user_docs_collection_name(str(user_id)))
    query = (message or "").strip() or "documento"
    vector = await aembed_text(query)
    must: list[models.FieldCondition] = [
        models.FieldCondition(key="metadata.type", match=models.MatchValue(value="doc_chunk")),
        models.FieldCondition(key="metadata.user_id", match=models.MatchValue(value=str(user_id))),
    ]
    if conversation_id:
        must.append(
            models.FieldCondition(
                key="metadata.conversation_id",
                match=models.MatchValue(value=str(conversation_id)),
            )
        )
    result = await client.query_points(
        collection_name=collection_name,
        query=vector,
        limit=limit,
        with_payload=True,
        query_filter=models.Filter(must=must),
    )
    points = getattr(result, "points", result) or []
    return _map_document_hits(list(points))


async def _recent_document_citations(
    *,
    user_id: str,
    conversation_id: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    client = get_async_qdrant_client()
    collection_name = await aget_or_create_collection(build_user_docs_collection_name(str(user_id)))
    must: list[models.FieldCondition] = [
        models.FieldCondition(key="metadata.type", match=models.MatchValue(value="doc_chunk")),
        models.FieldCondition(key="metadata.user_id", match=models.MatchValue(value=str(user_id))),
    ]
    if conversation_id:
        must.append(
            models.FieldCondition(
                key="metadata.conversation_id",
                match=models.MatchValue(value=str(conversation_id)),
            )
        )
    scroll_result = await client.scroll(
        collection_name=collection_name,
        scroll_filter=models.Filter(must=must),
        limit=max(limit * 4, limit),
        with_payload=True,
    )
    points = scroll_result[0] if isinstance(scroll_result, tuple) else (scroll_result or [])
    return _map_document_hits(list(points)[:limit])


async def collect_chat_citations(
    *,
    message: str,
    user_id: str | None,
    conversation_id: str | None,
    memory_service: Any | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    citations: list[dict[str, Any]] = []
    attempted_lookups = 0
    successful_lookups = 0

    if user_id:
        attempted_lookups += 1
        try:
            doc_citations = await _query_document_citations(
                message=message,
                user_id=str(user_id),
                conversation_id=conversation_id,
                limit=limit,
            )
            if not doc_citations and references_uploaded_material(message):
                doc_citations = await _recent_document_citations(
                    user_id=str(user_id),
                    conversation_id=conversation_id,
                    limit=limit,
                )
            citations.extend(doc_citations)
            successful_lookups += 1
        except Exception:
            pass

    if memory_service is not None:
        attempted_lookups += 1
        try:
            filters: dict[str, Any] = {"status_not": "duplicate"}
            if conversation_id:
                filters["metadata.session_id"] = conversation_id
            if user_id:
                filters["metadata.user_id"] = str(user_id)
            memory_hits = await memory_service.recall_filtered(
                query=message,
                filters=filters,
                limit=limit,
                min_score=0.1,
            )
            citations.extend(map_citation_hits(memory_hits))
            successful_lookups += 1
        except Exception:
            pass

    merged = _dedupe_citations(citations, limit=limit)
    return {
        "citations": merged,
        "retrieval_failed": bool(attempted_lookups and successful_lookups == 0 and not merged),
    }
