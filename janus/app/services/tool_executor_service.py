import asyncio
import inspect
import json
import os
import re
import time
from typing import Any

import structlog

from app.core.autonomy.policy_engine import PolicyConfig, PolicyEngine, RiskProfile
from app.core.tools import action_registry

logger = structlog.get_logger(__name__)


class ToolExecutorError(Exception):
    """Erro base para execução de ferramentas."""

    pass


class ToolExecutorService:
    """
    Service responsible for parsing tool calls from LLM output and executing them.
    """

    def __init__(self, max_concurrency: int | None = None, timeout_seconds: float | None = None):
        self._max_concurrency = self._parse_max_concurrency(max_concurrency)
        self._timeout_seconds = self._parse_timeout_seconds(timeout_seconds)
        self._semaphore = (
            asyncio.Semaphore(self._max_concurrency) if self._max_concurrency > 0 else None
        )

    def _parse_max_concurrency(self, max_concurrency: int | None) -> int:
        if max_concurrency is not None:
            return int(max_concurrency)
        raw = os.getenv("TOOL_EXECUTOR_MAX_CONCURRENCY", "").strip()
        if raw:
            try:
                return int(raw)
            except ValueError:
                return 4
        return 4

    def _parse_timeout_seconds(self, timeout_seconds: float | None) -> float | None:
        if timeout_seconds is not None:
            return float(timeout_seconds)
        raw = os.getenv("TOOL_EXECUTOR_TIMEOUT_SECONDS", "").strip()
        if not raw:
            return 30.0
        try:
            return float(raw)
        except ValueError:
            return 30.0

    def _build_default_policy(self) -> PolicyEngine:
        risk_profile = os.getenv("CHAT_TOOL_RISK_PROFILE", RiskProfile.BALANCED)
        auto_confirm = os.getenv("CHAT_TOOL_AUTO_CONFIRM", "false").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        allowlist = {
            name.strip() for name in os.getenv("CHAT_TOOL_ALLOWLIST", "").split(",") if name.strip()
        }
        blocklist = {
            name.strip() for name in os.getenv("CHAT_TOOL_BLOCKLIST", "").split(",") if name.strip()
        }
        max_actions = int(os.getenv("CHAT_TOOL_MAX_ACTIONS", "20"))
        max_seconds = int(os.getenv("CHAT_TOOL_MAX_SECONDS", "60"))

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

    def parse_tool_calls(self, text: str) -> list[dict[str, Any]]:
        """Extrai chamadas de ferramenta XML do texto."""
        calls = []
        # Regex para capturar blocos <tool_use>...</tool_use>
        pattern = re.compile(r"<tool_use>(.*?)</tool_use>", re.DOTALL)
        matches = pattern.findall(text)

        for content in matches:
            try:
                name_match = re.search(r"<name>(.*?)</name>", content, re.DOTALL)
                args_match = re.search(r"<args>(.*?)</args>", content, re.DOTALL)

                if name_match and args_match:
                    name = name_match.group(1).strip()
                    args_str = args_match.group(1).strip()

                    try:
                        args = json.loads(args_str)
                    except json.JSONDecodeError:
                        # Fallback se o modelo alucinar formatação
                        args = {"raw_args": args_str}

                    calls.append({"name": name, "args": args})
            except Exception as e:
                logger.warning("tool_call_parse_failed", error=str(e), block_content=content[:100])

        return calls

    async def execute_tool_calls(
        self,
        calls: list[dict[str, Any]],
        strict: bool = True,
        policy: PolicyEngine | None = None,
        user_id: str | None = None,
        timeout_seconds: float | None = None,
    ) -> list[dict[str, str]]:
        effective_policy = policy or self._build_default_policy()
        if policy is None:
            effective_policy.reset_cycle_quota()
        effective_timeout = self._timeout_seconds if timeout_seconds is None else timeout_seconds

        outputs = []
        for call in calls:
            name = call["name"]
            args = call["args"]

            if not effective_policy.can_continue_cycle():
                outputs.append({"name": name, "result": "Policy limit reached for this cycle."})
                continue

            decision = effective_policy.validate_tool_call(name, args, user_id=user_id)
            if decision.require_confirmation:
                pending_id = None
                if user_id:
                    try:
                        from app.repositories.pending_action_repository import (
                            PendingActionRepository,
                        )

                        repo = PendingActionRepository()
                        pending = repo.create(
                            user_id=str(user_id),
                            tool_name=name,
                            args_json=json.dumps(args, ensure_ascii=False),
                            run_id=None,
                            cycle=None,
                        )
                        pending_id = getattr(pending, "id", None)
                    except Exception:
                        pending_id = None
                msg = "Tool requires confirmation before execution."
                if pending_id:
                    msg += f" Pending action id: {pending_id}."
                outputs.append({"name": name, "result": msg})
                continue

            if not decision.allowed:
                outputs.append(
                    {
                        "name": name,
                        "result": f"Tool blocked by policy: {decision.reason or 'not allowed'}",
                    }
                )
                continue

            tool = action_registry.get_tool(name)
            if not tool:
                if strict:
                    outputs.append({"name": name, "result": f"Error: Tool '{name}' not found."})
                else:
                    outputs.append(
                        {"name": name, "result": f"Skipped: Tool '{name}' not available."}
                    )
                continue

            start = time.perf_counter()
            success = False
            error_msg = None
            try:

                async def _invoke_tool() -> Any:
                    # Suporta async (ainvoke) e sync (invoke/func)
                    if hasattr(tool, "ainvoke"):
                        return await tool.ainvoke(args)
                    if inspect.iscoroutinefunction(tool.func) or (
                        hasattr(tool, "coroutine") and tool.coroutine
                    ):
                        return await tool.func(**args)
                    return await asyncio.to_thread(tool.invoke, args)

                if self._semaphore:
                    async with self._semaphore:
                        if effective_timeout and effective_timeout > 0:
                            result = await asyncio.wait_for(
                                _invoke_tool(), timeout=effective_timeout
                            )
                        else:
                            result = await _invoke_tool()
                else:
                    if effective_timeout and effective_timeout > 0:
                        result = await asyncio.wait_for(_invoke_tool(), timeout=effective_timeout)
                    else:
                        result = await _invoke_tool()

                success = True
                outputs.append({"name": name, "result": str(result)})
            except asyncio.TimeoutError:
                error_msg = "timeout"
                timeout_msg = (
                    f"Tool execution timed out after {effective_timeout:.0f}s."
                    if effective_timeout
                    else "Tool execution timed out."
                )
                outputs.append({"name": name, "result": timeout_msg})
            except Exception as e:
                error_msg = str(e)
                logger.error(
                    "tool_execution_failed",
                    tool_name=name,
                    error_type=type(e).__name__,
                    error=str(e),
                    exc_info=True,
                )
                # Retorna erro formatado para o LLM tentar corrigir
                if strict:
                    outputs.append(
                        {"name": name, "result": f"System: Tool Error (STOP and rethink): {e!s}"}
                    )
                else:
                    outputs.append({"name": name, "result": f"Tool Error (non-fatal): {e!s}"})
            finally:
                duration = time.perf_counter() - start
                try:
                    action_registry.record_call(
                        tool_name=name,
                        duration=duration,
                        success=success,
                        error=error_msg,
                        input_args=args,
                        user_id=user_id,
                    )
                except Exception:
                    pass

        return outputs
