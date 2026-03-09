"""
Document Parser Service with hierarchical fallbacks.
Extracts text from various document formats.
"""

import json
import re
import time
import structlog
from app.core.infrastructure.fallback_chain import FallbackChain
from app.core.monitoring.document_metrics import get_metrics_recorder
from app.core.exceptions.document_exceptions import ExtractionFailedError

logger = structlog.get_logger(__name__)


class DocumentParserService:
    """
    Parses documents with fallback strategies.

    Fallback chain:
    1. Specialized parser (PyPDF2, zipfile, BeautifulSoup)
    2. Plain text fallback
    3. Empty string (logged warning)
    """

    def __init__(self):
        self._metrics = get_metrics_recorder()

    def parse(self, data: bytes, content_type: str, filename: str) -> str:
        """
        Parse document with automatic format detection and fallbacks.

        Args:
            data: Raw file bytes
            content_type: MIME type
            filename: Original filename

        Returns:
            Extracted text (empty string if all strategies fail)
        """
        ct = (content_type or "").lower()

        # Determine parser type
        if ct.startswith("text/plain"):
            return self._parse_plain(data)
        elif ct.startswith("application/json") or ct.endswith("+json") or filename.lower().endswith(".json"):
            return self._parse_json(data)
        elif ct.startswith("text/html") or ct.startswith("application/xhtml"):
            return self._parse_html(data)
        elif ct.startswith("application/pdf") or filename.lower().endswith(".pdf"):
            return self._parse_pdf(data)
        elif (
            ct == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            or filename.lower().endswith(".docx")
        ):
            return self._parse_docx(data)
        else:
            logger.warning(
                "unsupported_file_type",
                content_type=content_type,
                filename=filename,
            )
            return ""

    def _parse_plain(self, data: bytes) -> str:
        """Parse plain text file."""
        t0 = time.perf_counter()

        try:
            text = data.decode("utf-8", errors="ignore")
            self._metrics.record_parse("plain", "success", time.perf_counter() - t0)
            return text
        except Exception as e:
            self._metrics.record_parse("plain", "error", time.perf_counter() - t0)
            logger.warning("plain_text_parse_failed", error=str(e))
            return ""

    def _parse_json(self, data: bytes) -> str:
        """Parse JSON files into searchable text lines."""
        t0 = time.perf_counter()

        try:
            raw = data.decode("utf-8", errors="ignore")
            parsed = json.loads(raw)

            lines: list[str] = []

            def _walk(value, path: str = "") -> None:
                if isinstance(value, dict):
                    for key, child in value.items():
                        child_path = f"{path}.{key}" if path else str(key)
                        _walk(child, child_path)
                    return
                if isinstance(value, list):
                    for index, child in enumerate(value):
                        child_path = f"{path}[{index}]" if path else f"[{index}]"
                        _walk(child, child_path)
                    return
                normalized = re.sub(r"\s+", " ", str(value)).strip()
                if not normalized:
                    return
                lines.append(f"{path}: {normalized}" if path else normalized)

            _walk(parsed)

            text = "\n".join(lines).strip()
            if not text:
                text = raw
            self._metrics.record_parse("json", "success", time.perf_counter() - t0)
            return text
        except Exception as e:
            self._metrics.record_parse("json", "error", time.perf_counter() - t0)
            logger.warning("json_parse_failed", error=str(e))
            return ""

    def _parse_html(self, data: bytes) -> str:
        """Parse HTML file."""
        t0 = time.perf_counter()

        try:
            html = data.decode("utf-8", errors="ignore")

            # Strip scripts and styles
            html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
            html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)

            # Remove HTML tags
            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text).strip()

            self._metrics.record_parse("html", "success", time.perf_counter() - t0)
            return text
        except Exception as e:
            self._metrics.record_parse("html", "error", time.perf_counter() - t0)
            logger.warning("html_parse_failed", error=str(e))
            return ""

    def _parse_docx(self, data: bytes) -> str:
        """Parse DOCX file."""
        t0 = time.perf_counter()

        try:
            import zipfile
            from io import BytesIO
            from xml.etree import ElementTree as ET

            zf = zipfile.ZipFile(BytesIO(data))
            with zf.open("word/document.xml") as f:
                xml = f.read()

            root = ET.fromstring(xml)
            texts = [elem.text for elem in root.iter() if elem.text]

            text = " ".join(texts)
            text = re.sub(r"\s+", " ", text).strip()

            self._metrics.record_parse("docx", "success", time.perf_counter() - t0)
            return text
        except Exception as e:
            self._metrics.record_parse("docx", "error", time.perf_counter() - t0)
            logger.warning("docx_parse_failed", error=str(e))
            return ""

    def _parse_pdf(self, data: bytes) -> str:
        """Parse PDF file with fallback strategies."""
        t0 = time.perf_counter()

        # Try PyPDF2
        chain = FallbackChain(
            strategies=[
                lambda: self._parse_pdf_pypdf2(data),
                lambda: self._parse_pdf_minimal(data),
            ],
            component_name="pdf_parse",
        )

        try:
            text = chain.execute()
            self._metrics.record_parse("pdf", "success", time.perf_counter() - t0)
            return text
        except Exception as e:
            self._metrics.record_parse("pdf", "error", time.perf_counter() - t0)
            logger.warning("pdf_parse_all_failed", error=str(e))
            return ""

    def _parse_pdf_pypdf2(self, data: bytes) -> str:
        """Primary PDF parser using PyPDF2."""
        import io
        import PyPDF2

        reader = PyPDF2.PdfReader(io.BytesIO(data))
        texts = []

        for page in getattr(reader, "pages", []) or []:
            try:
                page_text = page.extract_text() or ""
                if page_text:
                    texts.append(page_text)
            except Exception as e:
                logger.debug("pdf_page_extraction_failed", error=str(e))
                continue

        if not texts:
            raise ExtractionFailedError("pdf", "No text extracted from any page")

        return " ".join(texts).strip()

    def _parse_pdf_minimal(self, data: bytes) -> str:
        """Minimal PDF fallback (returns empty - logged)."""
        logger.info("pdf_minimal_fallback_used")
        return ""
