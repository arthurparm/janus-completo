import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import settings


@dataclass(frozen=True)
class DocumentSemanticMetadata:
    doc_type: str
    entities: dict[str, list[str]]
    summary: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_type": self.doc_type,
            "entities": self.entities,
            "summary": self.summary,
            "confidence": self.confidence,
        }


class DocumentSemanticEnrichmentService:
    _TECH_KEYWORDS = (
        "python",
        "fastapi",
        "django",
        "flask",
        "postgres",
        "mysql",
        "redis",
        "neo4j",
        "qdrant",
        "docker",
        "kubernetes",
        "javascript",
        "typescript",
        "react",
        "angular",
        "node",
        "sql",
        "api",
    )

    def enrich(self, *, text: str, filename: str, content_type: str) -> DocumentSemanticMetadata:
        if not bool(getattr(settings, "AI_DOC_ENRICHMENT_ENABLED", True)):
            return DocumentSemanticMetadata(
                doc_type="unknown",
                entities={},
                summary="",
                confidence=0.0,
            )

        max_chars = int(getattr(settings, "AI_DOC_ENRICHMENT_MAX_TEXT_CHARS", 12000) or 12000)
        sample = (text or "")[: max(512, max_chars)]
        doc_type, confidence = self._classify_doc_type(
            text=sample, filename=filename, content_type=content_type
        )
        entities = self._extract_entities(sample)
        summary = self._build_summary(sample)
        return DocumentSemanticMetadata(
            doc_type=doc_type,
            entities=entities,
            summary=summary,
            confidence=confidence,
        )

    def _classify_doc_type(self, *, text: str, filename: str, content_type: str) -> tuple[str, float]:
        lowered = (text or "").lower()
        ct = (content_type or "").lower()
        ext = Path(filename or "").suffix.lower()

        code_exts = {
            ".py",
            ".js",
            ".ts",
            ".tsx",
            ".jsx",
            ".java",
            ".go",
            ".rs",
            ".rb",
            ".php",
            ".cs",
            ".sql",
            ".yml",
            ".yaml",
            ".json",
            ".toml",
        }
        if ext in code_exts:
            return "code", 0.93

        if ct.startswith("text/html") or ext in {".html", ".htm"}:
            return "web_page", 0.86

        if any(
            token in lowered
            for token in (
                "lgpd",
                "gdpr",
                "privacidade",
                "privacy policy",
                "termos de uso",
                "terms of service",
                "contrato",
            )
        ):
            return "policy_legal", 0.85

        if any(
            token in lowered
            for token in (
                "ata da reunião",
                "ata da reuniao",
                "action items",
                "próximos passos",
                "proximos passos",
                "participantes",
                "decisões",
                "decisoes",
            )
        ):
            return "meeting_notes", 0.82

        if any(
            token in lowered
            for token in (
                "jira",
                "incident",
                "incidente",
                "bug",
                "ticket",
                "root cause",
                "postmortem",
            )
        ):
            return "ticket_incident", 0.80

        if "```" in text or "def " in lowered or "class " in lowered:
            return "technical_doc", 0.74

        if re.search(r"\b(api|arquitetura|design|endpoint|microservice)\b", lowered):
            return "technical_doc", 0.72

        return "general", 0.60

    def _extract_entities(self, text: str) -> dict[str, list[str]]:
        max_per_type = int(getattr(settings, "AI_DOC_ENRICHMENT_MAX_ENTITIES_PER_TYPE", 8) or 8)

        emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text or "")
        raw_urls = re.findall(r"https?://[^\s)>\"]+", text or "")
        urls = [u.rstrip(".,;:!?") for u in raw_urls]
        ticket_ids = re.findall(r"\b[A-Z]{2,10}-\d{1,6}\b", text or "")
        dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{2}/\d{2}/\d{4}\b", text or "")
        file_paths = re.findall(
            r"(?:[A-Za-z]:\\[^\s]+|/(?:[A-Za-z0-9._-]+/)+[A-Za-z0-9._-]+)",
            text or "",
        )

        lowered = (text or "").lower()
        technologies = [kw for kw in self._TECH_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", lowered)]

        entities = {
            "emails": self._dedupe_take(emails, max_per_type),
            "urls": self._dedupe_take(urls, max_per_type),
            "ticket_ids": self._dedupe_take(ticket_ids, max_per_type),
            "dates": self._dedupe_take(dates, max_per_type),
            "file_paths": self._dedupe_take(file_paths, max_per_type),
            "technologies": self._dedupe_take(technologies, max_per_type),
        }
        return {k: v for k, v in entities.items() if v}

    def _build_summary(self, text: str) -> str:
        max_chars = int(getattr(settings, "AI_DOC_ENRICHMENT_SUMMARY_MAX_CHARS", 280) or 280)
        clean = re.sub(r"\s+", " ", text or "").strip()
        if not clean:
            return ""

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip()]
        if not sentences:
            return clean[:max_chars]

        preferred = []
        focus_terms = ("objetivo", "problema", "solução", "solucao", "resumo", "conclus")
        for sentence in sentences:
            lowered = sentence.lower()
            if any(term in lowered for term in focus_terms):
                preferred.append(sentence)

        selected: list[str] = []
        if sentences:
            selected.append(sentences[0])
        for sentence in preferred:
            if sentence not in selected:
                selected.append(sentence)
            if len(" ".join(selected)) >= max_chars:
                break
        if len(selected) == 1 and len(sentences) > 1:
            selected.append(sentences[1])

        summary = " ".join(selected).strip()
        if len(summary) > max_chars:
            summary = summary[: max_chars - 3].rstrip() + "..."
        return summary

    @staticmethod
    def _dedupe_take(values: list[str], limit: int) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for value in values:
            val = (value or "").strip()
            if not val:
                continue
            key = val.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(val)
            if len(out) >= max(1, limit):
                break
        return out
