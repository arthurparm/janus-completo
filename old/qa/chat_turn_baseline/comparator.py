from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

from qa.chat_turn_baseline.harness import SCENARIOS, capture_all, load_snapshots, snapshot_root

NORMALIZED_FIELDS = (
    "strategy",
    "business_state",
    "response",
    "citations",
    "citation_status",
    "understanding",
    "confirmation",
    "agent_state",
    "delivery_status",
    "provider",
    "model",
    "failure_classification",
    "add_message_writes",
    "update_message_payload_writes",
)


def load_classification(repository_root: Path) -> dict[str, Any]:
    path = snapshot_root(repository_root) / "CLASSIFICATION.json"
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _flatten(value: Any, *, path: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    if isinstance(value, dict):
        if not value and path:
            flattened[path] = {}
        for key in sorted(value):
            child = f"{path}.{key}" if path else str(key)
            flattened.update(_flatten(value[key], path=child))
        return flattened
    if isinstance(value, list):
        if not value and path:
            flattened[path] = []
        for index, item in enumerate(value):
            flattened.update(_flatten(item, path=f"{path}[{index}]"))
        return flattened
    flattened[path] = value
    return flattened


def _rule_base(rule: str) -> str:
    return re.sub(r"\[[^0-9][^\]]*\]", "", rule)


def _path_matches(rule: str, path: str) -> bool:
    base = _rule_base(rule)
    return path == base or path.startswith(f"{base}.") or path.startswith(f"{base}[")


def _difference_classification(path: str, decision: dict[str, Any]) -> str:
    preserve = [str(item) for item in decision.get("preserve_paths") or []]
    correct = [str(item) for item in decision.get("correct_paths") or []]
    if any(_path_matches(rule, path) for rule in correct):
        return "intentional_correction"
    if any(_path_matches(rule, path) for rule in preserve):
        return "regression"
    return "regression"


def compare_snapshot_to_baseline(
    *,
    current: dict[str, Any],
    baseline: dict[str, Any],
    decision: dict[str, Any],
) -> list[dict[str, Any]]:
    current_flat = _flatten(_canonicalize_domain(current))
    baseline_flat = _flatten(_canonicalize_domain(baseline))
    differences: list[dict[str, Any]] = []
    for path in sorted(set(current_flat) | set(baseline_flat)):
        baseline_value = baseline_flat.get(path, {"__missing__": True})
        current_value = current_flat.get(path, {"__missing__": True})
        if current_value == baseline_value:
            continue
        differences.append(
            {
                "path": path,
                "classification": _difference_classification(path, decision),
                "baseline": deepcopy(baseline_value),
                "current": deepcopy(current_value),
            }
        )
    return differences


def _strategy(snapshot: dict[str, Any]) -> str:
    terminal = snapshot.get("terminal") or {}
    if terminal.get("event") == "error" or int(terminal.get("status_code") or 0) >= 400:
        return "failure"
    execution = snapshot.get("execution") or {}
    if int(execution.get("study_job_create_count") or 0) > 0:
        return "study_job"
    if int(execution.get("blocking_study_count") or 0) > 0:
        return "blocking_study"
    if int(execution.get("agent_loop_count") or 0) > 0:
        return "agent_loop"
    output = snapshot.get("output") or {}
    model = str(output.get("model") or "")
    known_models = {
        "discovery": "static_discovery",
        "tools_docs": "static_docs",
        "capabilities": "static_capabilities",
        "tool_creation": "blocked_tool_creation",
        "secret_memory": "secret_recall",
        "document_grounding": "document_grounding",
        "document_processing": "knowledge_space_pending",
        "knowledge_space_pending": "knowledge_space_pending",
    }
    if model in known_models:
        return known_models[model]
    if int(execution.get("llm_invoke_count") or 0) > 0:
        return "llm"
    return "static_or_short_circuit"


def _business_state(snapshot: dict[str, Any]) -> str:
    terminal = snapshot.get("terminal") or {}
    if terminal.get("event") == "error" or int(terminal.get("status_code") or 0) >= 400:
        return "failed"
    output = snapshot.get("output") or {}
    persisted = ((snapshot.get("persistence") or {}).get("last_assistant") or {})
    delivery = output.get("delivery_status") or persisted.get("delivery_status")
    if delivery:
        return str(delivery)
    agent_state = output.get("agent_state") or persisted.get("agent_state") or {}
    if isinstance(agent_state, dict) and agent_state.get("state"):
        return str(agent_state["state"])
    return "completed"


def _domain_value(snapshot: dict[str, Any], field: str) -> Any:
    output = snapshot.get("output") or {}
    persisted = ((snapshot.get("persistence") or {}).get("last_assistant") or {})
    value = output.get(field)
    if value is None:
        if field == "response":
            return persisted.get("text")
        return persisted.get(field)
    return value


def _canonicalize_domain(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _canonicalize_domain(item)
            for key, item in sorted(value.items())
            if item is not None
        }
    if isinstance(value, list):
        return [_canonicalize_domain(item) for item in value]
    return value


def normalize_domain(snapshot: dict[str, Any]) -> dict[str, Any]:
    writes = (snapshot.get("persistence") or {}).get("writes") or {}
    normalized = {
        "strategy": _strategy(snapshot),
        "business_state": _business_state(snapshot),
        "response": _canonicalize_domain(_domain_value(snapshot, "response")),
        "citations": _canonicalize_domain(_domain_value(snapshot, "citations")),
        "citation_status": _canonicalize_domain(_domain_value(snapshot, "citation_status")),
        "understanding": _canonicalize_domain(_domain_value(snapshot, "understanding")),
        "confirmation": _canonicalize_domain(_domain_value(snapshot, "confirmation")),
        "agent_state": _canonicalize_domain(_domain_value(snapshot, "agent_state")),
        "delivery_status": _domain_value(snapshot, "delivery_status"),
        "provider": _domain_value(snapshot, "provider"),
        "model": _domain_value(snapshot, "model"),
        "failure_classification": _domain_value(snapshot, "failure_classification"),
        "add_message_writes": int(writes.get("add_message") or 0),
        "update_message_payload_writes": int(writes.get("update_message_payload") or 0),
    }
    assert tuple(normalized) == NORMALIZED_FIELDS
    return normalized


def compare_transport_pair(
    rest_snapshot: dict[str, Any],
    sse_snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    rest = normalize_domain(rest_snapshot)
    sse = normalize_domain(sse_snapshot)
    return [
        {"field": field, "rest": deepcopy(rest[field]), "sse": deepcopy(sse[field])}
        for field in NORMALIZED_FIELDS
        if rest[field] != sse[field]
    ]


def build_comparison_report(
    *,
    current: dict[str, dict[str, Any]],
    baseline: dict[str, dict[str, Any]],
    classification: dict[str, Any],
) -> dict[str, Any]:
    snapshot_differences: dict[str, list[dict[str, Any]]] = {}
    regressions = 0
    intentional_corrections = 0
    for relative_path in sorted(set(current) | set(baseline)):
        current_snapshot = current.get(relative_path, {})
        baseline_snapshot = baseline.get(relative_path, {})
        scenario = str(baseline_snapshot.get("scenario") or current_snapshot.get("scenario") or "")
        transport = str(
            baseline_snapshot.get("transport") or current_snapshot.get("transport") or ""
        )
        decision = (
            ((classification.get("scenarios") or {}).get(scenario) or {}).get(transport) or {}
        )
        decision = {
            **decision,
            "correct_paths": [
                *(classification.get("approved_refactor_paths") or []),
                *((classification.get("approved_scenario_paths") or {}).get(scenario) or []),
                *(decision.get("correct_paths") or []),
            ],
        }
        differences = compare_snapshot_to_baseline(
            current=current_snapshot,
            baseline=baseline_snapshot,
            decision=decision,
        )
        if differences:
            snapshot_differences[relative_path] = differences
        regressions += sum(item["classification"] == "regression" for item in differences)
        intentional_corrections += sum(
            item["classification"] == "intentional_correction" for item in differences
        )

    parity: dict[str, list[dict[str, Any]]] = {}
    for scenario in SCENARIOS:
        rest_path = f"{scenario.name}/rest.json"
        sse_path = f"{scenario.name}/sse.json"
        parity[scenario.name] = compare_transport_pair(current[rest_path], current[sse_path])

    return {
        "summary": {
            "snapshots": len(current),
            "regressions": regressions,
            "intentional_corrections": intentional_corrections,
            "scenarios_with_parity_gaps": sum(bool(items) for items in parity.values()),
        },
        "snapshot_differences": snapshot_differences,
        "normalized_parity": parity,
    }


async def compare_current_to_golden(repository_root: Path) -> dict[str, Any]:
    return build_comparison_report(
        current=await capture_all(),
        baseline=load_snapshots(repository_root),
        classification=load_classification(repository_root),
    )
