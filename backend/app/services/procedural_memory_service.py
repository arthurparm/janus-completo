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


class ProceduralMemoryService:
    """Stores recurring work instructions as durable user procedures."""

    _SIGNAL_TERMS = (
        "sempre",
        "daqui pra frente",
        "toda vez",
        "quando eu pedir",
        "termine com",
        "comece com",
        "responda com",
        "use o formato",
        "siga este formato",
        "quero que voce",
        "quero que você",
        "me entregue",
        "nos proximos pedidos",
        "nos próximos pedidos",
    )

    def should_inspect_message(self, message: str) -> bool:
        text = str(message or "").strip().lower()
        if len(text) < 12:
            return False
        return any(term in text for term in self._SIGNAL_TERMS)

    def extract_rule(self, message: str) -> dict[str, Any] | None:
        text = str(message or "").strip()
        if not text or not self.should_inspect_message(text):
            return None

        lowered = text.lower()
        instruction = self._normalize_instruction_text(text)
        if len(instruction) < 10:
            return None

        confidence = 0.82
        if "sempre" in lowered or "toda vez" in lowered or "daqui pra frente" in lowered:
            confidence = 0.92
        if "termine com" in lowered or "responda com" in lowered:
            confidence = max(confidence, 0.88)

        return {
            "should_persist": True,
            "instruction_text": instruction,
            "scope": self._infer_scope(lowered),
            "procedure_kind": self._infer_procedure_kind(lowered),
            "confidence": confidence,
            "stability_score": 0.94 if confidence >= 0.9 else 0.88,
        }

    async def maybe_capture_from_message(
        self,
        *,
        message: str,
        user_id: str | None,
        conversation_id: str | None,
        threshold: float = 0.8,
    ) -> dict[str, Any] | None:
        if not user_id:
            return None

        extracted = self.extract_rule(message)
        if not extracted or not extracted.get("should_persist"):
            return None
        if float(extracted.get("confidence") or 0.0) < threshold:
            return None

        dedupe_key = self._dedupe_key(
            user_id=str(user_id),
            scope=str(extracted["scope"]),
            instruction_text=str(extracted["instruction_text"]),
        )
        if await self._rule_exists(user_id=str(user_id), dedupe_key=dedupe_key):
            return {"status": "duplicate", "dedupe_key": dedupe_key, **extracted}

        await self._deactivate_scope_conflicts(
            user_id=str(user_id),
            scope=str(extracted["scope"]),
            keep_dedupe_key=dedupe_key,
        )
        now_ms = int(time.time() * 1000)
        resolved_conversation = str(conversation_id) if conversation_id else None
        metadata = {
            "type": "procedural_rule",
            "memory_subtype": "procedural_rule",
            "memory_class": "procedural",
            "procedure_kind": extracted["procedure_kind"],
            "instruction_text": extracted["instruction_text"],
            "scope": extracted["scope"],
            "confidence": float(extracted["confidence"]),
            "importance": 8.8,
            "retention_policy": "persistent",
            "recall_policy": "always",
            "sensitivity": "normal",
            "stability_score": float(extracted.get("stability_score") or 0.9),
            "user_id": str(user_id),
            "session_id": resolved_conversation,
            "conversation_id": resolved_conversation,
            "source_role": "user",
            "origin": "chat.procedural_extractor",
            "source_channel": "chat",
            "dedupe_key": dedupe_key,
            "timestamp": now_ms,
            "ts_ms": now_ms,
            "active": True,
        }
        content = f"Instrução procedural do usuário: {extracted['instruction_text']}"
        try:
            exp = await generative_memory_service.add_memory(
                content,
                type="procedural",
                metadata=metadata,
            )
            return {
                "status": "created",
                "id": getattr(exp, "id", None),
                "dedupe_key": dedupe_key,
                **extracted,
            }
        except Exception as exc:
            logger.warning("procedural_memory_capture_failed", error=str(exc), user_id=str(user_id))
            return None

    async def list_rules(
        self,
        *,
        user_id: str,
        conversation_id: str | None = None,
        limit: int = 10,
        active_only: bool = True,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        collection_name = await aget_or_create_collection(build_user_memory_collection_name(user_id))
        client = get_async_qdrant_client()

        must: list[qdrant_models.FieldCondition] = [
            qdrant_models.FieldCondition(
                key="metadata.user_id",
                match=qdrant_models.MatchValue(value=str(user_id)),
            ),
            qdrant_models.FieldCondition(
                key="metadata.type",
                match=qdrant_models.MatchValue(value="procedural_rule"),
            ),
        ]
        if active_only:
            must.append(
                qdrant_models.FieldCondition(
                    key="metadata.active",
                    match=qdrant_models.MatchValue(value=True),
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
                logger.warning("procedural_memory_query_embed_failed", error=str(exc))
        if not points:
            points, _ = await client.scroll(
                collection_name=collection_name,
                scroll_filter=qfilter,
                limit=min(200, max(limit * 5, limit)),
                with_payload=True,
            )

        items = [self._point_to_rule_item(point) for point in points]
        deduped: dict[str, dict[str, Any]] = {}
        for item in items:
            key = str(item.get("scope") or item.get("dedupe_key") or item.get("id"))
            current = deduped.get(key)
            if current is None or int(item.get("ts_ms") or 0) > int(current.get("ts_ms") or 0):
                deduped[key] = item
        ranked = sorted(deduped.values(), key=self._rule_rank, reverse=True)
        if query and not used_vector_query:
            qnorm = str(query).lower()
            ranked = [
                item
                for item in ranked
                if qnorm in str(item.get("instruction_text") or "").lower()
                or qnorm in str(item.get("content") or "").lower()
            ]
        return ranked[:limit]

    def format_procedural_context(self, items: list[dict[str, Any]]) -> str | None:
        if not items:
            return None
        lines = [
            "Instruções de Trabalho:",
            "- Estas são instruções persistentes do usuário.",
            "- Siga-as por padrão, salvo se a mensagem atual pedir algo diferente.",
        ]
        for item in items[:5]:
            instruction = str(item.get("instruction_text") or item.get("content") or "").strip()
            if instruction:
                lines.append(f"- {instruction}")
        return "\n".join(lines) if len(lines) > 1 else None

    async def _rule_exists(self, *, user_id: str, dedupe_key: str) -> bool:
        try:
            items = await self.list_rules(user_id=user_id, limit=50, active_only=True)
            return any(str(item.get("dedupe_key")) == dedupe_key for item in items)
        except Exception as exc:
            logger.warning("procedural_memory_dedupe_check_failed", error=str(exc), user_id=user_id)
            return False

    async def _deactivate_scope_conflicts(
        self,
        *,
        user_id: str,
        scope: str,
        keep_dedupe_key: str,
    ) -> None:
        try:
            items = await self.list_rules(user_id=user_id, limit=50, active_only=True)
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
            collection_name = await aget_or_create_collection(build_user_memory_collection_name(user_id))
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
            logger.warning("procedural_memory_scope_deactivate_failed", error=str(exc), user_id=user_id)

    def _normalize_instruction_text(self, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
        cleaned = re.sub(r"^\s*(janus[:,]?\s*)?", "", cleaned, flags=re.IGNORECASE)
        return cleaned[:500]

    def _infer_scope(self, lowered_text: str) -> str:
        text = lowered_text.lower()
        if "proximos passos" in text or "próximos passos" in text or "termine com" in text:
            return "closing"
        if "topico" in text or "tópico" in text or "lista" in text or "formato" in text:
            return "format"
        if "workflow" in text or "passo" in text or "rotina" in text:
            return "workflow"
        if "estudo" in text:
            return "study"
        return "interaction"

    def _infer_procedure_kind(self, lowered_text: str) -> str:
        text = lowered_text.lower()
        if "termine" in text or "comece" in text:
            return "response_structure"
        if "workflow" in text or "rotina" in text:
            return "workflow"
        if "estudo" in text:
            return "study_routine"
        return "interaction_rule"

    def _normalize_for_hash(self, text: str) -> str:
        lowered = str(text or "").lower()
        lowered = re.sub(r"[\W_]+", " ", lowered)
        return re.sub(r"\s+", " ", lowered).strip()

    def _dedupe_key(self, *, user_id: str, scope: str, instruction_text: str) -> str:
        base = f"{user_id}:{scope}:{self._normalize_for_hash(instruction_text)}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def _point_to_rule_item(self, point: Any) -> dict[str, Any]:
        payload = getattr(point, "payload", {}) or {}
        meta = payload.get("metadata") or {}
        ts_ms = self._coerce_ts_ms(payload.get("ts_ms")) or self._coerce_ts_ms(meta.get("timestamp"))
        return {
            "id": str(getattr(point, "id", "")),
            "content": payload.get("content", ""),
            "ts_ms": ts_ms,
            "score": getattr(point, "score", None),
            "active": bool(meta.get("active", True)),
            "instruction_text": meta.get("instruction_text"),
            "procedure_kind": meta.get("procedure_kind"),
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
                return int(float(value))
            except Exception:
                return None
        return None

    def _rule_rank(self, item: dict[str, Any]) -> float:
        base_score = float(item.get("score") or 0.0)
        confidence = float(item.get("confidence") or 0.0)
        stability = float(item.get("stability_score") or 0.0)
        ts_ms = int(item.get("ts_ms") or 0)
        now_ms = int(time.time() * 1000)
        age_hours = max(0.0, (now_ms - ts_ms) / 3_600_000.0) if ts_ms else 24.0
        recency = math.pow(0.998, age_hours)
        return base_score + (confidence * 0.6) + (stability * 0.8) + (recency * 0.2)


procedural_memory_service = ProceduralMemoryService()
