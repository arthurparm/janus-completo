import asyncio
import inspect
import json
import os
import re
import time
from datetime import datetime
from typing import Any

import structlog
from pydantic import ValidationError

from app.config import settings
from app.core.autonomy.policy_engine import (
    PolicyConfig,
    PolicyEngine,
    RiskProfile,
    SimulationResult,
)
from app.core.infrastructure.redis_usage_tracker import get_redis_usage_tracker
from app.core.security.redaction import redact_sensitive_payload
from app.core.tools import action_registry
from app.repositories.observability_repository import record_audit_event_direct
from app.repositories.tool_usage_repository import ToolUsageRepository

logger = structlog.get_logger(__name__)


class ToolExecutorError(Exception):
    """Erro base para execuÃ§Ã£o de ferramentas."""

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
            name.strip()
            for name in os.getenv("CHAT_TOOL_ALLOWLIST", "").split(",")
            if name.strip()
        }
        blocklist = {
            name.strip()
            for name in os.getenv("CHAT_TOOL_BLOCKLIST", "").split(",")
            if name.strip()
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

    def _extract_json_envelope_payload(self, text: str) -> str | None:
        if not isinstance(text, str):
            return None
        stripped = text.strip()
        if not stripped:
            return None

        # Fast path: payload is already a single fenced JSON block or raw JSON object.
        fenced = re.fullmatch(r"```(?:json)?\s*(\{.*\})\s*```", stripped, re.DOTALL)
        if fenced:
            return fenced.group(1).strip()

        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped

        # Look for JSON fenced blocks anywhere in the text.
        for match in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE):
            candidate = match.group(1).strip()
            if candidate.startswith("{") and candidate.endswith("}"):
                try:
                    decoded = json.loads(candidate)
                except json.JSONDecodeError:
                    continue
                if isinstance(decoded, dict) and decoded.get("type") == "tool_call_envelope":
                    return candidate

        # Fallback: scan for a JSON object embedded in plain text.
        decoder = json.JSONDecoder()
        for idx, char in enumerate(text):
            if char != "{":
                continue
            try:
                decoded, consumed = decoder.raw_decode(text[idx:])
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, dict) and decoded.get("type") == "tool_call_envelope":
                return text[idx : idx + consumed]
        return None

    def parse_tool_calls(self, text: str) -> list[dict[str, Any]]:
        """
        Extract tool calls using strict JSON envelope.

        Accepted envelope:
        {
          "type": "tool_call_envelope",
          "version": "1.0",
          "calls": [{"name": "...", "args": {...}}]
        }
        """
        payload = self._extract_json_envelope_payload(text)
        if payload is None:
            return []

        try:
            envelope = json.loads(payload)
        except json.JSONDecodeError as e:
            logger.warning("tool_call_envelope_json_invalid", error=str(e))
            return []

        if not isinstance(envelope, dict):
            return []
        if envelope.get("type") != "tool_call_envelope":
            return []

        version = envelope.get("version")
        if not isinstance(version, str) or not version.strip():
            logger.warning("tool_call_envelope_missing_version")
            return []

        calls_raw = envelope.get("calls")
        if not isinstance(calls_raw, list):
            logger.warning("tool_call_envelope_calls_not_list")
            return []

        normalized: list[dict[str, Any]] = []
        for idx, call in enumerate(calls_raw):
            if not isinstance(call, dict):
                logger.warning(
                    "tool_call_envelope_item_invalid", index=idx, reason="item_not_object"
                )
                return []

            name = call.get("name")
            args = call.get("args")
            if not isinstance(name, str) or not name.strip():
                logger.warning("tool_call_envelope_item_invalid", index=idx, reason="invalid_name")
                return []
            if not isinstance(args, dict):
                logger.warning("tool_call_envelope_item_invalid", index=idx, reason="invalid_args")
                return []

            normalized.append({"name": name.strip(), "args": args})

        return normalized

    def _validate_tool_args(
        self, *, tool: Any, args: Any
    ) -> tuple[bool, dict[str, Any] | Any, str | None]:
        """
        Validate tool arguments using its Pydantic args_schema when available.

        Returns:
            (is_valid, normalized_args, error_message)
        """
        schema = getattr(tool, "args_schema", None)
        if schema is None:
            return True, args, None

        if not isinstance(args, dict):
            return (
                False,
                args,
                "Invalid arguments: args must be a JSON object for this tool schema.",
            )

        try:
            parsed = schema.model_validate(args)
            normalized = parsed.model_dump(mode="python", exclude_none=True)
            return True, normalized, None
        except ValidationError as e:
            try:
                details = e.errors()
            except Exception:
                details = str(e)
            return False, args, f"Invalid arguments for tool schema: {details}"
        except Exception as e:
            return False, args, f"Invalid arguments for tool schema: {e}"

    def _audit_pre_execution_event(
        self,
        *,
        tool_name: str,
        status: str,
        reason: str,
        user_id: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        try:
            safe_detail = (
                redact_sensitive_payload(detail or {})
                if isinstance(detail, dict)
                else {"detail": redact_sensitive_payload(detail)}
            )
            payload = {
                "user_id": user_id or "-",
                "endpoint": "tool_executor",
                "action": "tool_precheck",
                "tool": tool_name,
                "status": status,
                "detail": {"reason": redact_sensitive_payload(reason), **safe_detail},
            }
            record_audit_event_direct(payload)
        except Exception as e:
            logger.warning(
                "tool_precheck_audit_failed",
                tool_name=tool_name,
                status=status,
                reason=reason,
                error=str(e),
            )

    def _simulation_to_storage(self, simulation: SimulationResult | None) -> tuple[str | None, str | None]:
        if simulation is None:
            return None, None
        payload = {
            "is_destructive": bool(simulation.is_destructive),
            "expected_impact": simulation.expected_impact,
            "affected_resources": list(simulation.affected_resources or []),
            "reversible": bool(simulation.reversible),
            "final_risk_level": simulation.final_risk_level,
            "summary": simulation.summary,
            "generated_at": simulation.generated_at,
        }
        return json.dumps(payload, ensure_ascii=False), str(simulation.simulation_version or "v1")

    def _build_scope_metadata(self, args: dict[str, Any] | Any) -> tuple[str | None, list[str]]:
        if not isinstance(args, dict) or not args:
            return None, []

        interesting_keys = (
            "conversation_id",
            "project_id",
            "session_id",
            "thread_id",
            "path",
            "file_path",
            "url",
            "host",
            "container",
            "service_name",
            "collection",
            "collection_name",
            "doc_id",
            "resource_id",
            "target",
            "targets",
        )
        targets: list[str] = []
        for key in interesting_keys:
            value = args.get(key)
            if isinstance(value, (str, int, float)) and str(value).strip():
                targets.append(f"{key}={value}")
            elif isinstance(value, list):
                for item in value[:3]:
                    if isinstance(item, (str, int, float)) and str(item).strip():
                        targets.append(f"{key}={item}")
        unique_targets = list(dict.fromkeys(targets))
        if not unique_targets:
            return None, []
        summary = ", ".join(unique_targets[:3])
        if len(unique_targets) > 3:
            summary += f" (+{len(unique_targets) - 3} alvo(s))"
        return summary, unique_targets[:10]

    def _create_pending_action(
        self,
        *,
        user_id: str | None,
        tool_name: str,
        safe_args: dict[str, Any] | Any,
        simulation: SimulationResult | None = None,
    ) -> int | None:
        if not user_id:
            return None
        try:
            from app.repositories.pending_action_repository import PendingActionRepository

            simulation_summary_json, simulation_version = self._simulation_to_storage(simulation)
            repo = PendingActionRepository()
            pending = repo.create(
                user_id=str(user_id),
                tool_name=tool_name,
                args_json=json.dumps(safe_args, ensure_ascii=False),
                run_id=None,
                cycle=None,
                simulation_summary_json=simulation_summary_json,
                simulation_generated_at=(
                    datetime.fromisoformat(str(simulation.generated_at))
                    if simulation and simulation.generated_at
                    else None
                ),
                simulation_version=simulation_version,
            )
            return getattr(pending, "id", None)
        except Exception:
            return None

    async def execute_tool_calls(
        self,
        calls: list[dict[str, Any]],
        strict: bool = True,
        policy: PolicyEngine | None = None,
        user_id: str | None = None,
        project_id: str | None = None,
        timeout_seconds: float | None = None,
    ) -> list[dict[str, str]]:
        effective_policy = policy or self._build_default_policy()
        if policy is None:
            effective_policy.reset_cycle_quota()
        effective_timeout = self._timeout_seconds if timeout_seconds is None else timeout_seconds

        outputs = []
        daily_limits = getattr(settings, "TOOL_DAILY_QUOTAS", {}) or {}
        sliding_limits = getattr(settings, "TOOL_SLIDING_WINDOW_QUOTAS", {}) or {}
        for call in calls:
            name = call["name"]
            args = call["args"]
            safe_args: Any = {}

            if not effective_policy.can_continue_cycle():
                self._audit_pre_execution_event(
                    tool_name=name,
                    status="blocked",
                    reason="policy_cycle_limit",
                    user_id=user_id,
                )
                outputs.append({"name": name, "result": "Policy limit reached for this cycle."})
                continue

            args_text = ""
            try:
                args_text = json.dumps(args, ensure_ascii=False, default=str)
            except Exception:
                args_text = str(args)

            content_safety = effective_policy.validate_content_safety(args_text)
            if not content_safety.allowed:
                self._audit_pre_execution_event(
                    tool_name=name,
                    status="blocked",
                    reason="content_safety",
                    user_id=user_id,
                    detail={"policy_reason": content_safety.reason},
                )
                outputs.append(
                    {
                        "name": name,
                        "result": f"Tool blocked by content safety: {content_safety.reason or 'unsafe content'}",
                    }
                )
                continue

            tool = action_registry.get_tool(name)
            if not tool:
                self._audit_pre_execution_event(
                    tool_name=name,
                    status="not_found",
                    reason="tool_not_registered",
                    user_id=user_id,
                )
                if strict:
                    outputs.append({"name": name, "result": f"Error: Tool '{name}' not found."})
                else:
                    outputs.append(
                        {"name": name, "result": f"Skipped: Tool '{name}' not available."}
                    )
                continue

            args_valid, normalized_args, args_error = self._validate_tool_args(tool=tool, args=args)
            if not args_valid:
                self._audit_pre_execution_event(
                    tool_name=name,
                    status="blocked",
                    reason="invalid_args_schema",
                    user_id=user_id,
                    detail={"error": args_error},
                )
                outputs.append(
                    {
                        "name": name,
                        "result": args_error
                        or "Invalid arguments for tool schema validation.",
                    }
                )
                continue
            args = normalized_args
            safe_args = redact_sensitive_payload(args)
            scope_summary, scope_targets = self._build_scope_metadata(safe_args)
            if isinstance(safe_args, dict):
                if scope_summary:
                    safe_args.setdefault("scope_summary", scope_summary)
                if scope_targets:
                    safe_args.setdefault("scope_targets", scope_targets)
            simulation: SimulationResult | None = None
            simulate_tool = getattr(effective_policy, "simulate_tool_call", None)
            if callable(simulate_tool):
                try:
                    simulation = simulate_tool(name, args)
                except Exception as sim_error:
                    logger.warning(
                        "tool_simulation_failed",
                        tool_name=name,
                        error=str(sim_error),
                    )

            decision = effective_policy.validate_tool_call(name, args, user_id=user_id)
            if simulation and simulation.is_destructive:
                pending_id = self._create_pending_action(
                    user_id=user_id,
                    tool_name=name,
                    safe_args=safe_args,
                    simulation=simulation,
                )
                msg = (
                    "Tool flagged as destructive. Dry-run simulation completed; "
                    "manual confirmation is required before execution."
                )
                if pending_id:
                    msg += f" Pending action id: {pending_id}."
                self._audit_pre_execution_event(
                    tool_name=name,
                    status="pending_confirmation",
                    reason="destructive_simulation_requires_confirmation",
                    user_id=user_id,
                    detail={
                        "pending_id": pending_id,
                        "simulation_risk_level": simulation.final_risk_level,
                        "simulation_summary": simulation.summary,
                    },
                )
                outputs.append({"name": name, "result": msg})
                continue
            if decision.require_confirmation:
                pending_id = self._create_pending_action(
                    user_id=user_id,
                    tool_name=name,
                    safe_args=safe_args,
                    simulation=simulation,
                )
                msg = "Tool requires confirmation before execution."
                if pending_id:
                    msg += f" Pending action id: {pending_id}."
                self._audit_pre_execution_event(
                    tool_name=name,
                    status="pending_confirmation",
                    reason=decision.reason or "requires_confirmation",
                    user_id=user_id,
                    detail={"pending_id": pending_id},
                )
                outputs.append({"name": name, "result": msg})
                continue

            if not decision.allowed:
                self._audit_pre_execution_event(
                    tool_name=name,
                    status="blocked",
                    reason=decision.reason or "policy_block",
                    user_id=user_id,
                )
                outputs.append(
                    {
                        "name": name,
                        "result": f"Tool blocked by policy: {decision.reason or 'not allowed'}",
                    }
                )
                continue

            # Quota diÃ¡ria por usuÃ¡rio (aplica apenas apÃ³s aprovaÃ§Ã£o e antes de executar)
            if user_id and name in daily_limits:
                limit = int(daily_limits.get(name, 0) or 0)
                if limit > 0:
                    try:
                        repo = ToolUsageRepository()
                        allowed, count, max_limit = repo.increment_if_within_limit(
                            user_id=str(user_id), tool_name=name, daily_limit=limit
                        )
                        if not allowed:
                            self._audit_pre_execution_event(
                                tool_name=name,
                                status="quota_exceeded",
                                reason="daily_quota",
                                user_id=user_id,
                                detail={"count": count, "limit": max_limit},
                            )
                            outputs.append(
                                {
                                    "name": name,
                                    "result": f"Cota diÃ¡ria atingida para '{name}'. "
                                    f"Uso: {count}/{max_limit}.",
                                }
                            )
                            continue
                    except Exception as e:
                        logger.warning(
                            "tool_usage_quota_check_failed",
                            tool_name=name,
                            user_id=str(user_id),
                            error=str(e),
                        )

            sliding_rule = sliding_limits.get(name)
            if isinstance(sliding_rule, dict):
                tracker = get_redis_usage_tracker()
                window_seconds = int(sliding_rule.get("window_seconds", 0) or 0)
                if tracker is not None and window_seconds > 0:
                    quota_specs = (
                        ("user", user_id, int(sliding_rule.get("user_limit", 0) or 0)),
                        ("project", project_id, int(sliding_rule.get("project_limit", 0) or 0)),
                    )
                    quota_blocked = False
                    for quota_kind, quota_id, quota_limit in quota_specs:
                        if not quota_id or quota_limit <= 0:
                            continue
                        allowed, count, max_limit, window = await tracker.sliding_window_check_and_increment(
                            kind=quota_kind,
                            tool_name=name,
                            id_=str(quota_id),
                            limit=quota_limit,
                            window_seconds=window_seconds,
                        )
                        if allowed:
                            continue
                        self._audit_pre_execution_event(
                            tool_name=name,
                            status="quota_exceeded",
                            reason="sliding_window_quota",
                            user_id=user_id,
                            detail={
                                "quota_kind": quota_kind,
                                "count": count,
                                "limit": max_limit,
                                "window_seconds": window,
                            },
                        )
                        outputs.append(
                            {
                                "name": name,
                                "result": (
                                    f"Cota temporária atingida para '{name}' em escopo {quota_kind}. "
                                    f"Uso: {count}/{max_limit} em {window}s."
                                ),
                            }
                        )
                        quota_blocked = True
                        break
                    if quota_blocked:
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
                error_msg = str(redact_sensitive_payload(str(e)))
                logger.error(
                    "tool_execution_failed",
                    tool_name=name,
                    error_type=type(e).__name__,
                    error=error_msg,
                    exc_info=True,
                )
                # Retorna erro formatado para o LLM tentar corrigir
                if strict:
                    outputs.append(
                        {
                            "name": name,
                            "result": f"System: Tool Error (STOP and rethink): {error_msg}",
                        }
                    )
                else:
                    outputs.append({"name": name, "result": f"Tool Error (non-fatal): {error_msg}"})
            finally:
                duration = time.perf_counter() - start
                try:
                    action_registry.record_call(
                        tool_name=name,
                        duration=duration,
                        success=success,
                        error=error_msg,
                        input_args=safe_args if isinstance(safe_args, dict) else {},
                        user_id=user_id,
                    )
                except Exception:
                    pass

        return outputs
