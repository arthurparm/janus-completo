"""
Chat Agent Loop Service.
Executes ReAct (Reasoning + Acting) loop with tool execution fallbacks.
"""

import asyncio
import re
import structlog
from typing import Any
from app.config import settings
from app.core.autonomy.policy_engine import PolicyConfig, PolicyEngine, RiskProfile
from app.core.llm import ModelRole, ModelPriority
from app.core.infrastructure.fallback_chain import FallbackChain
from app.core.exceptions.chat_exceptions import LLMInvocationError, ToolExecutionError

logger = structlog.get_logger(__name__)
_PENDING_ACTION_ID_RE = re.compile(r"Pending action id:\s*(\d+)", re.IGNORECASE)


class ChatAgentLoop:
    """
    Executes ReAct agent loop with tool calling.

    Features:
    - Hierarchical tool execution fallbacks
    - Max iteration limit (prevents research paralysis)
    - Event publishing for UI streaming
    - Token tracking
    """

    def __init__(
        self,
        llm_service: Any,
        tool_executor: Any,
        rag_service: Any | None = None,
        event_publisher: Any | None = None,
        prompt_service: Any | None = None,
    ):
        """
        Initialize agent loop.

        Args:
            llm_service: LLM service for model invocation
            tool_executor: Tool executor service
            rag_service: Optional RAG service for context retrieval
            event_publisher: Optional event publisher
            prompt_service: Optional prompt builder service
        """
        self.llm_service = llm_service
        self.tool_executor = tool_executor
        self.rag_service = rag_service
        self.event_publisher = event_publisher
        self.prompt_service = prompt_service

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count."""
        if not text:
            return 0
        if self.prompt_service:
            try:
                return self.prompt_service.estimate_tokens(text)
            except Exception:
                pass
        return max(1, len(text) // 4)

    def _build_policy(self) -> PolicyEngine:
        risk_profile = str(settings.CHAT_TOOL_RISK_PROFILE or RiskProfile.BALANCED).strip()
        if not risk_profile:
            risk_profile = RiskProfile.BALANCED
        auto_confirm = bool(settings.CHAT_TOOL_AUTO_CONFIRM)
        allowlist = {name.strip() for name in settings.CHAT_TOOL_ALLOWLIST if str(name).strip()}
        blocklist = {name.strip() for name in settings.CHAT_TOOL_BLOCKLIST if str(name).strip()}
        max_actions = int(settings.CHAT_TOOL_MAX_ACTIONS)
        max_seconds = int(settings.CHAT_TOOL_MAX_SECONDS)

        return PolicyEngine(
            PolicyConfig(
                risk_profile=risk_profile,
                auto_confirm=auto_confirm,
                allowlist=allowlist,
                blocklist=blocklist,
                max_actions_per_cycle=max_actions,
                max_seconds_per_cycle=max_seconds,
            )
        )

    async def run_loop(
        self,
        conversation_id: str,
        initial_prompt: str,
        persona: str,
        message: str,
        role: ModelRole,
        priority: ModelPriority,
        timeout_seconds: int | None = None,
        user_id: str | None = None,
        project_id: str | None = None,
        max_iterations: int = 5,
    ) -> dict[str, Any]:
        """
        Execute ReAct agent loop.

        Args:
            conversation_id: Conversation ID
            initial_prompt: Initial built prompt
            persona: Conversation persona
            message: User message
            role: Model role
            priority: Model priority
            timeout_seconds: Optional timeout
            user_id: Optional user ID
            project_id: Optional project ID
            max_iterations: Max loop iterations (default 5)

        Returns:
            Dict with response, provider, model, tokens, etc.
        """
        current_prompt = initial_prompt
        total_in_tokens = self._estimate_tokens(current_prompt)
        total_out_tokens = 0
        final_response_text = ""
        last_result = {}
        pending_action_id: int | None = None
        pending_tool_name: str | None = None
        policy = self._build_policy()
        policy.reset_cycle_quota()

        user_content_safety = policy.validate_content_safety(message)
        if not user_content_safety.allowed:
            logger.warning(
                "chat_input_blocked_by_content_safety",
                conversation_id=conversation_id,
                reason=user_content_safety.reason,
            )
            blocked_response = (
                "Nao posso processar esse pedido porque ele contem instrucoes inseguras "
                "ou tentativa de bypass de politicas."
            )
            return {
                "response": blocked_response,
                "provider": "janus",
                "model": "policy_guard",
                "role": role.value,
                "conversation_id": conversation_id,
                "total_in_tokens": total_in_tokens,
                "total_out_tokens": self._estimate_tokens(blocked_response),
            }

        iteration = 0
        while iteration < max_iterations:
            iteration += 1

            logger.info(
                "agent_loop_iteration",
                iteration=iteration,
                max_iterations=max_iterations,
                conversation_id=conversation_id,
            )

            # Publish thought event
            if self.event_publisher:
                await self.event_publisher.publish_event(
                    conversation_id=conversation_id,
                    event_type="agent_thought",
                    agent_role=role.value,
                    content=f"Iteration {iteration}/{max_iterations}: Analyzing request and planning response",
                    user_id=user_id,
                )

            # Invoke LLM with fallback
            try:
                result = await self._invoke_llm_with_fallback(
                    prompt=current_prompt,
                    role=role,
                    priority=priority,
                    timeout_seconds=timeout_seconds,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    project_id=project_id,
                )
                last_result = result
            except Exception as e:
                logger.error(
                    "llm_invocation_failed_agent_loop",
                    iteration=iteration,
                    error=str(e),
                    conversation_id=conversation_id,
                )
                if iteration == 1:
                    raise  # Fail fast on first iteration
                break  # Return what we have so far

            response_text = result.get("response", "")
            total_out_tokens += self._estimate_tokens(response_text)

            response_content_safety = policy.validate_content_safety(response_text)
            if not response_content_safety.allowed:
                logger.warning(
                    "chat_model_response_blocked_by_content_safety",
                    conversation_id=conversation_id,
                    iteration=iteration,
                    reason=response_content_safety.reason,
                )
                final_response_text = (
                    "A resposta intermediaria foi bloqueada por politica de seguranca. "
                    "Reformule o pedido de forma objetiva."
                )
                break

            # Check for tool calls
            tool_calls = self.tool_executor.parse_tool_calls(response_text)

            if not tool_calls:
                # Final response (no tools)
                final_response_text = response_text

                # Publish decision event
                if self.event_publisher:
                    await self.event_publisher.publish_event(
                        conversation_id=conversation_id,
                        event_type="decision",
                        agent_role=role.value,
                        content="Finalizing response - analysis complete",
                        user_id=user_id,
                    )
                break

            # Execute tools with fallback
            logger.info(
                "tool_calls_detected",
                count=len(tool_calls),
                iteration=iteration,
                conversation_id=conversation_id,
            )

            # Publish tool call events
            if self.event_publisher:
                for tool_call in tool_calls:
                    await self.event_publisher.publish_event(
                        conversation_id=conversation_id,
                        event_type="tool_call",
                        agent_role=role.value,
                        content=f"Calling tool: {tool_call.get('name', 'unknown')}",
                        user_id=user_id,
                    )

            # Add agent reasoning to prompt
            current_prompt += f"\nAssistant: {response_text}"

            # Execute tools
            tool_outputs = await self._execute_tools_with_fallback(
                tool_calls,
                policy=policy,
                user_id=user_id,
                project_id=project_id,
            )

            # Add tool results to prompt
            for output in tool_outputs:
                current_prompt += f"\nSystem: Tool Output ({output['name']}):\n{output['result']}"
                try:
                    match = _PENDING_ACTION_ID_RE.search(str(output.get("result") or ""))
                    if match:
                        pending_action_id = int(match.group(1))
                        pending_tool_name = str(output.get("name") or "") or None
                except Exception:
                    pass

                # Publish tool completion
                if self.event_publisher:
                    result_preview = str(output["result"])[:200]
                    if len(str(output["result"])) > 200:
                        result_preview += "..."

                    await self.event_publisher.publish_event(
                        conversation_id=conversation_id,
                        event_type="tool_end",
                        agent_role=role.value,
                        content=f"Tool {output['name']} completed: {result_preview}",
                        user_id=user_id,
                    )

        # Handle max iterations reached
        if not final_response_text and iteration >= max_iterations:
            logger.warning(
                "agent_loop_max_iterations",
                max_iterations=max_iterations,
                conversation_id=conversation_id,
                message_preview=message[:100],
            )

            final_response_text = (
                f"Desculpe, essa tarefa mostrou-se mais complexa do que esperado. "
                f"Tentei {iteration} passos mas ainda não consegui uma resposta completa.\n\n"
                f"**Sugestões:**\n"
                f"- Simplifique a pergunta\n"
                f"- Quebre em partes menores\n"
                f"- Seja mais específico sobre o que precisa\n\n"
                f"*Estou sempre aprendendo a ser mais eficiente!* 🤖"
            )

        result_payload = {
            "response": final_response_text,
            "provider": last_result.get("provider", "janus"),
            "model": last_result.get("model", "agent"),
            "role": role.value,
            "conversation_id": conversation_id,
            "total_in_tokens": total_in_tokens,
            "total_out_tokens": total_out_tokens,
        }
        if pending_action_id is not None:
            result_payload["pending_action_id"] = pending_action_id
            if pending_tool_name:
                result_payload["pending_tool_name"] = pending_tool_name
        return result_payload

    async def _invoke_llm_with_fallback(
        self,
        prompt: str,
        role: ModelRole,
        priority: ModelPriority,
        timeout_seconds: int | None,
        conversation_id: str,
        user_id: str | None,
        project_id: str | None,
    ) -> dict[str, Any]:
        """Invoke LLM with fallback strategies."""

        async def primary():
            return await self.llm_service.invoke_llm(
                prompt=prompt,
                role=role,
                priority=priority,
                timeout_seconds=timeout_seconds,
                objective_id=conversation_id,
                user_id=user_id,
                project_id=project_id,
            )

        async def fallback_fast_model():
            # Try faster/cheaper model if primary fails
            return await self.llm_service.invoke_llm(
                prompt=prompt,
                role=role,
                priority=ModelPriority.FAST_AND_CHEAP,
                timeout_seconds=timeout_seconds,
                objective_id=conversation_id,
                user_id=user_id,
                project_id=project_id,
            )

        chain = FallbackChain(
            strategies=[primary, fallback_fast_model],
            component_name="llm_invocation",
        )

        return await chain.execute()

    async def _execute_tools_with_fallback(
        self,
        tool_calls: list[dict],
        policy: PolicyEngine | None,
        user_id: str | None,
        project_id: str | None,
    ) -> list[dict]:
        """Execute tools with fallback strategies."""

        async def primary():
            return await self.tool_executor.execute_tool_calls(
                tool_calls,
                policy=policy,
                user_id=user_id,
                project_id=project_id,
            )

        async def fallback_permissive():
            # Try with relaxed parameters if primary fails
            logger.info("tool_execution_fallback_permissive")
            return await self.tool_executor.execute_tool_calls(
                tool_calls,
                strict=False,
                policy=policy,
                user_id=user_id,
                project_id=project_id,
            )

        async def minimal_fallback():
            # Return error messages for all tools
            return [
                {
                    "name": tc.get("name", "unknown"),
                    "result": f"Tool execution failed for {tc.get('name')}. Please try a simpler approach.",
                }
                for tc in tool_calls
            ]

        chain = FallbackChain(
            strategies=[primary, fallback_permissive, minimal_fallback],
            component_name="tool_execution",
        )

        return await chain.execute()
