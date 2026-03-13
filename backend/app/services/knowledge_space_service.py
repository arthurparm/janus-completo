from __future__ import annotations

import re
import time
from collections import Counter
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog
from fastapi import HTTPException, Request, status
from qdrant_client import models

from app.core.embeddings.embedding_manager import aembed_text, aembed_texts
from app.db.graph import get_graph_db
from app.db.vector_store import (
    aget_or_create_collection,
    build_deterministic_point_id,
    build_user_docs_collection_name,
    get_async_qdrant_client,
)
from app.repositories.document_manifest_repository import DocumentManifestRepository
from app.repositories.knowledge_space_repository import KnowledgeSpaceRepository

logger = structlog.get_logger(__name__)

_SOURCE_TYPES = {"book", "manual", "course", "collection", "documentation"}
_QUERY_MODES = {"auto", "quick_lookup", "canonical_answer"}
_SPACE_READY_STATUSES = {"ready", "partial"}
_STOPWORDS = {
    "a",
    "ao",
    "aos",
    "as",
    "com",
    "como",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "entre",
    "for",
    "from",
    "na",
    "nas",
    "no",
    "nos",
    "o",
    "os",
    "ou",
    "para",
    "por",
    "que",
    "se",
    "sem",
    "sobre",
    "the",
    "to",
    "um",
    "uma",
}

_HEADING_KEYWORDS = {
    "anexo",
    "apendice",
    "apêndice",
    "apresentacao",
    "apresentação",
    "ameaças",
    "ameacas",
    "capitulo",
    "capítulo",
    "classes",
    "conceitos",
    "conclusao",
    "conclusão",
    "creditos",
    "créditos",
    "distincoes",
    "distinções",
    "equipamento",
    "exemplos",
    "exercicios",
    "exercícios",
    "glossario",
    "glossário",
    "indice",
    "índice",
    "introducao",
    "introdução",
    "magia",
    "metodologia",
    "objetivos",
    "origens",
    "parte",
    "pericias",
    "perícias",
    "poderes",
    "prefacio",
    "prefácio",
    "racas",
    "raças",
    "referencias",
    "referências",
    "recompensas",
    "regras",
    "resumo",
    "secao",
    "seção",
    "sumario",
    "sumário",
    "tesouro",
}


class KnowledgeSpaceService:
    def __init__(
        self,
        *,
        manifest_repo: DocumentManifestRepository | None = None,
        space_repo: KnowledgeSpaceRepository | None = None,
    ) -> None:
        self._manifest_repo = manifest_repo or DocumentManifestRepository()
        self._space_repo = space_repo or KnowledgeSpaceRepository()

    def build_space_id(self, user_id: str) -> str:
        return f"ks:{user_id}:{uuid4().hex}"

    def create_space(
        self,
        *,
        user_id: str,
        name: str,
        source_type: str = "documentation",
        source_id: str | None = None,
        edition_or_version: str | None = None,
        language: str | None = None,
        parent_collection_id: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        normalized_source_type = str(source_type or "documentation").strip().lower()
        if normalized_source_type not in _SOURCE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"source_type inválido: {normalized_source_type}",
            )
        return self._space_repo.create_space(
            knowledge_space_id=self.build_space_id(user_id),
            user_id=str(user_id),
            name=str(name or "").strip() or "Knowledge Space",
            source_type=normalized_source_type,
            source_id=source_id,
            edition_or_version=edition_or_version,
            language=language,
            parent_collection_id=parent_collection_id,
            description=description,
        )

    def list_spaces(self, *, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        return self._space_repo.list_spaces(user_id=str(user_id), limit=limit)

    def get_space(self, *, knowledge_space_id: str, user_id: str) -> dict[str, Any]:
        row = self._space_repo.get_space(knowledge_space_id=str(knowledge_space_id), user_id=str(user_id))
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="knowledge_space não encontrado")
        return row

    def get_space_status(self, *, knowledge_space_id: str, user_id: str) -> dict[str, Any]:
        space = self.get_space(knowledge_space_id=knowledge_space_id, user_id=user_id)
        manifests = self._manifest_repo.list_manifests(
            user_id=str(user_id),
            knowledge_space_id=str(knowledge_space_id),
            limit=500,
        )
        total = len(manifests)
        indexed = sum(1 for item in manifests if str(item.get("status") or "") == "indexed")
        processing = sum(1 for item in manifests if str(item.get("status") or "") == "processing")
        queued = sum(1 for item in manifests if str(item.get("status") or "") == "queued")
        failed = sum(
            1
            for item in manifests
            if str(item.get("status") or "") not in {"indexed", "processing", "queued"}
        )
        chunks_total = sum(int(item.get("chunks_total") or 0) for item in manifests)
        chunks_indexed = sum(int(item.get("chunks_indexed") or 0) for item in manifests)
        progress = 0.0
        if chunks_total > 0:
            progress = round(min(1.0, chunks_indexed / max(1, chunks_total)), 4)
        elif total > 0:
            progress = round(indexed / max(1, total), 4)
        return {
            **space,
            "documents_total": total,
            "documents_indexed": indexed,
            "documents_processing": processing,
            "documents_queued": queued,
            "documents_failed": failed,
            "chunks_total": chunks_total,
            "chunks_indexed": chunks_indexed,
            "progress": progress,
        }

    def mark_consolidation_requested(self, *, knowledge_space_id: str, user_id: str) -> dict[str, Any]:
        self.get_space(knowledge_space_id=knowledge_space_id, user_id=user_id)
        return self._space_repo.mark_consolidation(
            knowledge_space_id,
            status="processing",
            summary="Consolidação estrutural publicada para processamento assíncrono.",
        )

    async def attach_document(
        self,
        *,
        knowledge_space_id: str,
        doc_id: str,
        user_id: str,
        source_type: str | None = None,
        source_id: str | None = None,
        edition_or_version: str | None = None,
        language: str | None = None,
        parent_collection_id: str | None = None,
    ) -> dict[str, Any]:
        space = self.get_space(knowledge_space_id=knowledge_space_id, user_id=user_id)
        manifest = self._manifest_repo.get_manifest(doc_id, user_id)
        if manifest is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="documento não encontrado")

        scope_payload = self._build_scope_payload(
            knowledge_space_id=knowledge_space_id,
            source_type=source_type or space.get("source_type"),
            source_id=source_id or space.get("source_id"),
            edition_or_version=edition_or_version or space.get("edition_or_version"),
            language=language or space.get("language"),
            parent_collection_id=parent_collection_id or space.get("parent_collection_id"),
        )
        updated = self._manifest_repo.update_manifest(doc_id, **scope_payload)
        await self._sync_doc_scope_payload(user_id=str(user_id), doc_id=str(doc_id), scope_payload=scope_payload)
        return updated or manifest

    async def consolidate_space(
        self,
        *,
        knowledge_space_id: str,
        user_id: str,
        limit_docs: int = 20,
    ) -> dict[str, Any]:
        space = self.get_space(knowledge_space_id=knowledge_space_id, user_id=user_id)
        self._space_repo.mark_consolidation(
            knowledge_space_id,
            status="processing",
            summary="Consolidação estrutural em andamento.",
        )
        manifests = self._manifest_repo.list_manifests(
            user_id=str(user_id),
            knowledge_space_id=str(knowledge_space_id),
            limit=max(1, int(limit_docs)),
            statuses=["indexed"],
        )
        if not manifests:
            self._space_repo.mark_consolidation(
                knowledge_space_id,
                status="empty",
                summary="Nenhum documento indexado associado a este knowledge space.",
            )
            return {
                "knowledge_space_id": knowledge_space_id,
                "status": "empty",
                "documents_total": 0,
                "sections_total": 0,
                "canonical_points_indexed": 0,
            }

        sections: list[dict[str, Any]] = []
        documents_processed = 0
        for manifest in manifests:
            points = await self._load_document_points(
                user_id=str(user_id),
                doc_id=str(manifest["doc_id"]),
                knowledge_space_id=str(knowledge_space_id),
            )
            if not points:
                continue
            documents_processed += 1
            ordered_chunks = sorted(
                points,
                key=lambda item: int(((item.get("metadata") or {}).get("index") or 0)),
            )
            text = "\n".join(
                str(item.get("content") or "").strip() for item in ordered_chunks if str(item.get("content") or "").strip()
            ).strip()
            if not text:
                continue
            sections.extend(
                self._build_structured_sections(
                    text=text,
                    manifest=manifest,
                    knowledge_space=space,
                )
            )

        canonical_points = await self._index_canonical_sections(
            user_id=str(user_id),
            knowledge_space=space,
            sections=sections,
        )
        await self._persist_structure_graph(
            user_id=str(user_id),
            knowledge_space=space,
            manifests=manifests,
            sections=sections,
        )

        summary = self._build_consolidation_summary(space=space, manifests=manifests, sections=sections)
        status_value = "ready" if sections else "partial"
        self._space_repo.mark_consolidation(
            knowledge_space_id,
            status=status_value,
            summary=summary,
            last_consolidated_at=datetime.now(UTC),
        )
        return {
            "knowledge_space_id": knowledge_space_id,
            "status": status_value,
            "documents_total": int(documents_processed),
            "sections_total": int(len(sections)),
            "canonical_points_indexed": int(canonical_points),
            "summary": summary,
        }

    async def query_space(
        self,
        *,
        knowledge_space_id: str,
        user_id: str,
        question: str,
        mode: str = "auto",
        limit: int = 5,
    ) -> dict[str, Any]:
        normalized_mode = str(mode or "auto").strip().lower()
        if normalized_mode not in _QUERY_MODES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="mode inválido")

        space = self.get_space(knowledge_space_id=knowledge_space_id, user_id=user_id)
        manifests = self._manifest_repo.list_manifests(
            user_id=str(user_id),
            knowledge_space_id=str(knowledge_space_id),
            limit=200,
        )
        gaps_or_conflicts = self._detect_scope_conflicts(space=space, manifests=manifests)

        if normalized_mode in {"auto", "canonical_answer"} and str(space.get("consolidation_status") or "") in _SPACE_READY_STATUSES:
            canonical = await self._query_canonical(
                knowledge_space=space,
                user_id=str(user_id),
                question=question,
                limit=limit,
            )
            if canonical.get("citations"):
                canonical["gaps_or_conflicts"] = [*gaps_or_conflicts, *canonical.get("gaps_or_conflicts", [])]
                return canonical
            gaps_or_conflicts.append("Nenhuma evidência consolidada recuperável; fallback para chunks.")

        quick = await self._query_quick_lookup(
            knowledge_space=space,
            user_id=str(user_id),
            question=question,
            limit=limit,
        )
        quick["gaps_or_conflicts"] = [*gaps_or_conflicts, *quick.get("gaps_or_conflicts", [])]
        return quick

    def _build_scope_payload(
        self,
        *,
        knowledge_space_id: str | None,
        source_type: str | None,
        source_id: str | None,
        edition_or_version: str | None,
        language: str | None,
        parent_collection_id: str | None,
    ) -> dict[str, Any]:
        normalized_source_type = str(source_type or "documentation").strip().lower()
        if normalized_source_type not in _SOURCE_TYPES:
            normalized_source_type = "documentation"
        return {
            "knowledge_space_id": str(knowledge_space_id) if knowledge_space_id else None,
            "source_type": normalized_source_type,
            "source_id": str(source_id) if source_id else None,
            "edition_or_version": str(edition_or_version) if edition_or_version else None,
            "language": str(language) if language else None,
            "parent_collection_id": str(parent_collection_id) if parent_collection_id else None,
        }

    async def _sync_doc_scope_payload(
        self,
        *,
        user_id: str,
        doc_id: str,
        scope_payload: dict[str, Any],
    ) -> None:
        client = get_async_qdrant_client()
        collection_name = await aget_or_create_collection(build_user_docs_collection_name(user_id))
        points = await self._scroll_points(
            collection_name=collection_name,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(key="metadata.user_id", match=models.MatchValue(value=str(user_id))),
                    models.FieldCondition(key="metadata.doc_id", match=models.MatchValue(value=str(doc_id))),
                ]
            ),
        )
        for point in points:
            payload = getattr(point, "payload", {}) or {}
            metadata = dict(payload.get("metadata") or {})
            metadata.update({k: v for k, v in scope_payload.items() if v is not None})
            point_id = getattr(point, "id", None)
            if point_id is None:
                continue
            await client.set_payload(
                collection_name=collection_name,
                payload={"metadata": metadata},
                points=[point_id],
            )

    async def _load_document_points(
        self,
        *,
        user_id: str,
        doc_id: str,
        knowledge_space_id: str,
    ) -> list[dict[str, Any]]:
        client = get_async_qdrant_client()
        collection_name = await aget_or_create_collection(build_user_docs_collection_name(user_id))
        points = await self._scroll_points(
            collection_name=collection_name,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(key="metadata.type", match=models.MatchValue(value="doc_chunk")),
                    models.FieldCondition(key="metadata.user_id", match=models.MatchValue(value=str(user_id))),
                    models.FieldCondition(key="metadata.doc_id", match=models.MatchValue(value=str(doc_id))),
                    models.FieldCondition(
                        key="metadata.knowledge_space_id",
                        match=models.MatchValue(value=str(knowledge_space_id)),
                    ),
                ]
            ),
        )
        out: list[dict[str, Any]] = []
        for point in points:
            payload = getattr(point, "payload", {}) or {}
            out.append(
                {
                    "id": getattr(point, "id", None),
                    "content": payload.get("content"),
                    "metadata": payload.get("metadata") or {},
                }
            )
        return out

    def _build_structured_sections(
        self,
        *,
        text: str,
        manifest: dict[str, Any],
        knowledge_space: dict[str, Any],
    ) -> list[dict[str, Any]]:
        lines = [line.strip() for line in str(text or "").splitlines()]
        sections: list[dict[str, Any]] = []
        current_title = "Visão Geral"
        current_lines: list[str] = []
        order = 0

        def flush() -> None:
            nonlocal order, current_lines, current_title
            body = "\n".join(item for item in current_lines if item).strip()
            if not body:
                return
            normalized_title = self._normalize_heading_title(current_title)
            if sections and str(sections[-1]["title"]).strip() == normalized_title:
                merged_body = f"{sections[-1]['body']}\n{body}".strip()
                sections[-1]["body"] = merged_body
                sections[-1]["summary"] = self._summarize_text(merged_body)
                sections[-1]["concepts"] = self._extract_concepts(merged_body, title=normalized_title)
                current_lines = []
                return
            order += 1
            section_key = build_deterministic_point_id(
                "knowledge-section",
                knowledge_space.get("knowledge_space_id"),
                manifest.get("doc_id"),
                order,
                normalized_title,
            )
            sections.append(
                {
                    "section_id": section_key,
                    "doc_id": manifest.get("doc_id"),
                    "file_name": manifest.get("file_name"),
                    "knowledge_space_id": knowledge_space.get("knowledge_space_id"),
                    "title": normalized_title,
                    "order": order,
                    "body": body,
                    "summary": self._summarize_text(body),
                    "concepts": self._extract_concepts(body, title=normalized_title),
                }
            )
            current_lines = []

        for line in lines:
            if not line:
                continue
            if self._is_heading(line):
                normalized_heading = self._normalize_heading_title(line)
                if normalized_heading == self._normalize_heading_title(current_title) and not current_lines:
                    continue
                flush()
                current_title = normalized_heading
                continue
            current_lines.append(line)
        flush()

        if sections:
            return sections
        fallback_summary = self._summarize_text(text)
        return [
            {
                "section_id": build_deterministic_point_id(
                    "knowledge-section",
                    knowledge_space.get("knowledge_space_id"),
                    manifest.get("doc_id"),
                    1,
                    "Visão Geral",
                ),
                "doc_id": manifest.get("doc_id"),
                "file_name": manifest.get("file_name"),
                "knowledge_space_id": knowledge_space.get("knowledge_space_id"),
                "title": "Visão Geral",
                "order": 1,
                "body": text,
                "summary": fallback_summary,
                "concepts": self._extract_concepts(text, title="Visão Geral"),
            }
        ]

    def _is_heading(self, line: str) -> bool:
        normalized = str(line or "").strip()
        if len(normalized) < 4 or len(normalized) > 90:
            return False
        if re.search(r"\.{2,}", normalized):
            return False
        if "," in normalized:
            return False
        numeric_match = re.match(r"^(\d+(?:\.\d+)*)\.?\s+(.+)$", normalized)
        if numeric_match:
            remainder = str(numeric_match.group(2) or "").strip()
            if len(remainder) > 80:
                return False
            if remainder.count(".") > 1:
                return False
            return True
        if normalized.endswith(":"):
            tokens = [token for token in normalized[:-1].split() if token]
            if not tokens or len(tokens) > 6:
                return False
            first_token = self._normalize_heading_token(tokens[0])
            if first_token in _HEADING_KEYWORDS:
                return True
            if normalized[:-1].isupper() and not re.search(r"\d", normalized):
                return True
            return tokens[0][:1].isupper()
        if re.search(r"[.!?;]", normalized):
            return False
        if re.search(r"\b(?:https?://|www\.)", normalized, flags=re.IGNORECASE):
            return False
        if re.search(r"(?:R\$|T\$|\$)\s*\d", normalized):
            return False
        if normalized.isupper() and len(normalized.split()) <= 6 and not re.search(r"\d", normalized):
            return True
        letters = re.sub(r"[^A-Za-zÀ-ÿ0-9 -]", "", normalized)
        tokens = [token for token in letters.split() if token]
        if not tokens or len(tokens) > 6:
            return False
        if self._normalize_heading_token(tokens[0]) in _HEADING_KEYWORDS:
            return True
        if any(re.search(r"\d", token) for token in tokens):
            return False
        return False

    def _normalize_heading_title(self, line: str) -> str:
        return re.sub(r"\s+", " ", str(line or "").strip().rstrip(":")).strip()

    def _normalize_heading_token(self, token: str) -> str:
        return re.sub(r"[^A-Za-zÀ-ÿ]", "", str(token or "").strip()).lower()

    def _chunk_rows(self, rows: list[dict[str, Any]], *, batch_size: int) -> list[list[dict[str, Any]]]:
        if batch_size <= 0:
            return [rows]
        return [rows[index : index + batch_size] for index in range(0, len(rows), batch_size)]

    def _summarize_text(self, text: str, max_chars: int = 360) -> str:
        clean = re.sub(r"\s+", " ", str(text or "")).strip()
        if not clean:
            return ""
        sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", clean) if item.strip()]
        summary = " ".join(sentences[:2]).strip() if sentences else clean[:max_chars]
        if len(summary) > max_chars:
            summary = f"{summary[: max_chars - 3].rstrip()}..."
        return summary

    def _extract_concepts(self, text: str, *, title: str, limit: int = 6) -> list[str]:
        content = f"{title} {text}".lower()
        tokens = re.findall(r"[a-zà-ÿ][a-zà-ÿ0-9_-]{2,}", content)
        counts = Counter(token for token in tokens if token not in _STOPWORDS)
        return [item for item, _ in counts.most_common(limit)]

    async def _index_canonical_sections(
        self,
        *,
        user_id: str,
        knowledge_space: dict[str, Any],
        sections: list[dict[str, Any]],
    ) -> int:
        if not sections:
            return 0
        client = get_async_qdrant_client()
        collection_name = await aget_or_create_collection(build_user_docs_collection_name(user_id))
        await client.delete(
            collection_name=collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.type",
                            match=models.MatchValue(value="knowledge_canonical_summary"),
                        ),
                        models.FieldCondition(
                            key="metadata.user_id",
                            match=models.MatchValue(value=str(user_id)),
                        ),
                        models.FieldCondition(
                            key="metadata.knowledge_space_id",
                            match=models.MatchValue(value=str(knowledge_space["knowledge_space_id"])),
                        ),
                    ]
                )
            ),
        )
        texts = [f"{item['title']}\n{item['summary']}\n{' '.join(item['concepts'])}" for item in sections]
        vectors = await aembed_texts(texts)
        points: list[models.PointStruct] = []
        now_ms = int(time.time() * 1000)
        for section, vector in zip(sections, vectors, strict=False):
            payload = {
                "type": "knowledge_canonical_summary",
                "ts_ms": now_ms,
                "content": section["summary"],
                "metadata": {
                    "type": "knowledge_canonical_summary",
                    "user_id": str(user_id),
                    "knowledge_space_id": str(knowledge_space["knowledge_space_id"]),
                    "doc_id": str(section["doc_id"]),
                    "file_name": section["file_name"],
                    "section_id": section["section_id"],
                    "section_title": section["title"],
                    "section_order": int(section["order"]),
                    "concepts": section["concepts"],
                    "source_type": "document",
                    "origin": "knowledge_space.consolidation",
                    "timestamp": now_ms,
                },
            }
            points.append(
                models.PointStruct(
                    id=build_deterministic_point_id(
                        "knowledge-canonical-summary",
                        knowledge_space["knowledge_space_id"],
                        section["section_id"],
                    ),
                    vector=vector,
                    payload=payload,
                )
            )
        await client.upsert(collection_name=collection_name, points=points)
        return len(points)

    async def _persist_structure_graph(
        self,
        *,
        user_id: str,
        knowledge_space: dict[str, Any],
        manifests: list[dict[str, Any]],
        sections: list[dict[str, Any]],
    ) -> None:
        graph = await get_graph_db()
        await graph.execute(
            """
            MERGE (ks:KnowledgeSpace {id: $knowledge_space_id})
            SET ks.user_id = $user_id,
                ks.name = $name,
                ks.source_type = $source_type,
                ks.source_id = $source_id,
                ks.edition_or_version = $edition_or_version,
                ks.language = $language,
                ks.parent_collection_id = $parent_collection_id,
                ks.updated_at = timestamp()
            """,
            {
                "knowledge_space_id": str(knowledge_space["knowledge_space_id"]),
                "user_id": str(user_id),
                "name": knowledge_space.get("name"),
                "source_type": knowledge_space.get("source_type"),
                "source_id": knowledge_space.get("source_id"),
                "edition_or_version": knowledge_space.get("edition_or_version"),
                "language": knowledge_space.get("language"),
                "parent_collection_id": knowledge_space.get("parent_collection_id"),
            },
            operation="knowledge_space_graph_root",
        )
        work_rows = [
            {
                "doc_id": str(manifest["doc_id"]),
                "file_name": manifest.get("file_name"),
                "user_id": str(user_id),
                "source_type": manifest.get("source_type"),
                "source_id": manifest.get("source_id"),
                "edition_or_version": manifest.get("edition_or_version"),
                "language": manifest.get("language"),
            }
            for manifest in manifests
        ]
        if work_rows:
            await graph.execute(
                """
                MATCH (ks:KnowledgeSpace {id: $knowledge_space_id})
                UNWIND $works AS work
                MERGE (w:Work {doc_id: work.doc_id})
                SET w.file_name = work.file_name,
                    w.user_id = work.user_id,
                    w.source_type = work.source_type,
                    w.source_id = work.source_id,
                    w.edition_or_version = work.edition_or_version,
                    w.language = work.language,
                    w.updated_at = timestamp()
                MERGE (ks)-[:CONTAINS]->(w)
                """,
                {
                    "knowledge_space_id": str(knowledge_space["knowledge_space_id"]),
                    "works": work_rows,
                },
                operation="knowledge_space_graph_work_batch",
            )
        grouped: dict[str, list[dict[str, Any]]] = {}
        section_rows: list[dict[str, Any]] = []
        concept_rows: list[dict[str, Any]] = []
        for section in sections:
            grouped.setdefault(str(section["doc_id"]), []).append(section)
            section_rows.append(
                {
                    "doc_id": str(section["doc_id"]),
                    "section_id": str(section["section_id"]),
                    "knowledge_space_id": str(section["knowledge_space_id"]),
                    "title": section["title"],
                    "summary": section["summary"],
                    "order": int(section["order"]),
                    "summary_id": build_deterministic_point_id(
                        "graph-summary",
                        section["knowledge_space_id"],
                        section["section_id"],
                    ),
                }
            )
            for concept in section["concepts"]:
                concept_rows.append({"section_id": str(section["section_id"]), "concept": concept})
        for batch in self._chunk_rows(section_rows, batch_size=100):
            await graph.execute(
                """
                UNWIND $sections AS section
                MATCH (w:Work {doc_id: section.doc_id})
                MERGE (s:Section {section_id: section.section_id})
                SET s.knowledge_space_id = section.knowledge_space_id,
                    s.title = section.title,
                    s.summary = section.summary,
                    s.order = section.order,
                    s.updated_at = timestamp()
                MERGE (w)-[:CONTAINS]->(s)
                MERGE (cs:CanonicalSummary {summary_id: section.summary_id})
                SET cs.body = section.summary,
                    cs.updated_at = timestamp()
                MERGE (s)-[:SUPPORTED_BY]->(cs)
                """,
                {"sections": batch},
                operation="knowledge_space_graph_section_batch",
            )
        for batch in self._chunk_rows(concept_rows, batch_size=250):
            await graph.execute(
                """
                UNWIND $concepts AS item
                MATCH (s:Section {section_id: item.section_id})
                MERGE (c:Concept {name: item.concept})
                SET c.updated_at = timestamp()
                MERGE (s)-[:DEFINES]->(c)
                """,
                {"concepts": batch},
                operation="knowledge_space_graph_concept_batch",
            )
        for doc_id, rows in grouped.items():
            ordered = sorted(rows, key=lambda item: int(item["order"]))
            sequence_rows = [
                {
                    "previous_id": str(previous["section_id"]),
                    "current_id": str(current["section_id"]),
                }
                for previous, current in zip(ordered, ordered[1:], strict=False)
            ]
            for batch in self._chunk_rows(sequence_rows, batch_size=250):
                await graph.execute(
                    """
                    UNWIND $links AS link
                    MATCH (a:Section {section_id: link.previous_id})
                    MATCH (b:Section {section_id: link.current_id})
                    MERGE (a)-[:NEXT_SECTION]->(b)
                    """,
                    {"links": batch},
                    operation="knowledge_space_graph_sequence_batch",
                )

    def _build_consolidation_summary(
        self,
        *,
        space: dict[str, Any],
        manifests: list[dict[str, Any]],
        sections: list[dict[str, Any]],
    ) -> str:
        titles = [str(item["title"]).strip() for item in sections[:3] if str(item["title"]).strip()]
        docs = [str(item.get("file_name") or item.get("doc_id") or "").strip() for item in manifests[:3]]
        return (
            f"Espaço '{space['name']}' consolidado com {len(manifests)} documento(s) "
            f"e {len(sections)} seção(ões). "
            f"Documentos: {', '.join(item for item in docs if item)}. "
            f"Seções-chave: {', '.join(item for item in titles if item) or 'visão geral'}."
        ).strip()

    def _detect_scope_conflicts(self, *, space: dict[str, Any], manifests: list[dict[str, Any]]) -> list[str]:
        conflicts: list[str] = []
        editions = sorted(
            {
                str(item.get("edition_or_version") or "").strip()
                for item in manifests
                if str(item.get("edition_or_version") or "").strip()
            }
        )
        if len(editions) > 1:
            conflicts.append(f"Múltiplas edições/versões associadas ao espaço: {', '.join(editions)}.")
        if space.get("parent_collection_id"):
            conflicts.append("Espaço vinculado a coleção; respostas podem depender da ordem declarada dos volumes.")
        return conflicts

    async def _query_canonical(
        self,
        *,
        knowledge_space: dict[str, Any],
        user_id: str,
        question: str,
        limit: int,
    ) -> dict[str, Any]:
        client = get_async_qdrant_client()
        collection_name = await aget_or_create_collection(build_user_docs_collection_name(user_id))
        vector = await aembed_text(question)
        result = await client.query_points(
            collection_name=collection_name,
            query=vector,
            limit=max(1, int(limit)),
            with_payload=True,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.type",
                        match=models.MatchValue(value="knowledge_canonical_summary"),
                    ),
                    models.FieldCondition(
                        key="metadata.user_id",
                        match=models.MatchValue(value=str(user_id)),
                    ),
                    models.FieldCondition(
                        key="metadata.knowledge_space_id",
                        match=models.MatchValue(value=str(knowledge_space["knowledge_space_id"])),
                    ),
                ]
            ),
        )
        points = list(getattr(result, "points", result) or [])
        citations = [self._map_citation(point, snippet_limit=320) for point in points]
        confidence = self._average_score(points)
        answer = self._render_canonical_answer(points)
        return {
            "answer": answer,
            "mode_used": "canonical_answer",
            "base_used": "consolidated",
            "source_scope": self._build_source_scope(knowledge_space),
            "citations": citations,
            "confidence": confidence,
            "gaps_or_conflicts": [] if citations else ["Nenhum summary canônico relevante foi recuperado."],
        }

    async def _query_quick_lookup(
        self,
        *,
        knowledge_space: dict[str, Any],
        user_id: str,
        question: str,
        limit: int,
    ) -> dict[str, Any]:
        client = get_async_qdrant_client()
        collection_name = await aget_or_create_collection(build_user_docs_collection_name(user_id))
        vector = await aembed_text(question)
        result = await client.query_points(
            collection_name=collection_name,
            query=vector,
            limit=max(1, int(limit)),
            with_payload=True,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(key="metadata.type", match=models.MatchValue(value="doc_chunk")),
                    models.FieldCondition(key="metadata.user_id", match=models.MatchValue(value=str(user_id))),
                    models.FieldCondition(
                        key="metadata.knowledge_space_id",
                        match=models.MatchValue(value=str(knowledge_space["knowledge_space_id"])),
                    ),
                ]
            ),
        )
        points = list(getattr(result, "points", result) or [])
        citations = [self._map_citation(point, snippet_limit=220) for point in points]
        return {
            "answer": self._render_quick_answer(points, knowledge_space=knowledge_space),
            "mode_used": "quick_lookup",
            "base_used": "chunk_only",
            "source_scope": self._build_source_scope(knowledge_space),
            "citations": citations,
            "confidence": self._average_score(points),
            "gaps_or_conflicts": [] if citations else ["Nenhum chunk relevante foi recuperado para a pergunta."],
        }

    def _build_source_scope(self, knowledge_space: dict[str, Any]) -> dict[str, Any]:
        return {
            "knowledge_space_id": knowledge_space.get("knowledge_space_id"),
            "name": knowledge_space.get("name"),
            "source_type": knowledge_space.get("source_type"),
            "source_id": knowledge_space.get("source_id"),
            "edition_or_version": knowledge_space.get("edition_or_version"),
            "language": knowledge_space.get("language"),
            "parent_collection_id": knowledge_space.get("parent_collection_id"),
            "consolidation_status": knowledge_space.get("consolidation_status"),
        }

    def _render_canonical_answer(self, points: list[Any]) -> str:
        if not points:
            return "A base consolidada ainda não possui evidência suficiente para responder com segurança."
        lines = ["Base consolidada indica:"]
        for point in points[:3]:
            payload = getattr(point, "payload", {}) or {}
            metadata = payload.get("metadata") or {}
            title = str(metadata.get("section_title") or metadata.get("file_name") or "Seção").strip()
            summary = re.sub(r"\s+", " ", str(payload.get("content") or "").strip())
            if not summary:
                continue
            lines.append(f"- {title}: {summary}")
        return "\n".join(lines)

    def _render_quick_answer(self, points: list[Any], *, knowledge_space: dict[str, Any]) -> str:
        if not points:
            return (
                f"Não encontrei trechos relevantes no knowledge space '{knowledge_space['name']}'. "
                "A resposta pode exigir consolidação estrutural."
            )
        lines = ["Trechos relevantes encontrados:"]
        for point in points[:3]:
            payload = getattr(point, "payload", {}) or {}
            snippet = re.sub(r"\s+", " ", str(payload.get("content") or "").strip())
            if not snippet:
                continue
            trimmed = snippet[:220].rstrip()
            if len(snippet) > 220:
                trimmed = f"{trimmed}..."
            lines.append(f"- {trimmed}")
        return "\n".join(lines)

    def _map_citation(self, point: Any, *, snippet_limit: int) -> dict[str, Any]:
        payload = getattr(point, "payload", {}) or {}
        metadata = payload.get("metadata") or {}
        snippet = re.sub(r"\s+", " ", str(payload.get("content") or "").strip())
        if len(snippet) > snippet_limit:
            snippet = f"{snippet[: snippet_limit - 3].rstrip()}..."
        return {
            "id": getattr(point, "id", None),
            "doc_id": metadata.get("doc_id"),
            "file_name": metadata.get("file_name"),
            "title": metadata.get("section_title") or metadata.get("file_name"),
            "file_path": metadata.get("file_name"),
            "section_id": metadata.get("section_id"),
            "section_title": metadata.get("section_title"),
            "index": metadata.get("index"),
            "score": float(getattr(point, "score", 0.0) or 0.0),
            "source_type": metadata.get("source_type") or "document",
            "snippet": snippet,
        }

    def _average_score(self, points: list[Any]) -> float:
        if not points:
            return 0.0
        values = [float(getattr(point, "score", 0.0) or 0.0) for point in points]
        return round(sum(values) / max(1, len(values)), 4)

    async def _scroll_points(
        self,
        *,
        collection_name: str,
        query_filter: models.Filter,
        batch_size: int = 128,
    ) -> list[Any]:
        client = get_async_qdrant_client()
        offset = None
        rows: list[Any] = []
        while True:
            points, offset = await client.scroll(
                collection_name=collection_name,
                scroll_filter=query_filter,
                limit=max(1, int(batch_size)),
                with_payload=True,
                offset=offset,
            )
            rows.extend(points or [])
            if offset is None:
                break
        return rows


def get_knowledge_space_service(request: Request) -> KnowledgeSpaceService:
    if not hasattr(request.app.state, "knowledge_space_service"):
        request.app.state.knowledge_space_service = KnowledgeSpaceService()
    return request.app.state.knowledge_space_service
