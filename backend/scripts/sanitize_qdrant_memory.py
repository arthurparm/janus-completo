from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from qdrant_client import AsyncQdrantClient, models

from app.config import settings
from app.db.vector_store import (
    aensure_collection,
    build_deterministic_point_id,
    build_user_chat_collection_name,
    build_user_docs_collection_name,
    build_user_memory_collection_name,
)

LEGACY_USER_PATTERN = re.compile(r"^user_(?!chat_|docs_|memory_)(?P<user_id>[A-Za-z0-9_-]+)$")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sanitiza memórias do Qdrant e migra coleções legadas user_<id>."
    )
    parser.add_argument("--qdrant-url", default=None)
    parser.add_argument("--qdrant-api-key", default=None)
    parser.add_argument("--neo4j-uri", default=None)
    parser.add_argument("--neo4j-user", default=None)
    parser.add_argument("--neo4j-password", default=None)
    parser.add_argument("--output-json", default="outputs/qa/qdrant_sanitize_report.json")
    parser.add_argument("--drop-legacy", action="store_true")
    parser.add_argument("--purge-self-study", action="store_true")
    parser.add_argument("--skip-neo4j-cleanup", action="store_true")
    parser.add_argument("--self-study-url", default=None)
    parser.add_argument("--self-study-bearer-token", default=None)
    parser.add_argument("--self-study-mode", default="full")
    return parser.parse_args()


def _normalize_base_url(value: str | None) -> str:
    if value:
        return value.rstrip("/")
    scheme = "https" if bool(getattr(settings, "QDRANT_HTTPS", False)) else "http"
    return f"{scheme}://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}"


def _http_post_json(url: str, body: dict[str, Any], *, bearer_token: str | None = None) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload) if payload else {}


async def _list_collection_names(client: AsyncQdrantClient) -> list[str]:
    result = await client.get_collections()
    return [item.name for item in (result.collections or [])]


async def _scroll_all_points(client: AsyncQdrantClient, collection_name: str) -> list[models.Record]:
    points: list[models.Record] = []
    offset: str | int | None = None
    while True:
        batch, next_offset = await client.scroll(
            collection_name=collection_name,
            limit=256,
            with_payload=True,
            with_vectors=True,
            offset=offset,
        )
        points.extend(batch or [])
        if next_offset is None or not batch:
            break
        offset = next_offset
    return points


async def _snapshot_collections(client: AsyncQdrantClient) -> dict[str, dict[str, Any]]:
    snapshot: dict[str, dict[str, Any]] = {}
    for name in await _list_collection_names(client):
        info = await client.get_collection(collection_name=name)
        snapshot[name] = {
            "points_count": int(getattr(info, "points_count", 0) or 0),
            "indexed_vectors_count": int(getattr(info, "indexed_vectors_count", 0) or 0),
            "segments_count": int(getattr(info, "segments_count", 0) or 0),
            "status": str(getattr(info, "status", "")),
        }
    return snapshot


def _classify_legacy_target(payload: dict[str, Any]) -> str:
    meta = payload.get("metadata") or {}
    point_type = str(meta.get("type") or payload.get("type") or "").strip().lower()
    if point_type == "chat_msg":
        return "chat"
    if point_type == "doc_chunk":
        return "docs"
    return "memory"


def _normalize_timestamp_ms(payload: dict[str, Any], meta: dict[str, Any]) -> int:
    candidate = meta.get("ts_ms") or payload.get("ts_ms") or meta.get("timestamp")
    try:
        return int(float(candidate))
    except Exception:
        return int(time.time() * 1000)


def _normalize_payload_for_target(
    *,
    user_id: str,
    payload: dict[str, Any],
    target: str,
) -> tuple[str, dict[str, Any]]:
    meta = dict(payload.get("metadata") or {})
    content = str(payload.get("content") or "")
    ts_ms = _normalize_timestamp_ms(payload, meta)
    meta.setdefault("user_id", str(user_id))
    meta.setdefault("timestamp", ts_ms)
    meta.setdefault("ts_ms", ts_ms)

    if target == "chat":
        session_id = str(meta.get("session_id") or meta.get("conversation_id") or "legacy")
        role = str(meta.get("role") or "assistant")
        meta.setdefault("conversation_id", session_id)
        meta.setdefault("origin", "migration.legacy_chat")
        composite_id = str(
            payload.get("composite_id")
            or build_deterministic_point_id("chat-msg-composite", user_id, session_id, role, ts_ms, content)
        )
        point_id = build_deterministic_point_id("chat-msg", user_id, session_id, role, ts_ms, content)
        normalized = {
            "content": content,
            "type": "chat_msg",
            "ts_ms": ts_ms,
            "composite_id": composite_id,
            "metadata": meta | {"type": "chat_msg", "session_id": session_id, "role": role},
        }
        return point_id, normalized

    if target == "docs":
        doc_id = str(meta.get("doc_id") or f"legacy-doc:{user_id}")
        index = int(meta.get("index") or 0)
        norm = re.sub(r"\s+", " ", content).strip().lower()
        content_hash = str(meta.get("content_hash") or hashlib.sha256(norm.encode("utf-8")).hexdigest())
        meta.setdefault("origin", "migration.legacy_docs")
        meta.setdefault("status", str(meta.get("status") or "unique"))
        meta["doc_id"] = doc_id
        meta["index"] = index
        meta["content_hash"] = content_hash
        composite_id = str(
            payload.get("composite_id") or f"doc:{user_id}:{doc_id}:{index}:{content_hash}"
        )
        point_id = build_deterministic_point_id("doc-chunk", user_id, doc_id, index, content_hash)
        normalized = {
            "content": content,
            "type": "doc_chunk",
            "ts_ms": ts_ms,
            "composite_id": composite_id,
            "metadata": meta | {"type": "doc_chunk"},
        }
        return point_id, normalized

    point_type = str(meta.get("type") or payload.get("type") or "memory_item")
    meta.setdefault("origin", "migration.legacy_memory")
    stable_id = str(payload.get("id") or meta.get("id") or meta.get("pointer_id") or "")
    if not stable_id:
        stable_id = build_deterministic_point_id("user-memory", user_id, point_type, ts_ms, content)
    composite_id = str(payload.get("composite_id") or f"legacy:{user_id}:{point_type}:{stable_id}")
    normalized = {
        "content": content,
        "type": point_type,
        "timestamp": payload.get("timestamp"),
        "ts_ms": ts_ms,
        "composite_id": composite_id,
        "metadata": meta | {"type": point_type},
    }
    return stable_id, normalized


async def _migrate_legacy_collection(
    client: AsyncQdrantClient,
    legacy_name: str,
    *,
    drop_legacy: bool,
) -> dict[str, Any]:
    match = LEGACY_USER_PATTERN.match(legacy_name)
    if not match:
        return {"legacy_collection": legacy_name, "skipped": True}
    user_id = match.group("user_id")
    target_names = {
        "chat": build_user_chat_collection_name(user_id),
        "docs": build_user_docs_collection_name(user_id),
        "memory": build_user_memory_collection_name(user_id),
    }
    migrated = {"chat": 0, "docs": 0, "memory": 0}
    points = await _scroll_all_points(client, legacy_name)
    for target_name in target_names.values():
        await aensure_collection(client, target_name)

    batched_points: dict[str, list[models.PointStruct]] = {"chat": [], "docs": [], "memory": []}
    for point in points:
        payload = getattr(point, "payload", None) or {}
        vector = getattr(point, "vector", None)
        target = _classify_legacy_target(payload)
        point_id, normalized_payload = _normalize_payload_for_target(
            user_id=user_id,
            payload=payload,
            target=target,
        )
        batched_points[target].append(
            models.PointStruct(id=point_id, vector=vector or [0.0] * 1536, payload=normalized_payload)
        )
        migrated[target] += 1

    for target, points_batch in batched_points.items():
        if not points_batch:
            continue
        await client.upsert(collection_name=target_names[target], points=points_batch, wait=True)

    if drop_legacy:
        await client.delete_collection(collection_name=legacy_name)

    return {
        "legacy_collection": legacy_name,
        "points_read": len(points),
        "migrated": migrated,
        "dropped": bool(drop_legacy),
    }


async def _purge_self_study_points(client: AsyncQdrantClient) -> int:
    collection_name = getattr(settings, "QDRANT_COLLECTION_EPISODIC", "janus_episodic_memory")
    qfilter = models.Filter(
        must=[
            models.FieldCondition(
                key="metadata.origin", match=models.MatchValue(value="self_study")
            )
        ]
    )
    before = await client.count(collection_name=collection_name, count_filter=qfilter, exact=True)
    await client.delete(
        collection_name=collection_name,
        points_selector=models.FilterSelector(filter=qfilter),
        wait=True,
    )
    return int(getattr(before, "count", 0) or 0)


async def _cleanup_neo4j_self_study(uri: str, user: str, password: str) -> dict[str, int]:
    from neo4j import AsyncGraphDatabase

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    deleted = {"self_memory_nodes": 0, "experience_nodes": 0}
    try:
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (m:SelfMemory)
                WITH collect(m) AS nodes, count(m) AS total
                FOREACH (node IN nodes | DETACH DELETE node)
                RETURN total
                """
            )
            record = await result.single()
            deleted["self_memory_nodes"] = int(record[0] if record else 0)

            result = await session.run(
                """
                MATCH (e:Experience {origin: 'self_study'})
                WITH collect(e) AS nodes, count(e) AS total
                FOREACH (node IN nodes | DETACH DELETE node)
                RETURN total
                """
            )
            record = await result.single()
            deleted["experience_nodes"] = int(record[0] if record else 0)
    finally:
        await driver.close()
    return deleted


async def _trigger_self_study(url: str, bearer_token: str | None, mode: str) -> dict[str, Any]:
    return await asyncio.to_thread(
        _http_post_json,
        url,
        {"mode": mode, "reason": "qdrant_sanitize_rebuild"},
        bearer_token=bearer_token,
    )


async def _async_main(args: argparse.Namespace) -> dict[str, Any]:
    base_url = _normalize_base_url(args.qdrant_url)
    client = AsyncQdrantClient(
        url=base_url,
        api_key=args.qdrant_api_key or (
            settings.QDRANT_API_KEY.get_secret_value() if settings.QDRANT_API_KEY else None
        ),
        timeout=30,
    )
    report: dict[str, Any] = {
        "qdrant_url": base_url,
        "snapshot_before": await _snapshot_collections(client),
        "legacy_migrations": [],
    }
    collection_names = await _list_collection_names(client)
    for collection_name in collection_names:
        if not LEGACY_USER_PATTERN.match(collection_name):
            continue
        report["legacy_migrations"].append(
            await _migrate_legacy_collection(
                client,
                collection_name,
                drop_legacy=bool(args.drop_legacy),
            )
        )

    if args.purge_self_study:
        report["purged_self_study_points"] = await _purge_self_study_points(client)
        if not args.skip_neo4j_cleanup and args.neo4j_uri and args.neo4j_user and args.neo4j_password:
            report["neo4j_cleanup"] = await _cleanup_neo4j_self_study(
                args.neo4j_uri,
                args.neo4j_user,
                args.neo4j_password,
            )

    if args.self_study_url:
        report["self_study_trigger"] = await _trigger_self_study(
            args.self_study_url,
            args.self_study_bearer_token,
            args.self_study_mode,
        )

    report["snapshot_after"] = await _snapshot_collections(client)
    await client.close()
    return report


def main() -> None:
    args = _parse_args()
    report = asyncio.run(_async_main(args))
    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
