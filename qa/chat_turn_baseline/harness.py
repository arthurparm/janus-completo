from __future__ import annotations

import asyncio
import json
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, AsyncIterator, Callable, cast
from unittest.mock import AsyncMock, patch

from app.api.v1.endpoints.chat import chat_message
from app.core.llm import ModelPriority, ModelRole
from app.repositories.chat_repository import ChatRepositoryError
from app.services.chat.conversation_service import ConversationService
from app.services.chat.message_orchestration_service import MessageOrchestrationService
from app.services.chat.streaming_service import StreamingService
from fastapi import HTTPException

BASELINE_COMMIT = "aff4681741d77f09b1254d6eda0781d6aca0dc12"
BASELINE_REF = "refs/heads/codex/chat-turn-baseline-aff4681"
SNAPSHOT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Scenario:
    name: str
    message: str
    prompt_kind: str = "dynamic"
    knowledge_space_id: str | None = None


ADR_SCENARIOS: tuple[Scenario, ...] = (
    Scenario("light_chat", "Qual e o status do sistema?"),
    Scenario(
        "operational_non_light",
        "Implemente uma rotina operacional completa com validacao, rollback e relatorio detalhado.",
    ),
    Scenario("discovery", "Quais recursos estao disponiveis?", prompt_kind="discovery"),
    Scenario("docs", "Mostre a documentacao das ferramentas.", prompt_kind="docs"),
    Scenario("capabilities", "Quais sao suas capacidades locais?", prompt_kind="capabilities"),
    Scenario(
        "blocked_tool_creation",
        "Crie uma ferramenta nova para executar tarefas.",
        prompt_kind="tool_creation",
    ),
    Scenario("indexed_document", "Quais sinais o documento indexado menciona?"),
    Scenario(
        "knowledge_space_pending",
        "O que diz o material ativo?",
        knowledge_space_id="space-1",
    ),
    Scenario(
        "missing_required_with_knowledge_space",
        "Explique a funcao critica no codigo.",
        knowledge_space_id="space-1",
    ),
    Scenario(
        "missing_required_without_knowledge_space",
        "Explique a funcao ausente no codigo.",
    ),
    Scenario("secret_recall", "Qual e a minha senha ficticia do Wi-Fi?"),
    Scenario("high_risk", "Execute o deploy em production agora."),
    Scenario(
        "provider_error",
        "Implemente uma rotina operacional extensa que depende do provedor externo.",
    ),
    Scenario("citation_timeout", "Explique a funcao lenta no codigo."),
    Scenario("sse_disconnect_resume", "Conte uma curiosidade curta."),
)

ADDITIONAL_SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        "conversation_access_denied",
        "Explique a funcao privada no codigo.",
        knowledge_space_id="space-foreign",
    ),
)

SCENARIOS: tuple[Scenario, ...] = ADR_SCENARIOS + ADDITIONAL_SCENARIOS


DOCUMENT_CITATION = {
    "id": "citation-1",
    "doc_id": "doc-1",
    "title": "manual.txt",
    "file_path": "manual.txt",
    "source_type": "document",
    "line_start": 10,
    "line_end": 12,
    "line": 10,
    "snippet": "O documento registra sinais neurologicos agudos.",
}


class CaptureRepository:
    def __init__(self, scenario: Scenario, trace: list[str]):
        owner = "other-user" if scenario.name == "conversation_access_denied" else "user-1"
        self.conversation: dict[str, Any] = {
            "persona": "assistant",
            "summary": None,
            "user_id": owner,
            "project_id": "project-1",
            "messages": [],
        }
        self.trace = trace
        self.add_message_writes = 0
        self.update_message_payload_writes = 0

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        self.trace.append("repo.get_conversation")
        if conversation_id != "conv-1":
            raise ChatRepositoryError(f"Conversation not found: {conversation_id}")
        return self.conversation

    def get_recent_messages(self, conversation_id: str, limit: int = 20) -> list[dict[str, Any]]:
        self.trace.append(f"repo.get_recent_messages:{limit}")
        return [
            {
                "id": 0,
                "timestamp": 0.0,
                "role": "user",
                "text": "mensagem anterior",
            }
        ]

    def add_message(
        self,
        conversation_id: str,
        role: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.trace.append(f"repo.add_message:{role}")
        self.add_message_writes += 1
        payload = {
            "id": len(self.conversation["messages"]) + 1,
            "timestamp": 0.0,
            "role": role,
            "text": text,
            **deepcopy(metadata or {}),
        }
        self.conversation["messages"].append(payload)
        return deepcopy(payload)

    def get_last_assistant_message(
        self,
        conversation_id: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        self.trace.append("repo.get_last_assistant_message")
        self._assert_owner(user_id)
        for item in reversed(self.conversation["messages"]):
            if item.get("role") == "assistant":
                return cast(dict[str, Any], deepcopy(item))
        raise ChatRepositoryError("Assistant message not found")

    def update_message_payload(
        self,
        conversation_id: str,
        message_id: int,
        patch: dict[str, Any],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        self.trace.append("repo.update_message_payload")
        self._assert_owner(user_id)
        self.update_message_payload_writes += 1
        for item in self.conversation["messages"]:
            if int(item.get("id") or 0) == int(message_id):
                item.update(deepcopy(patch))
                return deepcopy(item)
        raise ChatRepositoryError("Message not found")

    def _assert_owner(self, user_id: str | None) -> None:
        owner = self.conversation.get("user_id")
        if user_id and owner and str(user_id) != str(owner):
            raise ChatRepositoryError("Access denied: user_id mismatch")

    def last_assistant(self) -> dict[str, Any] | None:
        for item in reversed(self.conversation["messages"]):
            if item.get("role") == "assistant":
                return cast(dict[str, Any], deepcopy(item))
        return None


class CapturePromptService:
    def __init__(self, scenario: Scenario, trace: list[str]):
        self.scenario = scenario
        self.trace = trace

    async def build_prompt(
        self,
        persona: str,
        history: list[dict[str, Any]],
        message: str,
        summary: str | None,
        relevant_memories: Any,
    ) -> str:
        self.trace.append("prompt.build")
        return f"{persona}:{message}"

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text or "") // 4)

    def is_discovery_query(self, message: str) -> bool:
        return self.scenario.prompt_kind == "discovery"

    def render_discovery_intro(self, tools: Any) -> str:
        return "discovery response"

    def is_docs_query(self, message: str) -> bool:
        return self.scenario.prompt_kind == "docs"

    def render_tools_documentation(self, tools: Any) -> str:
        return "docs response"

    def is_capabilities_query(self, message: str) -> bool:
        return self.scenario.prompt_kind == "capabilities"

    def render_local_capabilities(self) -> str:
        return "capabilities response"

    def is_tool_request(self, message: str) -> bool:
        return self.scenario.prompt_kind == "tool_creation"


class CaptureCommandHandler:
    def is_command(self, message: str) -> bool:
        return False

    async def handle_command(self, message: str, conversation_id: str) -> None:
        return None


def _request_summary(kwargs: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in (
        "role",
        "priority",
        "timeout_seconds",
        "task_type",
        "complexity",
        "policy_overrides",
        "user_id",
        "project_id",
    ):
        value = kwargs.get(key)
        if hasattr(value, "value"):
            value = getattr(value, "value")
        result[key] = deepcopy(value)
    return result


class CaptureLLM:
    def __init__(self, scenario: Scenario, trace: list[str]):
        self.scenario = scenario
        self.trace = trace
        self.invoke_requests: list[dict[str, Any]] = []
        self.select_requests: list[dict[str, Any]] = []

    async def select_provider(self, **kwargs: Any) -> dict[str, str]:
        self.trace.append("llm.select_provider")
        self.select_requests.append(_request_summary(kwargs))
        return {"provider": "baseline-llm", "model": "baseline-model"}

    def is_provider_open(self, provider: str) -> bool:
        return False

    async def invoke_llm(self, **kwargs: Any) -> dict[str, Any]:
        self.trace.append("llm.invoke")
        self.invoke_requests.append(_request_summary(kwargs))
        if self.scenario.name == "provider_error":
            raise RuntimeError("deterministic provider failure")
        if self.scenario.name == "indexed_document":
            response = json.dumps(
                {
                    "answer": "O documento registra sinais neurologicos agudos.",
                    "supported_points": [
                        {
                            "statement": "Ha sinais neurologicos agudos.",
                            "citation_ids": [1],
                        }
                    ],
                    "missing_information": [],
                },
                ensure_ascii=False,
            )
        elif self.scenario.name == "missing_required_with_knowledge_space":
            response = "Evidencia pendente. pending action id: 77"
        else:
            response = f"llm response:{self.scenario.name}"
        return {
            "response": response,
            "provider": "baseline-llm",
            "model": "baseline-model",
            "role": str(getattr(kwargs.get("role"), "value", "orchestrator")),
        }


class CaptureAgentLoop:
    def __init__(self, scenario: Scenario, trace: list[str]):
        self.scenario = scenario
        self.trace = trace
        self.requests: list[dict[str, Any]] = []

    async def run_loop(self, **kwargs: Any) -> dict[str, Any]:
        self.trace.append("agent_loop.run_loop")
        self.requests.append(_request_summary(kwargs))
        if self.scenario.name == "provider_error":
            raise RuntimeError("deterministic provider failure")
        if self.scenario.name == "missing_required_with_knowledge_space":
            response = "Evidencia pendente. pending action id: 77"
        else:
            response = f"agent-loop response:{self.scenario.name}"
        return {
            "response": response,
            "provider": "baseline-agent-loop",
            "model": "baseline-agent-model",
            "role": "orchestrator",
        }


class CaptureManifestRepository:
    def __init__(self, scenario: Scenario):
        self.scenario = scenario

    def list_manifests(self, **kwargs: Any) -> list[dict[str, Any]]:
        if self.scenario.name != "indexed_document":
            return []
        return [
            {
                "doc_id": "doc-1",
                "status": "indexed",
                "chunks_indexed": 3,
                "file_name": "manual.txt",
                "doc_role": "base",
            }
        ]


class CaptureOutbox:
    def __init__(self, trace: list[str]):
        self.trace = trace
        self.enqueues: list[dict[str, Any]] = []

    def enqueue_consolidation(self, **kwargs: Any) -> None:
        self.trace.append("outbox.enqueue_consolidation")
        self.enqueues.append(deepcopy(kwargs))


class CaptureStudyJobs:
    def __init__(self, trace: list[str]):
        self.trace = trace
        self.created = 0
        self.run = 0

    def create_job(self, **kwargs: Any) -> Any:
        self.trace.append("study_job.create")
        self.created += 1
        return SimpleNamespace(
            job_id="study-job-1",
            status="queued",
            placeholder_message=kwargs.get("placeholder_message"),
        )

    async def run_job(self, **kwargs: Any) -> None:
        self.trace.append("study_job.run")
        self.run += 1


class CaptureStudyService:
    instances: list["CaptureStudyService"] = []
    shared_trace: list[str] = []

    def __init__(self, **kwargs: Any):
        self.calls = 0
        self.__class__.instances.append(self)

    async def answer_with_study(self, *, progress_cb: Callable[..., Any], **kwargs: Any) -> dict[str, Any]:
        self.calls += 1
        self.__class__.shared_trace.append("study.callback:25")
        await progress_cb(25, "retrieval", "Buscando evidencias")
        self.__class__.shared_trace.append("study.callback:100")
        await progress_cb(100, "synthesis", "Sintetizando resposta")
        self.__class__.shared_trace.append("study.return")
        return {
            "response": "study response with evidence",
            "provider": "baseline-study",
            "model": "baseline-study-model",
            "citations": [deepcopy(DOCUMENT_CITATION)],
            "citation_status": {
                "mode": "required",
                "status": "complete",
                "count": 1,
                "reason": None,
            },
        }


class CaptureRoutingDecision:
    intent = "deployment"
    risk_level = "high"
    confidence = 0.91

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
        }


class CaptureRoutingService:
    def __init__(self, scenario: Scenario):
        self.scenario = scenario

    def resolve_role(self, requested_role: str, message: str) -> tuple[ModelRole, Any, bool]:
        if self.scenario.name == "high_risk":
            return ModelRole.ORCHESTRATOR, CaptureRoutingDecision(), True
        return ModelRole.ORCHESTRATOR, None, False


class CaptureFacade:
    def __init__(
        self,
        orchestration: MessageOrchestrationService,
        repo: CaptureRepository,
        trace: list[str],
    ):
        self.orchestration = orchestration
        self.repo = repo
        self.trace = trace

    def resolve_active_knowledge_space_id(
        self,
        *,
        conversation_id: str,
        user_id: str | None = None,
        requested_knowledge_space_id: str | None = None,
    ) -> str | None:
        self.trace.append("service.resolve_active_knowledge_space_id")
        return requested_knowledge_space_id

    async def resolve_authorized_knowledge_space_id(
        self,
        *,
        conversation_id: str,
        user_id: str | None = None,
        project_id: str | None = None,
        requested_knowledge_space_id: str | None = None,
    ) -> str | None:
        self.trace.append("service.resolve_authorized_knowledge_space_id")
        return await self.orchestration.resolve_authorized_knowledge_space_id(
            conversation_id=conversation_id,
            user_id=user_id,
            project_id=project_id,
            requested_knowledge_space_id=requested_knowledge_space_id,
        )

    async def send_message(self, **kwargs: Any) -> dict[str, Any]:
        self.trace.append("service.send_message")
        return cast(dict[str, Any], await self.orchestration.send_message(**kwargs))

    async def get_last_assistant_message(
        self,
        *,
        conversation_id: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        return self.repo.get_last_assistant_message(conversation_id, user_id=user_id)

    async def update_message_payload(
        self,
        *,
        conversation_id: str,
        message_id: int,
        patch: dict[str, Any],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        return self.repo.update_message_payload(
            conversation_id,
            message_id,
            patch,
            user_id=user_id,
        )

    async def persist_finalized_turn(self, **kwargs: Any) -> dict[str, Any]:
        self.trace.append("service.persist_finalized_turn")
        return await self.orchestration.persist_finalized_turn(**kwargs)


class CaptureHttpRequest:
    def __init__(self, scenario: Scenario, jobs: CaptureStudyJobs):
        self._payload = {
            "conversation_id": "conv-1",
            "message": scenario.message,
            "role": "auto",
            "priority": "fast_and_cheap",
            "project_id": "project-1",
            "knowledge_space_id": scenario.knowledge_space_id,
        }
        self.headers = {"authorization": "Bearer deterministic-test-token"}
        self.state = SimpleNamespace(actor_context=SimpleNamespace(actor_id="user-1"))
        self.app = SimpleNamespace(state=SimpleNamespace(chat_study_job_service=jobs))

    async def json(self) -> dict[str, Any]:
        return deepcopy(self._payload)


class CaptureMemory:
    pass


@dataclass
class CaptureEnvironment:
    scenario: Scenario
    trace: list[str]
    repo: CaptureRepository
    prompt: CapturePromptService
    llm: CaptureLLM
    agent_loop: CaptureAgentLoop
    outbox: CaptureOutbox
    jobs: CaptureStudyJobs
    orchestration: MessageOrchestrationService
    streaming: StreamingService
    facade: CaptureFacade


def _build_environment(scenario: Scenario) -> CaptureEnvironment:
    trace: list[str] = []
    repo = CaptureRepository(scenario, trace)
    prompt = CapturePromptService(scenario, trace)
    llm = CaptureLLM(scenario, trace)
    agent_loop = CaptureAgentLoop(scenario, trace)
    outbox = CaptureOutbox(trace)
    jobs = CaptureStudyJobs(trace)
    conversation = ConversationService(repo)
    orchestration = MessageOrchestrationService(
        repo=repo,
        llm_service=llm,
        tool_service=None,
        prompt_service=prompt,
        rag_service=None,
        command_handler=CaptureCommandHandler(),
        agent_loop=agent_loop,
        conversation_service=conversation,
        outbox_service=outbox,
        manifest_repo=CaptureManifestRepository(scenario),
    )
    orchestration.schedule_active_memory_capture = (
        lambda **kwargs: trace.append("active_memory.schedule")
    )
    orchestration._schedule_rag_index_message = (
        lambda **kwargs: trace.append(f"rag_index.schedule:{kwargs.get('role')}")
    )

    if scenario.name == "knowledge_space_pending":
        async def _processing_grounded(**kwargs: Any) -> dict[str, Any]:
            trace.append("grounding.processing_result")
            return {
                "response": "knowledge space is still processing",
                "provider": "janus",
                "model": "document_processing",
                "role": "orchestrator",
                "knowledge_space_id": "space-1",
                "processing_notice": "indexing in progress",
                "citations": [],
                "citation_status": {
                    "mode": "required",
                    "status": "missing_required",
                    "count": 0,
                    "reason": "no_sources",
                },
            }

        orchestration.generate_document_grounded_reply = _processing_grounded
    elif scenario.name == "missing_required_with_knowledge_space":
        async def _missing_grounding(**kwargs: Any) -> None:
            trace.append("grounding.no_result")
            return None

        orchestration.generate_document_grounded_reply = _missing_grounding

    streaming = StreamingService(
        repo=repo,
        llm_service=llm,
        tool_service=None,
        prompt_service=prompt,
        rag_service=None,
        conversation_service=conversation,
        message_orchestration_service=orchestration,
        study_job_service=jobs,
    )
    facade = CaptureFacade(orchestration, repo, trace)
    return CaptureEnvironment(
        scenario=scenario,
        trace=trace,
        repo=repo,
        prompt=prompt,
        llm=llm,
        agent_loop=agent_loop,
        outbox=outbox,
        jobs=jobs,
        orchestration=orchestration,
        streaming=streaming,
        facade=facade,
    )


def _pending_action_double(**kwargs: Any) -> tuple[int | None, str | None]:
    existing = kwargs.get("existing_pending_action_id")
    understanding = kwargs.get("understanding") or {}
    reason = understanding.get("confirmation_reason") if isinstance(understanding, dict) else None
    if existing is not None:
        return int(existing), reason
    if reason == "high_risk":
        return 4242, "high_risk"
    return None, reason


async def _document_citations_double(**kwargs: Any) -> list[dict[str, Any]]:
    return [deepcopy(DOCUMENT_CITATION)]


def _citation_result_for(scenario: Scenario) -> dict[str, Any]:
    if scenario.name == "citation_timeout":
        return {
            "citations": [deepcopy(DOCUMENT_CITATION)],
            "retrieval_failed": False,
        }
    return {"citations": [], "retrieval_failed": False}


async def _rest_citation_double(scenario: Scenario, **kwargs: Any) -> dict[str, Any]:
    if scenario.name == "citation_timeout":
        raise asyncio.TimeoutError
    return _citation_result_for(scenario)


async def _sse_citation_double(scenario: Scenario, **kwargs: Any) -> dict[str, Any]:
    return _citation_result_for(scenario)


def _patches(env: CaptureEnvironment) -> ExitStack:
    from app.services.chat import message_orchestration_service as orchestration_module
    from app.services.chat import streaming_service as streaming_module

    stack = ExitStack()
    stack.enter_context(
        patch.object(
            orchestration_module.secret_memory_service,
            "should_authorize_prompt_recall",
            lambda message: env.scenario.name == "secret_recall",
        )
    )
    secret_items = (
        [{"secret_label": "senha ficticia do wi-fi", "secret_value": "Abc12345"}]
        if env.scenario.name == "secret_recall"
        else []
    )
    stack.enter_context(
        patch.object(
            orchestration_module.secret_memory_service,
            "list_secrets",
            AsyncMock(return_value=secret_items),
        )
    )
    stack.enter_context(
        patch.object(
            orchestration_module.procedural_memory_service,
            "list_rules",
            AsyncMock(return_value=[]),
        )
    )
    stack.enter_context(
        patch.object(
            orchestration_module,
            "collect_document_citations",
            _document_citations_double,
        )
    )
    stack.enter_context(
        patch(
            "app.core.security.security_alerts.emit_security_alert",
            lambda *args, **kwargs: env.trace.append("security_alert.emit"),
        )
    )
    stack.enter_context(
        patch.object(
            chat_message,
            "get_intent_routing_service",
            lambda: CaptureRoutingService(env.scenario),
        )
    )
    stack.enter_context(
        patch.object(
            chat_message,
            "_collect_chat_citations_with_deadline",
            lambda **kwargs: _rest_citation_double(env.scenario, **kwargs),
        )
    )
    stack.enter_context(
        patch.object(chat_message, "maybe_create_fallback_pending_action", _pending_action_double)
    )
    stack.enter_context(
        patch.object(streaming_module, "maybe_create_fallback_pending_action", _pending_action_double)
    )
    stack.enter_context(
        patch.object(
            streaming_module,
            "collect_chat_citations",
            lambda **kwargs: _rest_citation_double(env.scenario, **kwargs),
        )
    )
    CaptureStudyService.instances = []
    CaptureStudyService.shared_trace = env.trace
    return stack


def _routing_inputs(scenario: Scenario) -> tuple[Any, bool]:
    if scenario.name == "high_risk":
        return CaptureRoutingDecision(), True
    return None, False


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _domain_fields(payload: dict[str, Any], response_text: str | None) -> dict[str, Any]:
    return {
        "response": response_text,
        "citations": _jsonable(payload.get("citations")) if payload.get("citations") is not None else None,
        "citation_status": _jsonable(payload.get("citation_status")),
        "understanding": _jsonable(payload.get("understanding")),
        "confirmation": _jsonable(payload.get("confirmation")),
        "agent_state": _jsonable(payload.get("agent_state")),
        "delivery_status": payload.get("delivery_status"),
        "provider": payload.get("provider"),
        "model": payload.get("model"),
        "failure_classification": payload.get("failure_classification"),
    }


def _persisted_fields(repo: CaptureRepository) -> dict[str, Any] | None:
    item = repo.last_assistant()
    if item is None:
        return None
    return {
        "text": item.get("text"),
        "citations": _jsonable(item.get("citations")),
        "citation_status": _jsonable(item.get("citation_status")),
        "understanding": _jsonable(item.get("understanding")),
        "confirmation": _jsonable(item.get("confirmation")),
        "agent_state": _jsonable(item.get("agent_state")),
        "delivery_status": item.get("delivery_status"),
        "provider": item.get("provider"),
        "model": item.get("model"),
        "failure_classification": item.get("failure_classification"),
    }


def _base_snapshot(
    env: CaptureEnvironment,
    *,
    transport: str,
    output: dict[str, Any],
    terminal: dict[str, Any],
    observations: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "baseline_commit": BASELINE_COMMIT,
        "baseline_ref": BASELINE_REF,
        "scenario": env.scenario.name,
        "transport": transport,
        "output": output,
        "terminal": terminal,
        "persistence": {
            "writes": {
                "add_message": env.repo.add_message_writes,
                "update_message_payload": env.repo.update_message_payload_writes,
            },
            "last_assistant": _persisted_fields(env.repo),
        },
        "execution": {
            "llm_invoke_count": len(env.llm.invoke_requests),
            "llm_requests": env.llm.invoke_requests,
            "agent_loop_count": len(env.agent_loop.requests),
            "agent_loop_requests": env.agent_loop.requests,
            "study_job_create_count": env.jobs.created,
            "blocking_study_count": sum(item.calls for item in CaptureStudyService.instances),
            "outbox_enqueue_count": len(env.outbox.enqueues),
        },
        "observations": {
            "trace": list(env.trace),
            **(observations or {}),
        },
    }


async def capture_rest(scenario: Scenario) -> dict[str, Any]:
    env = _build_environment(scenario)
    http = CaptureHttpRequest(scenario, env.jobs)
    payload: dict[str, Any] = {}
    status_code = 200
    with _patches(env):
        try:
            result = await chat_message.send_message(
                service=env.facade,
                http=http,
                memory=CaptureMemory(),
            )
            payload = _jsonable(result)
        except HTTPException as exc:
            status_code = int(exc.status_code)
            payload = {"error": _jsonable(exc.detail)}
        await asyncio.sleep(0)

    response_text = payload.get("response") if status_code < 400 else None
    observations: dict[str, Any] = {}
    if scenario.name == "sse_disconnect_resume":
        observations["transport_note"] = "REST has no SSE disconnect/replay framing in this case."
    return _base_snapshot(
        env,
        transport="rest",
        output=_domain_fields(payload, response_text),
        terminal={
            "kind": "http",
            "status_code": status_code,
            "error": payload.get("error") if status_code >= 400 else None,
        },
        observations=observations,
    )


def _parse_sse_chunk(chunk: str) -> tuple[str, Any]:
    event_name = "message"
    data_lines: list[str] = []
    for line in chunk.strip().splitlines():
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].lstrip())
    if not data_lines:
        return event_name, None
    raw = "\n".join(data_lines)
    try:
        return event_name, json.loads(raw)
    except Exception:
        return event_name, raw


async def _consume_stream(
    stream: AsyncIterator[str],
    trace: list[str],
    *,
    stop_after_first_token: bool = False,
) -> list[tuple[str, Any]]:
    events: list[tuple[str, Any]] = []
    async for chunk in stream:
        event_name, data = _parse_sse_chunk(chunk)
        trace.append(f"sse.event:{event_name}")
        events.append((event_name, data))
        if stop_after_first_token and event_name == "token":
            await stream.aclose()  # type: ignore[attr-defined]
            break
    return events


def _last_terminal(events: list[tuple[str, Any]]) -> tuple[str, dict[str, Any]]:
    for event_name, data in reversed(events):
        if event_name in {"done", "error"}:
            return event_name, data if isinstance(data, dict) else {}
    return "incomplete", {}


def _token_text(events: list[tuple[str, Any]]) -> str | None:
    parts = [
        str(data.get("text") or "")
        for event_name, data in events
        if event_name == "token" and isinstance(data, dict)
    ]
    return "".join(parts) if parts else None


async def capture_sse(scenario: Scenario) -> dict[str, Any]:
    env = _build_environment(scenario)
    routing_decision, route_applied = _routing_inputs(scenario)
    attempts: list[list[tuple[str, Any]]] = []
    with _patches(env):
        if scenario.name == "sse_disconnect_resume":
            first_stream = env.streaming.stream_message(
                conversation_id="conv-1",
                message=scenario.message,
                role=ModelRole.ORCHESTRATOR,
                priority=ModelPriority.FAST_AND_CHEAP,
                user_id="user-1",
                project_id="project-1",
                identity_source="actor",
                requested_role="auto",
                routing_decision=routing_decision,
                route_applied=route_applied,
            )
            attempts.append(
                await _consume_stream(first_stream, env.trace, stop_after_first_token=True)
            )
        stream = env.streaming.stream_message(
            conversation_id="conv-1",
            message=scenario.message,
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.FAST_AND_CHEAP,
            user_id="user-1",
            project_id="project-1",
            knowledge_space_id=scenario.knowledge_space_id,
            identity_source="actor",
            requested_role="auto",
            routing_decision=routing_decision,
            route_applied=route_applied,
        )
        attempts.append(await _consume_stream(stream, env.trace))

    final_events = attempts[-1]
    terminal_event, terminal_payload = _last_terminal(final_events)
    response_text = _token_text(final_events)
    output = _domain_fields(terminal_payload, response_text)
    terminal = {
        "kind": "sse",
        "event": terminal_event,
        "code": terminal_payload.get("code") if terminal_event == "error" else None,
        "http_status": terminal_payload.get("http_status") if terminal_event == "error" else None,
    }
    event_attempts = [[name for name, _ in events] for events in attempts]
    return _base_snapshot(
        env,
        transport="sse",
        output=output,
        terminal=terminal,
        observations={
            "connection_attempts": len(attempts),
            "event_sequence_by_attempt": event_attempts,
        },
    )


async def capture_all() -> dict[str, dict[str, Any]]:
    captures: dict[str, dict[str, Any]] = {}
    for scenario in SCENARIOS:
        captures[f"{scenario.name}/rest.json"] = await capture_rest(scenario)
        captures[f"{scenario.name}/sse.json"] = await capture_sse(scenario)
    return captures


def snapshot_root(repository_root: Path) -> Path:
    return repository_root / "qa" / "snapshots" / "chat_turn_baseline"


def write_snapshots(repository_root: Path, captures: dict[str, dict[str, Any]]) -> None:
    root = snapshot_root(repository_root)
    for relative_path, payload in captures.items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def load_snapshots(repository_root: Path) -> dict[str, dict[str, Any]]:
    root = snapshot_root(repository_root)
    loaded: dict[str, dict[str, Any]] = {}
    for scenario in SCENARIOS:
        for transport in ("rest", "sse"):
            relative_path = f"{scenario.name}/{transport}.json"
            loaded[relative_path] = json.loads((root / relative_path).read_text(encoding="utf-8"))
    return loaded
