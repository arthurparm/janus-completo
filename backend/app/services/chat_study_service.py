from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import time
from typing import Any
from uuid import uuid4

import structlog

from app.core.llm import ModelPriority, ModelRole
from app.services.chat.chat_citation_service import build_citation_status, collect_chat_citations

logger = structlog.get_logger(__name__)

_MAX_FILE_BYTES = 256 * 1024
_MAX_SNIPPET_LINES = 24
_MAX_CANDIDATES = 6
_IGNORE_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    "outputs",
    "output",
    ".angular",
    ".idea",
    ".vscode",
}
_TEXT_EXTS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".env",
    ".html",
    ".scss",
    ".css",
    ".sql",
    ".txt",
    ".sh",
}


def _repo_root() -> Path:
    env_root = Path(str(os.getenv("CHAT_STUDY_REPO_ROOT", "/app"))).resolve()
    if env_root.exists():
        return env_root
    return Path(__file__).resolve().parents[3]


def _question_tokens(question: str) -> list[str]:
    raw = re.findall(r"[A-Za-z0-9_./:-]{2,}", question.lower())
    stop = {
        "de",
        "da",
        "do",
        "das",
        "dos",
        "para",
        "com",
        "por",
        "the",
        "and",
        "que",
        "sobre",
        "uma",
        "um",
        "como",
        "qual",
        "quais",
        "me",
        "fala",
        "fale",
        "conta",
        "sobre",
        "sua",
        "seu",
    }
    seen: set[str] = set()
    tokens: list[str] = []
    for token in raw:
        if token in stop or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens[:24]


def _looks_text_file(path: Path) -> bool:
    if path.suffix.lower() in _TEXT_EXTS:
        return True
    return path.name.lower() in {"dockerfile", "makefile", "readme"}


def _sanitize_snippet(snippet: str) -> str:
    text = (snippet or "").strip()
    if len(text) > 1600:
        return f"{text[:1597]}..."
    return text


@dataclass
class ChatStudyJob:
    job_id: str
    conversation_id: str
    message_id: str
    question: str
    user_id: str | None
    status: str = "queued"
    progress: int = 0
    placeholder_message: str | None = None
    failure_classification: str | None = None
    final_response: dict[str, Any] | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class ChatStudyService:
    def __init__(
        self,
        *,
        llm_service: Any | None,
        knowledge_service: Any | None,
        autonomy_admin_service: Any | None,
    ) -> None:
        self._llm = llm_service
        self._knowledge = knowledge_service
        self._autonomy_admin = autonomy_admin_service
        self._repo_root = _repo_root()

    async def answer_with_study(
        self,
        *,
        question: str,
        role: ModelRole = ModelRole.ORCHESTRATOR,
        priority: ModelPriority = ModelPriority.FAST_AND_CHEAP,
        user_id: str | None = None,
        conversation_id: str | None = None,
        progress_cb: Any | None = None,
    ) -> dict[str, Any]:
        async def _progress(value: int, stage: str, reason: str) -> None:
            if progress_cb is None:
                return
            maybe = progress_cb(value, stage, reason)
            if asyncio.iscoroutine(maybe):
                await maybe

        infra_failure = await self._try_knowledge_first(
            question=question,
            role=role,
            priority=priority,
            progress=_progress,
        )

        await _progress(30, "document_scan", "Verificando documentos anexados a esta conversa.")
        doc_retrieval = await collect_chat_citations(
            message=question,
            conversation_id=conversation_id,
            memory_service=None,
            limit=_MAX_CANDIDATES,
        )
        citations = list(doc_retrieval.get("citations") or [])
        if citations:
            await _progress(90, "synthesis", "Sintetizando a resposta final com base nos documentos anexados.")
            answer = await self._synthesize_answer(
                question=question,
                citations=citations,
                role=role,
                priority=priority,
            )
            return {
                "response": answer,
                "citations": citations,
                "citation_status": build_citation_status(
                    message=question,
                    citations=citations,
                    retrieval_failed=bool(doc_retrieval.get("retrieval_failed")),
                ),
                "delivery_status": "completed",
                "failure_classification": infra_failure,
                "study_notice": "Estudando os documentos anexados para responder com segurança.",
                "provider": "janus",
                "model": "conversation-doc-study",
            }

        await _progress(45, "self_study", "Revisando a base local para localizar arquivos relevantes.")
        await self._run_self_study(question)

        await _progress(70, "repo_scan", "Lendo arquivos do repositório para montar evidências locais.")
        citations = await asyncio.to_thread(self._scan_repo_for_citations, question)

        await _progress(90, "synthesis", "Sintetizando a resposta final com fontes rastreáveis.")
        answer = await self._synthesize_answer(
            question=question,
            citations=citations,
            role=role,
            priority=priority,
        )
        citation_status = build_citation_status(message=question, citations=citations, retrieval_failed=False)
        if not citations:
            citation_status["status"] = "missing_required"
        return {
            "response": answer,
            "citations": citations,
            "citation_status": citation_status,
            "delivery_status": "completed",
            "failure_classification": infra_failure,
            "study_notice": "Estudando a base para responder com segurança; isso pode demorar.",
            "provider": "janus",
            "model": "repo-study",
        }

    async def _try_knowledge_first(
        self,
        *,
        question: str,
        role: ModelRole,
        priority: ModelPriority,
        progress: Any,
    ) -> str | None:
        del role, priority
        if self._knowledge is None:
            return None
        await progress(10, "knowledge_retry", "Verificando conhecimento já indexado antes de estudar a base.")
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                result = await self._knowledge.ask_code_with_citations(
                    question=question,
                    limit=8,
                    citation_limit=6,
                )
                if result.get("citations"):
                    return None
            except Exception as exc:
                last_error = exc
                logger.warning("chat_study_knowledge_retry_failed", attempt=attempt + 1, error=str(exc))
                await asyncio.sleep(0.4 * (attempt + 1))
        if last_error is None:
            health = await self._safe_knowledge_health()
            if health.get("status") == "degraded":
                return "infra_transient"
            return None
        health = await self._safe_knowledge_health()
        if health.get("status") in {"degraded", "partial"}:
            return "infra_transient"
        return "application"

    async def _safe_knowledge_health(self) -> dict[str, Any]:
        if self._knowledge is None or not hasattr(self._knowledge, "get_health_status"):
            return {}
        try:
            return await self._knowledge.get_health_status()
        except Exception as exc:
            logger.warning("chat_study_health_failed", error=str(exc))
            return {"status": "degraded"}

    async def _run_self_study(self, question: str) -> None:
        if self._autonomy_admin is None or not hasattr(self._autonomy_admin, "run_self_study"):
            return
        try:
            await self._autonomy_admin.run_self_study(
                mode="full",
                reason=f"chat_fallback:{question[:120]}",
                trigger_type="chat",
            )
        except Exception as exc:
            logger.warning("chat_study_self_study_failed", error=str(exc))

    def _iter_repo_files(self) -> list[Path]:
        files: list[Path] = []
        for path in self._repo_root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in _IGNORE_DIRS for part in path.parts):
                continue
            if not _looks_text_file(path):
                continue
            try:
                if path.stat().st_size > _MAX_FILE_BYTES:
                    continue
            except Exception:
                continue
            files.append(path)
        return files

    def _scan_repo_for_citations(self, question: str) -> list[dict[str, Any]]:
        tokens = _question_tokens(question)
        if not tokens:
            return []
        candidates: list[tuple[int, Path]] = []
        for path in self._iter_repo_files():
            rel = path.relative_to(self._repo_root).as_posix().lower()
            score = 0
            for token in tokens:
                if token in rel:
                    score += 8
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            lowered = content.lower()
            for token in tokens:
                if token in lowered:
                    score += 2
            if score > 0:
                candidates.append((score, path))
        candidates.sort(key=lambda item: item[0], reverse=True)
        citations: list[dict[str, Any]] = []
        for _, path in candidates[:_MAX_CANDIDATES]:
            citation = self._build_citation(path, tokens)
            if citation:
                citations.append(citation)
        return citations

    def _build_citation(self, path: Path, tokens: list[str]) -> dict[str, Any] | None:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            return None
        if not lines:
            return None
        best_idx = 0
        best_score = -1
        for idx, line in enumerate(lines):
            lowered = line.lower()
            score = sum(3 for token in tokens if token in lowered)
            if score > best_score:
                best_score = score
                best_idx = idx
        start = max(0, best_idx - 3)
        end = min(len(lines), start + _MAX_SNIPPET_LINES)
        snippet = "\n".join(lines[start:end])
        rel = path.relative_to(self._repo_root).as_posix()
        return {
            "id": f"{rel}:{start + 1}",
            "title": path.name,
            "file_path": rel,
            "source_type": "code",
            "type": "code",
            "line_start": start + 1,
            "line_end": end,
            "line": start + 1,
            "snippet": _sanitize_snippet(snippet),
            "score": round(max(0.1, best_score / max(1, len(tokens) * 3)), 2),
        }

    async def _synthesize_answer(
        self,
        *,
        question: str,
        citations: list[dict[str, Any]],
        role: ModelRole,
        priority: ModelPriority,
    ) -> str:
        if not citations:
            nearby = []
            for item in self._scan_repo_for_citations(question)[:5]:
                path = str(item.get("file_path") or "").strip()
                if path:
                    nearby.append(path)
            suffix = f" Arquivos mais próximos analisados: {', '.join(nearby)}." if nearby else ""
            return (
                "Eu procurei em toda a base do projeto, mas ainda não encontrei evidência suficiente "
                f"para responder com segurança.{suffix}"
            )

        evidence_blocks = []
        for item in citations[:4]:
            evidence_blocks.append(
                f"Arquivo: {item.get('file_path')} linhas {item.get('line_start')}-{item.get('line_end')}\n"
                f"{item.get('snippet')}"
            )
        if self._llm is None:
            refs = "; ".join(
                f"{item.get('file_path')}:{item.get('line_start')}" for item in citations[:4]
            )
            return (
                f"Analisei a base local para responder: {question}. "
                f"As evidências mais fortes estão em {refs}. "
                "Se você quiser, eu detalho qualquer um desses arquivos linha por linha."
            )
        evidence_text = "\n\n".join(evidence_blocks)
        prompt = (
            "Responda em português, de forma natural, objetiva e sem mencionar tool envelopes. "
            "Use somente as evidências fornecidas. Se a evidência for parcial, diga isso de forma direta.\n\n"
            f"Pergunta do usuário: {question}\n\n"
            "Evidências rastreáveis:\n"
            f"{evidence_text}\n\n"
            "Feche a resposta com uma frase curta oferecendo detalhamento de arquivo se fizer sentido."
        )
        try:
            result = await self._llm.invoke_llm(
                prompt=prompt,
                role=role,
                priority=priority,
                timeout_seconds=45,
                task_type="chat_repo_study",
            )
            text = str(result.get("response") or "").strip()
            if text:
                return text
        except Exception as exc:
            logger.warning("chat_study_llm_synthesis_failed", error=str(exc))
        refs = "; ".join(f"{item.get('file_path')}:{item.get('line_start')}" for item in citations[:4])
        return (
            f"Estudei a base para responder com segurança. Os pontos mais relevantes para essa pergunta "
            f"estão em {refs}. Posso abrir qualquer um desses arquivos em mais detalhe."
        )


class ChatStudyJobService:
    def __init__(self, *, study_service: ChatStudyService, chat_service: Any) -> None:
        self._study_service = study_service
        self._chat_service = chat_service
        self._jobs: dict[str, ChatStudyJob] = {}

    def create_job(
        self,
        *,
        conversation_id: str,
        message_id: str,
        question: str,
        user_id: str | None,
        placeholder_message: str,
    ) -> ChatStudyJob:
        job = ChatStudyJob(
            job_id=uuid4().hex,
            conversation_id=conversation_id,
            message_id=str(message_id),
            question=question,
            user_id=user_id,
            status="queued",
            progress=5,
            placeholder_message=placeholder_message,
        )
        self._jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> ChatStudyJob | None:
        return self._jobs.get(job_id)

    async def run_job(
        self,
        *,
        job_id: str,
        role: ModelRole = ModelRole.ORCHESTRATOR,
        priority: ModelPriority = ModelPriority.FAST_AND_CHEAP,
    ) -> None:
        job = self._jobs.get(job_id)
        if job is None:
            return
        job.status = "running"
        job.updated_at = time.time()

        async def _progress(value: int, _stage: str, reason: str) -> None:
            job.progress = value
            job.updated_at = time.time()
            if reason:
                job.placeholder_message = reason

        try:
            result = await self._study_service.answer_with_study(
                question=job.question,
                role=role,
                priority=priority,
                user_id=job.user_id,
                conversation_id=job.conversation_id,
                progress_cb=_progress,
            )
            patch = {
                "text": result["response"],
                "citations": result.get("citations") or [],
                "citation_status": result.get("citation_status"),
                "delivery_status": "completed",
                "failure_classification": result.get("failure_classification"),
                "provider": result.get("provider"),
                "model": result.get("model"),
            }
            await self._chat_service.update_message_payload(
                conversation_id=job.conversation_id,
                message_id=int(job.message_id),
                patch=patch,
                user_id=job.user_id,
            )
            job.status = "completed"
            job.progress = 100
            job.failure_classification = result.get("failure_classification")
            job.final_response = {
                "conversation_id": job.conversation_id,
                "message_id": str(job.message_id),
                **result,
            }
            job.updated_at = time.time()
        except Exception as exc:
            logger.error("chat_study_job_failed", job_id=job_id, error=str(exc))
            job.status = "failed"
            job.error = str(exc)
            job.updated_at = time.time()
            try:
                await self._chat_service.update_message_payload(
                    conversation_id=job.conversation_id,
                    message_id=int(job.message_id),
                    patch={
                        "text": "Falhei ao concluir o estudo automático dessa resposta. Tente novamente em instantes.",
                        "delivery_status": "failed",
                        "failure_classification": "application",
                    },
                    user_id=job.user_id,
                )
            except Exception:
                pass
