from __future__ import annotations

import time
from typing import Any

import structlog
from qdrant_client import models as qdrant_models

from app.config import settings
from app.core.infrastructure.logging_config import TRACE_ID
from app.core.memory.security import decrypt_text, encrypt_text, get_active_key_id
from app.db.vector_store import aget_or_create_collection, build_user_secret_collection_name, get_async_qdrant_client
from app.repositories.observability_repository import record_audit_event_direct

logger = structlog.get_logger(__name__)


class SecretKeyRotationService:
    """
    Recriptografia gradual da secret memory (Qdrant) sem downtime.

    Estratégia:
    - decripta usando metadados atuais (kid/enc) e fallbacks do keyring;
    - recripta usando a chave ativa (MEMORY_ACTIVE_KEY_ID);
    - atualiza payload (content + metadata.enc + metadata.kid) via upsert;
    - processa em lotes pequenos e repetíveis.
    """

    async def reencrypt_batch(
        self,
        *,
        limit: int = 100,
        active_only: bool = True,
    ) -> dict[str, Any]:
        provider = str(getattr(settings, "MEMORY_ENCRYPTION_PROVIDER", "keyring") or "keyring").strip()
        if provider == "vault_transit":
            return {"status": "skipped", "reason": "vault_transit_handles_rotation"}
        active_kid = get_active_key_id()
        if not active_kid:
            return {"status": "skipped", "reason": "no_active_key_id"}

        collection_name = await aget_or_create_collection(build_user_secret_collection_name())
        client = get_async_qdrant_client()

        must: list[qdrant_models.FieldCondition] = []
        if active_only:
            must.append(
                qdrant_models.FieldCondition(
                    key="metadata.active",
                    match=qdrant_models.MatchValue(value=True),
                )
            )
        qfilter = qdrant_models.Filter(must=must) if must else None

        points, next_page_offset = await client.scroll(
            collection_name=collection_name,
            scroll_filter=qfilter,
            limit=max(1, int(limit)),
            with_payload=True,
            with_vectors=True,
        )

        updated = 0
        skipped = 0
        failures = 0
        for point in points or []:
            try:
                payload = getattr(point, "payload", {}) or {}
                meta = payload.get("metadata") or {}
                current_kid = meta.get("kid")
                enc = meta.get("enc")

                if enc == "fernet" and str(current_kid or "") == str(active_kid):
                    skipped += 1
                    continue

                encrypted_content = str(payload.get("content") or "")
                plain = decrypt_text(encrypted_content, meta)

                new_cipher, new_enc = encrypt_text(plain, require_key=True)
                payload["content"] = new_cipher
                meta["enc"] = new_enc
                meta["kid"] = str(active_kid)
                meta["rekeyed_at_ms"] = int(time.time() * 1000)
                payload["metadata"] = meta

                await client.upsert(
                    collection_name=collection_name,
                    points=[
                        qdrant_models.PointStruct(
                            id=getattr(point, "id"),
                            vector=getattr(point, "vector"),
                            payload=payload,
                        )
                    ],
                )
                updated += 1
            except Exception as exc:
                failures += 1
                logger.warning("secret_reencrypt_failed", error=str(exc))

        try:
            record_audit_event_direct(
                user_id=None,
                endpoint="secret_memory",
                action="secret_reencrypt_batch",
                tool="secret_key_rotation",
                status="success" if failures == 0 else "partial",
                trace_id=TRACE_ID.get(),
                details_json={
                    "collection": collection_name,
                    "active_key_id": str(active_kid),
                    "updated": int(updated),
                    "skipped": int(skipped),
                    "failures": int(failures),
                    "next_offset": str(next_page_offset) if next_page_offset else None,
                },
            )
        except Exception:
            pass

        return {
            "status": "ok",
            "collection": collection_name,
            "active_key_id": str(active_kid),
            "updated": updated,
            "skipped": skipped,
            "failures": failures,
            "next_offset": next_page_offset,
        }


secret_key_rotation_service = SecretKeyRotationService()
