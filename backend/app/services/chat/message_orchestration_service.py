import asyncio
import hashlib
import os
import re
import textwrap
import time as _time
from typing import Any

import structlog

from app.core.agents.utils import parse_json_lenient
from app.core.exceptions.chat_exceptions import (
    ChatServiceError,
    ConversationNotFoundError,
    MessageTooLargeError,
)
from app.core.llm import ModelPriority, ModelRole
from app.core.llm.pricing import _provider_pricing
from app.core.monitoring.chat_metrics import (
    CHAT_LATENCY_SECONDS,
    CHAT_MESSAGES_TOTAL,
    CHAT_SPEND_USD_TOTAL,
    CHAT_TOKENS_TOTAL,
)
from app.core.routing import RouteIntent, get_knowledge_routing_policy
from app.core.workers.async_consolidation_worker import publish_consolidation_task
from app.repositories.chat_repository import ChatRepository, ChatRepositoryError
from app.repositories.document_manifest_repository import DocumentManifestRepository
from app.services.chat.chat_citation_service import (
    build_citation_status,
    collect_document_citations,
    references_uploaded_material,
)
from app.services.knowledge_space_service import KnowledgeSpaceService
from app.services.chat.message_helpers import (
    attach_understanding,
    build_understanding_payload,
    estimate_tokens,
    format_tool_creation_response,
    is_explicit_tool_creation,
    split_ui,
)
from app.services.chat.conversation_service import ConversationService
from app.services.chat_agent_loop import ChatAgentLoop
from app.services.chat_command_handler import ChatCommandHandler
from app.services.outbox_service import OutboxService
from app.services.procedural_memory_service import procedural_memory_service
from app.services.prompt_builder_service import PromptBuilderService
from app.services.rag_service import RAGService
from app.services.active_memory_service import active_memory_service
from app.services.secret_memory_service import secret_memory_service

logger = structlog.get_logger(__name__)


class MessageOrchestrationService:
    def __init__(
        self,
        *,
        repo: ChatRepository,
        llm_service: Any,
        tool_service: Any | None,
        prompt_service: PromptBuilderService,
        rag_service: RAGService | None,
        command_handler: ChatCommandHandler,
        agent_loop: ChatAgentLoop,
        conversation_service: ConversationService,
        outbox_service: OutboxService | None = None,
        manifest_repo: DocumentManifestRepository | None = None,
    ):
        self._repo = repo
        self._llm = llm_service
        self._tools = tool_service
        self._prompt_service = prompt_service
        self._rag_service = rag_service
        self._command_handler = command_handler
        self._agent_loop = agent_loop
        self._conversation_service = conversation_service
        self._outbox_service = outbox_service
        self._manifest_repo = manifest_repo or DocumentManifestRepository()

    def _should_use_light_chat(
        self,
        *,
        message: str,
        role: ModelRole,
        understanding: dict[str, Any] | None,
    ) -> bool:
        if role != ModelRole.ORCHESTRATOR:
            return False
        if not understanding or understanding.get("intent") not in {"general", "question"}:
            return False
        max_chars = int(os.getenv("CHAT_LIGHT_MAX_MESSAGE_CHARS", "160"))
        return len((message or "").strip()) <= max_chars

    def _schedule_rag_index_message(
        self,
        *,
        text: str,
        conversation_id: str,
        role: str,
        user_id: str | None,
        project_id: str | None,
        identity_source: str,
    ) -> None:
        if not self._rag_service or not text:
            return

        async def _index() -> None:
            try:
                await self._rag_service.maybe_index_message(
                    text=text,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    role=role,
                    caller_endpoint="/api/v1/chat/message",
                    transport="rest",
                    identity_source=identity_source,
                )
            except Exception as e:
                logger.warning(
                    "rag_index_message_failed",
                    conversation_id=conversation_id,
                    project_id=project_id,
                    role=role,
                    error_type=type(e).__name__,
                    error=str(e),
                )

        asyncio.create_task(_index())

    def schedule_active_memory_capture(
        self,
        *,
        message: str,
        user_id: str | None,
        conversation_id: str,
    ) -> None:
        if not user_id or not str(message or "").strip():
            return

        async def _capture() -> None:
            try:
                await active_memory_service.maybe_capture_from_message(
                    message=message,
                    user_id=user_id,
                    conversation_id=conversation_id,
                )
            except Exception as exc:
                logger.warning(
                    "active_memory_capture_failed",
                    conversation_id=conversation_id,
                    user_id=user_id,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )

        asyncio.create_task(_capture())

    @staticmethod
    def _trim_document_snippet(text: str | None, *, limit: int = 480) -> str:
        normalized = " ".join(str(text or "").split())
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[: limit - 3].rstrip()}..."

    def _list_document_manifests(
        self,
        *,
        user_id: str | None,
        conversation_id: str,
    ) -> list[dict[str, Any]]:
        if not user_id:
            return []
        try:
            return self._manifest_repo.list_manifests(
                user_id=str(user_id),
                conversation_id=str(conversation_id),
                limit=50,
            )
        except Exception as exc:
            logger.warning(
                "document_manifest_lookup_failed",
                conversation_id=conversation_id,
                user_id=user_id,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return []

    @staticmethod
    def _extract_knowledge_space_ids(manifests: list[dict[str, Any]]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for row in manifests:
            value = str(row.get("knowledge_space_id") or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered

    def _resolve_knowledge_space_id(
        self,
        *,
        manifests: list[dict[str, Any]],
        requested_knowledge_space_id: str | None,
    ) -> str | None:
        explicit = str(requested_knowledge_space_id or "").strip()
        if explicit:
            return explicit
        candidates = self._extract_knowledge_space_ids(manifests)
        if len(candidates) == 1:
            return candidates[0]
        return None

    @staticmethod
    def _tokenize_source_title(value: str | None) -> set[str]:
        text = re.sub(r"[^a-z0-9]+", " ", str(value or "").strip().lower())
        return {
            token
            for token in text.split()
            if len(token) >= 4 and token not in {"guide", "manual", "book", "livro", "guia"}
        }

    @staticmethod
    def _infer_manifest_source_role(row: dict[str, Any]) -> str:
        explicit = str(row.get("doc_role") or "").strip().lower()
        if explicit in {"base", "supplement", "reference", "appendix"}:
            return explicit
        title = " ".join(
            filter(
                None,
                [
                    str(row.get("file_name") or "").strip(),
                    str(row.get("semantic_summary") or "").strip(),
                ],
            )
        ).lower()
        primary_patterns = (
            r"\bcore\b",
            r"\bbase\b",
            r"\bbasic\b",
            r"\bbasico\b",
            r"\bbásico\b",
            r"\bmain\b",
            r"\bprincipal\b",
            r"\bprimary\b",
            r"\bprimary source\b",
            r"\bhandbook\b",
            r"\bmanual\b",
            r"\blivro base\b",
        )
        secondary_patterns = (
            r"\bsupplement\b",
            r"\bsuplement",
            r"\bcompanion\b",
            r"\bappendix\b",
            r"\bap[eê]ndice\b",
            r"\baddendum\b",
            r"\baddon\b",
            r"\bextra\b",
            r"\bbonus\b",
            r"\bcomplement",
            r"\boptional\b",
            r"\bopcional\b",
            r"\badvanced\b",
            r"\bavancad",
            r"\bextension\b",
            r"\bexpansion\b",
        )
        if any(re.search(pattern, title) for pattern in primary_patterns):
            return "base"
        if any(re.search(pattern, title) for pattern in secondary_patterns):
            return "supplement"
        return "base"

    @classmethod
    def _manifest_primary_rank(cls, row: dict[str, Any]) -> tuple[int, int]:
        role = cls._infer_manifest_source_role(row)
        explicit = str(row.get("doc_role") or "").strip().lower()
        role_score = {
            "base": 3,
            "reference": 2,
            "appendix": 1,
            "supplement": 0,
        }.get(explicit or role, 1)
        chunks = int(row.get("chunks_total") or row.get("chunks_indexed") or row.get("chunks") or 0)
        return role_score, chunks

    @classmethod
    def _message_explicitly_requests_secondary_sources(
        cls,
        *,
        message: str,
        manifests: list[dict[str, Any]],
        understanding: dict[str, Any] | None,
    ) -> bool:
        lowered = str(message or "").lower()
        secondary_patterns = (
            r"\bsuplement",
            r"\bsupplement\b",
            r"\bappendix\b",
            r"\bap[eê]ndice\b",
            r"\bcompanion\b",
            r"\baddendum\b",
            r"\bcomplement",
            r"\bextra\b",
            r"\bbonus\b",
            r"\boptional\b",
            r"\bopcional\b",
            r"\badvanced\b",
            r"\bavancad",
            r"\bexpansion\b",
        )
        if any(re.search(pattern, lowered) for pattern in secondary_patterns):
            return True
        for row in manifests:
            if cls._infer_manifest_source_role(row) != "supplement":
                continue
            tokens = cls._tokenize_source_title(str(row.get("file_name") or ""))
            if tokens and sum(1 for token in tokens if token in lowered) >= 2:
                return True
        intent = str((understanding or {}).get("intent") or "").strip().lower()
        return intent in {"comparison", "comparative"}

    @staticmethod
    def _message_prefers_primary_only(
        *,
        message: str,
        understanding: dict[str, Any] | None,
    ) -> bool:
        intent = str((understanding or {}).get("intent") or "").strip().lower()
        if intent in {"comparison", "comparative"}:
            return False
        lowered = str(message or "").lower()
        operational_patterns = (
            r"\bcrie\b",
            r"\bcriar\b",
            r"\bmonte\b",
            r"\bmontar\b",
            r"\bfa[cç]a\b",
            r"\bfazer\b",
            r"\bprepare\b",
            r"\bpreparar\b",
            r"\bresolva\b",
            r"\bresolver\b",
            r"\bcalcule\b",
            r"\bcalcular\b",
            r"\bexecute\b",
            r"\bexecutar\b",
            r"\bpreencha\b",
            r"\bpreencher\b",
            r"\bpasso a passo\b",
            r"\bworkflow\b",
            r"\bsequ[eê]ncia\b",
            r"\bprocesso\b",
            r"\bdo que precisa\b",
        )
        return any(re.search(pattern, lowered) for pattern in operational_patterns)

    @classmethod
    def _apply_document_source_policy(
        cls,
        *,
        citations: list[dict[str, Any]],
        manifests: list[dict[str, Any]],
        message: str,
        understanding: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        indexed = [
            row
            for row in manifests
            if str(row.get("status") or "") == "indexed" and int(row.get("chunks_indexed") or 0) > 0
        ]
        if len(indexed) <= 1 or not citations:
            return citations
        explicit_secondary = cls._message_explicitly_requests_secondary_sources(
            message=message,
            manifests=indexed,
            understanding=understanding,
        )
        prefer_primary_only = cls._message_prefers_primary_only(
            message=message,
            understanding=understanding,
        )
        manifest_by_doc_id = {
            str(row.get("doc_id") or "").strip(): row
            for row in indexed
            if str(row.get("doc_id") or "").strip()
        }
        ordered_primary_docs = [
            str(row.get("doc_id") or "").strip()
            for row in sorted(indexed, key=cls._manifest_primary_rank, reverse=True)
            if str(row.get("doc_id") or "").strip()
        ]
        if not ordered_primary_docs:
            return citations
        primary_doc_id = ordered_primary_docs[0]
        if explicit_secondary:
            return citations
        if not prefer_primary_only:
            return citations
        primary_citations = [
            citation for citation in citations if str(citation.get("doc_id") or "").strip() == primary_doc_id
        ]
        if primary_citations:
            return primary_citations
        # If there is no evidence in the primary source, keep the original ranking
        # so the assistant can still answer from a secondary source instead of failing silently.
        return citations

    @staticmethod
    def _prefer_canonical_answer(message: str, understanding: dict[str, Any] | None) -> bool:
        intent = str((understanding or {}).get("intent") or "").strip().lower()
        if intent in {"file_reference", "study", "analysis"}:
            return True
        lowered = str(message or "").lower()
        patterns = (
            r"\bsequencia\b",
            r"\bsequência\b",
            r"\bpasso a passo\b",
            r"\bworkflow\b",
            r"\bprocesso\b",
            r"\bcompar",
            r"\bcomo faco\b",
            r"\bcomo faço\b",
            r"\bcomplement",
            r"\bdiferen",
            r"\bdiferenc",
            r"\bdiferencie\b",
            r"\bamplia",
            r"\brelacion",
            r"\bconecta",
            r"\bplano\b",
            r"\bdependen",
            r"\bpre[- ]?requisito\b",
            r"\bordem\b",
            r"\bcole[cç][aã]o\b",
        )
        return any(re.search(pattern, lowered) for pattern in patterns)

    @staticmethod
    def _prefer_quick_lookup(message: str, understanding: dict[str, Any] | None) -> bool:
        intent = str((understanding or {}).get("intent") or "").strip().lower()
        if intent == "file_reference":
            return True
        lowered = str(message or "").lower()
        patterns = (
            r"\bonde\b",
            r"\bem que pagina\b",
            r"\bem que página\b",
            r"\bqual pagina\b",
            r"\bqual página\b",
            r"\bcite\b",
            r"\bcitacao\b",
            r"\bcitação\b",
            r"\btrecho\b",
            r"\bpagina\b",
            r"\bpágina\b",
            r"\blocaliz",
        )
        return any(re.search(pattern, lowered) for pattern in patterns)

    def _resolve_knowledge_space_mode(
        self,
        *,
        message: str,
        understanding: dict[str, Any] | None,
        requested_knowledge_space_id: str | None,
        source_scope: dict[str, Any] | None,
    ) -> str:
        return "auto"

    async def _generate_knowledge_space_reply(
        self,
        *,
        manifests: list[dict[str, Any]],
        requested_knowledge_space_id: str | None,
        conversation_id: str,
        message: str,
        role: ModelRole,
        user_id: str | None,
        understanding: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not user_id:
            return None
        knowledge_space_id = self._resolve_knowledge_space_id(
            manifests=manifests,
            requested_knowledge_space_id=requested_knowledge_space_id,
        )
        if not knowledge_space_id:
            return None
        service = KnowledgeSpaceService(manifest_repo=self._manifest_repo, llm_service=self._llm)
        source_scope = service.get_space(knowledge_space_id=knowledge_space_id, user_id=str(user_id))
        mode = self._resolve_knowledge_space_mode(
            message=message,
            understanding=understanding,
            requested_knowledge_space_id=requested_knowledge_space_id,
            source_scope=source_scope,
        )
        result = await service.query_space(
            knowledge_space_id=knowledge_space_id,
            user_id=str(user_id),
            question=message,
            mode=mode,
            limit=6,
        )
        result["provider"] = "janus"
        result["model"] = "knowledge_space"
        result["role"] = role.value
        result["conversation_id"] = conversation_id
        result["knowledge_space_id"] = knowledge_space_id
        result["response"] = str(result.get("response") or result.get("answer") or "").strip()
        result.setdefault("citation_status", build_citation_status(message=message, citations=result.get("citations") or []))

        source_scope = result.get("source_scope") or {}
        consolidation_status = str(source_scope.get("consolidation_status") or "").strip()
        if result.get("base_used") == "chunk_only" and consolidation_status not in {"ready", "partial"}:
            cta = (
                f"/api/v1/knowledge/spaces/{knowledge_space_id}/consolidate"
            )
            result["response"] = (
                f"{result.get('answer')}\n\n"
                "Este knowledge space ainda nao foi consolidado estruturalmente. "
                f"Para respostas canônicas, inicie a consolidação em `{cta}`."
            ).strip()
            gaps = list(result.get("gaps_or_conflicts") or [])
            gaps.append("Knowledge space sem consolidação pronta; resposta entregue via chunk_only.")
            result["gaps_or_conflicts"] = gaps
        return result

    def build_knowledge_space_runtime_notice(
        self,
        *,
        conversation_id: str,
        message: str,
        user_id: str | None,
        requested_knowledge_space_id: str | None = None,
    ) -> dict[str, Any] | None:
        if not user_id:
            return None
        manifests = self._list_document_manifests(
            user_id=user_id,
            conversation_id=conversation_id,
        )
        knowledge_space_id = self._resolve_knowledge_space_id(
            manifests=manifests,
            requested_knowledge_space_id=requested_knowledge_space_id,
        )
        if not knowledge_space_id:
            return None
        service = KnowledgeSpaceService(manifest_repo=self._manifest_repo, llm_service=self._llm)
        return service.estimate_query_timing(
            knowledge_space_id=knowledge_space_id,
            user_id=str(user_id),
            question=message,
            mode="auto",
        )

    def resolve_active_knowledge_space_id(
        self,
        *,
        conversation_id: str,
        user_id: str | None,
        requested_knowledge_space_id: str | None = None,
    ) -> str | None:
        if not user_id:
            return str(requested_knowledge_space_id or "").strip() or None
        manifests = self._list_document_manifests(
            user_id=user_id,
            conversation_id=conversation_id,
        )
        return self._resolve_knowledge_space_id(
            manifests=manifests,
            requested_knowledge_space_id=requested_knowledge_space_id,
        )

    def _should_use_document_grounding(
        self,
        *,
        message: str,
        understanding: dict[str, Any] | None,
        manifests: list[dict[str, Any]],
    ) -> bool:
        if not manifests:
            return False
        if (understanding or {}).get("intent") == "file_reference":
            return True
        if references_uploaded_material(message):
            return True
        return True

    def _build_document_processing_result(
        self,
        *,
        message: str,
        manifests: list[dict[str, Any]],
        role: ModelRole,
    ) -> dict[str, Any]:
        processing = [
            row
            for row in manifests
            if str(row.get("status") or "") in {"queued", "processing"}
        ]
        status = "processing" if any(str(row.get("status")) == "processing" for row in processing) else "queued"
        file_names = [str(row.get("file_name") or "documento") for row in processing[:3]]
        suffix = f" Arquivos: {', '.join(file_names)}." if file_names else ""
        response = (
            "Os documentos desta conversa ainda estao sendo processados. "
            "Assim que a indexacao terminar, eu respondo com base no arquivo enviado."
            f"{suffix}"
        )
        citations: list[dict[str, Any]] = []
        return {
            "response": response,
            "provider": "janus",
            "model": "document_processing",
            "role": role.value,
            "citations": citations,
            "citation_status": {
                "mode": "optional",
                "status": "not_applicable",
                "count": 0,
                "reason": "documents_processing",
            },
            "document_grounding": {
                "active": True,
                "mode": "processing",
                "manifest_statuses": [str(row.get("status") or "") for row in processing],
            },
        }

    def _build_document_grounding_prompt(
        self,
        *,
        message: str,
        citations: list[dict[str, Any]],
    ) -> str:
        evidence_blocks: list[str] = []
        for idx, citation in enumerate(citations, start=1):
            source = (
                citation.get("title")
                or citation.get("file_path")
                or citation.get("doc_id")
                or f"Documento {idx}"
            )
            snippet = self._trim_document_snippet(citation.get("snippet"))
            evidence_blocks.append(f"[{idx}] fonte={source}\n[trecho]\n{snippet}")
        evidence_text = "\n\n".join(evidence_blocks)
        return textwrap.dedent(
            f"""
            Voce esta respondendo uma pergunta sobre documentos enviados pelo usuario.
            Use SOMENTE as evidencias abaixo. Nao use conhecimento externo, nao invente e nao negue informacao que esteja nos trechos.

            Pergunta do usuario:
            {message}

            Evidencias:
            {evidence_text}

            Responda APENAS com JSON valido neste formato:
            {{
              "answer": "resposta curta e fiel ao documento",
              "supported_points": [
                {{"statement": "ponto suportado pelo documento", "citation_ids": [1], "quote": "trecho exato copiado da evidencia"}}
              ],
              "missing_information": ["aspecto que nao aparece no documento"]
            }}

            Regras:
            - "answer" deve descrever apenas o que esta suportado pelas evidencias.
            - "supported_points" deve listar somente fatos presentes nas evidencias.
            - Cada item de "supported_points" deve incluir "quote" com um trecho exato copiado da evidencia.
            - "missing_information" so pode conter itens realmente ausentes.
            - Se qualquer evidencia responder total ou parcialmente a pergunta, NAO diga que a informacao esta ausente.
            - Se as evidencias forem insuficientes, deixe "supported_points" vazio e explique isso em "answer".
            """
        ).strip()

    async def generate_secret_recall_reply(
        self,
        *,
        message: str,
        role: ModelRole,
        user_id: str | None,
        conversation_id: str | None,
    ) -> dict[str, Any] | None:
        if not user_id or not secret_memory_service.should_authorize_prompt_recall(message):
            return None
        items = await secret_memory_service.list_secrets(
            user_id=str(user_id),
            query=message,
            conversation_id=conversation_id,
            limit=1,
            reveal=True,
        )
        if not items:
            return {
                "response": "Nao encontrei um segredo autorizado salvo para esse pedido.",
                "provider": "janus",
                "model": "secret_memory",
                "role": role.value,
                "citations": [],
                "citation_status": {
                    "mode": "optional",
                    "status": "not_applicable",
                    "count": 0,
                    "reason": "secret_not_found",
                },
            }
        secret_item = items[0]
        label = str(secret_item.get("secret_label") or "segredo").strip()
        value = str(secret_item.get("secret_value") or "").strip()
        if not value:
            return None
        response = f"{label}: {value}"
        return {
            "response": response,
            "provider": "janus",
            "model": "secret_memory",
            "role": role.value,
            "citations": [],
            "citation_status": {
                "mode": "optional",
                "status": "not_applicable",
                "count": 0,
                "reason": "secret_authorized",
            },
        }

    async def apply_response_memory_policies(
        self,
        *,
        assistant_text: str,
        user_message: str,
        user_id: str | None,
        conversation_id: str,
    ) -> str:
        if not user_id or not str(assistant_text or "").strip():
            return assistant_text
        try:
            rules = await procedural_memory_service.list_rules(
                user_id=str(user_id),
                conversation_id=conversation_id,
                query=None,
                limit=10,
                active_only=True,
            )
        except Exception as exc:
            logger.warning(
                "procedural_memory_policy_lookup_failed",
                conversation_id=conversation_id,
                user_id=user_id,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return assistant_text

        normalized_message = str(user_message or "").lower()
        disable_next_steps = any(
            token in normalized_message
            for token in (
                "sem proximos passos",
                "sem próximos passos",
                "nao termine com proximos passos",
                "não termine com próximos passos",
            )
        )
        needs_closing_steps = any(str(rule.get("scope") or "") == "closing" for rule in rules)
        if needs_closing_steps and not disable_next_steps:
            if "próximos passos" not in assistant_text.lower() and "proximos passos" not in assistant_text.lower():
                assistant_text = (
                    assistant_text.rstrip()
                    + "\n\nPróximos passos:\n"
                    + "1. Diga se quer aprofundar, resumir ou aplicar isso.\n"
                    + "2. Se preferir, eu transformo a resposta em ações executáveis."
                )
        return assistant_text

    def _build_document_grounding_recheck_prompt(
        self,
        *,
        message: str,
        citations: list[dict[str, Any]],
    ) -> str:
        evidence_blocks: list[str] = []
        for idx, citation in enumerate(citations, start=1):
            source = (
                citation.get("title")
                or citation.get("file_path")
                or citation.get("doc_id")
                or f"Documento {idx}"
            )
            snippet = self._trim_document_snippet(citation.get("snippet"), limit=640)
            evidence_blocks.append(f"[{idx}] fonte={source}\n[trecho]\n{snippet}")
        evidence_text = "\n\n".join(evidence_blocks)
        return textwrap.dedent(
            f"""
            Voce vai verificar se as evidencias abaixo respondem a pergunta do usuario.
            Use SOMENTE os trechos fornecidos. Nao use conhecimento externo.

            Pergunta do usuario:
            {message}

            Evidencias:
            {evidence_text}

            Responda APENAS com JSON valido neste formato:
            {{
              "answered": true,
              "supported_points": [
                {{"statement": "resposta suportada pelo trecho", "citation_ids": [1], "quote": "trecho exato copiado da evidencia"}}
              ],
              "missing_information": ["aspecto que realmente nao foi encontrado"]
            }}

            Regras:
            - Marque "answered" como true se qualquer trecho responder total ou parcialmente a pergunta.
            - Toda resposta positiva precisa de pelo menos um item em "supported_points".
            - Todo item de "supported_points" deve incluir "quote" exatamente como aparece na evidencia.
            - Se houver uma resposta suportada, NAO liste esse mesmo ponto em "missing_information".
            """
        ).strip()

    @staticmethod
    def _is_document_operational_task(
        *,
        message: str,
        understanding: dict[str, Any] | None,
    ) -> bool:
        intent = str((understanding or {}).get("intent") or "").strip().lower()
        if intent == "action_request":
            return True
        lowered = str(message or "").lower()
        patterns = (
            r"\bcrie\b",
            r"\bcriar\b",
            r"\bmonte\b",
            r"\bmontar\b",
            r"\bfa[cç]a\b",
            r"\bfazer\b",
            r"\bprepare\b",
            r"\bpreparar\b",
            r"\bresolva\b",
            r"\bresolver\b",
            r"\bcalcule\b",
            r"\bcalcular\b",
            r"\bpreencha\b",
            r"\bpreencher\b",
            r"\bgere\b",
            r"\bgerar\b",
            r"\bescolha por mim\b",
            r"\bdo que precisa\b",
            r"\bpasso a passo\b",
        )
        return any(re.search(pattern, lowered) for pattern in patterns)

    def _build_document_operational_prompt(
        self,
        *,
        message: str,
        citations: list[dict[str, Any]],
    ) -> str:
        grouped: dict[str, list[tuple[int, dict[str, Any]]]] = {}
        for index, citation in enumerate(citations, start=1):
            source = str(citation.get("title") or citation.get("file_path") or citation.get("doc_id") or "Fonte").strip()
            grouped.setdefault(source, []).append((index, citation))
        evidence_blocks: list[str] = []
        for source, entries in grouped.items():
            evidence_blocks.append(f"Fonte: {source}")
            for index, citation in entries[:4]:
                snippet = self._trim_document_snippet(citation.get("snippet"))
                if not snippet:
                    continue
                evidence_blocks.append(f"[{index}] {snippet}")
            evidence_blocks.append("")
        sources_text = "\n".join(block for block in evidence_blocks if block is not None).strip()
        return textwrap.dedent(
            f"""
            Você está executando uma tarefa do usuário com base SOMENTE nas evidências documentais abaixo.

            Tarefa do usuário:
            {message}

            Fontes recuperadas:
            {sources_text}

            Regras obrigatórias:
            - Nao resuma o livro nem diga apenas "o documento fala sobre".
            - Use as evidências para PRODUZIR o artefato pedido pelo usuário.
            - Se a tarefa for montar algo, monte de forma direta e útil.
            - Se faltarem decisões do usuário, liste apenas as decisões realmente pendentes.
            - Se a fonte não trouxer algum detalhe necessário, liste isso como lacuna da fonte.
            - Nao invente fatos que nao estejam sustentados pelas evidencias.
            - Quando houver varias fontes, trate a fonte principal recuperada como canônica e as demais como apoio.

            Responda SOMENTE em JSON válido:
            {{
              "response": "artefato final ou execução direta da tarefa",
              "used_citation_ids": [1,2],
              "missing_user_decisions": ["decisão realmente pendente"],
              "source_gaps": ["lacuna real da fonte"],
              "artifact_type": "tipo curto do artefato"
            }}
            """
        ).strip()

    @staticmethod
    def _normalize_document_text(value: str | None) -> str:
        return " ".join(str(value or "").strip().split()).casefold()

    def _sanitize_document_grounding_extraction(
        self,
        *,
        extraction: dict[str, Any] | None,
        citations: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if not isinstance(extraction, dict):
            return None

        sanitized_points: list[dict[str, Any]] = []
        raw_points = extraction.get("supported_points") or []
        for item in raw_points:
            if not isinstance(item, dict):
                continue
            statement = str(item.get("statement") or "").strip()
            quote = str(item.get("quote") or "").strip()
            citation_ids = item.get("citation_ids") or []
            normalized_quote = self._normalize_document_text(quote)
            if not statement or not quote or not normalized_quote:
                continue

            matched_ids: list[int] = []
            for citation_id in citation_ids:
                try:
                    idx = int(citation_id)
                except (TypeError, ValueError):
                    continue
                if idx < 1 or idx > len(citations):
                    continue
                snippet = self._normalize_document_text(citations[idx - 1].get("snippet"))
                if normalized_quote and normalized_quote in snippet:
                    matched_ids.append(idx)
            if not matched_ids:
                continue
            sanitized_points.append(
                {
                    "statement": statement,
                    "citation_ids": matched_ids,
                    "quote": quote,
                }
            )

        missing_information = [
            str(item).strip()
            for item in (extraction.get("missing_information") or [])
            if str(item or "").strip()
        ]
        sanitized: dict[str, Any] = {
            "answer": str(extraction.get("answer") or "").strip(),
            "supported_points": sanitized_points,
            "missing_information": missing_information,
        }
        answered = extraction.get("answered")
        if isinstance(answered, bool):
            sanitized["answered"] = answered
        return sanitized

    def _sanitize_document_operational_extraction(
        self,
        *,
        extraction: dict[str, Any] | None,
        citations: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if not isinstance(extraction, dict):
            return None
        response = str(extraction.get("response") or "").strip()
        if not response:
            return None
        used_ids: list[int] = []
        for value in extraction.get("used_citation_ids") or []:
            try:
                idx = int(value)
            except (TypeError, ValueError):
                continue
            if 1 <= idx <= len(citations):
                used_ids.append(idx)
        missing_user_decisions = [
            str(item).strip()
            for item in (extraction.get("missing_user_decisions") or [])
            if str(item or "").strip()
        ]
        source_gaps = [
            str(item).strip()
            for item in (extraction.get("source_gaps") or [])
            if str(item or "").strip()
        ]
        return {
            "response": response,
            "used_citation_ids": sorted(set(used_ids)),
            "missing_user_decisions": missing_user_decisions,
            "source_gaps": source_gaps,
            "artifact_type": str(extraction.get("artifact_type") or "").strip(),
        }

    async def _recheck_document_grounding(
        self,
        *,
        message: str,
        citations: list[dict[str, Any]],
        role: ModelRole,
        priority: ModelPriority,
        timeout_seconds: int | None,
        user_id: str | None,
        project_id: str | None,
    ) -> dict[str, Any] | None:
        prompt = self._build_document_grounding_recheck_prompt(
            message=message,
            citations=citations,
        )
        extraction = await self._llm.invoke_llm(
            prompt=prompt,
            role=role,
            priority=priority,
            timeout_seconds=min(int(timeout_seconds or 30), 30),
            user_id=user_id,
            project_id=project_id,
        )
        raw_response = str(extraction.get("response") or "")
        parsed = parse_json_lenient(raw_response)
        return self._sanitize_document_grounding_extraction(
            extraction=parsed if isinstance(parsed, dict) else None,
            citations=citations,
        )

    async def _extract_document_grounding(
        self,
        *,
        message: str,
        citations: list[dict[str, Any]],
        role: ModelRole,
        priority: ModelPriority,
        timeout_seconds: int | None,
        user_id: str | None,
        project_id: str | None,
    ) -> dict[str, Any] | None:
        prompt = self._build_document_grounding_prompt(message=message, citations=citations)
        extraction = await self._llm.invoke_llm(
            prompt=prompt,
            role=role,
            priority=priority,
            timeout_seconds=min(int(timeout_seconds or 30), 30),
            user_id=user_id,
            project_id=project_id,
        )
        raw_response = str(extraction.get("response") or "")
        parsed = parse_json_lenient(raw_response)
        return self._sanitize_document_grounding_extraction(
            extraction=parsed if isinstance(parsed, dict) else None,
            citations=citations,
        )

    async def _extract_document_operational_grounding(
        self,
        *,
        message: str,
        citations: list[dict[str, Any]],
        role: ModelRole,
        priority: ModelPriority,
        timeout_seconds: int | None,
        user_id: str | None,
        project_id: str | None,
    ) -> dict[str, Any] | None:
        prompt = self._build_document_operational_prompt(message=message, citations=citations)
        extraction = await self._llm.invoke_llm(
            prompt=prompt,
            role=role,
            priority=priority,
            timeout_seconds=min(int(timeout_seconds or 45), 45),
            user_id=user_id,
            project_id=project_id,
        )
        raw_response = str(extraction.get("response") or "")
        parsed = parse_json_lenient(raw_response)
        return self._sanitize_document_operational_extraction(
            extraction=parsed if isinstance(parsed, dict) else None,
            citations=citations,
        )

    def _format_document_grounded_response(
        self,
        *,
        extraction: dict[str, Any] | None,
        citations: list[dict[str, Any]],
    ) -> str:
        if not extraction:
            top_snippets = [
                self._trim_document_snippet(citation.get("snippet"))
                for citation in citations[:3]
                if self._trim_document_snippet(citation.get("snippet"))
            ]
            if not top_snippets:
                return "Nao encontrei no documento trechos suficientes para responder com seguranca."
            body = "\n".join(f"- {snippet}" for snippet in top_snippets)
            return f"Do documento:\n{body}"

        answer = str(extraction.get("answer") or "").strip()
        supported_points = extraction.get("supported_points") or []
        missing_information = extraction.get("missing_information") or []
        answered = extraction.get("answered")
        allow_missing = (answered is False) or (answered is None and not citations)

        lines: list[str] = ["Do documento:"]
        if answer:
            lines.append(answer)

        supported_lines: list[str] = []
        for item in supported_points:
            if isinstance(item, dict):
                statement = str(item.get("statement") or "").strip()
            else:
                statement = str(item or "").strip()
            if statement:
                supported_lines.append(f"- {statement}")

        if supported_lines:
            lines.extend(supported_lines)
        elif citations and not allow_missing:
            lines.extend(
                f"- {self._trim_document_snippet(citation.get('snippet'))}"
                for citation in citations[:2]
                if self._trim_document_snippet(citation.get("snippet"))
            )

        if not supported_lines:
            missing_lines = [
                str(item).strip()
                for item in missing_information
                if str(item or "").strip()
            ]
            if missing_lines and allow_missing:
                lines.append("")
                lines.append("Nao encontrei no documento:")
                lines.extend(f"- {item}" for item in missing_lines)

        return "\n".join(line for line in lines if line is not None).strip()

    def _format_document_operational_response(
        self,
        *,
        extraction: dict[str, Any] | None,
        citations: list[dict[str, Any]],
    ) -> str:
        if not extraction:
            top_snippets = [
                self._trim_document_snippet(citation.get("snippet"))
                for citation in citations[:4]
                if self._trim_document_snippet(citation.get("snippet"))
            ]
            if not top_snippets:
                return "Nao encontrei no documento evidências suficientes para executar essa tarefa com segurança."
            lines = [
                "Ainda não consegui executar a tarefa inteira com segurança, mas estas evidências são as mais úteis:",
            ]
            lines.extend(f"- {snippet}" for snippet in top_snippets)
            return "\n".join(lines)
        lines = [str(extraction.get("response") or "").strip()]
        missing_user_decisions = extraction.get("missing_user_decisions") or []
        if missing_user_decisions:
            lines.append("")
            lines.append("Decisões pendentes do usuário:")
            lines.extend(f"- {item}" for item in missing_user_decisions[:6])
        source_gaps = extraction.get("source_gaps") or []
        if source_gaps:
            lines.append("")
            lines.append("Lacunas da fonte:")
            lines.extend(f"- {item}" for item in source_gaps[:6])
        return "\n".join(line for line in lines if line is not None).strip()

    async def generate_document_grounded_reply(
        self,
        *,
        conversation_id: str,
        message: str,
        role: ModelRole,
        priority: ModelPriority,
        timeout_seconds: int | None,
        user_id: str | None,
        project_id: str | None,
        requested_knowledge_space_id: str | None = None,
        understanding: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        manifests = self._list_document_manifests(
            user_id=user_id,
            conversation_id=conversation_id,
        )
        knowledge_space_result = await self._generate_knowledge_space_reply(
            manifests=manifests,
            requested_knowledge_space_id=requested_knowledge_space_id,
            conversation_id=conversation_id,
            message=message,
            role=role,
            user_id=user_id,
            understanding=understanding,
        )
        if knowledge_space_result is not None:
            return knowledge_space_result
        if not self._should_use_document_grounding(
            message=message,
            understanding=understanding,
            manifests=manifests,
        ):
            return None

        indexed_manifests = [
            row
            for row in manifests
            if str(row.get("status") or "") == "indexed" and int(row.get("chunks_indexed") or 0) > 0
        ]
        indexed_doc_ids = {
            str(row.get("doc_id") or "")
            for row in indexed_manifests
            if str(row.get("doc_id") or "").strip()
        }
        processing_manifests = [
            row
            for row in manifests
            if str(row.get("status") or "") in {"queued", "processing"}
        ]

        if not indexed_manifests and processing_manifests:
            return self._build_document_processing_result(
                message=message,
                manifests=processing_manifests,
                role=role,
            )

        citations: list[dict[str, Any]] = []
        retrieval_failed = False
        is_operational_task = self._is_document_operational_task(
            message=message,
            understanding=understanding,
        )
        retrieval_limit = 10 if is_operational_task else 6
        try:
            citations = await collect_document_citations(
                message=message,
                user_id=str(user_id) if user_id is not None else None,
                conversation_id=conversation_id,
                limit=retrieval_limit,
            )
            citations = self._apply_document_source_policy(
                citations=citations,
                manifests=indexed_manifests,
                message=message,
                understanding=understanding,
            )
            if indexed_doc_ids:
                citations = [
                    citation
                    for citation in citations
                    if str(citation.get("doc_id") or "") in indexed_doc_ids
                ]
                if not citations:
                    fallback_citations = await collect_document_citations(
                        message="documento enviado",
                        user_id=str(user_id) if user_id is not None else None,
                        conversation_id=conversation_id,
                        limit=retrieval_limit,
                    )
                    fallback_citations = self._apply_document_source_policy(
                        citations=fallback_citations,
                        manifests=indexed_manifests,
                        message=message,
                        understanding=understanding,
                    )
                    citations = [
                        citation
                        for citation in fallback_citations
                        if str(citation.get("doc_id") or "") in indexed_doc_ids
                    ]
        except Exception as exc:
            retrieval_failed = True
            logger.warning(
                "document_grounding_citation_lookup_failed",
                conversation_id=conversation_id,
                user_id=user_id,
                error_type=type(exc).__name__,
                error=str(exc),
            )

        citation_status = build_citation_status(
            message=message,
            citations=citations,
            retrieval_failed=retrieval_failed,
        )
        if not citations:
            response = "Nao encontrei no documento enviado trechos suficientes para responder com seguranca."
            if processing_manifests:
                response += " Ainda ha documentos desta conversa em processamento."
            return {
                "response": response,
                "provider": "janus",
                "model": "document_grounding",
                "role": role.value,
                "citations": citations,
                "citation_status": citation_status,
                "document_grounding": {
                    "active": True,
                    "mode": "no_evidence",
                    "manifest_statuses": [str(row.get("status") or "") for row in manifests],
                },
            }

        extraction: dict[str, Any] | None = None
        provider = "janus"
        model = "document_grounding"
        try:
            if is_operational_task:
                extraction = await self._extract_document_operational_grounding(
                    message=message,
                    citations=citations,
                    role=role,
                    priority=priority,
                    timeout_seconds=timeout_seconds,
                    user_id=user_id,
                    project_id=project_id,
                )
            else:
                extraction = await self._extract_document_grounding(
                    message=message,
                    citations=citations,
                    role=role,
                    priority=priority,
                    timeout_seconds=timeout_seconds,
                    user_id=user_id,
                    project_id=project_id,
                )
        except Exception as exc:
            logger.warning(
                "document_grounding_extraction_failed",
                conversation_id=conversation_id,
                user_id=user_id,
                error_type=type(exc).__name__,
                error=str(exc),
            )

        if citations and not is_operational_task and (not extraction or not (extraction.get("supported_points") or [])):
            try:
                rechecked = await self._recheck_document_grounding(
                    message=message,
                    citations=citations,
                    role=role,
                    priority=priority,
                    timeout_seconds=timeout_seconds,
                    user_id=user_id,
                    project_id=project_id,
                )
                if rechecked:
                    extraction = rechecked
            except Exception as exc:
                logger.warning(
                    "document_grounding_recheck_failed",
                    conversation_id=conversation_id,
                    user_id=user_id,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )

        if is_operational_task:
            response = self._format_document_operational_response(
                extraction=extraction,
                citations=citations,
            )
        else:
            response = self._format_document_grounded_response(
                extraction=extraction,
                citations=citations,
            )
        return {
            "response": response,
            "provider": provider,
            "model": model,
            "role": role.value,
            "citations": citations,
            "citation_status": citation_status,
            "document_grounding": {
                "active": True,
                "mode": "strict",
                "manifest_statuses": [str(row.get("status") or "") for row in manifests],
                "indexed_doc_ids": sorted(indexed_doc_ids),
            },
        }

    async def send_message(
        self,
        conversation_id: str,
        message: str,
        role: ModelRole,
        priority: ModelPriority,
        timeout_seconds: int | None = None,
        user_id: str | None = None,
        project_id: str | None = None,
        knowledge_space_id: str | None = None,
        identity_source: str = "unknown",
    ) -> dict[str, Any]:
        try:
            conv = await asyncio.to_thread(self._repo.get_conversation, conversation_id)
        except ChatRepositoryError as e:
            raise ConversationNotFoundError(str(e)) from e

        self._conversation_service.validate_conversation_access(
            conversation_id, conv, user_id, project_id
        )

        max_bytes = int(os.getenv("CHAT_MAX_MESSAGE_BYTES", str(10 * 1024)))
        size_bytes = 0
        try:
            size_bytes = len(message.encode("utf-8")) if message else 0
        except Exception:
            size_bytes = len(message) if message else 0
        if message and size_bytes > max_bytes:
            raise MessageTooLargeError(size_bytes, max_bytes)
        understanding = build_understanding_payload(message)
        use_light_chat = self._should_use_light_chat(
            message=message,
            role=role,
            understanding=understanding,
        )

        await asyncio.to_thread(self._repo.add_message, conversation_id, role="user", text=message)
        CHAT_MESSAGES_TOTAL.labels(role="user", outcome="accepted").inc()
        self.schedule_active_memory_capture(
            message=message,
            user_id=user_id,
            conversation_id=conversation_id,
        )
        self._schedule_rag_index_message(
            text=message,
            conversation_id=conversation_id,
            role="user",
            user_id=user_id,
            project_id=project_id,
            identity_source=identity_source,
        )

        if self._command_handler.is_command(message):
            start_t = _time.time()
            assistant_text = await self._command_handler.handle_command(
                message, conversation_id, user_id
            )
            if assistant_text:
                clean_text, ui = split_ui(assistant_text)
                elapsed = max(0.0, _time.time() - start_t)
                CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
                CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()

                await asyncio.to_thread(
                    self._repo.add_message, conversation_id, role="assistant", text=assistant_text
                )
                out_tokens = estimate_tokens(self._prompt_service, assistant_text)
                CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

                result = {
                    "response": clean_text,
                    "provider": "janus",
                    "model": "quick_command",
                    "role": role.value,
                    "conversation_id": conversation_id,
                }
                if ui:
                    result["ui"] = ui
                return attach_understanding(result, understanding)

        if self._prompt_service.is_discovery_query(message):
            start_t = _time.time()
            assistant_text = self._prompt_service.render_discovery_intro(self._tools)
            clean_text, ui = split_ui(assistant_text)
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()

            await asyncio.to_thread(
                self._repo.add_message, conversation_id, role="assistant", text=assistant_text
            )
            out_tokens = estimate_tokens(self._prompt_service, assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            try:
                if self._rag_service:
                    await self._rag_service.maybe_summarize(
                        conversation_id,
                        role=role,
                        priority=priority,
                        user_id=user_id,
                        project_id=project_id,
                    )
            except Exception as e:
                logger.warning("log_warning", message=f"Failed to trigger summary during discovery for {conversation_id}: {e}"
                )

            result = {
                "response": clean_text,
                "provider": "janus",
                "model": "discovery",
                "role": role.value,
            }
            if ui:
                result["ui"] = ui

            result_with_conv = dict(result)
            result_with_conv["conversation_id"] = conversation_id
            try:
                self.trigger_post_response_events(
                    conversation_id=conversation_id,
                    user_message=message,
                    assistant_text=assistant_text,
                    result=result,
                    user_id=user_id,
                    project_id=project_id,
                )
            except Exception:
                pass
            return attach_understanding(result_with_conv, understanding)

        if self._prompt_service.is_docs_query(message):
            start_t = _time.time()
            assistant_text = self._prompt_service.render_tools_documentation(self._tools)
            clean_text, ui = split_ui(assistant_text)
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()

            await asyncio.to_thread(
                self._repo.add_message, conversation_id, role="assistant", text=assistant_text
            )
            out_tokens = estimate_tokens(self._prompt_service, assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            try:
                if self._rag_service:
                    await self._rag_service.maybe_summarize(
                        conversation_id,
                        role=role,
                        priority=priority,
                        user_id=user_id,
                        project_id=project_id,
                    )
            except Exception:
                pass

            result = {
                "response": clean_text,
                "provider": "janus",
                "model": "tools_docs",
                "role": role.value,
            }
            if ui:
                result["ui"] = ui

            result_with_conv = dict(result)
            result_with_conv["conversation_id"] = conversation_id
            try:
                self.trigger_post_response_events(
                    conversation_id=conversation_id,
                    user_message=message,
                    assistant_text=assistant_text,
                    result=result,
                    user_id=user_id,
                    project_id=project_id,
                )
            except Exception:
                pass
            return attach_understanding(result_with_conv, understanding)

        if self._prompt_service.is_capabilities_query(message):
            start_t = _time.time()
            assistant_text = self._prompt_service.render_local_capabilities(self._tools)
            clean_text, ui = split_ui(assistant_text)
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()

            await asyncio.to_thread(
                self._repo.add_message, conversation_id, role="assistant", text=assistant_text
            )
            out_tokens = estimate_tokens(self._prompt_service, assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            try:
                if self._rag_service:
                    await self._rag_service.maybe_summarize(
                        conversation_id,
                        role=role,
                        priority=priority,
                        user_id=user_id,
                        project_id=project_id,
                    )
            except Exception:
                pass

            result = {
                "response": clean_text,
                "provider": "janus",
                "model": "capabilities",
                "role": role.value,
            }
            if ui:
                result["ui"] = ui

            result_with_conv = dict(result)
            result_with_conv["conversation_id"] = conversation_id
            try:
                self.trigger_post_response_events(
                    conversation_id=conversation_id,
                    user_message=message,
                    assistant_text=assistant_text,
                    result=result,
                    user_id=user_id,
                    project_id=project_id,
                )
            except Exception:
                pass
            return attach_understanding(result_with_conv, understanding)

        if self._prompt_service.is_tool_request(message) and is_explicit_tool_creation(message):
            start_t = _time.time()
            if not self._tools:
                assistant_text = "Tool creation is unavailable: tool service is not configured."
            else:
                try:
                    from app.core.evolution import EvolutionManager

                    manager = EvolutionManager(self._llm, self._tools)
                    tool_result = await manager.evolve_tool(message)
                    assistant_text = format_tool_creation_response(tool_result)
                except Exception as e:
                    assistant_text = f"Falha ao criar ferramenta: {e}"

            clean_text, ui = split_ui(assistant_text)
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()

            await asyncio.to_thread(
                self._repo.add_message, conversation_id, role="assistant", text=assistant_text
            )
            out_tokens = estimate_tokens(self._prompt_service, assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            try:
                if self._rag_service:
                    await self._rag_service.maybe_summarize(
                        conversation_id,
                        role=role,
                        priority=priority,
                        user_id=user_id,
                        project_id=project_id,
                    )
            except Exception:
                pass

            result = {
                "response": clean_text,
                "provider": "janus",
                "model": "tool_creation",
                "role": role.value,
            }
            if ui:
                result["ui"] = ui

            result_with_conv = dict(result)
            result_with_conv["conversation_id"] = conversation_id
            try:
                self.trigger_post_response_events(
                    conversation_id=conversation_id,
                    user_message=message,
                    assistant_text=assistant_text,
                    result=result,
                    user_id=user_id,
                    project_id=project_id,
                )
            except Exception:
                pass
            return attach_understanding(result_with_conv, understanding)

        grounded_result = await self.generate_document_grounded_reply(
            conversation_id=conversation_id,
            message=message,
            role=role,
            priority=priority,
            timeout_seconds=timeout_seconds,
            user_id=user_id,
            project_id=project_id,
            requested_knowledge_space_id=knowledge_space_id,
            understanding=understanding,
        )
        if grounded_result is not None:
            start_t = _time.time()
            assistant_text = str(grounded_result.get("response") or "")
            clean_text, ui = split_ui(assistant_text)
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()

            await asyncio.to_thread(
                self._repo.add_message,
                conversation_id,
                role="assistant",
                text=assistant_text,
                metadata={
                    "knowledge_space_id": grounded_result.get("knowledge_space_id"),
                    "mode_used": grounded_result.get("mode_used"),
                    "base_used": grounded_result.get("base_used"),
                    "answer_strategy": grounded_result.get("answer_strategy"),
                    "estimated_wait_seconds": grounded_result.get("estimated_wait_seconds"),
                    "estimated_wait_range_seconds": grounded_result.get("estimated_wait_range_seconds"),
                    "processing_profile": grounded_result.get("processing_profile"),
                    "processing_notice": grounded_result.get("processing_notice"),
                    "evidence_count": grounded_result.get("evidence_count"),
                    "source_roles_used": grounded_result.get("source_roles_used"),
                    "source_scope": grounded_result.get("source_scope"),
                    "gaps_or_conflicts": grounded_result.get("gaps_or_conflicts"),
                    "citations": grounded_result.get("citations"),
                    "citation_status": grounded_result.get("citation_status"),
                    "provider": grounded_result.get("provider"),
                    "model": grounded_result.get("model"),
                },
            )
            out_tokens = estimate_tokens(self._prompt_service, assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)
            self._schedule_rag_index_message(
                text=clean_text or assistant_text,
                conversation_id=conversation_id,
                role="assistant",
                user_id=user_id,
                project_id=project_id,
                identity_source=identity_source,
            )

            result_with_conv = dict(grounded_result)
            result_with_conv["conversation_id"] = conversation_id
            result_with_conv["response"] = clean_text
            if ui:
                result_with_conv["ui"] = ui
            try:
                self.trigger_post_response_events(
                    conversation_id=conversation_id,
                    user_message=message,
                    assistant_text=assistant_text,
                    result=grounded_result,
                    user_id=user_id,
                    project_id=project_id,
                )
            except Exception:
                pass
            return attach_understanding(result_with_conv, understanding)

        secret_result = await self.generate_secret_recall_reply(
            message=message,
            role=role,
            user_id=user_id,
            conversation_id=conversation_id,
        )
        if secret_result is not None:
            assistant_text = str(secret_result.get("response") or "")
            await asyncio.to_thread(
                self._repo.add_message,
                conversation_id,
                role="assistant",
                text=assistant_text,
            )
            result_with_conv = dict(secret_result)
            result_with_conv["conversation_id"] = conversation_id
            try:
                self.trigger_post_response_events(
                    conversation_id=conversation_id,
                    user_message=message,
                    assistant_text=assistant_text,
                    result=secret_result,
                    user_id=user_id,
                    project_id=project_id,
                )
            except Exception:
                pass
            return attach_understanding(result_with_conv, understanding)

        persona = conv.get("persona") or "assistant"
        history = await asyncio.to_thread(self._repo.get_recent_messages, conversation_id, limit=60)
        relevant_memories = None
        knowledge_route = None
        if self._rag_service and not use_light_chat:
            knowledge_route = get_knowledge_routing_policy().resolve(
                RouteIntent.CHAT_CONTEXT_RETRIEVAL,
                user_id=user_id,
                include_graph=False,
                query=message,
            )
            logger.info(
                "chat.knowledge_routing_decision",
                conversation_id=conversation_id,
                rule_id=knowledge_route.rule_id,
                primary=knowledge_route.primary.value,
                fallback=knowledge_route.fallback,
            )
            relevant_memories = await self._rag_service.retrieve_context(
                message,
                user_id=user_id,
                conversation_id=conversation_id,
                caller_endpoint="/api/v1/chat/message",
                transport="rest",
                identity_source=identity_source,
                route_decision=knowledge_route,
            )

        prompt = await self._prompt_service.build_prompt(
            persona, history, message, conv.get("summary"), relevant_memories
        )
        in_tokens = estimate_tokens(self._prompt_service, prompt)
        CHAT_TOKENS_TOTAL.labels(direction="in").inc(in_tokens)

        try:
            start_t = _time.time()
            if use_light_chat:
                result = await self._llm.invoke_llm(
                    prompt=prompt,
                    role=role,
                    priority=priority,
                    timeout_seconds=timeout_seconds,
                    user_id=user_id,
                    project_id=project_id,
                )
            else:
                result = await self._agent_loop.run_loop(
                    conversation_id=conversation_id,
                    initial_prompt=prompt,
                    persona=persona,
                    message=message,
                    role=role,
                    priority=priority,
                    timeout_seconds=timeout_seconds,
                    user_id=user_id,
                    project_id=project_id,
                )
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()
        except Exception as e:
            logger.error("Agent loop failed in chat", exc_info=e)
            try:
                elapsed = max(0.0, _time.time() - start_t)
                CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="error").observe(elapsed)
                CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="error").inc()
            except Exception:
                pass
            raise ChatServiceError(str(e)) from e

        assistant_text = await self.apply_response_memory_policies(
            assistant_text=str(result.get("response", "")),
            user_message=message,
            user_id=user_id,
            conversation_id=conversation_id,
        )
        clean_text, ui = split_ui(assistant_text)
        await asyncio.to_thread(
            self._repo.add_message, conversation_id, role="assistant", text=assistant_text
        )
        out_tokens = estimate_tokens(self._prompt_service, assistant_text)
        CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

        rag_text = clean_text or assistant_text
        self._schedule_rag_index_message(
            text=rag_text,
            conversation_id=conversation_id,
            role="assistant",
            user_id=user_id,
            project_id=project_id,
            identity_source=identity_source,
        )

        try:
            provider = result.get("provider", "unknown")
            pricing = _provider_pricing.get(provider)
            if pricing:
                cost = (in_tokens / 1000.0) * float(pricing.input_per_1k_usd) + (
                    out_tokens / 1000.0
                ) * float(pricing.output_per_1k_usd)
                if user_id:
                    CHAT_SPEND_USD_TOTAL.labels(kind="user").inc(cost)
                if project_id:
                    CHAT_SPEND_USD_TOTAL.labels(kind="project").inc(cost)
        except Exception:
            pass

        if self._rag_service:
            try:
                await self._rag_service.maybe_summarize(
                    conversation_id,
                    role=role,
                    priority=priority,
                    user_id=user_id,
                    project_id=project_id,
                )
            except Exception as e:
                logger.warning(
                    "rag_summarization_failed",
                    conversation_id=conversation_id,
                    error_type=type(e).__name__,
                    error=str(e),
                )

        result_with_conv = dict(result)
        result_with_conv["conversation_id"] = conversation_id
        result_with_conv["response"] = clean_text
        if ui:
            result_with_conv["ui"] = ui
        try:
            self.trigger_post_response_events(
                conversation_id=conversation_id,
                user_message=message,
                assistant_text=assistant_text,
                result=result,
                user_id=user_id,
                project_id=project_id,
            )
        except Exception:
            pass
        return attach_understanding(result_with_conv, understanding)

    def trigger_post_response_events(
        self,
        conversation_id: str,
        user_message: str,
        assistant_text: str,
        result: dict[str, Any],
        user_id: str | None,
        project_id: str | None,
    ) -> None:
        try:
            digest = hashlib.sha256(
                f"{conversation_id}:{assistant_text}".encode("utf-8")
            ).hexdigest()[:16]
            experience_id = f"{conversation_id}:{digest}"
            dedupe_key = f"consolidation:{conversation_id}:{digest}"
            consolidation_payload = {
                "mode": "single",
                "experience_id": experience_id,
                "experience_content": assistant_text,
                "metadata": {
                    "conversation_id": conversation_id,
                    "role": result.get("role"),
                    "provider": result.get("provider"),
                    "model": result.get("model"),
                    "user_message": (user_message or "")[:500],
                    "user_id": user_id,
                    "project_id": project_id,
                    "dedupe_key": dedupe_key,
                },
            }
            if self._outbox_service:
                self._outbox_service.enqueue_consolidation(
                    payload=consolidation_payload,
                    aggregate_id=conversation_id,
                    dedupe_key=dedupe_key,
                )
            else:
                asyncio.create_task(
                    publish_consolidation_task(consolidation_payload, correlation_id=conversation_id)
                )
        except Exception:
            pass
