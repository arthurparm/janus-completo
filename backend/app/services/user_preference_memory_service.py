from __future__ import annotations

import hashlib
import math
import re
import time
from typing import Any

import structlog
from qdrant_client import models as qdrant_models

from app.core.embeddings.embedding_manager import aembed_text
from app.core.memory.generative_memory import generative_memory_service
from app.db.vector_store import (
    aget_or_create_collection,
    build_user_memory_collection_name,
    get_async_qdrant_client,
)

logger = structlog.get_logger(__name__)


class UserPreferenceMemoryService:
    """Captures and retrieves persistent user preferences (do/don't)."""

    _SIGNAL_TERMS = (
        "prefiro",
        "não quero",
        "nao quero",
        "não use",
        "nao use",
        "não faça",
        "nao faça",
        "sempre",
        "evite",
        "quero que você",
        "quero que voce",
        "daqui pra frente",
        "lembre",
        "considere",
    )

    _DONT_TERMS = (
        "não use",
        "nao use",
        "não faça",
        "nao faça",
        "não faca",
        "nao faca",
        "não quero",
        "nao quero",
        "evite",
    )

    def should_inspect_message(self, message: str) -> bool:
        text = str(message or "").strip().lower()
        if len(text) < 6:
            return False
        return any(term in text for term in self._SIGNAL_TERMS)

    def extract_preference(self, message: str) -> dict[str, Any] | None:
        text = str(message or "").strip()
        if not text or not self.should_inspect_message(text):
            return None

        lowered = text.lower()
        kind = "dont" if any(term in lowered for term in self._DONT_TERMS) else "do"

        confidence = 0.78
        if "daqui pra frente" in lowered or "sempre" in lowered:
            confidence = 0.9
        if "não use" in lowered or "nao use" in lowered or "não faça" in lowered or "nao faça" in lowered:
            confidence = 0.92
        if "considere" in lowered:
            confidence = min(confidence, 0.76)

        instruction = self._normalize_instruction_text(text)
        if len(instruction) < 6:
            return None

        return {
            "should_persist": True,
            "preference_kind": kind,
            "instruction_text": instruction,
            "source_span": text[:400],
            "scope": self._infer_scope(lowered),
            "confidence": confidence,
            "stability_score": self._infer_stability_score(lowered),
        }

    async def maybe_capture_from_message(
        self,
        *,
        message: str,
        user_id: str | None,
        conversation_id: str | None,
        threshold: float = 0.75,
    ) -> dict[str, Any] | None:
        if not user_id:
            return None

        extracted = self.extract_preference(message)
        if not extracted:
            return None
        if not extracted.get("should_persist"):
            return None
        if float(extracted.get("confidence") or 0.0) < threshold:
            return None

        dedupe_key = self._dedupe_key(
            user_id=str(user_id),
            preference_kind=str(extracted["preference_kind"]),
            instruction_text=str(extracted["instruction_text"]),
        )
        exists = await self._preference_exists(user_id=str(user_id), dedupe_key=dedupe_key)
        if exists:
            return {"status": "duplicate", "dedupe_key": dedupe_key, **extracted}

        now_ms = int(time.time() * 1000)
        resolved_conversation = str(conversation_id) if conversation_id else None
        await self._deactivate_scope_conflicts(
            user_id=str(user_id),
            scope=str(extracted["scope"]),
            keep_dedupe_key=dedupe_key,
        )
        metadata = {
            "type": "user_preference",
            "memory_subtype": "user_preference",
            "memory_class": "semantic",
            "preference_kind": extracted["preference_kind"],
            "instruction_text": extracted["instruction_text"],
            "scope": extracted["scope"],
            "confidence": float(extracted["confidence"]),
            "importance": 8.5 if str(extracted["preference_kind"]) == "dont" else 7.5,
            "retention_policy": "persistent",
            "recall_policy": "always",
            "sensitivity": "normal",
            "stability_score": float(extracted.get("stability_score") or 0.88),
            "user_id": str(user_id),
            "session_id": resolved_conversation,
            "conversation_id": resolved_conversation,
            "source_role": "user",
            "origin": "chat.user_preference_extractor",
            "source_channel": "chat",
            "dedupe_key": dedupe_key,
            "timestamp": now_ms,
            "ts_ms": now_ms,
            "active": True,
        }
        content = self._build_preference_content(
            preference_kind=str(extracted["preference_kind"]),
            instruction_text=str(extracted["instruction_text"]),
        )
        try:
            exp = await generative_memory_service.add_memory(content, type="semantic", metadata=metadata)
            return {
                "status": "created",
                "id": getattr(exp, "id", None),
                "dedupe_key": dedupe_key,
                **extracted,
            }
        except Exception as exc:
            logger.warning("user_preference_capture_failed", error=str(exc), user_id=str(user_id))
            return None

    async def list_preferences(
        self,
        *,
        user_id: str,
        conversation_id: str | None = None,
        limit: int = 20,
        active_only: bool = True,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        collection_name = await aget_or_create_collection(
            build_user_memory_collection_name(user_id)
        )
        client = get_async_qdrant_client()

        must: list[qdrant_models.FieldCondition] = [
            qdrant_models.FieldCondition(
                key="metadata.user_id", match=qdrant_models.MatchValue(value=str(user_id))
            ),
            qdrant_models.FieldCondition(
                key="metadata.type", match=qdrant_models.MatchValue(value="user_preference")
            ),
        ]
        if active_only:
            must.append(
                qdrant_models.FieldCondition(
                    key="metadata.active", match=qdrant_models.MatchValue(value=True)
                )
            )
        if conversation_id:
            must.append(
                qdrant_models.FieldCondition(
                    key="metadata.conversation_id",
                    match=qdrant_models.MatchValue(value=str(conversation_id)),
                )
            )
        qfilter = qdrant_models.Filter(must=must)

        points: list[Any] = []
        used_vector_query = False
        if query:
            try:
                vec = await aembed_text(query)
                res = await client.query_points(
                    collection_name=collection_name,
                    query=vec,
                    limit=max(limit * 3, limit),
                    with_payload=True,
                    query_filter=qfilter,
                )
                points = getattr(res, "points", res) or []
                used_vector_query = True
            except Exception as exc:
                logger.warning("user_preference_query_embed_failed", error=str(exc))
                scroll_limit = min(200, max(limit * 5, limit))
                points, _ = await client.scroll(
                    collection_name=collection_name,
                    scroll_filter=qfilter,
                    limit=scroll_limit,
                    with_payload=True,
                )
        else:
            scroll_limit = min(200, max(limit * 5, limit))
            points, _ = await client.scroll(
                collection_name=collection_name,
                scroll_filter=qfilter,
                limit=scroll_limit,
                with_payload=True,
            )

        items = [self._point_to_preference_item(point) for point in points]
        deduped: dict[str, dict[str, Any]] = {}
        for item in items:
            key = str(item.get("dedupe_key") or item.get("instruction_text") or item.get("content") or item.get("id"))
            current = deduped.get(key)
            if current is None or int(item.get("ts_ms") or 0) > int(current.get("ts_ms") or 0):
                deduped[key] = item

        ranked = sorted(
            deduped.values(),
            key=lambda item: self._preference_rank(item),
            reverse=True,
        )
        if query and not used_vector_query:
            qnorm = str(query).lower()
            ranked = [
                item for item in ranked
                if qnorm in str(item.get("instruction_text") or "").lower()
                or qnorm in str(item.get("content") or "").lower()
            ]
        return ranked[:limit]

    def format_preference_context(self, items: list[dict[str, Any]]) -> str | None:
        if not items:
            return None

        do_items: list[str] = []
        dont_items: list[str] = []
        for item in items:
            instruction = str(item.get("instruction_text") or item.get("content") or "").strip()
            if not instruction:
                continue
            if str(item.get("preference_kind") or "").lower() == "dont":
                dont_items.append(instruction)
            else:
                do_items.append(instruction)

        if not do_items and not dont_items:
            return None

        lines = [
            "Preferências e Perfil:",
            "- Use estas preferências para ajustar tom, profundidade e formato da resposta.",
        ]
        if do_items:
            lines.append("FAZER:")
            lines.extend(f"- {text}" for text in do_items[:5])
        if dont_items:
            lines.append("NÃO FAZER:")
            lines.extend(f"- {text}" for text in dont_items[:5])
        return "\n".join(lines)

    def _infer_scope(self, lowered_text: str) -> str:
        text = lowered_text.lower()
        if "emoji" in text:
            return "style"
        if "curt" in text or "diret" in text or "detalh" in text:
            return "verbosity"
        if "portugu" in text or "english" in text or "ingl" in text:
            return "language"
        if "tópico" in text or "topico" in text or "lista" in text or "bullet" in text:
            return "format"
        if "passo" in text or "workflow" in text or "procedimento" in text:
            return "workflow"
        if "segurança" in text or "seguranca" in text or "risco" in text:
            return "safety"
        return "other"

    def _infer_stability_score(self, lowered_text: str) -> float:
        text = lowered_text.lower()
        if "daqui pra frente" in text or "sempre" in text:
            return 0.94
        if "prefiro" in text or "não quero" in text or "nao quero" in text:
            return 0.88
        return 0.8

    def _normalize_instruction_text(self, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
        cleaned = re.sub(r"^\s*(janus[:,]?\s*)?", "", cleaned, flags=re.IGNORECASE)
        return cleaned[:500]

    def _dedupe_key(self, *, user_id: str, preference_kind: str, instruction_text: str) -> str:
        base = f"{user_id}:{preference_kind}:{self._normalize_for_hash(instruction_text)}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def _normalize_for_hash(self, text: str) -> str:
        lowered = str(text or "").lower()
        lowered = re.sub(r"[\W_]+", " ", lowered)
        return re.sub(r"\s+", " ", lowered).strip()

    async def _preference_exists(self, *, user_id: str, dedupe_key: str) -> bool:
        try:
            items = await self.list_preferences(user_id=user_id, limit=50, active_only=True)
            return any(str(item.get("dedupe_key")) == dedupe_key for item in items)
        except Exception as exc:
            logger.warning("user_preference_dedupe_check_failed", error=str(exc), user_id=user_id)
            return False

    async def _deactivate_scope_conflicts(
        self,
        *,
        user_id: str,
        scope: str,
        keep_dedupe_key: str,
    ) -> None:
        try:
            items = await self.list_preferences(user_id=user_id, limit=50, active_only=True)
            conflicting_ids = [
                str(item.get("id") or "").strip()
                for item in items
                if str(item.get("scope") or "") == str(scope)
                and str(item.get("dedupe_key") or "") != keep_dedupe_key
                and str(item.get("id") or "").strip()
            ]
            if not conflicting_ids:
                return
            client = get_async_qdrant_client()
            collection_name = await aget_or_create_collection(
                build_user_memory_collection_name(user_id)
            )
            now_ms = int(time.time() * 1000)
            for point_id in conflicting_ids:
                existing = await client.retrieve(
                    collection_name=collection_name,
                    ids=[point_id],
                    with_payload=True,
                    with_vectors=False,
                )
                payload = getattr(existing[0], "payload", {}) if existing else {}
                metadata = dict((payload or {}).get("metadata") or {})
                metadata.update(
                    {
                        "active": False,
                        "superseded_at": now_ms,
                        "superseded_reason": "scope_replaced",
                    }
                )
                await client.set_payload(
                    collection_name=collection_name,
                    payload={"metadata": metadata},
                    points=[point_id],
                )
        except Exception as exc:
            logger.warning("user_preference_scope_deactivate_failed", error=str(exc), user_id=user_id)

    def _build_preference_content(self, *, preference_kind: str, instruction_text: str) -> str:
        label = "NÃO FAZER" if preference_kind == "dont" else "FAZER"
        return f"Preferência do usuário ({label}): {instruction_text}"

    def _point_to_preference_item(self, point: Any) -> dict[str, Any]:
        payload = getattr(point, "payload", {}) or {}
        meta = payload.get("metadata") or {}
        ts_ms = self._coerce_ts_ms(payload.get("ts_ms")) or self._coerce_ts_ms(meta.get("timestamp"))
        return {
            "id": str(getattr(point, "id", "")),
            "content": payload.get("content", ""),
            "ts_ms": ts_ms,
            "score": getattr(point, "score", None),
            "active": bool(meta.get("active", True)),
            "preference_kind": meta.get("preference_kind"),
            "instruction_text": meta.get("instruction_text"),
            "scope": meta.get("scope"),
            "confidence": meta.get("confidence"),
            "user_id": meta.get("user_id"),
            "conversation_id": meta.get("conversation_id") or meta.get("session_id"),
            "session_id": meta.get("session_id"),
            "origin": meta.get("origin"),
            "dedupe_key": meta.get("dedupe_key"),
            "memory_class": meta.get("memory_class"),
            "retention_policy": meta.get("retention_policy"),
            "recall_policy": meta.get("recall_policy"),
            "sensitivity": meta.get("sensitivity"),
            "stability_score": meta.get("stability_score"),
            "metadata": meta,
        }

    def _coerce_ts_ms(self, value: Any | None) -> int | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            try:
                parsed = float(value)
                return int(parsed)
            except Exception:
                return None
        return None

    def _preference_rank(self, item: dict[str, Any]) -> float:
        base_score = float(item.get("score") or 0.0)
        confidence = float(item.get("confidence") or 0.0)
        ts_ms = int(item.get("ts_ms") or 0)
        now_ms = int(time.time() * 1000)
        age_hours = max(0.0, (now_ms - ts_ms) / 3_600_000.0) if ts_ms else 24.0
        recency = math.pow(0.995, age_hours)
        return base_score + (confidence * 0.5) + (recency * 0.4)


user_preference_memory_service = UserPreferenceMemoryService()
