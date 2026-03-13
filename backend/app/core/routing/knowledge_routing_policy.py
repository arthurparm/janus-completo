from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class RouteTarget(str, Enum):
    POSTGRES = "postgres"
    QDRANT = "qdrant"
    NEO4J = "neo4j"


class RouteIntent(str, Enum):
    CHAT_CONTEXT_RETRIEVAL = "chat_context_retrieval"
    RAG_SEARCH = "rag_search"
    RAG_USER_CHAT_SEARCH = "rag_user_chat_search"
    RAG_PRODUCTIVITY_SEARCH = "rag_productivity_search"
    RAG_HYBRID_SEARCH = "rag_hybrid_search"
    KNOWLEDGE_GRAPH_QUERY = "knowledge_graph_query"


@dataclass(frozen=True)
class RouteDecision:
    primary: RouteTarget
    secondary: tuple[RouteTarget, ...]
    reason: str
    rule_id: str
    mode: str = "deterministic"

    @property
    def fallback(self) -> list[str]:
        return [target.value for target in self.secondary]


class KnowledgeRoutingPolicy:
    def __init__(
        self,
        *,
        mode: str,
        default_decision: RouteDecision,
        rules: dict[str, RouteDecision],
    ):
        self._mode = str(mode or "deterministic").strip().lower() or "deterministic"
        self._default_decision = default_decision
        self._rules = rules

    def resolve(
        self,
        intent: RouteIntent | str,
        *,
        user_id: str | None = None,
        include_graph: bool = True,
        query: str | None = None,
    ) -> RouteDecision:
        del query
        key = _normalize_intent(intent)
        decision = self._rules.get(key, self._default_decision)

        if (
            self._mode == "deterministic"
            and not user_id
            and _intent_requires_user_scope(key)
            and decision.primary == RouteTarget.QDRANT
            and RouteTarget.POSTGRES in decision.secondary
        ):
            # Deterministic fallback for requests that cannot be user-scoped in vector storage.
            return RouteDecision(
                primary=RouteTarget.POSTGRES,
                secondary=tuple(target for target in decision.secondary if target != RouteTarget.POSTGRES),
                reason="Missing user_id for vector route; fallback to structured storage.",
                rule_id=f"{decision.rule_id}.missing_user_fallback",
                mode=self._mode,
            )

        if not include_graph and RouteTarget.NEO4J in decision.secondary:
            return RouteDecision(
                primary=decision.primary,
                secondary=tuple(target for target in decision.secondary if target != RouteTarget.NEO4J),
                reason=decision.reason,
                rule_id=f"{decision.rule_id}.graph_disabled",
                mode=self._mode,
            )

        return decision


def _normalize_intent(intent: RouteIntent | str) -> str:
    if isinstance(intent, RouteIntent):
        return intent.value
    return str(intent or "").strip().lower()


def _intent_requires_user_scope(intent: str) -> bool:
    return intent in {
        RouteIntent.CHAT_CONTEXT_RETRIEVAL.value,
        RouteIntent.RAG_USER_CHAT_SEARCH.value,
        RouteIntent.RAG_PRODUCTIVITY_SEARCH.value,
    }


def _parse_target(raw: Any, *, fallback: RouteTarget) -> RouteTarget:
    text = str(raw or "").strip().lower()
    if text == RouteTarget.POSTGRES.value:
        return RouteTarget.POSTGRES
    if text == RouteTarget.QDRANT.value:
        return RouteTarget.QDRANT
    if text == RouteTarget.NEO4J.value:
        return RouteTarget.NEO4J
    return fallback


def _parse_secondary(raw: Any) -> tuple[RouteTarget, ...]:
    if not isinstance(raw, list):
        return tuple()
    parsed: list[RouteTarget] = []
    for item in raw:
        target = _parse_target(item, fallback=RouteTarget.POSTGRES)
        if target not in parsed:
            parsed.append(target)
    return tuple(parsed)


def _build_decision(raw: dict[str, Any], *, fallback_rule_id: str) -> RouteDecision:
    primary = _parse_target(raw.get("primary"), fallback=RouteTarget.POSTGRES)
    secondary = _parse_secondary(raw.get("secondary"))
    reason = str(raw.get("reason") or "Deterministic routing decision.")
    rule_id = str(raw.get("rule_id") or fallback_rule_id)
    return RouteDecision(
        primary=primary,
        secondary=secondary,
        reason=reason,
        rule_id=rule_id,
        mode="deterministic",
    )


def _default_policy_path() -> Path:
    return (Path(__file__).resolve().parents[1] / "config" / "routing_policy.yaml").resolve()


def load_knowledge_routing_policy() -> KnowledgeRoutingPolicy:
    requested_mode = str(os.getenv("JANUS_ROUTING_POLICY_MODE", "deterministic")).strip().lower()
    policy_path = Path(
        os.getenv("JANUS_ROUTING_POLICY_PATH", str(_default_policy_path()))
    ).resolve()

    try:
        with policy_path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
    except Exception:
        raw = {}

    defaults_raw = raw.get("defaults") if isinstance(raw, dict) else None
    defaults = (
        defaults_raw
        if isinstance(defaults_raw, dict)
        else {
            "primary": "postgres",
            "secondary": [],
            "reason": "Fallback deterministic route.",
            "rule_id": "default.postgres_only",
        }
    )
    default_decision = _build_decision(defaults, fallback_rule_id="default.postgres_only")

    rules_raw = raw.get("rules") if isinstance(raw, dict) else {}
    rules: dict[str, RouteDecision] = {}
    if isinstance(rules_raw, dict):
        for intent, value in rules_raw.items():
            if not isinstance(value, dict):
                continue
            key = _normalize_intent(str(intent))
            rules[key] = _build_decision(value, fallback_rule_id=f"rule.{key}")

    mode = requested_mode if requested_mode == "deterministic" else "deterministic"
    return KnowledgeRoutingPolicy(mode=mode, default_decision=default_decision, rules=rules)


_CACHED_POLICY: KnowledgeRoutingPolicy | None = None
_CACHE_KEY: tuple[str, str] | None = None


def get_knowledge_routing_policy() -> KnowledgeRoutingPolicy:
    global _CACHED_POLICY, _CACHE_KEY
    key = (
        str(os.getenv("JANUS_ROUTING_POLICY_MODE", "deterministic")).strip().lower(),
        str(os.getenv("JANUS_ROUTING_POLICY_PATH", str(_default_policy_path()))),
    )
    if _CACHED_POLICY is None or _CACHE_KEY != key:
        _CACHED_POLICY = load_knowledge_routing_policy()
        _CACHE_KEY = key
    return _CACHED_POLICY
