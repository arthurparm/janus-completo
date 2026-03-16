from __future__ import annotations

import asyncio
import os
import re
import time
import unicodedata
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog
from fastapi import HTTPException, Request, status
from qdrant_client import models

from app.core.agents.utils import parse_json_lenient
from app.core.embeddings.embedding_manager import aembed_text, aembed_texts
from app.core.llm import ModelPriority, ModelRole
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
_SPACE_READY_STATUSES = {"ready", "partial", "processing"}
_DOC_ROLES = {"base", "supplement", "reference", "appendix"}
_SECTION_ROLES = {
    "front_matter",
    "core_rules",
    "supplement_rules",
    "appendix",
    "optional_rules",
    "table_like",
    "noise",
}
_ANSWER_STRATEGIES = {"comparative", "sequence", "scope", "locator"}
_CANONICAL_POINT_TYPES = {
    "knowledge_canonical_summary",
    "knowledge_evidence_anchor",
    "knowledge_flow_step",
    "knowledge_comparison_frame",
}
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
_FRONT_MATTER_KEYWORDS = {
    "apresentacao",
    "apresentação",
    "creditos",
    "créditos",
    "introducao",
    "introdução",
    "prefacio",
    "prefácio",
    "sumario",
    "sumário",
}
_APPENDIX_KEYWORDS = {"anexo", "apendice", "apêndice", "glossario", "glossário", "indice", "índice"}
_OPTIONAL_KEYWORDS = {"opcional", "variacao", "variação", "alternativa", "extra", "avancado", "avançado"}
_SUPPLEMENT_KEYWORDS = {
    "suplemento",
    "expansao",
    "expansão",
    "complemento",
    "herois",
    "heróis",
    "atlas",
    "guia",
}
_REFERENCE_KEYWORDS = {"faq", "referencia", "referência", "resumo", "gm", "mestre", "screen"}
_NOISE_PATTERNS = (
    r"^p[aá]g(?:ina)?\.?\s*\d+$",
    r"^\d+$",
    r"^\d+\s*/\s*\d+$",
    r"^(?:todos os direitos reservados|impresso no brasil|copyright)\b",
    r"^isbn\b",
)
_GENERIC_HEADING_KEYWORDS = {
    "capitulo",
    "capítulo",
    "parte",
    "secao",
    "seção",
    "topico",
    "tópico",
    "visao",
    "visão",
    "geral",
}
_LOW_SIGNAL_QUERY_TOKENS = {"onde", "trecho", "pagina", "página", "secao", "seção", "capitulo", "capítulo"}
_MARKETING_KEYWORDS = {
    "seu jogo nunca foi",
    "centenas de combina",
    "instrucoes para mestres",
    "instruções para mestres",
    "historia e geografia de arton",
    "história e geografia de arton",
    "linha de tempo",
    "goblin de ouro",
}
_EDITORIAL_KEYWORDS = {
    "editor executivo",
    "editor senior",
    "editor sênior",
    "jambo editora",
    "romancista",
    "rpgista",
    "revista dragao brasil",
    "revista dragão brasil",
    "primeira producao audiovisual",
    "primeira produção audiovisual",
    "autor da trilogia",
    "a flecha de fogo",
    "leonel caldela",
}


class KnowledgeSpaceService:
    def __init__(
        self,
        *,
        manifest_repo: DocumentManifestRepository | None = None,
        space_repo: KnowledgeSpaceRepository | None = None,
        llm_service: Any | None = None,
    ) -> None:
        self._manifest_repo = manifest_repo or DocumentManifestRepository()
        self._space_repo = space_repo or KnowledgeSpaceRepository()
        self._llm = llm_service

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
        space = self._reconcile_ready_processing_space(
            knowledge_space=space,
            documents_processing=processing,
            documents_queued=queued,
        )
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
            "sections_total": int(space.get("sections_total") or 0),
            "sections_indexed": int(space.get("sections_indexed") or 0),
            "sections_skipped_as_noise": int(space.get("sections_skipped_as_noise") or 0),
            "canonical_frames_total": int(space.get("canonical_frames_total") or 0),
            "consolidation_quality_score": float(space.get("consolidation_quality_score") or 0.0),
        }

    def _reconcile_ready_processing_space(
        self,
        *,
        knowledge_space: dict[str, Any],
        documents_processing: int = 0,
        documents_queued: int = 0,
    ) -> dict[str, Any]:
        if str(knowledge_space.get("consolidation_status") or "") != "processing":
            return knowledge_space
        if int(knowledge_space.get("sections_indexed") or 0) <= 0:
            return knowledge_space
        if int(knowledge_space.get("canonical_frames_total") or 0) <= 0:
            return knowledge_space
        if int(documents_processing) > 0 or int(documents_queued) > 0:
            return knowledge_space
        reconciled = self._space_repo.mark_consolidation(
            str(knowledge_space["knowledge_space_id"]),
            status="ready",
            summary=(
                str(knowledge_space.get("consolidation_summary") or "").strip()
                or "Base canônica disponível."
            ),
            sections_total=int(knowledge_space.get("sections_total") or 0),
            sections_indexed=int(knowledge_space.get("sections_indexed") or 0),
            sections_skipped_as_noise=int(knowledge_space.get("sections_skipped_as_noise") or 0),
            canonical_frames_total=int(knowledge_space.get("canonical_frames_total") or 0),
            consolidation_quality_score=float(knowledge_space.get("consolidation_quality_score") or 0.0),
        )
        return reconciled or knowledge_space

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
        doc_role: str | None = None,
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
            doc_role=doc_role or manifest.get("doc_role") or self._infer_doc_role(manifest, space),
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
        skipped_sections = 0
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
            built_sections = self._build_structured_sections(
                points=ordered_chunks,
                manifest=manifest,
                knowledge_space=space,
            )
            sections.extend(built_sections)

        heuristic_sections, initial_skipped = self._finalize_sections(sections)
        skipped_sections += initial_skipped
        sections = await self._enrich_sections_with_llm(heuristic_sections, knowledge_space=space)
        sections, extra_skipped = self._finalize_sections(sections)
        skipped_sections += extra_skipped
        consolidation_metrics = self._build_consolidation_metrics(
            sections=sections,
            skipped_sections=skipped_sections,
        )

        canonical_points = await self._index_canonical_sections(
            user_id=str(user_id),
            knowledge_space=space,
            sections=sections,
        )
        summary = self._build_consolidation_summary(
            space=space,
            manifests=manifests,
            sections=sections,
            metrics=consolidation_metrics,
        )
        last_consolidated_at = datetime.now(UTC)
        status_value = "ready" if sections else "partial"
        self._space_repo.mark_consolidation(
            knowledge_space_id,
            status=status_value,
            summary=summary,
            last_consolidated_at=last_consolidated_at,
            sections_total=int(consolidation_metrics["sections_total"]),
            sections_indexed=int(consolidation_metrics["sections_indexed"]),
            sections_skipped_as_noise=int(consolidation_metrics["sections_skipped_as_noise"]),
            canonical_frames_total=int(consolidation_metrics["canonical_frames_total"]),
            consolidation_quality_score=str(consolidation_metrics["consolidation_quality_score"]),
        )
        try:
            await self._persist_structure_graph(
                user_id=str(user_id),
                knowledge_space=space,
                manifests=manifests,
                sections=sections,
            )
        except Exception as exc:
            logger.warning(
                "knowledge_space_graph_persist_failed",
                knowledge_space_id=str(knowledge_space_id),
                user_id=str(user_id),
                error=str(exc),
            )
            summary = f"{summary} Persistência de grafo ficou parcial: {exc}"
            self._space_repo.mark_consolidation(
                knowledge_space_id,
                status=status_value,
                summary=summary,
                last_consolidated_at=last_consolidated_at,
                sections_total=int(consolidation_metrics["sections_total"]),
                sections_indexed=int(consolidation_metrics["sections_indexed"]),
                sections_skipped_as_noise=int(consolidation_metrics["sections_skipped_as_noise"]),
                canonical_frames_total=int(consolidation_metrics["canonical_frames_total"]),
                consolidation_quality_score=str(consolidation_metrics["consolidation_quality_score"]),
            )
        return {
            "knowledge_space_id": knowledge_space_id,
            "status": status_value,
            "documents_total": int(documents_processed),
            "sections_total": int(consolidation_metrics["sections_total"]),
            "sections_indexed": int(consolidation_metrics["sections_indexed"]),
            "sections_skipped_as_noise": int(consolidation_metrics["sections_skipped_as_noise"]),
            "canonical_frames_total": int(consolidation_metrics["canonical_frames_total"]),
            "consolidation_quality_score": float(consolidation_metrics["consolidation_quality_score"]),
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
        active_manifests = self._manifest_repo.list_manifests(
            user_id=str(user_id),
            knowledge_space_id=str(knowledge_space_id),
            limit=200,
            statuses=["indexed"],
        )
        active_doc_ids = {
            str(item.get("doc_id") or "").strip()
            for item in active_manifests
            if str(item.get("doc_id") or "").strip()
        }
        gaps_or_conflicts = self._detect_scope_conflicts(space=space, manifests=manifests)
        prefer_locator = self._prefer_locator(question)
        canonical_timeout_seconds = float(
            os.getenv("KNOWLEDGE_SPACE_CANONICAL_TIMEOUT_SECONDS", "12") or 12
        )
        has_canonical_metrics = bool(
            int(space.get("canonical_frames_total") or 0) > 0
            or int(space.get("sections_indexed") or 0) > 0
        )

        if normalized_mode == "auto" and prefer_locator:
            quick = await self._query_quick_lookup(
                knowledge_space=space,
                user_id=str(user_id),
                question=question,
                limit=limit,
                active_doc_ids=active_doc_ids,
            )
            quick["gaps_or_conflicts"] = [*gaps_or_conflicts, *quick.get("gaps_or_conflicts", [])]
            return quick

        should_try_canonical = (
            normalized_mode == "canonical_answer"
            or (
                normalized_mode == "auto"
                and str(space.get("consolidation_status") or "") in _SPACE_READY_STATUSES
                and has_canonical_metrics
            )
        )
        if should_try_canonical:
            try:
                canonical = await asyncio.wait_for(
                    self._query_canonical(
                        knowledge_space=space,
                        user_id=str(user_id),
                        question=question,
                        limit=limit,
                        active_doc_ids=active_doc_ids,
                    ),
                    timeout=canonical_timeout_seconds,
                )
            except asyncio.TimeoutError:
                gaps_or_conflicts.append(
                    "Consulta canônica excedeu o tempo limite; fallback para chunks."
                )
            else:
                if canonical.get("citations"):
                    canonical["gaps_or_conflicts"] = [
                        *gaps_or_conflicts,
                        *canonical.get("gaps_or_conflicts", []),
                    ]
                    return canonical
                gaps_or_conflicts.append("Nenhuma evidência consolidada recuperável; fallback para chunks.")

        quick = await self._query_quick_lookup(
            knowledge_space=space,
            user_id=str(user_id),
            question=question,
            limit=limit,
            active_doc_ids=active_doc_ids,
        )
        quick["gaps_or_conflicts"] = [*gaps_or_conflicts, *quick.get("gaps_or_conflicts", [])]
        return quick

    def _build_scope_payload(
        self,
        *,
        knowledge_space_id: str | None,
        source_type: str | None,
        source_id: str | None,
        doc_role: str | None,
        edition_or_version: str | None,
        language: str | None,
        parent_collection_id: str | None,
    ) -> dict[str, Any]:
        normalized_source_type = str(source_type or "documentation").strip().lower()
        if normalized_source_type not in _SOURCE_TYPES:
            normalized_source_type = "documentation"
        normalized_doc_role = str(doc_role or "").strip().lower() or None
        if normalized_doc_role not in _DOC_ROLES:
            normalized_doc_role = None
        return {
            "knowledge_space_id": str(knowledge_space_id) if knowledge_space_id else None,
            "source_type": normalized_source_type,
            "source_id": str(source_id) if source_id else None,
            "doc_role": normalized_doc_role,
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
        text: str | None = None,
        points: list[dict[str, Any]] | None = None,
        manifest: dict[str, Any],
        knowledge_space: dict[str, Any],
    ) -> list[dict[str, Any]]:
        doc_role = self._infer_doc_role(manifest, knowledge_space)
        prepared_lines = self._prepare_document_lines(text=text, points=points)
        sections: list[dict[str, Any]] = []
        current_title = "Visão Geral"
        current_lines: list[str] = []
        current_chunk_ids: list[str] = []
        order = 0

        def flush() -> None:
            nonlocal order, current_lines, current_title, current_chunk_ids
            body = "\n".join(item for item in current_lines if item).strip()
            if not body:
                return
            normalized_title = self._normalize_heading_title(current_title)
            section_role = self._classify_section(
                title=normalized_title,
                body=body,
                doc_role=doc_role,
                order=order + 1,
            )
            applies_to = self._infer_applies_to(normalized_title, body, section_role=section_role)
            if sections and str(sections[-1]["title"]).strip() == normalized_title and sections[-1]["doc_role"] == doc_role:
                merged_body = f"{sections[-1]['body']}\n{body}".strip()
                sections[-1]["body"] = merged_body
                sections[-1]["summary"] = self._summarize_text(merged_body)
                sections[-1]["canonical_summary"] = self._summarize_text(merged_body, max_chars=440)
                sections[-1]["concepts"] = self._extract_concepts(merged_body, title=normalized_title)
                sections[-1]["applies_to"] = sorted(
                    set(sections[-1].get("applies_to") or []).union(applies_to)
                )
                sections[-1]["evidence_span_ids"] = sorted(
                    set(sections[-1].get("evidence_span_ids") or []).union(current_chunk_ids)
                )
                current_lines = []
                current_chunk_ids = []
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
                    "canonical_summary": self._summarize_text(body, max_chars=440),
                    "concepts": self._extract_concepts(body, title=normalized_title),
                    "doc_role": doc_role,
                    "section_role": section_role,
                    "applies_to": applies_to,
                    "is_optional_rule": bool(section_role == "optional_rules"),
                    "extends_or_overrides": self._infer_extends_or_overrides(normalized_title, body, doc_role),
                    "evidence_span_ids": sorted(set(current_chunk_ids)),
                    "body_excerpt": self._trim_text(body, max_chars=520),
                    "classification_source": "heuristic",
                }
            )
            current_lines = []
            current_chunk_ids = []

        for line in prepared_lines:
            line_text = str(line.get("text") or "").strip()
            chunk_id = str(line.get("chunk_id") or "").strip()
            if not line_text:
                continue
            if line.get("kind") == "heading":
                normalized_heading = self._normalize_heading_title(line_text)
                if normalized_heading == self._normalize_heading_title(current_title) and not current_lines:
                    continue
                flush()
                current_title = normalized_heading
                continue
            current_lines.append(line_text)
            if chunk_id:
                current_chunk_ids.append(chunk_id)
        flush()

        if sections:
            return sections
        fallback_text = str(text or "").strip()
        if not fallback_text and points:
            fallback_text = "\n".join(
                str(item.get("content") or "").strip() for item in points if str(item.get("content") or "").strip()
            ).strip()
        fallback_summary = self._summarize_text(fallback_text)
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
                "body": fallback_text,
                "summary": fallback_summary,
                "canonical_summary": self._summarize_text(fallback_text, max_chars=440),
                "concepts": self._extract_concepts(fallback_text, title="Visão Geral"),
                "doc_role": doc_role,
                "section_role": "core_rules",
                "applies_to": self._infer_applies_to("Visão Geral", fallback_text, section_role="core_rules"),
                "is_optional_rule": False,
                "extends_or_overrides": self._infer_extends_or_overrides("Visão Geral", fallback_text, doc_role),
                "evidence_span_ids": [
                    str(item.get("id"))
                    for item in (points or [])
                    if item.get("id") is not None
                ],
                "body_excerpt": self._trim_text(fallback_text, max_chars=520),
                "classification_source": "fallback",
            }
        ]

    def _prepare_document_lines(
        self,
        *,
        text: str | None,
        points: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        raw_entries: list[dict[str, Any]] = []
        if points:
            for point in points:
                chunk_id = point.get("id")
                chunk_text = self._clean_document_text(str(point.get("content") or ""))
                for line in chunk_text.splitlines():
                    raw_entries.append({"text": line.strip(), "chunk_id": chunk_id})
        else:
            for line in self._clean_document_text(str(text or "")).splitlines():
                raw_entries.append({"text": line.strip(), "chunk_id": None})

        repeated_candidates = Counter(
            self._normalize_line_key(item["text"])
            for item in raw_entries
            if self._is_repeated_noise_candidate(item["text"])
        )
        repeated_noise = {
            key
            for key, count in repeated_candidates.items()
            if key and count >= 4
        }

        prepared: list[dict[str, Any]] = []
        for item in raw_entries:
            line = self._normalize_inline_text(item["text"])
            if not line:
                continue
            line_key = self._normalize_line_key(line)
            if line_key in repeated_noise:
                continue
            if self._is_noise_line(line):
                continue
            if self._looks_like_table_line(line):
                continue
            prepared.append(
                {
                    "text": line,
                    "chunk_id": item.get("chunk_id"),
                    "kind": "heading" if self._is_heading(line) else "body",
                }
            )
        return prepared

    def _clean_document_text(self, text: str) -> str:
        normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
        normalized = re.sub(r"(\w)-\n(?=[a-zà-ÿ])", r"\1", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"[ \t]+\n", "\n", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized

    def _normalize_inline_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip()).strip()

    def _normalize_line_key(self, value: str) -> str:
        normalized = self._normalize_inline_text(value).casefold()
        normalized = re.sub(r"\d+", "#", normalized)
        return normalized

    def _is_repeated_noise_candidate(self, value: str) -> bool:
        line = self._normalize_inline_text(value)
        return 3 <= len(line) <= 80 and (line.isupper() or bool(re.search(r"\d", line)))

    def _is_noise_line(self, value: str) -> bool:
        line = self._normalize_inline_text(value)
        lowered = line.casefold()
        if not line:
            return True
        if any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in _NOISE_PATTERNS):
            return True
        if re.search(r"\.{4,}", line):
            return True
        if re.search(r"\b(?:sum[áa]rio|table of contents)\b.*\.{2,}", lowered):
            return True
        return False

    def _looks_like_table_line(self, value: str) -> bool:
        line = self._normalize_inline_text(value)
        if not line:
            return False
        if re.search(r"(?:\|\s*){2,}", line):
            return True
        if re.search(r"(?:R\$|T\$|\$)\s*[\d.,]+", line) and len(line.split()) >= 4:
            return True
        tokens = line.split()
        numeric_tokens = sum(bool(re.search(r"[\d%$]", token)) for token in tokens)
        return len(tokens) >= 5 and numeric_tokens >= max(3, len(tokens) // 2)

    def _classify_section(
        self,
        title: str,
        body: str,
        *,
        doc_role: str,
        order: int,
    ) -> str:
        content = f"{title} {body}".casefold()
        title_key = self._normalize_heading_token(title)
        if order <= 2 and any(keyword in content for keyword in _FRONT_MATTER_KEYWORDS):
            return "front_matter"
        if title_key in _APPENDIX_KEYWORDS or any(keyword in content for keyword in _APPENDIX_KEYWORDS):
            return "appendix"
        if any(keyword in content for keyword in _OPTIONAL_KEYWORDS):
            return "optional_rules"
        if self._looks_like_table_line(body):
            return "table_like"
        if len(body.split()) < 15 and order > 2:
            return "noise"
        if doc_role == "supplement":
            return "supplement_rules"
        return "core_rules"

    def _infer_applies_to(self, title: str, body: str, *, section_role: str) -> list[str]:
        content = f"{title} {body}".casefold()
        applies_to: list[str] = []
        if any(token in content for token in ("personagem", "atribut", "classe", "raça", "raca", "origem", "perícia", "pericia")):
            applies_to.append("base_creation")
        if any(token in content for token in ("poder", "talento", "magia", "equipamento", "arma", "distin")):
            applies_to.append("character_options")
        if any(token in content for token in ("passo", "sequência", "sequencia", "etapa", "procedimento")):
            applies_to.append("workflow")
        if section_role == "optional_rules":
            applies_to.append("optional_rules")
        if not applies_to:
            applies_to.append("general_rules")
        return applies_to

    def _infer_extends_or_overrides(self, title: str, body: str, doc_role: str) -> str | None:
        content = f"{title} {body}".casefold()
        if any(token in content for token in ("substitui", "sobrescreve", "override", "em vez de")):
            return "overrides"
        if doc_role == "supplement" or any(token in content for token in ("adiciona", "novas opções", "novo poder", "complementa", "expande")):
            return "extends"
        return None

    def _infer_doc_role(self, manifest: dict[str, Any], knowledge_space: dict[str, Any]) -> str:
        explicit = str(manifest.get("doc_role") or "").strip().lower()
        if explicit in _DOC_ROLES:
            return explicit
        haystack = " ".join(
            str(value or "")
            for value in (
                manifest.get("file_name"),
                manifest.get("source_id"),
                manifest.get("source_type"),
                knowledge_space.get("name"),
            )
        ).casefold()
        if any(keyword in haystack for keyword in _APPENDIX_KEYWORDS):
            return "appendix"
        if any(keyword in haystack for keyword in _REFERENCE_KEYWORDS):
            return "reference"
        if any(keyword in haystack for keyword in _SUPPLEMENT_KEYWORDS):
            return "supplement"
        return "base"

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

    def _normalize_search_text(self, value: str) -> str:
        normalized = unicodedata.normalize("NFKD", str(value or ""))
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        normalized = normalized.casefold()
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _compact_search_text(self, value: str) -> str:
        return re.sub(r"\s+", "", self._normalize_search_text(value))

    def _tokenize_search_terms(self, value: str, *, min_len: int = 3) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9_-]{%d,}" % max(1, int(min_len)), self._normalize_search_text(value))
            if token not in _STOPWORDS and token not in _LOW_SIGNAL_QUERY_TOKENS
        }

    def _score_heading_quality(self, title: str) -> float:
        normalized = self._normalize_heading_title(title)
        searchable = self._normalize_search_text(normalized)
        tokens = [token for token in searchable.split() if token]
        if not tokens:
            return 0.0
        score = 0.18
        if len(tokens) <= 7:
            score += 0.18
        else:
            score -= 0.10
        if any(token in _HEADING_KEYWORDS for token in tokens):
            score += 0.22
        if re.match(r"^\d+(?:\.\d+)*\.?\s+", normalized):
            score += 0.18
        if normalized.isupper() and len(tokens) <= 6:
            score += 0.08
        if any(token in _GENERIC_HEADING_KEYWORDS for token in tokens) and len(set(tokens)) <= 2:
            score -= 0.25
        if re.search(r"[.!?;]", normalized):
            score -= 0.25
        if re.search(r"\.{2,}", normalized):
            score -= 0.20
        if sum(char.isdigit() for char in normalized) >= max(4, len(normalized) // 3):
            score -= 0.12
        return round(max(0.0, min(1.0, score)), 4)

    def _score_content_density(self, body: str) -> float:
        clean = re.sub(r"\s+", " ", str(body or "").strip())
        if not clean:
            return 0.0
        tokens = re.findall(r"[A-Za-zÀ-ÿ0-9_-]+", clean)
        if not tokens:
            return 0.0
        alpha_tokens = [token for token in tokens if re.search(r"[A-Za-zÀ-ÿ]", token)]
        unique_ratio = len(set(token.casefold() for token in alpha_tokens)) / max(1, len(alpha_tokens))
        alpha_ratio = len(alpha_tokens) / max(1, len(tokens))
        score = 0.12
        score += min(0.38, len(alpha_tokens) / 120)
        score += unique_ratio * 0.24
        score += alpha_ratio * 0.18
        if len(alpha_tokens) < 25:
            score -= 0.18
        if self._looks_like_table_line(clean):
            score -= 0.22
        if re.search(r"\.{4,}", clean):
            score -= 0.12
        return round(max(0.0, min(1.0, score)), 4)

    def _score_noise(self, *, title: str, body: str, section_role: str, order: int) -> float:
        searchable_title = self._normalize_search_text(title)
        searchable_body = self._normalize_search_text(body)
        score = 0.0
        if section_role == "noise":
            score += 0.62
        if section_role == "table_like":
            score += 0.48
        if section_role == "front_matter":
            score += 0.20
        if order <= 2 and any(keyword in searchable_title or keyword in searchable_body for keyword in _FRONT_MATTER_KEYWORDS):
            score += 0.18
        if len(body.split()) < 40:
            score += 0.16
        if any(keyword in searchable_title or keyword in searchable_body for keyword in _MARKETING_KEYWORDS):
            score += 0.40
        if self._looks_like_editorial_content(title=title, body=body):
            score += 0.48
        if re.search(r"\.{4,}", searchable_title) or re.search(r"\.{4,}", searchable_body):
            score += 0.20
        if any(re.search(pattern, searchable_title, flags=re.IGNORECASE) for pattern in _NOISE_PATTERNS):
            score += 0.22
        return round(max(0.0, min(1.0, score)), 4)

    def _looks_like_editorial_content(self, *, title: str, body: str) -> bool:
        searchable = self._normalize_search_text(f"{title} {body}")
        return any(keyword in searchable for keyword in _EDITORIAL_KEYWORDS)

    def _has_creation_foundation_signal(self, *, title: str, content: str, doc_role: str) -> bool:
        searchable = self._normalize_search_text(f"{title} {content}")
        if doc_role != "base":
            return False
        if any(
            token in searchable
            for token in (
                "criacao de personagem",
                "criação de personagem",
                "construção de personagens",
                "construcao de personagens",
                "capitulo um",
                "capítulo um",
            )
        ):
            return True
        creation_tokens = ("atribut", "raca", "raça", "classe", "origem", "personagem")
        return sum(1 for token in creation_tokens if token in searchable) >= 3

    def _apply_section_quality(self, section: dict[str, Any]) -> dict[str, Any]:
        heading_quality_score = self._score_heading_quality(str(section.get("title") or ""))
        content_density_score = self._score_content_density(str(section.get("body") or ""))
        noise_score = self._score_noise(
            title=str(section.get("title") or ""),
            body=str(section.get("body") or ""),
            section_role=str(section.get("section_role") or "core_rules"),
            order=int(section.get("order") or 0),
        )
        role_bonus = {
            "core_rules": 0.22,
            "supplement_rules": 0.18,
            "optional_rules": 0.07,
            "appendix": 0.02,
            "front_matter": -0.12,
            "table_like": -0.25,
            "noise": -0.32,
        }.get(str(section.get("section_role") or "core_rules"), 0.0)
        evidence_bonus = min(0.08, len(section.get("evidence_span_ids") or []) * 0.02)
        usefulness_score = (
            0.14
            + (heading_quality_score * 0.24)
            + (content_density_score * 0.34)
            + role_bonus
            + evidence_bonus
            - (noise_score * 0.42)
        )
        usefulness_score = round(max(0.0, min(1.0, usefulness_score)), 4)
        is_useful = (
            usefulness_score >= 0.42
            and noise_score < 0.70
            and str(section.get("section_role") or "") not in {"noise", "table_like", "front_matter"}
            and content_density_score >= 0.18
        )
        merged = dict(section)
        merged["heading_quality_score"] = heading_quality_score
        merged["content_density_score"] = content_density_score
        merged["noise_score"] = noise_score
        merged["usefulness_score"] = usefulness_score
        merged["is_useful"] = bool(is_useful)
        return merged

    def _finalize_sections(self, sections: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
        if not sections:
            return [], 0
        decorated = [self._apply_section_quality(section) for section in sections]
        useful = [section for section in decorated if section.get("is_useful")]
        if not useful:
            best = max(decorated, key=lambda item: float(item.get("usefulness_score") or 0.0))
            best["is_useful"] = True
            useful = [best]
        useful.sort(key=lambda item: int(item.get("order") or 0))
        return useful, max(0, len(decorated) - len(useful))

    def _build_query_profile(self, question: str) -> dict[str, Any]:
        lowered = self._normalize_search_text(question)
        terms = self._tokenize_search_terms(question)
        phrases = self._extract_query_phrases(question)
        explicit_locator = self._prefer_locator(question)
        asks_for_creation = any(
            token in lowered
            for token in (
                "criacao de personagem",
                "criação de personagem",
                "criar personagem",
                "construir personagem",
                "construcao de personagem",
                "construção de personagem",
                "ficha",
            )
        )
        asks_for_ordering = any(
            token in lowered
            for token in (
                "primeiro",
                "depois",
                "em que ponto",
                "em que etapa",
                "sequencia",
                "sequência",
                "passo",
                "ordem",
            )
        )
        asks_for_supplement = any(
            token in lowered
            for token in (
                "suplement",
                "herois",
                "herois de arton",
                "heróis de arton",
                "adiciona",
                "novas opcoes",
                "novas opções",
                "acrescenta",
                "amplia",
            )
        )
        asks_for_base = any(
            token in lowered for token in ("livro base", "regra principal", "nucleo", "núcleo", "jogo do ano")
        )
        source_hints = [
            hint
            for hint in ("herois de arton", "jogo do ano", "livro base")
            if hint in lowered
        ]
        source_terms = {
            token
            for hint in source_hints
            for token in self._tokenize_search_terms(hint, min_len=3)
        }
        topic_terms = {token for token in terms if token not in source_terms}
        topic_phrases = {
            phrase
            for phrase in phrases
            if not all(token in source_terms for token in self._tokenize_search_terms(phrase, min_len=3))
        }
        return {
            "normalized": lowered,
            "terms": terms,
            "topic_terms": topic_terms,
            "phrases": phrases,
            "topic_phrases": topic_phrases,
            "explicit_locator": explicit_locator,
            "asks_for_supplement": asks_for_supplement,
            "asks_for_base": asks_for_base,
            "asks_for_creation": asks_for_creation,
            "asks_for_ordering": asks_for_ordering,
            "asks_for_sequence": asks_for_creation or asks_for_ordering,
            "source_hints": source_hints,
            "source_terms": source_terms,
            "expects_exact_evidence": explicit_locator or any(token in lowered for token in ("onde", "trecho", "pagina", "página")),
        }

    def _extract_query_phrases(self, question: str) -> set[str]:
        normalized = self._normalize_search_text(question)
        tokens = [
            token
            for token in re.findall(r"[a-z0-9_-]{3,}", normalized)
            if token not in _STOPWORDS and token not in _LOW_SIGNAL_QUERY_TOKENS
        ]
        phrases: set[str] = set()
        for size in (3, 2):
            for index in range(0, max(0, len(tokens) - size + 1)):
                phrase = " ".join(tokens[index : index + size]).strip()
                if len(phrase) >= 8:
                    phrases.add(phrase)
        for explicit in (
            "herois de arton",
            "jogo do ano",
            "livro base",
            "criacao de personagem",
            "criar personagem",
            "novas racas",
            "novas opcoes",
        ):
            if explicit in normalized:
                phrases.add(explicit)
        return phrases

    def _trim_text(self, text: str | None, *, max_chars: int) -> str:
        normalized = re.sub(r"\s+", " ", str(text or "").strip())
        if len(normalized) <= max_chars:
            return normalized
        return f"{normalized[: max_chars - 3].rstrip()}..."

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

    async def _enrich_sections_with_llm(
        self,
        sections: list[dict[str, Any]],
        *,
        knowledge_space: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if not sections or self._llm is None:
            return sections
        max_sections = int(os.getenv("KNOWLEDGE_SPACE_LLM_SECTION_LIMIT", "18") or 18)
        overall_timeout = float(
            os.getenv("KNOWLEDGE_SPACE_LLM_ENRICH_TIMEOUT_SECONDS", "150") or 150
        )
        semaphore = asyncio.Semaphore(3)
        selected_ids = {
            str(item.get("section_id") or "")
            for item in self._select_sections_for_llm_enrichment(sections, max_sections=max_sections)
        }

        async def _enrich_one(section: dict[str, Any]) -> dict[str, Any]:
            if len(section.get("body", "").split()) < 40:
                return section
            prompt = self._build_section_enrichment_prompt(section=section, knowledge_space=knowledge_space)
            async with semaphore:
                try:
                    result = await self._llm.invoke_llm(
                        prompt=prompt,
                        role=ModelRole.KNOWLEDGE_CURATOR,
                        priority=ModelPriority.HIGH_QUALITY,
                        timeout_seconds=45,
                        task_type="knowledge_space_consolidation",
                        complexity="medium",
                    )
                    parsed = parse_json_lenient(str(result.get("response") or ""))
                except Exception:
                    return section
            return self._merge_llm_section_enrichment(section=section, payload=parsed if isinstance(parsed, dict) else None)

        tasks: list[asyncio.Future[Any] | asyncio.Task[Any]] = []
        section_order = {str(section.get("section_id") or ""): index for index, section in enumerate(sections)}
        for section in sections:
            section_id = str(section.get("section_id") or "")
            if section_id in selected_ids:
                tasks.append(asyncio.create_task(_enrich_one(section)))
            else:
                future = asyncio.get_running_loop().create_future()
                future.set_result(section)
                tasks.append(future)
        try:
            results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=overall_timeout)
        except asyncio.TimeoutError:
            for task in tasks:
                if isinstance(task, asyncio.Task) and not task.done():
                    task.cancel()
            logger.warning(
                "knowledge_space_llm_enrichment_timeout",
                knowledge_space_id=str(knowledge_space.get("knowledge_space_id") or ""),
                selected_sections=len(selected_ids),
                timeout_seconds=overall_timeout,
            )
            return sections
        ordered_results = sorted(
            results,
            key=lambda item: section_order.get(str(item.get("section_id") or ""), 999999),
        )
        return ordered_results

    def _select_sections_for_llm_enrichment(
        self,
        sections: list[dict[str, Any]],
        *,
        max_sections: int,
    ) -> list[dict[str, Any]]:
        if max_sections <= 0:
            return []
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        fallback: list[dict[str, Any]] = []
        for section in sections:
            section_role = str(section.get("section_role") or "").strip().lower()
            if section_role in {"noise", "table_like", "front_matter"}:
                continue
            if len(str(section.get("body") or "").split()) < 40:
                continue
            usefulness = float(section.get("usefulness_score") or 0.0)
            if usefulness < 0.46:
                continue
            doc_role = str(section.get("doc_role") or "base").strip().lower() or "base"
            grouped[doc_role].append(section)
            fallback.append(section)
        for rows in grouped.values():
            rows.sort(
                key=lambda item: (
                    -float(item.get("usefulness_score") or 0.0),
                    -float(item.get("heading_quality_score") or 0.0),
                    int(item.get("order") or 0),
                )
            )
        fallback.sort(
            key=lambda item: (
                -float(item.get("usefulness_score") or 0.0),
                -float(item.get("heading_quality_score") or 0.0),
                int(item.get("order") or 0),
            )
        )
        selected: list[dict[str, Any]] = []
        selected_ids: set[str] = set()
        roles_by_priority = ["base", "supplement", "reference", "appendix"]
        for role in roles_by_priority:
            row = next(
                (
                    item
                    for item in grouped.get(role, [])
                    if str(item.get("section_id") or "") not in selected_ids
                ),
                None,
            )
            if row is None:
                continue
            selected.append(row)
            selected_ids.add(str(row.get("section_id") or ""))
            if len(selected) >= max_sections:
                break
        if len(selected) < max_sections:
            for row in fallback:
                section_id = str(row.get("section_id") or "")
                if section_id in selected_ids:
                    continue
                selected.append(row)
                selected_ids.add(section_id)
                if len(selected) >= max_sections:
                    break
        return selected

    def _build_section_enrichment_prompt(
        self,
        *,
        section: dict[str, Any],
        knowledge_space: dict[str, Any],
    ) -> str:
        allowed_roles = ", ".join(sorted(_SECTION_ROLES))
        return (
            "Você está consolidando conhecimento documental em uma base canônica.\n"
            "Responda APENAS com JSON válido.\n\n"
            f"Knowledge space: {knowledge_space.get('name')}\n"
            f"Documento: {section.get('file_name')}\n"
            f"Papel do documento: {section.get('doc_role')}\n"
            f"Título da seção: {section.get('title')}\n"
            f"Resumo heurístico: {section.get('canonical_summary')}\n"
            f"Texto da seção:\n{section.get('body_excerpt')}\n\n"
            "Formato:\n"
            "{\n"
            '  "canonical_summary": "resumo curto e fiel",\n'
            f'  "section_role": "{allowed_roles}",\n'
            '  "applies_to": ["base_creation|character_options|workflow|optional_rules|general_rules"],\n'
            '  "extends_or_overrides": "extends|overrides|none",\n'
            '  "is_optional_rule": false\n'
            "}\n\n"
            "Regras:\n"
            "- Não invente fatos.\n"
            "- Preserve o papel documental entre livro base, suplemento e apêndice.\n"
            "- Use apenas informações explícitas no trecho.\n"
            "- Se a seção parecer ruído, use section_role=noise.\n"
        )

    def _merge_llm_section_enrichment(
        self,
        *,
        section: dict[str, Any],
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not payload:
            return section
        merged = dict(section)
        summary = self._trim_text(str(payload.get("canonical_summary") or ""), max_chars=440)
        if summary:
            merged["canonical_summary"] = summary
            merged["summary"] = self._trim_text(summary, max_chars=360)
        section_role = str(payload.get("section_role") or "").strip().lower()
        if section_role in _SECTION_ROLES:
            merged["section_role"] = section_role
            merged["is_optional_rule"] = bool(section_role == "optional_rules")
        applies_to = [
            str(item).strip()
            for item in (payload.get("applies_to") or [])
            if str(item or "").strip()
        ]
        if applies_to:
            merged["applies_to"] = sorted(set(applies_to))
        extends_or_overrides = str(payload.get("extends_or_overrides") or "").strip().lower()
        if extends_or_overrides in {"extends", "overrides"}:
            merged["extends_or_overrides"] = extends_or_overrides
        elif extends_or_overrides == "none":
            merged["extends_or_overrides"] = None
        if "is_optional_rule" in payload:
            merged["is_optional_rule"] = bool(payload.get("is_optional_rule"))
        merged["classification_source"] = "llm"
        return merged

    def _build_consolidation_metrics(
        self,
        *,
        sections: list[dict[str, Any]],
        skipped_sections: int,
    ) -> dict[str, Any]:
        sections_total = len(sections) + max(0, int(skipped_sections))
        sections_indexed = len(sections)
        canonical_frames_total = sum(
            1
            for item in sections
            if item.get("section_role") in {"core_rules", "supplement_rules", "optional_rules"}
        )
        useful_ratio = sections_indexed / max(1, sections_total)
        canonical_ratio = canonical_frames_total / max(1, sections_indexed)
        usefulness_quality = sum(float(item.get("usefulness_score") or 0.0) for item in sections) / max(1, sections_indexed)
        quality_score = round(
            min(
                1.0,
                (useful_ratio * 0.30) + (canonical_ratio * 0.25) + (usefulness_quality * 0.45),
            ),
            4,
        )
        return {
            "sections_total": sections_total,
            "sections_indexed": sections_indexed,
            "sections_skipped_as_noise": int(skipped_sections),
            "canonical_frames_total": canonical_frames_total,
            "consolidation_quality_score": quality_score,
        }

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
                            key="metadata.user_id",
                            match=models.MatchValue(value=str(user_id)),
                        ),
                        models.FieldCondition(
                            key="metadata.knowledge_space_id",
                            match=models.MatchValue(value=str(knowledge_space["knowledge_space_id"])),
                        ),
                        models.FieldCondition(
                            key="metadata.origin",
                            match=models.MatchValue(value="knowledge_space.consolidation"),
                        ),
                    ]
                )
            ),
        )
        records: list[tuple[dict[str, Any], str, str, str]] = []
        for section in sections:
            records.append(
                (
                    section,
                    "knowledge_canonical_summary",
                    section["canonical_summary"],
                    f"{section['title']}\n{section['canonical_summary']}\n{' '.join(section['concepts'])}",
                )
            )
            records.append(
                (
                    section,
                    "knowledge_evidence_anchor",
                    section["body_excerpt"],
                    f"{section['title']}\n{section['body_excerpt']}",
                )
            )
            if "workflow" in (section.get("applies_to") or []):
                records.append(
                    (
                        section,
                        "knowledge_flow_step",
                        section["canonical_summary"],
                        f"etapa {section['order']} {section['title']}\n{section['canonical_summary']}",
                    )
                )
            if section.get("doc_role") in {"base", "supplement"}:
                comparison_text = (
                    f"{section.get('doc_role')}: {section['title']}. "
                    f"{section['canonical_summary']}"
                )
                records.append((section, "knowledge_comparison_frame", comparison_text, comparison_text))

        batch_size = int(os.getenv("KNOWLEDGE_SPACE_CANONICAL_EMBED_BATCH_SIZE", "48") or 48)
        now_ms = int(time.time() * 1000)
        total_points = 0
        for batch_start in range(0, len(records), max(1, batch_size)):
            record_batch = records[batch_start : batch_start + max(1, batch_size)]
            vectors = await aembed_texts([record[3] for record in record_batch])
            points: list[models.PointStruct] = []
            for record, vector in zip(record_batch, vectors, strict=False):
                section, point_type, content, embedding_text = record
                payload = {
                    "type": point_type,
                    "ts_ms": now_ms,
                    "content": content,
                    "metadata": {
                        "type": point_type,
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
                        "doc_role": section.get("doc_role"),
                        "section_role": section.get("section_role"),
                        "applies_to": section.get("applies_to") or [],
                        "is_optional_rule": bool(section.get("is_optional_rule")),
                        "extends_or_overrides": section.get("extends_or_overrides"),
                        "is_useful": bool(section.get("is_useful")),
                        "noise_score": float(section.get("noise_score") or 0.0),
                        "heading_quality_score": float(section.get("heading_quality_score") or 0.0),
                        "content_density_score": float(section.get("content_density_score") or 0.0),
                        "usefulness_score": float(section.get("usefulness_score") or 0.0),
                        "answer_strategy": (
                            "comparative"
                            if point_type == "knowledge_comparison_frame"
                            else "sequence"
                            if point_type == "knowledge_flow_step"
                            else "scope"
                        ),
                        "embedding_text": embedding_text[:1200],
                        "evidence_span_ids": section.get("evidence_span_ids") or [],
                        "timestamp": now_ms,
                    },
                }
                points.append(
                    models.PointStruct(
                        id=build_deterministic_point_id(
                            "knowledge-canonical-point",
                            knowledge_space["knowledge_space_id"],
                            section["section_id"],
                            point_type,
                        ),
                        vector=vector,
                        payload=payload,
                    )
                )
            await self._upsert_points_resilient(
                client=client,
                collection_name=collection_name,
                points=points,
            )
            total_points += len(points)
        return total_points

    async def _upsert_points_resilient(
        self,
        *,
        client: Any,
        collection_name: str,
        points: list[models.PointStruct],
        min_batch_size: int = 8,
    ) -> None:
        if not points:
            return
        try:
            await client.upsert(collection_name=collection_name, points=points)
            return
        except Exception:
            if len(points) <= max(1, int(min_batch_size)):
                raise
        midpoint = max(1, len(points) // 2)
        await self._upsert_points_resilient(
            client=client,
            collection_name=collection_name,
            points=points[:midpoint],
            min_batch_size=min_batch_size,
        )
        await self._upsert_points_resilient(
            client=client,
            collection_name=collection_name,
            points=points[midpoint:],
            min_batch_size=min_batch_size,
        )

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
                "doc_role": manifest.get("doc_role") or self._infer_doc_role(manifest, knowledge_space),
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
                    w.doc_role = work.doc_role,
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
            base_doc_ids = [item["doc_id"] for item in work_rows if item.get("doc_role") == "base"]
            supplement_links = [
                {"supplement_doc_id": item["doc_id"], "base_doc_id": base_doc_id}
                for item in work_rows
                if item.get("doc_role") == "supplement"
                for base_doc_id in base_doc_ids
            ]
            if supplement_links:
                await graph.execute(
                    """
                    UNWIND $links AS link
                    MATCH (supp:Work {doc_id: link.supplement_doc_id})
                    MATCH (base:Work {doc_id: link.base_doc_id})
                    MERGE (supp)-[:SUPPLEMENTS]->(base)
                    """,
                    {"links": supplement_links},
                    operation="knowledge_space_graph_supplement_batch",
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
                    "doc_role": section.get("doc_role"),
                    "section_role": section.get("section_role"),
                    "applies_to": section.get("applies_to") or [],
                    "is_optional_rule": bool(section.get("is_optional_rule")),
                    "extends_or_overrides": section.get("extends_or_overrides"),
                    "is_useful": bool(section.get("is_useful")),
                    "usefulness_score": float(section.get("usefulness_score") or 0.0),
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
                    s.doc_role = section.doc_role,
                    s.section_role = section.section_role,
                    s.applies_to = section.applies_to,
                    s.is_optional_rule = section.is_optional_rule,
                    s.extends_or_overrides = section.extends_or_overrides,
                    s.is_useful = section.is_useful,
                    s.usefulness_score = section.usefulness_score,
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
        metrics: dict[str, Any],
    ) -> str:
        titles = [str(item["title"]).strip() for item in sections[:3] if str(item["title"]).strip()]
        docs = [str(item.get("file_name") or item.get("doc_id") or "").strip() for item in manifests[:3]]
        roles = sorted(
            {
                str(item.get("doc_role") or self._infer_doc_role(item, space)).strip()
                for item in manifests
                if str(item.get("file_name") or "").strip()
            }
        )
        return (
            f"Espaço '{space['name']}' consolidado com {len(manifests)} documento(s) "
            f"e {metrics['sections_indexed']} seção(ões) úteis de {metrics['sections_total']} detectadas. "
            f"Documentos: {', '.join(item for item in docs if item)}. "
            f"Papéis: {', '.join(item for item in roles if item) or 'base'}. "
            f"Frames canônicos: {metrics['canonical_frames_total']}. "
            f"Qualidade estimada: {metrics['consolidation_quality_score']:.2f}. "
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
        roles = {
            str(item.get("doc_role") or self._infer_doc_role(item, space)).strip()
            for item in manifests
            if str(item.get("file_name") or "").strip()
        }
        if roles and "base" not in roles:
            conflicts.append("Não há documento marcado como base; a resposta pode ficar dominada por suplemento ou referência.")
        if space.get("parent_collection_id"):
            conflicts.append("Espaço vinculado a coleção; respostas podem depender da ordem declarada dos volumes.")
        return conflicts

    def _lexical_overlap(self, *, text: str, title: str, concepts: list[str], query_terms: set[str]) -> int:
        searchable_text = self._normalize_search_text(text)
        searchable_title = self._normalize_search_text(title)
        searchable_concepts = {self._normalize_search_text(item) for item in concepts if self._normalize_search_text(item)}
        return sum(
            1
            for token in query_terms
            if token in searchable_text or token in searchable_title or token in searchable_concepts
        )

    def _phrase_overlap(self, *, text: str, title: str, query_phrases: set[str]) -> int:
        searchable_text = self._normalize_search_text(text)
        searchable_title = self._normalize_search_text(title)
        compact_text = self._compact_search_text(text)
        compact_title = self._compact_search_text(title)
        return sum(
            1
            for phrase in query_phrases
            if phrase
            and (
                phrase in searchable_text
                or phrase in searchable_title
                or self._compact_search_text(phrase) in compact_text
                or self._compact_search_text(phrase) in compact_title
            )
        )

    def _is_low_trust_sequence_title(self, title: str) -> bool:
        normalized = self._normalize_heading_title(title)
        if not normalized:
            return False
        if re.match(r"^\d{2,}\s+[A-ZÀ-Ý]{3,}", normalized):
            return True
        uppercase_tokens = [
            token for token in re.findall(r"[A-Za-zÀ-ÿ]+", normalized) if token.isupper() and len(token) >= 3
        ]
        searchable = self._normalize_search_text(normalized)
        if len(uppercase_tokens) >= 2 and "capitulo" not in searchable and "capítulo" not in searchable:
            return True
        return False

    def _is_sequence_anchor(self, *, title: str, content: str, doc_role: str) -> bool:
        searchable_title = self._normalize_search_text(title)
        searchable_content = self._normalize_search_text(content)
        if doc_role == "base" and any(
            token in searchable_title for token in ("capitulo um", "capítulo um", "criacao de personagens", "criação de personagens")
        ):
            return True
        if doc_role == "base" and all(
            token in searchable_content for token in ("atribut", "raca", "classe")
        ):
            return True
        if doc_role == "supplement" and any(
            token in searchable_title for token in ("campeoes de arton", "campeões de arton", "capitulo 1", "capítulo 1")
        ):
            return True
        if doc_role == "supplement" and all(
            token in searchable_content for token in ("novas", "opcoes")
        ):
            return True
        return False

    def _looks_like_specific_option_chunk(self, *, title: str, content: str) -> bool:
        searchable_title = self._normalize_search_text(title)
        searchable_content = self._normalize_search_text(content)
        if any(token in searchable_title for token in ("equipamento real", "meditacao mistica", "meditação mística")):
            return True
        if searchable_content.count("pré-requisito") >= 1 or searchable_content.count("pre-requisito") >= 1:
            return True
        if searchable_content.count("•") >= 3:
            return True
        return False

    def _classify_chunk_match(
        self,
        *,
        point_score: float,
        lexical_overlap: int,
        phrase_overlap: int,
        explicit_locator: bool,
    ) -> str:
        if phrase_overlap >= 1:
            return "exact_match"
        if lexical_overlap >= 2:
            return "exact_match"
        if lexical_overlap >= 1 and point_score >= 0.30:
            return "strong_semantic"
        if not explicit_locator and point_score >= 0.55:
            return "strong_semantic"
        return "weak_semantic"

    async def _query_canonical(
        self,
        *,
        knowledge_space: dict[str, Any],
        user_id: str,
        question: str,
        limit: int,
        active_doc_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        client = get_async_qdrant_client()
        collection_name = await aget_or_create_collection(build_user_docs_collection_name(user_id))
        vector = await aembed_text(question)
        answer_strategy = self._detect_answer_strategy(question)
        query_profile = self._build_query_profile(question)
        candidate_points: list[Any] = []
        for point_type in self._resolve_canonical_query_types(answer_strategy):
            result = await client.query_points(
                collection_name=collection_name,
                query=vector,
                limit=max(6, int(limit) * 4),
                with_payload=True,
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.type",
                            match=models.MatchValue(value=point_type),
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
            candidate_points.extend(list(getattr(result, "points", result) or []))
            if query_profile.get("asks_for_sequence") or query_profile.get("expects_exact_evidence"):
                candidate_points.extend(
                    await self._scroll_points(
                        collection_name=collection_name,
                        query_filter=models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="metadata.type",
                                    match=models.MatchValue(value=point_type),
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
                )

        candidate_points = self._filter_points_by_doc_ids(candidate_points, active_doc_ids=active_doc_ids)
        selected = self._select_canonical_candidates(
            points=candidate_points,
            question=question,
            query_profile=query_profile,
            answer_strategy=answer_strategy,
            limit=limit,
        )
        citations = [self._map_citation(item["point"], snippet_limit=320) for item in selected]
        confidence = self._average_score([item["point"] for item in selected])
        answer = self._render_canonical_answer(selected, answer_strategy=answer_strategy)
        gaps = self._build_canonical_gaps(
            selected=selected,
            answer_strategy=answer_strategy,
            confidence=confidence,
            query_profile=query_profile,
        )
        return {
            "answer": answer,
            "mode_used": "canonical_answer",
            "base_used": "consolidated",
            "source_scope": self._build_source_scope(knowledge_space),
            "citations": citations,
            "confidence": confidence,
            "gaps_or_conflicts": gaps if citations else ["Nenhum summary canônico relevante foi recuperado."],
            "answer_strategy": answer_strategy,
            "evidence_count": len(citations),
            "source_roles_used": sorted({str(item["doc_role"]) for item in selected if item.get("doc_role")}),
        }

    def _resolve_canonical_query_types(self, answer_strategy: str) -> list[str]:
        point_types = ["knowledge_canonical_summary", "knowledge_evidence_anchor"]
        if answer_strategy == "sequence":
            point_types.append("knowledge_flow_step")
        if answer_strategy == "comparative":
            point_types.append("knowledge_comparison_frame")
        return point_types

    def _detect_answer_strategy(self, question: str) -> str:
        lowered = str(question or "").casefold()
        if self._prefer_locator(question):
            return "locator"
        if any(
            token in lowered
            for token in (
                "passo",
                "sequên",
                "sequenc",
                "etapa",
                "ordem",
                "como fazer",
                "processo",
                "primeiro",
                "depois",
                "criacao de personagem",
                "criação de personagem",
                "criar personagem",
                "ficha",
                "em que ponto",
            )
        ):
            return "sequence"
        if any(token in lowered for token in ("compar", "diferen", "versus", "vs", "amplia", "suplement")):
            return "comparative"
        return "scope"

    def _prefer_locator(self, question: str) -> bool:
        lowered = str(question or "").casefold()
        return any(token in lowered for token in ("página", "pagina", "trecho", "onde", "citação", "citacao"))

    def _select_canonical_candidates(
        self,
        *,
        points: list[Any],
        question: str,
        query_profile: dict[str, Any],
        answer_strategy: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        lowered_question = str(query_profile.get("normalized") or self._normalize_search_text(question))
        question_terms = set(query_profile.get("terms") or [])
        topic_terms = set(query_profile.get("topic_terms") or question_terms)
        query_phrases = set(query_profile.get("phrases") or [])
        topic_phrases = set(query_profile.get("topic_phrases") or query_phrases)
        source_hints = {self._normalize_search_text(item) for item in (query_profile.get("source_hints") or []) if item}
        for point in points:
            payload = getattr(point, "payload", {}) or {}
            metadata = payload.get("metadata") or {}
            section_id = str(metadata.get("section_id") or getattr(point, "id", ""))
            content = str(payload.get("content") or "").strip()
            title = str(metadata.get("section_title") or "").strip()
            file_name = str(metadata.get("file_name") or "").strip()
            concepts = [str(item).strip().casefold() for item in (metadata.get("concepts") or []) if str(item).strip()]
            lexical_overlap = self._lexical_overlap(
                text=content,
                title=title,
                concepts=concepts,
                query_terms=question_terms,
            )
            topic_lexical_overlap = self._lexical_overlap(
                text=content,
                title=title,
                concepts=concepts,
                query_terms=topic_terms,
            )
            phrase_overlap = self._phrase_overlap(
                text=content,
                title=f"{title} {file_name}",
                query_phrases=query_phrases,
            )
            topic_phrase_overlap = self._phrase_overlap(
                text=content,
                title=title,
                query_phrases=topic_phrases,
            )
            base_score = float(getattr(point, "score", 0.0) or 0.0)
            rerank_score = base_score
            doc_role = str(metadata.get("doc_role") or "base").strip().lower() or "base"
            section_role = str(metadata.get("section_role") or "core_rules").strip().lower() or "core_rules"
            usefulness_score = float(metadata.get("usefulness_score") or 0.0)
            heading_quality_score = float(metadata.get("heading_quality_score") or 0.0)
            content_density_score = float(metadata.get("content_density_score") or 0.0)
            noise_score = float(metadata.get("noise_score") or 0.0)
            applies_to = metadata.get("applies_to") or []
            searchable_title = self._normalize_search_text(title)
            searchable_file_name = self._normalize_search_text(file_name)
            source_target_match = any(
                hint in searchable_title or hint in searchable_file_name for hint in source_hints
            )
            if answer_strategy in {"scope", "sequence"} and doc_role == "base":
                rerank_score += 0.14
            if answer_strategy == "comparative" and doc_role == "supplement":
                rerank_score += 0.12
            if section_role == "core_rules":
                rerank_score += 0.08
            if section_role == "supplement_rules":
                rerank_score += 0.06
            if section_role == "optional_rules":
                rerank_score -= 0.04 if answer_strategy != "sequence" else 0.18
            if answer_strategy == "sequence" and "workflow" in applies_to:
                rerank_score += 0.12
            if answer_strategy == "sequence" and query_profile.get("asks_for_creation") and (
                "base_creation" in applies_to or "workflow" in applies_to
            ):
                rerank_score += 0.14
            if answer_strategy == "sequence" and self._is_sequence_anchor(
                title=title,
                content=content,
                doc_role=doc_role,
            ):
                rerank_score += 0.26
            if answer_strategy == "sequence" and query_profile.get("asks_for_ordering") and doc_role == "base":
                section_order = int(metadata.get("section_order") or 999999)
                rerank_score += max(0.0, 0.18 - min(0.18, max(0, section_order - 1) * 0.015))
                if any(token in searchable_title for token in ("toques finais", "finais", "final")):
                    rerank_score -= 0.22
            if answer_strategy == "sequence" and self._is_low_trust_sequence_title(title):
                rerank_score -= 0.28
            if answer_strategy == "sequence" and self._looks_like_specific_option_chunk(title=title, content=content):
                rerank_score -= 0.22
            if self._looks_like_editorial_content(title=title, body=content):
                rerank_score -= 0.48
            rerank_score += min(0.24, lexical_overlap * 0.05)
            rerank_score += min(0.30, phrase_overlap * 0.10)
            rerank_score += min(0.16, topic_lexical_overlap * 0.06)
            rerank_score += min(0.18, topic_phrase_overlap * 0.12)
            rerank_score += min(0.18, usefulness_score * 0.18)
            rerank_score += min(0.10, heading_quality_score * 0.08)
            rerank_score += min(0.08, content_density_score * 0.06)
            rerank_score -= min(0.28, noise_score * 0.28)
            if heading_quality_score < 0.20:
                rerank_score -= 0.10
            if answer_strategy == "sequence" and (heading_quality_score < 0.35 or noise_score > 0.45):
                rerank_score -= 0.24
            if (
                query_profile.get("expects_exact_evidence")
                and source_hints
                and source_target_match
                and topic_lexical_overlap == 0
                and topic_phrase_overlap == 0
            ):
                rerank_score -= 0.34
            if source_hints and not source_target_match and query_profile.get("asks_for_supplement"):
                rerank_score -= 0.12
            if source_target_match:
                rerank_score += 0.14
            if question_terms and lexical_overlap == 0 and phrase_overlap == 0 and query_profile.get("expects_exact_evidence"):
                rerank_score -= 0.20
            if answer_strategy == "comparative" and lexical_overlap == 0 and doc_role == "supplement":
                rerank_score -= 0.08
            if query_profile.get("asks_for_supplement") and doc_role == "supplement":
                rerank_score += 0.08
            if query_profile.get("asks_for_base") and doc_role == "base":
                rerank_score += 0.06
            if (
                answer_strategy == "sequence"
                and query_profile.get("asks_for_creation")
                and doc_role == "base"
                and not self._has_creation_foundation_signal(title=title, content=content, doc_role=doc_role)
                and not self._is_sequence_anchor(title=title, content=content, doc_role=doc_role)
            ):
                rerank_score -= 0.42
            existing = grouped.get(section_id)
            if existing is None or rerank_score > existing["rerank_score"]:
                grouped[section_id] = {
                    "point": point,
                    "section_id": section_id,
                    "doc_id": str(metadata.get("doc_id") or ""),
                    "doc_role": doc_role,
                    "section_role": section_role,
                    "section_order": int(metadata.get("section_order") or 0),
                    "title": title,
                    "content": content,
                    "applies_to": applies_to,
                    "usefulness_score": usefulness_score,
                    "lexical_overlap": lexical_overlap,
                    "topic_lexical_overlap": topic_lexical_overlap,
                    "phrase_overlap": phrase_overlap,
                    "topic_phrase_overlap": topic_phrase_overlap,
                    "rerank_score": rerank_score,
                }
        ordered = sorted(
            grouped.values(),
            key=lambda item: (-item["rerank_score"], item["section_order"] or 999999),
        )
        selected: list[dict[str, Any]] = []
        if answer_strategy == "comparative":
            base_item = next((item for item in ordered if item["doc_role"] == "base"), None)
            supplement_item = next((item for item in ordered if item["doc_role"] == "supplement"), None)
            for item in (base_item, supplement_item):
                if item is None:
                    continue
                if item["lexical_overlap"] == 0 and query_profile.get("expects_exact_evidence"):
                    continue
                selected.append(item)
            selected_ids = {item["section_id"] for item in selected}
            for item in ordered:
                if len(selected) >= max(1, int(limit)):
                    break
                if item["section_id"] in selected_ids:
                    continue
                if item["doc_role"] == "supplement" and not supplement_item and item["lexical_overlap"] == 0 and item["phrase_overlap"] == 0:
                    continue
                selected.append(item)
                selected_ids.add(item["section_id"])
            return selected
        if answer_strategy == "sequence":
            sequence_limit = max(1, int(limit))
            sequence_selected: list[dict[str, Any]] = []
            selected_ids: set[str] = set()
            base_candidates = [item for item in ordered if item["doc_role"] == "base"]
            trustworthy_base_candidates = [
                item
                for item in base_candidates
                if not self._is_low_trust_sequence_title(str(item.get("title") or ""))
                and float(item.get("usefulness_score") or 0.0) >= 0.45
                and not self._looks_like_editorial_content(
                    title=str(item.get("title") or ""),
                    body=str(item.get("content") or ""),
                )
            ]
            if trustworthy_base_candidates:
                base_candidates = trustworthy_base_candidates
            if query_profile.get("asks_for_creation"):
                creation_candidates = [
                    item
                    for item in base_candidates
                    if (
                        {"base_creation", "workflow"} & set(item.get("applies_to") or [])
                        and (
                            self._has_creation_foundation_signal(
                                title=str(item.get("title") or ""),
                                content=str(item.get("content") or ""),
                                doc_role=str(item.get("doc_role") or "base"),
                            )
                            or self._is_sequence_anchor(
                                title=str(item.get("title") or ""),
                                content=str(item.get("content") or ""),
                                doc_role=str(item.get("doc_role") or "base"),
                            )
                        )
                    )
                ]
                if creation_candidates:
                    base_candidates = creation_candidates
            if query_profile.get("asks_for_ordering"):
                base_candidates = sorted(
                    base_candidates,
                    key=lambda item: (item["section_order"] or 999999, -item["rerank_score"]),
                )
            if base_candidates:
                primary_base = base_candidates[0]
                sequence_selected.append(primary_base)
                selected_ids.add(primary_base["section_id"])
            if query_profile.get("asks_for_supplement"):
                supplement_candidates = [
                    item
                    for item in ordered
                    if item["doc_role"] == "supplement"
                    and item["section_id"] not in selected_ids
                    and (
                        item["lexical_overlap"] > 0
                        or item["phrase_overlap"] > 0
                        or {"character_options", "workflow"} & set(item.get("applies_to") or [])
                    )
                ]
                if supplement_candidates:
                    supplement = supplement_candidates[0]
                    sequence_selected.append(supplement)
                    selected_ids.add(supplement["section_id"])
            for item in ordered:
                if len(sequence_selected) >= sequence_limit:
                    break
                if item["section_id"] in selected_ids:
                    continue
                if item["doc_role"] in {"base", "supplement"} and item["doc_id"] in {
                    row["doc_id"] for row in sequence_selected
                }:
                    continue
                sequence_selected.append(item)
                selected_ids.add(item["section_id"])
            return sequence_selected
        used_doc_ids: set[str] = set()
        for item in ordered:
            if len(selected) >= max(1, int(limit)):
                break
            if answer_strategy == "sequence" and item["doc_role"] == "supplement" and not any(
                row["doc_role"] == "base" for row in selected
            ):
                continue
            if answer_strategy == "sequence" and item["doc_role"] == "supplement" and any(
                row["doc_role"] == "supplement" for row in selected
            ):
                continue
            if item["lexical_overlap"] == 0 and query_profile.get("expects_exact_evidence") and answer_strategy != "sequence":
                continue
            if item["doc_id"] in used_doc_ids and item["doc_role"] != "supplement" and answer_strategy != "scope":
                continue
            selected.append(item)
            used_doc_ids.add(item["doc_id"])
        if answer_strategy == "sequence" and any(
            token in lowered_question for token in ("suplement", "amplia", "adiciona", "herois", "heróis")
        ):
            selected_ids = {item["section_id"] for item in selected}
            has_supplement = any(item.get("doc_role") == "supplement" for item in selected)
            if not has_supplement:
                for item in ordered:
                    if item["section_id"] in selected_ids:
                        continue
                    if item.get("doc_role") != "supplement":
                        continue
                    if item["lexical_overlap"] == 0 and query_profile.get("expects_exact_evidence"):
                        continue
                    selected.append(item)
                    if len(selected) > max(1, int(limit)):
                        selected = selected[: max(1, int(limit)) - 1] + [item]
                    break
        return selected

    def _build_canonical_gaps(
        self,
        *,
        selected: list[dict[str, Any]],
        answer_strategy: str,
        confidence: float,
        query_profile: dict[str, Any],
    ) -> list[str]:
        gaps: list[str] = []
        roles = {str(item.get("doc_role") or "") for item in selected if str(item.get("doc_role") or "")}
        if answer_strategy == "comparative" and len(roles) < 2:
            gaps.append("Resposta comparativa com baixa diversidade de fontes; apenas um papel documental dominou a evidência.")
        if confidence < 0.35:
            gaps.append("Evidência consolidada fraca; resposta parcial para evitar inferência indevida.")
        if any(item.get("section_role") == "optional_rules" for item in selected) and answer_strategy != "comparative":
            gaps.append("Parte da evidência vem de regras opcionais; valide se elas se aplicam ao seu caso.")
        if query_profile.get("expects_exact_evidence") and selected and not any(int(item.get("lexical_overlap") or 0) > 0 for item in selected):
            gaps.append("A base consolidada recuperou contexto relevante, mas sem apoio lexical forte para a formulação exata da pergunta.")
        if answer_strategy == "sequence" and query_profile.get("asks_for_supplement") and "supplement" not in roles:
            gaps.append("A sequência principal foi encontrada, mas faltou uma extensão clara vinda do suplemento.")
        return gaps

    async def _query_quick_lookup(
        self,
        *,
        knowledge_space: dict[str, Any],
        user_id: str,
        question: str,
        limit: int,
        active_doc_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        client = get_async_qdrant_client()
        collection_name = await aget_or_create_collection(build_user_docs_collection_name(user_id))
        vector = await aembed_text(question)
        query_profile = self._build_query_profile(question)
        result = await client.query_points(
            collection_name=collection_name,
            query=vector,
            limit=max(10, int(limit) * 6),
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
        if query_profile.get("expects_exact_evidence") or query_profile.get("source_hints"):
            points.extend(
                await self._scroll_points(
                    collection_name=collection_name,
                    query_filter=models.Filter(
                        must=[
                            models.FieldCondition(key="metadata.type", match=models.MatchValue(value="doc_chunk")),
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
                    batch_size=256,
                )
            )
        points = self._filter_points_by_doc_ids(points, active_doc_ids=active_doc_ids)
        selected = self._select_quick_lookup_points(
            points=points,
            question=question,
            query_profile=query_profile,
            limit=limit,
        )
        citations = [self._map_citation(point, snippet_limit=220) for point in selected]
        return {
            "answer": self._render_quick_answer(selected, knowledge_space=knowledge_space),
            "mode_used": "quick_lookup",
            "base_used": "chunk_only",
            "source_scope": self._build_source_scope(knowledge_space),
            "citations": citations,
            "confidence": self._average_score(selected),
            "gaps_or_conflicts": (
                []
                if citations
                else ["Nenhum chunk com suporte lexical suficiente foi recuperado para a pergunta."]
            ),
            "answer_strategy": "locator",
            "evidence_count": len(citations),
            "source_roles_used": sorted(
                {
                    str(((getattr(point, "payload", {}) or {}).get("metadata") or {}).get("doc_role") or "")
                    for point in selected
                    if str(((getattr(point, "payload", {}) or {}).get("metadata") or {}).get("doc_role") or "")
                }
            ),
        }

    def _select_quick_lookup_points(
        self,
        *,
        points: list[Any],
        question: str,
        query_profile: dict[str, Any],
        limit: int,
    ) -> list[Any]:
        lowered_question = str(query_profile.get("normalized") or self._normalize_search_text(question))
        question_terms = set(query_profile.get("terms") or [])
        topic_terms = set(query_profile.get("topic_terms") or question_terms)
        query_phrases = set(query_profile.get("phrases") or [])
        topic_phrases = set(query_profile.get("topic_phrases") or query_phrases)
        source_hints = {self._normalize_search_text(item) for item in (query_profile.get("source_hints") or []) if item}
        ranked: list[tuple[float, int, Any]] = []
        for point in points:
            payload = getattr(point, "payload", {}) or {}
            metadata = payload.get("metadata") or {}
            content = str(payload.get("content") or "")
            title = str(metadata.get("section_title") or metadata.get("file_name") or "")
            file_name = str(metadata.get("file_name") or "")
            lexical_overlap = self._lexical_overlap(
                text=content,
                title=title,
                concepts=[],
                query_terms=question_terms,
            )
            topic_lexical_overlap = self._lexical_overlap(
                text=content,
                title=title,
                concepts=[],
                query_terms=topic_terms,
            )
            phrase_overlap = self._phrase_overlap(
                text=content,
                title=f"{title} {file_name}",
                query_phrases=query_phrases,
            )
            topic_phrase_overlap = self._phrase_overlap(
                text=content,
                title=title,
                query_phrases=topic_phrases,
            )
            point_score = float(getattr(point, "score", 0.0) or 0.0)
            rerank_score = point_score + min(0.28, lexical_overlap * 0.06) + min(0.32, phrase_overlap * 0.12)
            rerank_score += min(0.18, topic_lexical_overlap * 0.08)
            rerank_score += min(0.22, topic_phrase_overlap * 0.14)
            doc_role = str(metadata.get("doc_role") or "").strip().lower()
            searchable_content = self._normalize_search_text(content)
            searchable_file_name = self._normalize_search_text(file_name)
            searchable_title = self._normalize_search_text(title)
            source_target_match = any(
                hint in searchable_file_name or hint in searchable_title for hint in source_hints
            )
            if self._looks_like_editorial_content(title=title, body=content):
                rerank_score -= 0.42
            if doc_role == "supplement" and query_profile.get("asks_for_supplement"):
                rerank_score += 0.10
            if source_target_match:
                rerank_score += 0.16
            elif source_hints:
                rerank_score -= 0.12
            if (
                query_profile.get("expects_exact_evidence")
                and source_target_match
                and topic_lexical_overlap == 0
                and topic_phrase_overlap == 0
            ):
                rerank_score -= 0.32
            if any(token in lowered_question for token in ("raca", "racas")) and any(
                token in searchable_content for token in ("raca", "racas")
            ):
                rerank_score += 0.10
            if any(token in lowered_question for token in ("raca", "racas")) and not any(
                token in searchable_content or token in self._compact_search_text(content)
                for token in ("raca", "racas")
            ):
                rerank_score -= 0.10
            if "novas racas" in query_phrases and "novas racas" not in searchable_content:
                if "novasracas" in self._compact_search_text(content):
                    rerank_score += 0.16
                else:
                    rerank_score -= 0.14
            if re.search(r"\.{4,}", content) or len(searchable_content.split()) < 12:
                rerank_score -= 0.14
            match_class = self._classify_chunk_match(
                point_score=point_score,
                lexical_overlap=lexical_overlap,
                phrase_overlap=phrase_overlap,
                explicit_locator=bool(query_profile.get("explicit_locator")),
            )
            if match_class == "exact_match":
                rerank_score += 0.08
            elif match_class == "weak_semantic":
                rerank_score -= 0.12
            ranked.append((rerank_score, max(lexical_overlap, topic_lexical_overlap), point))
        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
        minimum_match_classes = {"exact_match", "strong_semantic"}
        selected: list[Any] = []
        for _, lexical_overlap, point in ranked:
            payload = getattr(point, "payload", {}) or {}
            metadata = payload.get("metadata") or {}
            content = str(payload.get("content") or "")
            phrase_overlap = self._phrase_overlap(
                text=content,
                title=f"{metadata.get('section_title') or ''} {metadata.get('file_name') or ''}",
                query_phrases=query_phrases,
            )
            topic_lexical_overlap = self._lexical_overlap(
                text=content,
                title=str(metadata.get("section_title") or metadata.get("file_name") or ""),
                concepts=[],
                query_terms=topic_terms,
            )
            topic_phrase_overlap = self._phrase_overlap(
                text=content,
                title=str(metadata.get("section_title") or ""),
                query_phrases=topic_phrases,
            )
            match_class = self._classify_chunk_match(
                point_score=float(getattr(point, "score", 0.0) or 0.0),
                lexical_overlap=lexical_overlap,
                phrase_overlap=phrase_overlap,
                explicit_locator=bool(query_profile.get("explicit_locator")),
            )
            if (
                query_profile.get("expects_exact_evidence")
                and topic_phrases
                and topic_phrase_overlap == 0
                and topic_lexical_overlap < 1
            ):
                continue
            if query_profile.get("expects_exact_evidence") and match_class not in minimum_match_classes:
                continue
            if self._looks_like_editorial_content(
                title=str(metadata.get("section_title") or metadata.get("file_name") or ""),
                body=content,
            ):
                continue
            selected.append(point)
            if len(selected) >= max(1, int(limit)):
                break
        if selected:
            return selected
        if query_profile.get("expects_exact_evidence"):
            return []
        return [point for _, _, point in ranked[: max(1, int(limit))]]

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
            "sections_total": int(knowledge_space.get("sections_total") or 0),
            "sections_indexed": int(knowledge_space.get("sections_indexed") or 0),
            "sections_skipped_as_noise": int(knowledge_space.get("sections_skipped_as_noise") or 0),
            "canonical_frames_total": int(knowledge_space.get("canonical_frames_total") or 0),
            "consolidation_quality_score": float(knowledge_space.get("consolidation_quality_score") or 0.0),
        }

    def _render_canonical_answer(self, selected: list[dict[str, Any]], *, answer_strategy: str) -> str:
        if not selected:
            return "A base consolidada ainda não possui evidência suficiente para responder com segurança."
        if answer_strategy == "comparative":
            return self._render_comparative_answer(selected)
        if answer_strategy == "sequence":
            return self._render_sequence_answer(selected)
        return self._render_scope_answer(selected)

    def _render_comparative_answer(self, selected: list[dict[str, Any]]) -> str:
        grouped: dict[str, dict[str, Any]] = {}
        for item in selected:
            grouped.setdefault(str(item.get("doc_role") or "base"), item)
        base = grouped.get("base")
        supplement = grouped.get("supplement")
        lines = ["Síntese curta:"]
        if base and supplement:
            lines.append("O livro base traz a regra principal; o suplemento entra como ampliação pontual e não como substituição.")
        else:
            lines.append("A comparação ficou parcial; a base consolidada não recuperou evidência forte o bastante para os dois papéis documentais.")
        if base:
            lines.append(f"Base: {base['title']} - {self._trim_text(base['content'], max_chars=220)}")
        if supplement:
            lines.append(
                f"Suplemento: {supplement['title']} - {self._trim_text(supplement['content'], max_chars=220)}"
            )
        for role in ("reference", "appendix"):
            if grouped.get(role):
                lines.append(
                    f"{role.capitalize()}: {grouped[role]['title']} - {self._trim_text(grouped[role]['content'], max_chars=180)}"
                )
        return "\n".join(lines)

    def _render_sequence_answer(self, selected: list[dict[str, Any]]) -> str:
        base_items = sorted(
            [item for item in selected if item.get("doc_role") == "base"],
            key=lambda item: (item["section_order"] or 999999, -item["rerank_score"]),
        )
        supplement_items = sorted(
            [item for item in selected if item.get("doc_role") == "supplement"],
            key=lambda item: (item["section_order"] or 999999, -item["rerank_score"]),
        )
        context_items = sorted(
            [
                item
                for item in selected
                if item.get("doc_role") not in {"base", "supplement"}
            ],
            key=lambda item: (item["section_order"] or 999999, -item["rerank_score"]),
        )
        ordered = base_items + supplement_items + context_items
        lines = ["Sequência sugerida pela base consolidada:"]
        for index, item in enumerate(ordered[:4], start=1):
            role_label = "Base" if item.get("doc_role") == "base" else "Suplemento" if item.get("doc_role") == "supplement" else "Contexto"
            suffix = " (ampliação)" if item.get("doc_role") == "supplement" else ""
            lines.append(
                f"{index}. [{role_label}] {item['title']}: {self._trim_text(item['content'], max_chars=180)}{suffix}"
            )
        return "\n".join(lines)

    def _render_scope_answer(self, selected: list[dict[str, Any]]) -> str:
        primary = selected[0]
        lines = [f"Síntese curta: {self._trim_text(primary['content'], max_chars=220)}"]
        if primary.get("doc_role") == "base":
            lines.append("Regra principal: a evidência dominante veio do material base.")
        for item in selected[1:3]:
            note = "Extensão" if item.get("doc_role") == "supplement" else "Contexto"
            lines.append(f"{note}: {item['title']} - {self._trim_text(item['content'], max_chars=180)}")
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
            metadata = payload.get("metadata") or {}
            snippet = re.sub(r"\s+", " ", str(payload.get("content") or "").strip())
            if not snippet:
                continue
            trimmed = snippet[:220].rstrip()
            if len(snippet) > 220:
                trimmed = f"{trimmed}..."
            title = str(metadata.get("section_title") or metadata.get("file_name") or "Trecho").strip()
            lines.append(f"- {title}: {trimmed}")
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
            "doc_role": metadata.get("doc_role"),
            "section_role": metadata.get("section_role"),
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

    def _filter_points_by_doc_ids(
        self,
        points: list[Any],
        *,
        active_doc_ids: set[str] | None,
    ) -> list[Any]:
        if not active_doc_ids:
            return list(points)
        filtered: list[Any] = []
        for point in points:
            payload = getattr(point, "payload", {}) or {}
            metadata = payload.get("metadata") or {}
            doc_id = str(metadata.get("doc_id") or "").strip()
            if doc_id in active_doc_ids:
                filtered.append(point)
        return filtered


def get_knowledge_space_service(request: Request) -> KnowledgeSpaceService:
    if not hasattr(request.app.state, "knowledge_space_service"):
        request.app.state.knowledge_space_service = KnowledgeSpaceService(
            llm_service=getattr(request.app.state, "llm_service", None)
        )
    return request.app.state.knowledge_space_service
