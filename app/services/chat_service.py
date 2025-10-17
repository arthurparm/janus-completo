import structlog
from typing import Dict, Any, List, Optional
from fastapi import Request

from app.repositories.chat_repository import ChatRepository, ChatRepositoryError
from app.services.llm_service import LLMService, LLMServiceError
from app.services.tool_service import ToolService
from app.core.llm import ModelRole, ModelPriority
from app.core.monitoring.chat_metrics import (
    CHAT_MESSAGES_TOTAL,
    CHAT_LATENCY_SECONDS,
    CHAT_TOKENS_TOTAL,
    CHAT_SPEND_USD_TOTAL,
    update_active_conversations,
)
from app.core.llm.llm_manager import _provider_pricing  # type: ignore
import time as _time
import json

logger = structlog.get_logger(__name__)


class ChatServiceError(Exception):
    """Base exception for Chat service errors."""
    pass


class ConversationNotFoundError(ChatServiceError):
    pass


class ChatService:
    """
    Orchestrates chat conversations, composing prompts with persona and history,
    delegating LLM invocation to LLMService, and storing messages in ChatRepository.
    """

    def __init__(self, repo: ChatRepository, llm_service: LLMService, tool_service: Optional[ToolService] = None):
        self._repo = repo
        self._llm = llm_service
        self._tools = tool_service

    def start_conversation(self, persona: Optional[str], user_id: Optional[str], project_id: Optional[str]) -> str:
        cid = self._repo.start_conversation(persona, user_id, project_id)
        try:
            update_active_conversations(self._repo.count_conversations())
        except Exception:
            pass
        return cid

    def send_message(
            self,
            conversation_id: str,
            message: str,
            role: ModelRole,
            priority: ModelPriority,
            timeout_seconds: Optional[int] = None,
            user_id: Optional[str] = None,
            project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            conv = self._repo.get_conversation(conversation_id)
        except ChatRepositoryError as e:
            raise ConversationNotFoundError(str(e)) from e

        persona = conv.get("persona") or "assistant"
        history = self._repo.get_recent_messages(conversation_id, limit=20)
        prompt = self._build_prompt(persona, history, message, conv.get("summary"))

        # Store user message before invocation
        self._repo.add_message(conversation_id, role="user", text=message)
        CHAT_MESSAGES_TOTAL.labels(role="user", outcome="accepted").inc()
        in_tokens = self._estimate_tokens(prompt)
        CHAT_TOKENS_TOTAL.labels(direction="in").inc(in_tokens)

        # Intercepta fluxo de descoberta interativa de ferramentas/configuração
        if self._tools and self._is_discovery_query(message):
            start_t = _time.time()
            assistant_text = self._render_discovery_intro()
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()

            # Store assistant response
            self._repo.add_message(conversation_id, role="assistant", text=assistant_text)
            out_tokens = self._estimate_tokens(assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            try:
                self._maybe_summarize(conversation_id, role=role, priority=priority, user_id=user_id,
                                      project_id=project_id)
            except Exception:
                pass

            result = {
                "response": assistant_text,
                "provider": "janus",
                "model": "discovery",
                "role": role.value,
            }

            result_with_conv = dict(result)
            result_with_conv["conversation_id"] = conversation_id
            return result_with_conv

        # Intercepta geração automática de documentação das ferramentas
        if self._tools and self._is_docs_query(message):
            start_t = _time.time()
            assistant_text = self._render_tools_documentation()
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()

            # Store assistant response
            self._repo.add_message(conversation_id, role="assistant", text=assistant_text)
            out_tokens = self._estimate_tokens(assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            # Summarização automática se histórico for grande
            try:
                self._maybe_summarize(conversation_id, role=role, priority=priority, user_id=user_id,
                                      project_id=project_id)
            except Exception:
                pass

            result = {
                "response": assistant_text,
                "provider": "janus",
                "model": "tools_docs",
                "role": role.value,
            }

            result_with_conv = dict(result)
            result_with_conv["conversation_id"] = conversation_id
            return result_with_conv

        # Intercepta perguntas sobre capacidades/ferramentas e responde com dados locais
        if self._tools and self._is_capabilities_query(message):
            start_t = _time.time()
            assistant_text = self._render_local_capabilities()
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()

            # Store assistant response
            self._repo.add_message(conversation_id, role="assistant", text=assistant_text)
            out_tokens = self._estimate_tokens(assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            # Summarização automática se histórico for grande
            try:
                self._maybe_summarize(conversation_id, role=role, priority=priority, user_id=user_id,
                                      project_id=project_id)
            except Exception:
                pass

            result = {
                "response": assistant_text,
                "provider": "janus",
                "model": "capabilities",
                "role": role.value,
            }

            result_with_conv = dict(result)
            result_with_conv["conversation_id"] = conversation_id
            return result_with_conv

        try:
            start_t = _time.time()
            result = self._llm.invoke_llm(
                prompt=prompt,
                role=role,
                priority=priority,
                timeout_seconds=timeout_seconds,
                user_id=user_id,
                project_id=project_id,
            )
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()
        except LLMServiceError as e:
            logger.error("LLM invocation failed in chat", exc_info=e)
            try:
                elapsed = max(0.0, _time.time() - start_t)
                CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="error").observe(elapsed)
                CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="error").inc()
            except Exception:
                pass
            raise ChatServiceError(str(e)) from e

        # Store assistant response
        assistant_text = result.get("response", "")
        self._repo.add_message(conversation_id, role="assistant", text=assistant_text)
        out_tokens = self._estimate_tokens(assistant_text)
        CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

        # Aproxima custo com pricing do provedor, se disponível
        try:
            provider = result.get("provider", "unknown")
            pricing = _provider_pricing.get(provider)
            if pricing:
                cost = (in_tokens / 1000.0) * float(pricing.input_per_1k_usd) + (out_tokens / 1000.0) * float(
                    pricing.output_per_1k_usd)
                if user_id:
                    CHAT_SPEND_USD_TOTAL.labels(kind="user").inc(cost)
                if project_id:
                    CHAT_SPEND_USD_TOTAL.labels(kind="project").inc(cost)
        except Exception:
            pass

        # Summarização automática se histórico for grande
        try:
            self._maybe_summarize(conversation_id, role=role, priority=priority, user_id=user_id, project_id=project_id)
        except Exception:
            # não quebrar o fluxo de resposta por erro de sumarização
            pass

        result_with_conv = dict(result)
        result_with_conv["conversation_id"] = conversation_id
        return result_with_conv

    def get_history(self, conversation_id: str) -> Dict[str, Any]:
        try:
            conv = self._repo.get_conversation(conversation_id)
        except ChatRepositoryError as e:
            raise ConversationNotFoundError(str(e)) from e
        return {
            "conversation_id": conversation_id,
            "persona": conv.get("persona"),
            "messages": conv.get("messages", []),
        }

    @staticmethod
    def _build_prompt(persona: str, history: List[Dict[str, Any]], new_user_message: str,
                      summary: Optional[str]) -> str:
        lines: List[str] = []
        # Identidade e tom (Português por padrão), reforçando primeira pessoa
        lines.append("System: Você é o assistente Janus. Fale sempre na primeira pessoa (eu) e trate o usuário na segunda pessoa (você). Evite se referir a si mesmo na terceira pessoa ou como 'o Janus' ou 'o assistente'. Use um tom polido, profissional e natural, seja direto e claro, e destaque próximos passos quando útil. Não revele detalhes internos nem o modelo subjacente. Responda no mesmo idioma do usuário; por padrão, em português.")
        # A persona pode refinar o estilo, sem violar as regras acima
        lines.append(f"System: Persona atual: {persona}. Adapte o estilo ao contexto, mantendo clareza e profissionalismo.")
        if summary:
            lines.append("System: Existe um sumário da conversa; use-o como contexto.")
            lines.append(f"Summary: {summary}")
        if history:
            lines.append("Conversation so far:")
            for m in history:
                r = m.get("role", "user")
                t = m.get("text", "")
                if r == "assistant":
                    lines.append(f"Assistant: {t}")
                else:
                    lines.append(f"User: {t}")
        lines.append(f"User: {new_user_message}")
        lines.append("Assistant:")
        return "\n".join(lines)

    def _estimate_tokens(self, text: str) -> int:
        # aproximação simples: ~4 caracteres por token
        try:
            return max(1, int(len(text) / 4))
        except Exception:
            return 1

    def _maybe_summarize(
            self,
            conversation_id: str,
            role: ModelRole,
            priority: ModelPriority,
            user_id: Optional[str],
            project_id: Optional[str],
            threshold_messages: int = 40,
    ) -> None:
        conv = self._repo.get_conversation(conversation_id)
        msgs = conv.get("messages", [])
        if len(msgs) < threshold_messages:
            return
        # já possui summary recente?
        if conv.get("summary"):
            return
        # montar texto para sumarização
        snippet = []
        for m in msgs[-threshold_messages:]:
            r = m.get("role", "user")
            t = m.get("text", "")
            prefix = "User" if r != "assistant" else "Assistant"
            snippet.append(f"{prefix}: {t}")
        sum_prompt = "Summarize the following conversation succinctly to preserve context:\n" + "\n".join(snippet)
        try:
            res = self._llm.invoke_llm(
                prompt=sum_prompt,
                role=ModelRole.KNOWLEDGE_CURATOR,
                priority=ModelPriority.FAST_AND_CHEAP,
                timeout_seconds=30,
                user_id=user_id,
                project_id=project_id,
            )
            summary_text = res.get("response", "")
            self._repo.update_summary(conversation_id, summary_text)
        except Exception:
            # falha silenciosa
            pass

    # Conversas: list/rename/delete com RBAC básico
    def list_conversations(self, user_id: Optional[str] = None, project_id: Optional[str] = None, limit: int = 50) -> \
    List[Dict[str, Any]]:
        return self._repo.list_conversations(user_id=user_id, project_id=project_id, limit=limit)

    def rename_conversation(self, conversation_id: str, new_title: str, user_id: Optional[str] = None,
                            project_id: Optional[str] = None) -> None:
        try:
            self._repo.rename_conversation(conversation_id, new_title, user_id=user_id, project_id=project_id)
        except ChatRepositoryError as e:
            raise ChatServiceError(str(e))

    def delete_conversation(self, conversation_id: str, user_id: Optional[str] = None,
                            project_id: Optional[str] = None) -> None:
        try:
            self._repo.delete_conversation(conversation_id, user_id=user_id, project_id=project_id)
            try:
                update_active_conversations(self._repo.count_conversations())
            except Exception:
                pass
        except ChatRepositoryError as e:
            raise ChatServiceError(str(e))

    # --- Query detectors and renderers ---
    def _is_capabilities_query(self, text: str) -> bool:
        try:
            t = (text or "").lower()
            keywords = [
                "quais funcionalidades", "funcionalidades", "ferramentas disponíveis", "listar ferramentas",
                "o que você pode fazer", "capacidades", "habilidades", "comandos disponíveis",
                "ferramentas locais", "minhas ferramentas",
                "capabilities", "what can you do", "tools available", "list tools", "available tools", "skills",
                "features"
            ]
            return any(k in t for k in keywords)
        except Exception:
            return False

    def _is_discovery_query(self, text: str) -> bool:
        try:
            t = (text or "").lower()
            keywords = [
                "coletar informações", "coleta de informações", "coletar dados", "questionário", "wizard",
                "configurar ferramentas", "configurar ambiente", "descoberta de ferramentas", "levantamento",
                "diagnóstico de ferramentas", "mapear ferramentas", "plano dinâmico",
                "collect information", "information gathering", "collect data", "questionnaire", "setup",
                "configure tools", "tool discovery", "diagnostic", "survey"
            ]
            return any(k in t for k in keywords)
        except Exception:
            return False

    def _is_docs_query(self, text: str) -> bool:
        try:
            t = (text or "").lower()
            keywords = [
                "gerar documentação", "documentação de ferramentas", "explicar ferramentas", "texto explicativo",
                "documentar as ferramentas", "criar documentação", "documentação automática", "detalhar ferramentas",
                "tool docs", "generate docs", "tools documentation"
            ]
            return any(k in t for k in keywords)
        except Exception:
            return False

    def _render_local_capabilities(self) -> str:
        # Fallback se o serviço de ferramentas não está disponível
        if not self._tools:
            return (
                "Capacidades locais: serviço de ferramentas não disponível. "
                "Use /web/overview para consultar status do sistema."
            )

        try:
            metas = self._tools.list_tools(category=None, permission_level=None, tags=None)
            stats = self._tools.get_statistics()
        except Exception:
            metas = []
            stats = {}

        if not metas:
            return (
                "Nenhuma ferramenta registrada no momento. "
                "Você pode criar ferramentas dinâmicas via Action Module (Sprint 6)."
            )

        # Agrupa por categoria
        grouped: Dict[str, List[str]] = {}
        for m in metas:
            cat = getattr(m.category, "value", str(m.category))
            perm = getattr(m.permission_level, "value", str(m.permission_level))
            grouped.setdefault(cat, []).append(f"{m.name} ({perm})")

        lines: List[str] = []
        lines.append("Capacidades locais detectadas dinamicamente:")
        lines.append(f"- Ferramentas registradas: {len(metas)}")
        if stats:
            total_calls = stats.get("total_calls")
            success_rate = stats.get("success_rate")
            if total_calls is not None and success_rate is not None:
                lines.append(f"- Uso recente: {total_calls} chamadas, taxa de sucesso {success_rate}")

        for cat, items in sorted(grouped.items(), key=lambda x: x[0]):
            lines.append(f"- Categoria '{cat}': {', '.join(sorted(items))}")

        lines.append(
            "\nDica: pergunte 'executar diagnóstico de ferramentas' para um fluxo guiado de verificação."
        )
        return "\n".join(lines)

    def _render_tools_documentation(self) -> str:
        # Fallback se o serviço de ferramentas não está disponível
        if not self._tools:
            return (
                "Não consigo gerar documentação local porque o serviço de ferramentas não está disponível. "
                "Verifique o estado do ToolService."
            )

        try:
            return self._tools.generate_documentation(include_stats=True, format="markdown")
        except Exception as e:
            logger.error("Falha ao gerar documentação de ferramentas", exc_info=e)
            return (
                "Ocorreu um erro ao gerar a documentação das ferramentas locais. "
                "Tente novamente mais tarde."
            )

    def _render_discovery_intro(self) -> str:
        # Usa estado atual para montar um plano adaptativo
        metas: List[Any] = []
        stats: Dict[str, Any] = {}
        if self._tools:
            try:
                metas = self._tools.list_tools(category=None, permission_level=None, tags=None)
                stats = self._tools.get_statistics()
            except Exception:
                pass

        categorias = sorted({getattr(m.category, "value", str(m.category)) for m in metas}) if metas else []
        pontos = [
            "1) Seleção de categorias relevantes (filesystem, system, web, computation, database)",
            "2) Nível de permissão desejado (read_only, safe, write, dangerous)",
            "3) Rate limit por minuto (ex.: 10, 30, 60)",
            "4) Preferência de confirmação antes de executar (sim/não)",
            "5) Ferramentas prioritárias para uso frequente",
            "6) Execução de diagnóstico rápido para validar acesso (get_system_info, list_directory, execute_python_expression)"
        ]

        lines: List[str] = []
        lines.append("Plano dinâmico de coleta e validação de ferramentas locais:")
        if categorias:
            lines.append(f"- Categorias detectadas agora: {', '.join(categorias)}")
        if stats:
            lines.append(
                f"- Registro atual: {stats.get('total_tools_registered', 0)} ferramentas, "
                f"{stats.get('total_calls', 0)} chamadas recentes"
            )

        lines.append("\nFluxo interativo:")
        for p in pontos:
            lines.append(f"- {p}")

        lines.append(
            "\nComo responder: envie algo como 'Categorias: filesystem, system; Permissões: safe; "
            "Rate limit: 30; Confirmar: sim; Prioridades: read_file, search_web; Iniciar diagnóstico'."
        )
        lines.append(
            "Eu vou adaptar as próximas perguntas com base nas suas respostas e no que estiver "
            "efetivamente disponível localmente."
        )
        return "\n".join(lines)

    # Streaming helper: retorna generator de eventos SSE (strings já formatadas)
    def stream_message(
            self,
            conversation_id: str,
            message: str,
            role: ModelRole,
            priority: ModelPriority,
            timeout_seconds: Optional[int] = None,
            user_id: Optional[str] = None,
            project_id: Optional[str] = None,
    ):
        yield "event: start\n\n"
        # add user message
        self._repo.add_message(conversation_id, role="user", text=message)
        _ack = json.dumps({"conversation_id": conversation_id})
        yield f"event: ack\ndata: {_ack}\n\n"

        # compute prompt
        conv = self._repo.get_conversation(conversation_id)
        persona = conv.get("persona") or "assistant"
        history = self._repo.get_recent_messages(conversation_id, limit=20)
        prompt = self._build_prompt(persona, history, message, conv.get("summary"))
        in_tokens = self._estimate_tokens(prompt)
        CHAT_TOKENS_TOTAL.labels(direction="in").inc(in_tokens)

        # Intercepta discovery interativo e responde sem invocar LLM
        if self._tools and self._is_discovery_query(message):
            start_t = _time.time()
            assistant_text = self._render_discovery_intro()
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)

            for i in range(0, len(assistant_text), 256):
                chunk = assistant_text[i:i + 256]
                _partial = json.dumps({"text": chunk})
                yield f"event: partial\ndata: {_partial}\n\n"

            self._repo.add_message(conversation_id, role="assistant", text=assistant_text)
            out_tokens = self._estimate_tokens(assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            _done = json.dumps({
                "conversation_id": conversation_id,
                "provider": "janus",
                "model": "discovery",
            })
            yield f"event: done\ndata: {_done}\n\n"
            return

        # Intercepta geração automática de documentação das ferramentas em streaming
        if self._tools and self._is_docs_query(message):
            start_t = _time.time()
            assistant_text = self._render_tools_documentation()
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)

            for i in range(0, len(assistant_text), 256):
                chunk = assistant_text[i:i + 256]
                _partial = json.dumps({"text": chunk})
                yield f"event: partial\ndata: {_partial}\n\n"

            self._repo.add_message(conversation_id, role="assistant", text=assistant_text)
            out_tokens = self._estimate_tokens(assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            _done = json.dumps({
                "conversation_id": conversation_id,
                "provider": "janus",
                "model": "tools_docs",
            })
            yield f"event: done\ndata: {_done}\n\n"
            return

        # Intercepta perguntas de capacidades e responde sem invocar LLM
        if self._tools and self._is_capabilities_query(message):
            start_t = _time.time()
            assistant_text = self._render_local_capabilities()
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)

            # naive chunking for SSE partials
            for i in range(0, len(assistant_text), 256):
                chunk = assistant_text[i:i + 256]
                _partial = json.dumps({"text": chunk})
                yield f"event: partial\ndata: {_partial}\n\n"

            self._repo.add_message(conversation_id, role="assistant", text=assistant_text)
            out_tokens = self._estimate_tokens(assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            _done = json.dumps({
                "conversation_id": conversation_id,
                "provider": "janus",
                "model": "capabilities",
            })
            yield f"event: done\ndata: {_done}\n\n"
            return

        try:
            start_t = _time.time()
            result = self._llm.invoke_llm(
                prompt=prompt,
                role=role,
                priority=priority,
                timeout_seconds=timeout_seconds,
                user_id=user_id,
                project_id=project_id,
            )
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            assistant_text = result.get("response", "")
            # naive chunking for SSE partials
            for i in range(0, len(assistant_text), 256):
                chunk = assistant_text[i:i + 256]
                _partial = json.dumps({"text": chunk})
                yield f"event: partial\ndata: {_partial}\n\n"
            self._repo.add_message(conversation_id, role="assistant", text=assistant_text)
            out_tokens = self._estimate_tokens(assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)
            # custo aproximado
            try:
                provider = result.get("provider", "unknown")
                pricing = _provider_pricing.get(provider)
                if pricing:
                    cost = (in_tokens / 1000.0) * float(pricing.input_per_1k_usd) + (out_tokens / 1000.0) * float(
                        pricing.output_per_1k_usd)
                    if user_id:
                        CHAT_SPEND_USD_TOTAL.labels(kind="user").inc(cost)
                    if project_id:
                        CHAT_SPEND_USD_TOTAL.labels(kind="project").inc(cost)
            except Exception:
                pass

            _done = json.dumps({
                "conversation_id": conversation_id,
                "provider": result.get("provider"),
                "model": result.get("model"),
            })
            yield f"event: done\ndata: {_done}\n\n"
        except Exception as e:
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="error").observe(max(0.0, _time.time() - start_t))
            _err = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {_err}\n\n"


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service

    # --- Helpers ---
