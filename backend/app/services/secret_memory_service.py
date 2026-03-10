from __future__ import annotations

import hashlib
import re
import time
from typing import Any

import structlog
from qdrant_client import models as qdrant_models

from app.core.embeddings.embedding_manager import aembed_text
from app.core.memory.security import decrypt_text, encrypt_text
from app.db.vector_store import (
    aget_or_create_collection,
    build_deterministic_point_id,
    build_user_secret_collection_name,
    get_async_qdrant_client,
)

logger = structlog.get_logger(__name__)


class SecretMemoryService:
    """Stores user secrets in a separate encrypted namespace with explicit recall only."""

    _SECRET_TERMS = (
        "senha",
        "token",
        "api key",
        "apikey",
        "chave",
        "credencial",
        "codigo de acesso",
        "código de acesso",
        "segredo",
    )
    _EXPLICIT_RECALL_PATTERNS = (
        r"\bqual (?:e|é)\b.*\b(?:senha|token|segredo|codigo de acesso|código de acesso|api key|chave)\b",
        r"\bme lembra\b.*\b(?:senha|token|segredo|codigo de acesso|código de acesso|api key|chave)\b",
        r"\blembra\b.*\b(?:senha|token|segredo|codigo de acesso|código de acesso|api key|chave)\b",
        r"\brecupere\b.*\b(?:senha|token|segredo|codigo de acesso|código de acesso|api key|chave)\b",
        r"\bmostre\b.*\b(?:senha|token|segredo|codigo de acesso|código de acesso|api key|chave)\b",
    )

    def should_inspect_message(self, message: str) -> bool:
        text = str(message or "").strip().lower()
        if len(text) < 8:
            return False
        return any(term in text for term in self._SECRET_TERMS)

    def should_authorize_prompt_recall(self, message: str) -> bool:
        text = str(message or "").strip().lower()
        if not self.should_inspect_message(text):
            return False
        return any(re.search(pattern, text) for pattern in self._EXPLICIT_RECALL_PATTERNS)

    def extract_secret(self, message: str) -> dict[str, Any] | None:
        text = str(message or "").strip()
        lowered = text.lower()
        if not text or not self.should_inspect_message(text):
            return None

        label_match = re.search(
            r"(?P<label>(?:senha|token|api key|apikey|chave|credencial|codigo de acesso|código de acesso)(?: [^:=]{0,80})?)\s*(?:é|eh|=|:)\s*(?P<value>.+)$",
            lowered,
        )
        if not label_match:
            return None
        value_match = re.search(
            r"(?:é|eh|=|:)\s*(?P<value>.+)$",
            text,
            flags=re.IGNORECASE,
        )
        label = str(label_match.group("label") or "").strip()
        value = self._normalize_secret_value(str((value_match.group("value") if value_match else "") or ""))
        if not label or not value:
            return None

        secret_type = self._infer_secret_type(label)
        normalized_label = self._normalize_label(label)
        return {
            "should_persist": True,
            "secret_label": normalized_label,
            "secret_type": secret_type,
            "secret_scope": self._infer_scope(normalized_label),
            "secret_value": value[:1000],
            "masked_value": self._mask_value(value),
            "confidence": 0.96,
        }

    async def maybe_capture_from_message(
        self,
        *,
        message: str,
        user_id: str | None,
        conversation_id: str | None,
        threshold: float = 0.9,
    ) -> dict[str, Any] | None:
        if not user_id:
            return None
        extracted = self.extract_secret(message)
        if not extracted or not extracted.get("should_persist"):
            return None
        if float(extracted.get("confidence") or 0.0) < threshold:
            return None
        stored = await self.store_secret(
            user_id=str(user_id),
            label=str(extracted["secret_label"]),
            value=str(extracted["secret_value"]),
            secret_type=str(extracted["secret_type"]),
            secret_scope=str(extracted["secret_scope"]),
            conversation_id=conversation_id,
            source="chat.secret_extractor",
        )
        return {"status": "created", **stored}

    async def store_secret(
        self,
        *,
        user_id: str,
        label: str,
        value: str,
        secret_type: str,
        secret_scope: str | None = None,
        conversation_id: str | None = None,
        source: str = "memory.secret_api",
    ) -> dict[str, Any]:
        collection_name = await aget_or_create_collection(build_user_secret_collection_name(user_id))
        client = get_async_qdrant_client()
        now_ms = int(time.time() * 1000)
        normalized_label = self._normalize_label(label)
        point_id = build_deterministic_point_id("user-secret", user_id, secret_type, normalized_label)
        encrypted_value, enc_method = encrypt_text(str(value))
        summary_text = f"Segredo do usuário: {normalized_label}"
        try:
            vector = await aembed_text(summary_text)
        except Exception:
            vector = [0.0] * 1536
        payload = {
            "content": encrypted_value,
            "type": "secret",
            "ts_ms": now_ms,
            "composite_id": f"secret:{user_id}:{point_id}",
            "metadata": {
                "type": "secret",
                "memory_class": "secret",
                "retention_policy": "persistent",
                "recall_policy": "explicit_only",
                "sensitivity": "secret",
                "stability_score": 0.98,
                "scope": "user",
                "source_channel": "chat" if source.startswith("chat.") else "api",
                "user_id": str(user_id),
                "conversation_id": str(conversation_id) if conversation_id else None,
                "secret_type": str(secret_type),
                "secret_label": normalized_label,
                "secret_scope": str(secret_scope or "personal"),
                "masked_value": self._mask_value(value),
                "origin": source,
                "timestamp": now_ms,
                "ts_ms": now_ms,
                "active": True,
                "enc": enc_method,
                "consent_source": source,
                "consent_captured_at": now_ms,
            },
        }
        await client.upsert(
            collection_name=collection_name,
            points=[qdrant_models.PointStruct(id=point_id, vector=vector, payload=payload)],
        )
        return {
            "id": point_id,
            "secret_label": normalized_label,
            "secret_type": str(secret_type),
            "secret_scope": str(secret_scope or "personal"),
            "masked_value": self._mask_value(value),
        }

    async def list_secrets(
        self,
        *,
        user_id: str,
        query: str | None = None,
        conversation_id: str | None = None,
        limit: int = 20,
        active_only: bool = True,
        reveal: bool = False,
    ) -> list[dict[str, Any]]:
        collection_name = await aget_or_create_collection(build_user_secret_collection_name(user_id))
        client = get_async_qdrant_client()
        must: list[qdrant_models.FieldCondition] = [
            qdrant_models.FieldCondition(
                key="metadata.user_id",
                match=qdrant_models.MatchValue(value=str(user_id)),
            )
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
        if query:
            try:
                vector = await aembed_text(query)
                result = await client.query_points(
                    collection_name=collection_name,
                    query=vector,
                    limit=max(limit * 3, limit),
                    with_payload=True,
                    query_filter=qfilter,
                )
                points = list(getattr(result, "points", result) or [])
            except Exception as exc:
                logger.warning("secret_memory_query_embed_failed", error=str(exc), user_id=user_id)
        if not points:
            points, _ = await client.scroll(
                collection_name=collection_name,
                scroll_filter=qfilter,
                limit=min(200, max(limit * 5, limit)),
                with_payload=True,
            )

        items = [self._point_to_secret_item(point, reveal=reveal) for point in points]
        deduped: dict[str, dict[str, Any]] = {}
        for item in items:
            key = str(item.get("secret_label") or item.get("id"))
            current = deduped.get(key)
            if current is None or int(item.get("ts_ms") or 0) > int(current.get("ts_ms") or 0):
                deduped[key] = item
        ranked = sorted(deduped.values(), key=lambda item: int(item.get("ts_ms") or 0), reverse=True)
        return ranked[:limit]

    async def build_authorized_prompt_context(
        self,
        *,
        user_id: str,
        message: str,
        conversation_id: str | None = None,
        limit: int = 3,
    ) -> str | None:
        if not self.should_authorize_prompt_recall(message):
            return None
        items = await self.list_secrets(
            user_id=user_id,
            query=message,
            conversation_id=conversation_id,
            limit=limit,
            reveal=True,
        )
        if not items:
            return None
        lines = [
            "Segredos Autorizados:",
            "- O usuário pediu explicitamente estes valores nesta resposta.",
            "- Você pode citá-los literalmente ao responder esta pergunta específica.",
        ]
        for item in items[:limit]:
            label = str(item.get("secret_label") or "segredo").strip()
            secret_value = str(item.get("secret_value") or "").strip()
            if secret_value:
                lines.append(f"- {label}: {secret_value}")
        return "\n".join(lines) if len(lines) > 1 else None

    def _point_to_secret_item(self, point: Any, *, reveal: bool) -> dict[str, Any]:
        payload = getattr(point, "payload", {}) or {}
        meta = payload.get("metadata") or {}
        encrypted_content = str(payload.get("content") or "")
        value = decrypt_text(encrypted_content, meta) if reveal else None
        return {
            "id": str(getattr(point, "id", "")),
            "ts_ms": meta.get("ts_ms") or meta.get("timestamp") or payload.get("ts_ms"),
            "secret_label": meta.get("secret_label"),
            "secret_type": meta.get("secret_type"),
            "secret_scope": meta.get("secret_scope"),
            "masked_value": meta.get("masked_value"),
            "active": bool(meta.get("active", True)),
            "memory_class": meta.get("memory_class"),
            "retention_policy": meta.get("retention_policy"),
            "recall_policy": meta.get("recall_policy"),
            "sensitivity": meta.get("sensitivity"),
            "stability_score": meta.get("stability_score"),
            "conversation_id": meta.get("conversation_id"),
            "origin": meta.get("origin"),
            "secret_value": value if reveal else None,
            "metadata": meta,
        }

    def _infer_secret_type(self, label: str) -> str:
        lowered = str(label or "").lower()
        if "token" in lowered:
            return "token"
        if "api key" in lowered or "apikey" in lowered:
            return "api_key"
        if "codigo de acesso" in lowered or "código de acesso" in lowered:
            return "access_code"
        if "chave" in lowered:
            return "key"
        if "credencial" in lowered:
            return "credential"
        return "password"

    def _infer_scope(self, label: str) -> str:
        lowered = str(label or "").lower()
        if "wifi" in lowered or "wi-fi" in lowered:
            return "network"
        if "api" in lowered:
            return "integration"
        return "personal"

    def _normalize_label(self, label: str) -> str:
        lowered = str(label or "").strip().lower()
        lowered = re.sub(r"\s+", " ", lowered)
        return lowered[:120]

    def _normalize_secret_value(self, value: str) -> str:
        normalized = str(value or "").strip()
        normalized = normalized.rstrip(" \t\r\n")
        normalized = re.sub(r"[.!?,;:]+$", "", normalized)
        return normalized[:1000]

    def _mask_value(self, value: str) -> str:
        raw = str(value or "")
        if len(raw) <= 4:
            return "*" * len(raw)
        return f"{raw[:2]}{'*' * max(2, len(raw) - 4)}{raw[-2:]}"


secret_memory_service = SecretMemoryService()
