import asyncio
import math
import re
from dataclasses import dataclass
from typing import Any

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

try:
    from sentence_transformers import CrossEncoder  # type: ignore
except Exception:
    CrossEncoder = None  # type: ignore


@dataclass
class SemanticRerankResult:
    items: list[dict[str, Any]]
    method: str
    applied: bool
    candidate_count: int


class SemanticRerankerService:
    def __init__(self) -> None:
        self._cross_encoder = None
        self._cross_encoder_failed = False
        self._lock = asyncio.Lock()

    async def rerank(
        self,
        *,
        query: str,
        items: list[dict[str, Any]],
        top_k: int,
    ) -> SemanticRerankResult:
        if not bool(getattr(settings, "RAG_RERANK_ENABLED", True)):
            return SemanticRerankResult(
                items=items[:top_k],
                method="disabled",
                applied=False,
                candidate_count=len(items),
            )
        if len(items) <= 1:
            return SemanticRerankResult(
                items=items[:top_k],
                method="passthrough",
                applied=False,
                candidate_count=len(items),
            )

        backend = str(getattr(settings, "RAG_RERANK_BACKEND", "cross_encoder")).strip().lower()
        if backend == "cross_encoder":
            ranked = await self._rerank_cross_encoder(query=query, items=items, top_k=top_k)
            if ranked is not None:
                return SemanticRerankResult(
                    items=ranked,
                    method="cross_encoder",
                    applied=True,
                    candidate_count=len(items),
                )

        ranked = self._rerank_heuristic(query=query, items=items, top_k=top_k)
        return SemanticRerankResult(
            items=ranked,
            method="heuristic",
            applied=True,
            candidate_count=len(items),
        )

    async def _rerank_cross_encoder(
        self, *, query: str, items: list[dict[str, Any]], top_k: int
    ) -> list[dict[str, Any]] | None:
        model = await self._get_cross_encoder()
        if model is None:
            return None

        contents = [self._extract_content(it) for it in items]
        if not any(contents):
            return None

        max_chars = int(getattr(settings, "RAG_RERANK_MAX_CONTENT_CHARS", 1200))
        pairs = [(query, (c or "")[:max_chars]) for c in contents]
        try:
            scores = await asyncio.to_thread(model.predict, pairs)
        except Exception as exc:
            logger.warning("cross_encoder_rerank_failed", error=str(exc))
            return None

        scored = []
        norm_base_scores = self._normalize([self._as_float(it.get("score")) for it in items])
        norm_ce_scores = self._normalize([self._as_float(v) for v in scores])
        profile = self._infer_query_profile(query)
        norm_metadata_scores = self._normalize(
            [self._metadata_alignment_score(it, profile) for it in items]
        )
        norm_recency_scores = self._normalize([self._item_timestamp(it) for it in items])
        ce_weight = float(getattr(settings, "RAG_RERANK_CROSS_ENCODER_WEIGHT", 0.75))
        base_weight = float(getattr(settings, "RAG_RERANK_BASE_SCORE_WEIGHT", 0.25))
        metadata_weight = float(getattr(settings, "RAG_RERANK_METADATA_WEIGHT", 0.10))
        recency_weight = float(getattr(settings, "RAG_RERANK_RECENCY_WEIGHT", 0.05))
        total_weight = ce_weight + base_weight + metadata_weight + recency_weight
        if total_weight <= 0:
            ce_weight, base_weight, metadata_weight, recency_weight = 0.75, 0.25, 0.0, 0.0
            total_weight = 1.0

        for i, it in enumerate(items):
            combined = (
                ce_weight * norm_ce_scores[i]
                + base_weight * norm_base_scores[i]
                + metadata_weight * norm_metadata_scores[i]
                + recency_weight * norm_recency_scores[i]
            ) / total_weight
            scored.append((combined, it))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [it for _, it in scored[:top_k]]

    def _rerank_heuristic(self, *, query: str, items: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        query_tokens = self._tokenize(query)
        profile = self._infer_query_profile(query)
        if not query_tokens:
            return items[:top_k]

        base_scores = self._normalize([self._as_float(it.get("score")) for it in items])
        metadata_scores = self._normalize([self._metadata_alignment_score(it, profile) for it in items])
        recency_scores = self._normalize([self._item_timestamp(it) for it in items])
        text_weight = float(getattr(settings, "RAG_RERANK_HEURISTIC_TEXT_WEIGHT", 0.55))
        base_weight = float(getattr(settings, "RAG_RERANK_HEURISTIC_BASE_WEIGHT", 0.30))
        metadata_weight = float(getattr(settings, "RAG_RERANK_HEURISTIC_METADATA_WEIGHT", 0.10))
        recency_weight = float(getattr(settings, "RAG_RERANK_HEURISTIC_RECENCY_WEIGHT", 0.05))
        total_weight = text_weight + base_weight + metadata_weight + recency_weight
        if total_weight <= 0:
            text_weight, base_weight, metadata_weight, recency_weight = 0.55, 0.30, 0.10, 0.05
            total_weight = 1.0

        ranked: list[tuple[float, dict[str, Any]]] = []

        for idx, it in enumerate(items):
            content = self._extract_content(it).lower()
            c_tokens = self._tokenize(content)
            overlap = 0.0
            if c_tokens:
                overlap = len(query_tokens.intersection(c_tokens)) / max(1, len(query_tokens))
            phrase_bonus = 0.15 if query.lower()[:80] in content else 0.0
            heuristic = min(1.0, overlap + phrase_bonus)
            score = (
                text_weight * heuristic
                + base_weight * base_scores[idx]
                + metadata_weight * metadata_scores[idx]
                + recency_weight * recency_scores[idx]
            ) / total_weight
            ranked.append((score, it))

        ranked.sort(key=lambda x: x[0], reverse=True)
        return [it for _, it in ranked[:top_k]]

    async def _get_cross_encoder(self):
        if self._cross_encoder is not None:
            return self._cross_encoder
        if self._cross_encoder_failed:
            return None
        if CrossEncoder is None:
            self._cross_encoder_failed = True
            return None

        async with self._lock:
            if self._cross_encoder is not None:
                return self._cross_encoder
            if self._cross_encoder_failed:
                return None
            model_name = str(
                getattr(
                    settings,
                    "RAG_RERANK_CROSS_ENCODER_MODEL",
                    "cross-encoder/ms-marco-MiniLM-L-6-v2",
                )
            )
            try:
                self._cross_encoder = await asyncio.to_thread(CrossEncoder, model_name)
                logger.info("cross_encoder_loaded", model=model_name)
                return self._cross_encoder
            except Exception as exc:
                self._cross_encoder_failed = True
                logger.warning(
                    "cross_encoder_unavailable_fallback_heuristic",
                    model=model_name,
                    error=str(exc),
                )
                return None

    def _extract_content(self, item: dict[str, Any]) -> str:
        if not isinstance(item, dict):
            return ""
        return (
            str(item.get("content") or "")
            or str((item.get("payload") or {}).get("content") or "")
            or str(item.get("page_content") or "")
        )

    def _tokenize(self, text: str) -> set[str]:
        raw = re.findall(r"[a-zA-Z0-9_]{3,}", text or "")
        return {t.lower() for t in raw}

    def _infer_query_profile(self, query: str) -> dict[str, Any]:
        tokens = self._tokenize(query or "")
        text = (query or "").lower()

        code_intent = bool(
            tokens.intersection(
                {"code", "codigo", "python", "typescript", "javascript", "funcao", "function"}
            )
            or any(marker in text for marker in (".py", ".ts", ".js", "stack trace", "traceback"))
        )
        policy_intent = bool(
            tokens.intersection({"lgpd", "gdpr", "privacy", "compliance", "policy", "termos"})
        )
        chat_intent = bool(tokens.intersection({"conversa", "conversation", "chat", "historico"}))

        preferred_semantic_types: set[str] = set()
        if code_intent:
            preferred_semantic_types.update({"code", "technical_doc"})
        if policy_intent:
            preferred_semantic_types.update({"policy_legal"})

        preferred_metadata_types: set[str] = set()
        if chat_intent:
            preferred_metadata_types.add("chat_msg")
        else:
            preferred_metadata_types.add("doc_chunk")

        return {
            "preferred_semantic_types": preferred_semantic_types,
            "preferred_metadata_types": preferred_metadata_types,
        }

    def _metadata_alignment_score(self, item: dict[str, Any], profile: dict[str, Any]) -> float:
        metadata = self._extract_metadata(item)
        if not metadata:
            return 0.0

        score = 0.0
        metadata_type = str(metadata.get("type") or "").strip().lower()
        semantic_doc_type = str(metadata.get("semantic_doc_type") or "").strip().lower()

        preferred_metadata_types = profile.get("preferred_metadata_types", set())
        preferred_semantic_types = profile.get("preferred_semantic_types", set())

        if metadata_type and metadata_type in preferred_metadata_types:
            score += 0.7
        if semantic_doc_type and semantic_doc_type in preferred_semantic_types:
            score += 1.0
        return min(1.0, score)

    def _extract_metadata(self, item: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(item, dict):
            return {}
        meta = item.get("metadata")
        if isinstance(meta, dict):
            return meta
        payload = item.get("payload")
        if isinstance(payload, dict) and isinstance(payload.get("metadata"), dict):
            return payload.get("metadata") or {}
        return {}

    def _item_timestamp(self, item: dict[str, Any]) -> float:
        metadata = self._extract_metadata(item)
        raw = metadata.get("timestamp")
        try:
            return float(raw)
        except Exception:
            return 0.0

    def _as_float(self, value: Any) -> float:
        try:
            return float(value)
        except Exception:
            return 0.0

    def _normalize(self, values: list[float]) -> list[float]:
        if not values:
            return []
        finite = [v if math.isfinite(v) else 0.0 for v in values]
        lo, hi = min(finite), max(finite)
        if hi <= lo:
            return [1.0 for _ in finite]
        return [(v - lo) / (hi - lo) for v in finite]


_semantic_reranker_service: SemanticRerankerService | None = None


def get_semantic_reranker() -> SemanticRerankerService:
    global _semantic_reranker_service
    if _semantic_reranker_service is None:
        _semantic_reranker_service = SemanticRerankerService()
    return _semantic_reranker_service
