from __future__ import annotations

from typing import Any

from app.api.v1.endpoints.chat.policies import requires_mandatory_citations


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

