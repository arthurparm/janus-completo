import structlog
import re
from typing import List, Dict, Any, Optional
from uuid import uuid4
from qdrant_client import QdrantClient, models
from app.db.vector_store import get_or_create_collection, get_qdrant_client
from app.core.embeddings.embedding_manager import embed_texts

logger = structlog.get_logger(__name__)

class DocumentIngestionService:
    def __init__(self, memory_service):
        self._memory_service = memory_service

    def _extract_text_plain(self, data: bytes) -> str:
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _extract_text_html(self, data: bytes) -> str:
        try:
            html = data.decode("utf-8", errors="ignore")
        except Exception:
            html = ""
        html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
        html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _extract_text_docx(self, data: bytes) -> str:
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
            return txt
        except Exception:
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

    async def ingest_file(self, user_id: str, filename: str, content_type: str, data: bytes) -> Dict[str, Any]:
        doc_id = f"doc:{user_id}:{uuid4().hex}"
        text = ""
        ct = (content_type or "").lower()
        if ct.startswith("text/plain"):
            text = self._extract_text_plain(data)
        elif ct.startswith("text/html") or ct.startswith("application/xhtml"):
            text = self._extract_text_html(data)
        elif ct == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or filename.lower().endswith(".docx"):
            text = self._extract_text_docx(data)
        else:
            return {"doc_id": doc_id, "chunks": 0, "status": "unsupported_content_type"}

        chunks = self._chunk_text(text)
        if not chunks:
            return {"doc_id": doc_id, "chunks": 0, "status": "empty"}

        vectors = embed_texts(chunks)
        collection_name = get_or_create_collection(f"user_{user_id}")
        client: QdrantClient = get_qdrant_client()
        points: List[models.PointStruct] = []
        ts_ms = __import__("time").time()
        ts_ms = int(ts_ms * 1000)
        for i, vec in enumerate(vectors):
            pid = f"doc:{user_id}:{doc_id}:{i}"
            payload = {
                "metadata": {
                    "type": "doc_chunk",
                    "user_id": user_id,
                    "doc_id": doc_id,
                    "file_name": filename,
                    "timestamp": ts_ms,
                    "index": i,
                },
                "content": chunks[i][:2000],
            }
            points.append(models.PointStruct(id=pid, vector=vec, payload=payload))
        client.upsert(collection_name=collection_name, points=points)
        return {"doc_id": doc_id, "chunks": len(chunks), "status": "indexed"}

