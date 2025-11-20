import structlog
import hashlib
import re
from typing import List, Dict, Any, Optional
from uuid import uuid4
from qdrant_client import QdrantClient, models
from app.db.vector_store import get_or_create_collection, get_qdrant_client
from app.core.infrastructure.logging_config import TRACE_ID, USER_ID
from app.repositories.observability_repository import record_audit_event_direct
try:
    from opentelemetry import trace  # type: ignore
    _OTEL = True
    _tracer = trace.get_tracer(__name__)
except Exception:
    _OTEL = False
    from contextlib import nullcontext
    _tracer = None
from app.core.embeddings.embedding_manager import embed_texts
try:
    from prometheus_client import Counter  # type: ignore
except Exception:
    class Counter:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass
        def inc(self, *args, **kwargs):
            pass
        def labels(self, *args, **kwargs):
            return self

logger = structlog.get_logger(__name__)

class DocumentIngestionService:
    def __init__(self, memory_service):
        self._memory_service = memory_service

    def _extract_text_plain(self, data: bytes) -> str:
        import time as _t
        _t0 = _t.perf_counter()
        try:
            s = data.decode("utf-8", errors="ignore")
            try:
                _DOC_PARSE_TOTAL.labels("plain", "success").inc()
                _DOC_PARSE_LATENCY.labels("plain", "success").observe(max(0.0, _t.perf_counter() - _t0))
            except Exception:
                pass
            return s
        except Exception:
            try:
                _DOC_PARSE_TOTAL.labels("plain", "error").inc()
                _DOC_PARSE_LATENCY.labels("plain", "error").observe(max(0.0, _t.perf_counter() - _t0))
            except Exception:
                pass
            return ""

    def _extract_text_html(self, data: bytes) -> str:
        import time as _t
        _t0 = _t.perf_counter()
        try:
            try:
                html = data.decode("utf-8", errors="ignore")
            except Exception:
                html = ""
            html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
            html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text).strip()
            try:
                _DOC_PARSE_TOTAL.labels("html", "success").inc()
                _DOC_PARSE_LATENCY.labels("html", "success").observe(max(0.0, _t.perf_counter() - _t0))
            except Exception:
                pass
            return text
        except Exception:
            try:
                _DOC_PARSE_TOTAL.labels("html", "error").inc()
                _DOC_PARSE_LATENCY.labels("html", "error").observe(max(0.0, _t.perf_counter() - _t0))
            except Exception:
                pass
            return ""

    def _extract_text_docx(self, data: bytes) -> str:
        import time as _t
        _t0 = _t.perf_counter()
        try:
            import zipfile
            from xml.etree import ElementTree as ET
            from io import BytesIO
            zf = zipfile.ZipFile(BytesIO(data))
            with zf.open("word/document.xml") as f:
                xml = f.read()
            root = ET.fromstring(xml)
            texts: List[str] = []
            for elem in root.iter():
                if elem.text:
                    texts.append(elem.text)
            txt = " ".join(texts)
            txt = re.sub(r"\s+", " ", txt).strip()
            try:
                _DOC_PARSE_TOTAL.labels("docx", "success").inc()
                _DOC_PARSE_LATENCY.labels("docx", "success").observe(max(0.0, _t.perf_counter() - _t0))
            except Exception:
                pass
            return txt
        except Exception:
            try:
                _DOC_PARSE_TOTAL.labels("docx", "error").inc()
                _DOC_PARSE_LATENCY.labels("docx", "error").observe(max(0.0, _t.perf_counter() - _t0))
            except Exception:
                pass
            return ""

    def _extract_text_pdf(self, data: bytes) -> str:
        import time as _t
        _t0 = _t.perf_counter()
        try:
            import io
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(io.BytesIO(data))
                texts: List[str] = []
                for page in getattr(reader, "pages", []) or []:
                    try:
                        texts.append(page.extract_text() or "")
                    except Exception:
                        pass
                s = " ".join([t for t in texts if t]).strip()
            except Exception:
                s = ""
            try:
                _DOC_PARSE_TOTAL.labels("pdf", "success").inc()
                _DOC_PARSE_LATENCY.labels("pdf", "success").observe(max(0.0, _t.perf_counter() - _t0))
            except Exception:
                pass
            return s
        except Exception:
            try:
                _DOC_PARSE_TOTAL.labels("pdf", "error").inc()
                _DOC_PARSE_LATENCY.labels("pdf", "error").observe(max(0.0, _t.perf_counter() - _t0))
            except Exception:
                pass
            return ""

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        if not text:
            return []
        chunks: List[str] = []
        start = 0
        n = len(text)
        while start < n:
            end = min(n, start + chunk_size)
            chunk = text[start:end]
            chunks.append(chunk)
            if end >= n:
                break
            start = end - overlap
            if start < 0:
                start = 0
        return chunks

    async def ingest_file(self, user_id: str, filename: str, content_type: str, data: bytes, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        doc_id = f"doc:{user_id}:{uuid4().hex}"
        span_cm = (_tracer.start_as_current_span("doc.ingest") if _OTEL else nullcontext())
        with span_cm as span:
            if _OTEL and span is not None:
                try:
                    tid = TRACE_ID.get()
                    sid = USER_ID.get()
                    if tid and tid != "-":
                        span.set_attribute("janus.trace_id", tid)
                    if sid and sid != "-":
                        span.set_attribute("janus.user_id", sid)
                    span.set_attribute("doc.filename", filename)
                    span.set_attribute("doc.content_type", (content_type or "").lower())
                except Exception:
                    pass
        text = ""
        ct = (content_type or "").lower()
        import time as _t
        _t0_ext = _t.perf_counter()
        if ct.startswith("text/plain"):
            text = self._extract_text_plain(data)
        elif ct.startswith("text/html") or ct.startswith("application/xhtml"):
            text = self._extract_text_html(data)
        elif ct.startswith("application/pdf") or filename.lower().endswith(".pdf"):
            text = self._extract_text_pdf(data)
        elif ct == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or filename.lower().endswith(".docx"):
            text = self._extract_text_docx(data)
        else:
            return {"doc_id": doc_id, "chunks": 0, "status": "unsupported_content_type"}
        try:
            _DOC_INGEST_LATENCY.observe(max(0.0, _t.perf_counter() - _t0_ext))
        except Exception:
            pass

        try:
            from app.config import settings
            chunk_size = int(getattr(settings, "DOC_CHUNK_SIZE", 1000) or 1000)
            overlap = int(getattr(settings, "DOC_CHUNK_OVERLAP", 100) or 100)
        except Exception:
            chunk_size = 1000
            overlap = 100
        _t0_chunk = _t.perf_counter()
        chunks = self._chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        try:
            if _OTEL and span is not None:
                span.set_attribute("doc.chunk_count", len(chunks))
            try:
                _DOC_INGEST_CHUNKS_COUNT.observe(float(len(chunks)))
            except Exception:
                pass
        except Exception:
            pass
        try:
            _DOC_INGEST_LATENCY.observe(max(0.0, _t.perf_counter() - _t0_chunk))
        except Exception:
            pass
        if not chunks:
            try:
                _DOC_INGEST_FILES_TOTAL.labels("empty").inc()
            except Exception:
                pass
            try:
                _DOC_INGEST_FILES_USER_TOTAL.labels(str(user_id), "empty").inc()
            except Exception:
                pass
            try:
                record_audit_event_direct({
                    "user_id": int(user_id) if user_id is not None else None,
                    "endpoint": "doc:ingest",
                    "action": "ingest",
                    "tool": "documents",
                    "status": "empty",
                    "latency_ms": None,
                    "trace_id": TRACE_ID.get(),
                })
            except Exception:
                pass
            return {"doc_id": doc_id, "chunks": 0, "status": "empty"}

        _t0 = __import__("time").perf_counter()
        vectors = embed_texts(chunks)
        try:
            _DOC_INGEST_LATENCY.observe(max(0.0, __import__("time").perf_counter() - _t0))
        except Exception:
            pass
        collection_name = get_or_create_collection(f"user_{user_id}")
        client: QdrantClient = get_qdrant_client()
        try:
            from qdrant_client import models as _models
            max_points_user = int(getattr(settings, "DOC_INDEX_MAX_POINTS_PER_USER", 500000) or 500000)
            qfilter_user = _models.Filter(must=[
                _models.FieldCondition(key="metadata.type", match=_models.MatchValue(value="doc_chunk")),
                _models.FieldCondition(key="metadata.user_id", match=_models.MatchValue(value=str(user_id))),
            ])
            cnt_user = client.count(collection_name=collection_name, count_filter=qfilter_user, exact=True)
            cur_user = int(getattr(cnt_user, "count", 0) or 0)
            if cur_user >= max_points_user:
                try:
                    _DOC_INGEST_FILES_TOTAL.labels("quota_exceeded").inc()
                except Exception:
                    pass
                return {"doc_id": doc_id, "chunks": 0, "status": "quota_exceeded"}
        except Exception:
            pass
        points: List[models.PointStruct] = []
        ts_ms = __import__("time").time()
        ts_ms = int(ts_ms * 1000)
        for i, vec in enumerate(vectors):
            pid = f"doc:{user_id}:{doc_id}:{i}"
            # Hash de conteúdo normalizado para dedupe
            norm = re.sub(r"\s+", " ", chunks[i]).strip().lower()
            content_hash = hashlib.sha256(norm.encode("utf-8")).hexdigest()
            # Verificar duplicidade existente
            dup_status = "unique"
            try:
                from qdrant_client import models as _models
                qfilter_hash = _models.Filter(must=[
                    _models.FieldCondition(key="metadata.content_hash", match=_models.MatchValue(value=content_hash)),
                    _models.FieldCondition(key="metadata.user_id", match=_models.MatchValue(value=str(user_id))),
                ])
                cnt_hash = client.count(collection_name=collection_name, count_filter=qfilter_hash, exact=True)
                if int(getattr(cnt_hash, "count", 0) or 0) > 0:
                    dup_status = "duplicate"
            except Exception:
                pass
            payload = {
                "metadata": {
                    "type": "doc_chunk",
                    "user_id": user_id,
                    "doc_id": doc_id,
                    "file_name": filename,
                    "timestamp": ts_ms,
                    "index": i,
                    "content_hash": content_hash,
                    "status": dup_status,
                    "conversation_id": conversation_id,
                },
                "content": chunks[i][:2000],
            }
            points.append(models.PointStruct(id=pid, vector=vec, payload=payload))
        client.upsert(collection_name=collection_name, points=points)
        try:
            _DOC_INGEST_POINTS_TOTAL.labels("success").inc(len(points))
            _DOC_INGEST_FILES_TOTAL.labels("indexed").inc()
            _DOC_INGEST_POINTS_USER_TOTAL.labels(str(user_id)).inc(len(points))
            _DOC_INGEST_FILES_USER_TOTAL.labels(str(user_id), "indexed").inc()
            _DOC_INGEST_LATENCY.observe(__import__("time").perf_counter() - _t0)
        except Exception:
            pass
        try:
            record_audit_event_direct({
                "user_id": int(user_id) if user_id is not None else None,
                "endpoint": "doc:ingest",
                "action": "ingest",
                "tool": "documents",
                "status": "indexed",
                "latency_ms": int((__import__("time").perf_counter() - _t0) * 1000),
                "trace_id": TRACE_ID.get(),
            })
        except Exception:
            pass
        return {"doc_id": doc_id, "chunks": len(chunks), "status": "indexed"}
_DOC_INGEST_POINTS_TOTAL = Counter("doc_ingest_points_total", "Pontos indexados na ingestão de documentos", ["outcome"])
_DOC_INGEST_FILES_TOTAL = Counter("doc_ingest_files_total", "Arquivos ingeridos", ["status"])
try:
    from prometheus_client import Histogram, Counter as _CounterUser  # type: ignore
    _DOC_INGEST_LATENCY = Histogram("doc_ingest_latency_seconds", "Latência da ingestão de documentos")
    _DOC_INGEST_CHUNKS_COUNT = Histogram("doc_ingest_chunks_count", "Distribuição de chunks por ingestão")  # type: ignore
    _DOC_INGEST_POINTS_USER_TOTAL = _CounterUser("doc_ingest_points_user_total", "Pontos indexados por usuário", ["user_id"])  # type: ignore
    _DOC_INGEST_FILES_USER_TOTAL = _CounterUser("doc_ingest_files_user_total", "Arquivos ingeridos por usuário", ["user_id", "status"])  # type: ignore
    _DOC_PARSE_LATENCY = Histogram("doc_parse_latency_seconds", "Latência de parsing por tipo", ["type", "outcome"])  # type: ignore
    _DOC_PARSE_TOTAL = _CounterUser("doc_parse_total", "Operações de parsing", ["type", "outcome"])  # type: ignore
except Exception:
    class _NoopHist:
        def observe(self, *a, **k):
            pass
    _DOC_INGEST_LATENCY = _NoopHist()
    class _NoopH:
        def observe(self, *a, **k):
            pass
    _DOC_INGEST_CHUNKS_COUNT = _NoopH()
    class _NoopC:
        def labels(self, *a, **k):
            return self
        def inc(self, *a, **k):
            pass
    _DOC_INGEST_POINTS_USER_TOTAL = _NoopC()
    _DOC_INGEST_FILES_USER_TOTAL = _NoopC()
    _DOC_PARSE_LATENCY = _NoopH()
    _DOC_PARSE_TOTAL = _NoopC()

