from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable, Literal, Sequence

import numpy as np
from numpy.typing import NDArray

from app.config import settings
from app.db.vector_store import (
    build_user_chat_collection_name,
    build_user_docs_collection_name,
    build_user_memory_collection_name,
    get_async_qdrant_client,
)

ExperimentalDomain = Literal["docs", "chat", "memory"]

_DOMAIN_TO_COLLECTION = {
    "docs": build_user_docs_collection_name(),
    "chat": build_user_chat_collection_name(),
    "memory": build_user_memory_collection_name(),
}


class ExperimentalIndexError(RuntimeError):
    """Base error for the experimental retrieval index."""


class ExperimentalIndexNotReadyError(ExperimentalIndexError):
    """Raised when the experimental index was selected but not built."""


@dataclass(frozen=True)
class ExperimentalIndexManifest:
    domain: ExperimentalDomain
    version: str
    backend: str
    source_collection: str
    built_at: str
    point_count: int
    success_count: int
    failure_count: int
    duration_seconds: float
    index_id: str
    files: dict[str, str]
    filters: dict[str, Any]
    quantization: dict[str, Any]


@dataclass(frozen=True)
class ExperimentalBuildResult:
    manifest: ExperimentalIndexManifest
    output_dir: str
    dry_run: bool


@dataclass(frozen=True)
class SearchDiff:
    overlap_ratio: float
    only_active: list[str]
    only_shadow: list[str]


@dataclass
class QuantizedIndexArtifact:
    manifest: ExperimentalIndexManifest
    codes: NDArray[np.float32]
    mins: NDArray[np.float32]
    scales: NDArray[np.float32]
    sign_vector: NDArray[np.float32]
    vector_dimension: int
    point_ids: NDArray[np.str_]
    payloads: list[dict[str, Any]]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _resolve_index_root() -> Path:
    configured = str(
        getattr(settings, "KNOWLEDGE_EXPERIMENTAL_INDEX_ROOT", "workspace/knowledge_experimental")
    ).strip()
    root = Path(configured)
    if not root.is_absolute():
        cwd = Path.cwd()
        root = cwd / configured
    root.mkdir(parents=True, exist_ok=True)
    return root


def _normalize_score(raw_score: float) -> float:
    return float(max(0.0, min(1.0, 0.5 + 0.5 * math.tanh(raw_score))))


def _scope_key(filters: dict[str, Any]) -> str:
    relevant = {
        key: value
        for key, value in filters.items()
        if value not in (None, "", [], {}, ())
    }
    if not relevant:
        return "global"
    digest = sha256(json.dumps(relevant, sort_keys=True).encode("utf-8")).hexdigest()
    return digest[:16]


def _result_identity(item: Any) -> str:
    payload = getattr(item, "payload", None) or {}
    metadata = payload.get("metadata") or {}
    candidates = [
        getattr(item, "id", None),
        metadata.get("doc_id"),
        payload.get("composite_id"),
        metadata.get("session_id"),
        metadata.get("conversation_id"),
    ]
    for candidate in candidates:
        if candidate:
            return str(candidate)
    return "unknown"


def compare_result_sets(active: Sequence[Any], shadow: Sequence[Any]) -> SearchDiff:
    active_ids = [_result_identity(item) for item in active]
    shadow_ids = [_result_identity(item) for item in shadow]
    active_set = set(active_ids)
    shadow_set = set(shadow_ids)
    overlap = active_set.intersection(shadow_set)
    denominator = max(1, max(len(active_set), len(shadow_set)))
    return SearchDiff(
        overlap_ratio=len(overlap) / denominator,
        only_active=sorted(active_set - shadow_set),
        only_shadow=sorted(shadow_set - active_set),
    )


def _point_matches_domain(payload: dict[str, Any], domain: ExperimentalDomain) -> bool:
    metadata = payload.get("metadata") or {}
    point_type = str(metadata.get("type") or payload.get("type") or "").strip().lower()
    if domain == "docs":
        return point_type == "doc_chunk"
    if domain == "chat":
        return point_type == "chat_msg"
    return True


def _point_matches_filters(payload: dict[str, Any], filters: dict[str, Any]) -> bool:
    metadata = payload.get("metadata") or {}
    doc_id = filters.get("doc_id")
    if doc_id and str(metadata.get("doc_id")) != str(doc_id):
        return False
    knowledge_space_id = filters.get("knowledge_space_id")
    if knowledge_space_id and str(metadata.get("knowledge_space_id")) != str(knowledge_space_id):
        return False
    memory_type = filters.get("memory_type")
    if memory_type and str(metadata.get("type")) != str(memory_type):
        return False
    origin = filters.get("origin")
    if origin and str(metadata.get("origin")) != str(origin):
        return False
    session_id = filters.get("session_id")
    if session_id and str(metadata.get("session_id")) != str(session_id):
        return False
    role = filters.get("role")
    if role and str(metadata.get("role")) != str(role):
        return False
    start_ts = filters.get("start_ts")
    end_ts = filters.get("end_ts")
    if start_ts is not None or end_ts is not None:
        timestamp = int(metadata.get("timestamp") or 0)
        if start_ts is not None and timestamp < int(start_ts):
            return False
        if end_ts is not None and timestamp > int(end_ts):
            return False
    exclude_duplicate = bool(filters.get("exclude_duplicate"))
    if exclude_duplicate and str(metadata.get("status")) == "duplicate":
        return False
    return True


class ExperimentalIndexManager:
    """TurboQuant-inspired file-backed retrieval backend for the Knowledge Plane."""

    def __init__(self, root_dir: Path | None = None):
        self._root_dir = root_dir or _resolve_index_root()

    def _version(self) -> str:
        return str(getattr(settings, "KNOWLEDGE_EXPERIMENTAL_INDEX_VERSION", "v1")).strip() or "v1"

    def _backend_name(self) -> str:
        return "turboquant_inspired_rotated_scalar_quantization"

    def _quant_bits(self) -> int:
        return int(getattr(settings, "KNOWLEDGE_EXPERIMENTAL_QUANT_BITS", 8) or 8)

    def _output_dir(self, domain: ExperimentalDomain, filters: dict[str, Any]) -> Path:
        version = self._version()
        scope = _scope_key(filters)
        path = self._root_dir / domain / version / scope
        path.mkdir(parents=True, exist_ok=True)
        return path

    def manifest_path(self, domain: ExperimentalDomain, filters: dict[str, Any] | None = None) -> Path:
        return self._output_dir(domain, filters or {}) / "manifest.json"

    def last_build_summary(self, domain: ExperimentalDomain | None = None) -> dict[str, Any] | None:
        domains: Iterable[ExperimentalDomain]
        if domain is None:
            domains = ("docs", "chat", "memory")
        else:
            domains = (domain,)
        latest: dict[str, Any] | None = None
        latest_ts = ""
        for candidate_domain in domains:
            manifest_path = self.manifest_path(candidate_domain)
            if not manifest_path.exists():
                continue
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            built_at = str(data.get("built_at") or "")
            if built_at >= latest_ts:
                latest = data
                latest_ts = built_at
        return latest

    async def build_index(
        self,
        *,
        domain: ExperimentalDomain,
        user_id: str | None = None,
        knowledge_space_id: str | None = None,
        doc_id: str | None = None,
        rebuild_full: bool = False,
        since_ts: int | None = None,
        dry_run: bool = False,
    ) -> ExperimentalBuildResult:
        filters = {
            "user_id": user_id,
            "knowledge_space_id": knowledge_space_id,
            "doc_id": doc_id,
            "since_ts": since_ts,
        }
        started_at = time.perf_counter()
        source_collection = _DOMAIN_TO_COLLECTION[domain]
        raw_points = await self._read_points(collection_name=source_collection)
        filtered_points: list[tuple[str, NDArray[np.float32], dict[str, Any]]] = []
        failures = 0
        for point in raw_points:
            payload = getattr(point, "payload", None) or {}
            vector = getattr(point, "vector", None)
            point_id = getattr(point, "id", None)
            if point_id is None or vector is None or not _point_matches_domain(payload, domain):
                continue
            if not _point_matches_filters(payload, filters):
                continue
            metadata = payload.get("metadata") or {}
            if since_ts is not None and int(metadata.get("timestamp") or 0) < int(since_ts):
                continue
            try:
                filtered_points.append(
                    (
                        str(point_id),
                        np.asarray(vector, dtype=np.float32),
                        payload,
                    )
                )
            except Exception:
                failures += 1
        output_dir = self._output_dir(domain, filters if not rebuild_full else {})
        manifest = ExperimentalIndexManifest(
            domain=domain,
            version=self._version(),
            backend=self._backend_name(),
            source_collection=source_collection,
            built_at=_utc_now(),
            point_count=len(filtered_points),
            success_count=len(filtered_points),
            failure_count=failures,
            duration_seconds=max(0.0, time.perf_counter() - started_at),
            index_id=f"{domain}:{self._version()}:{_scope_key(filters if not rebuild_full else {})}",
            files={
                "index": str(output_dir / "index.npz"),
                "payloads": str(output_dir / "payloads.json"),
                "report": str(output_dir / "build_report.json"),
            },
            filters=filters if not rebuild_full else {},
            quantization={"bits": self._quant_bits(), "rotation": "random_sign"},
        )
        report = {
            "manifest": asdict(manifest),
            "status": "dry_run" if dry_run else "built",
        }
        if dry_run:
            self._write_report(output_dir=output_dir, report=report)
            return ExperimentalBuildResult(manifest=manifest, output_dir=str(output_dir), dry_run=True)

        if not filtered_points:
            raise ExperimentalIndexError(f"Nenhum ponto elegível encontrado para o domínio '{domain}'.")

        point_ids = [point_id for point_id, _, _ in filtered_points]
        payloads = [payload for _, _, payload in filtered_points]
        vectors = np.stack([vector for _, vector, _ in filtered_points]).astype(np.float32)
        codes, mins, scales, sign_vector = self._quantize_vectors(vectors=vectors, bits=self._quant_bits())

        np.savez_compressed(
            output_dir / "index.npz",
            codes=codes,
            mins=mins,
            scales=scales,
            sign_vector=sign_vector,
            vector_dimension=np.asarray([vectors.shape[1]], dtype=np.int32),
            point_ids=np.asarray(point_ids, dtype="<U128"),
        )
        (output_dir / "payloads.json").write_text(
            json.dumps(payloads, ensure_ascii=False),
            encoding="utf-8",
        )
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(asdict(manifest), ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_report(output_dir=output_dir, report=report)
        return ExperimentalBuildResult(manifest=manifest, output_dir=str(output_dir), dry_run=False)

    async def append_point(
        self,
        *,
        domain: ExperimentalDomain,
        point_id: str,
        vector: Sequence[float],
        payload: dict[str, Any],
    ) -> None:
        artifact = self.load_index(domain=domain)
        payloads = list(artifact.payloads)
        point_ids = list(artifact.point_ids.tolist())
        existed = point_id in point_ids
        if existed:
            idx = point_ids.index(point_id)
            payloads[idx] = payload
        else:
            point_ids.append(point_id)
            payloads.append(payload)
        dequantized = artifact.codes.astype(np.float32) * artifact.scales + artifact.mins
        restored = dequantized * artifact.sign_vector
        vector_array = np.asarray(vector, dtype=np.float32)
        if vector_array.ndim != 1:
            raise ExperimentalIndexError("Vetor experimental inválido para append_point.")
        if vector_array.shape[0] != restored.shape[1]:
            raise ExperimentalIndexError("Dimensão do vetor incompatível com o índice experimental.")
        if existed:
            restored[idx] = vector_array
        else:
            restored = np.vstack([restored, vector_array])
        output_dir = self.manifest_path(domain).parent
        codes, mins, scales, sign_vector = self._quantize_vectors(vectors=restored, bits=self._quant_bits())
        np.savez_compressed(
            output_dir / "index.npz",
            codes=codes,
            mins=mins,
            scales=scales,
            sign_vector=sign_vector,
            vector_dimension=np.asarray([restored.shape[1]], dtype=np.int32),
            point_ids=np.asarray(point_ids, dtype="<U128"),
        )
        (output_dir / "payloads.json").write_text(json.dumps(payloads, ensure_ascii=False), encoding="utf-8")
        manifest_payload = asdict(artifact.manifest)
        manifest_payload["built_at"] = _utc_now()
        manifest_payload["point_count"] = len(point_ids)
        manifest_payload["success_count"] = len(point_ids)
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_index(
        self,
        *,
        domain: ExperimentalDomain,
        filters: dict[str, Any] | None = None,
    ) -> QuantizedIndexArtifact:
        output_dir = self._output_dir(domain, filters or {})
        manifest_path = output_dir / "manifest.json"
        if not manifest_path.exists():
            raise ExperimentalIndexNotReadyError(
                f"Índice experimental do domínio '{domain}' não foi construído em {output_dir}."
            )
        manifest = ExperimentalIndexManifest(**json.loads(manifest_path.read_text(encoding="utf-8")))
        npz = np.load(output_dir / "index.npz")
        payloads = json.loads((output_dir / "payloads.json").read_text(encoding="utf-8"))
        return QuantizedIndexArtifact(
            manifest=manifest,
            codes=np.asarray(npz["codes"], dtype=np.float32),
            mins=np.asarray(npz["mins"], dtype=np.float32),
            scales=np.asarray(npz["scales"], dtype=np.float32),
            sign_vector=np.asarray(npz["sign_vector"], dtype=np.float32),
            vector_dimension=int(np.asarray(npz["vector_dimension"])[0]),
            point_ids=np.asarray(npz["point_ids"]),
            payloads=payloads,
        )

    def search(
        self,
        *,
        domain: ExperimentalDomain,
        query_vector: Sequence[float],
        limit: int,
        filters: dict[str, Any],
    ) -> list[SimpleNamespace]:
        artifact = self.load_index(domain=domain)
        query = np.asarray(query_vector, dtype=np.float32)
        if query.ndim != 1 or query.shape[0] != artifact.vector_dimension:
            raise ExperimentalIndexError("Dimensão do vetor de busca incompatível com o índice experimental.")
        rotated_query = query * artifact.sign_vector
        scores = np.matmul(artifact.codes, rotated_query * artifact.scales) + float(
            np.sum(artifact.mins * rotated_query)
        )
        candidates: list[tuple[float, int]] = []
        for idx, raw_score in enumerate(scores.tolist()):
            payload = artifact.payloads[idx]
            if not _point_matches_domain(payload, domain):
                continue
            if not _point_matches_filters(payload, filters):
                continue
            candidates.append((float(raw_score), idx))
        candidates.sort(key=lambda item: item[0], reverse=True)
        results: list[SimpleNamespace] = []
        for raw_score, idx in candidates[: max(1, limit)]:
            results.append(
                SimpleNamespace(
                    id=str(artifact.point_ids[idx]),
                    score=_normalize_score(raw_score),
                    payload=artifact.payloads[idx],
                )
            )
        return results

    async def _read_points(self, *, collection_name: str) -> list[Any]:
        client = get_async_qdrant_client()
        points: list[Any] = []
        offset: Any = None
        while True:
            batch, offset = await client.scroll(
                collection_name=collection_name,
                limit=256,
                with_payload=True,
                with_vectors=True,
                offset=offset,
            )
            points.extend(batch or [])
            if offset is None:
                break
        return points

    def _write_report(self, *, output_dir: Path, report: dict[str, Any]) -> None:
        report_path = output_dir / "build_report.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def _quantize_vectors(
        self,
        *,
        vectors: NDArray[np.float32],
        bits: int,
    ) -> tuple[NDArray[np.float32], NDArray[np.float32], NDArray[np.float32], NDArray[np.float32]]:
        if vectors.ndim != 2:
            raise ExperimentalIndexError("Os vetores experimentais devem ser uma matriz 2D.")
        if bits < 2 or bits > 8:
            raise ExperimentalIndexError("KNOWLEDGE_EXPERIMENTAL_QUANT_BITS deve estar entre 2 e 8.")
        rng = np.random.default_rng(42)
        sign_vector = rng.choice(np.asarray([-1.0, 1.0], dtype=np.float32), size=vectors.shape[1])
        rotated = vectors * sign_vector
        mins = rotated.min(axis=0).astype(np.float32)
        maxs = rotated.max(axis=0).astype(np.float32)
        levels = float((2**bits) - 1)
        scales = np.maximum((maxs - mins) / max(levels, 1.0), 1e-6).astype(np.float32)
        codes = np.rint((rotated - mins) / scales).astype(np.uint8)
        return codes.astype(np.float32), mins, scales, sign_vector.astype(np.float32)
