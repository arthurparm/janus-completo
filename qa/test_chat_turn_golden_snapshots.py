from __future__ import annotations

import json
from pathlib import Path

import pytest

from qa.chat_turn_baseline.harness import (
    ADDITIONAL_SCENARIOS,
    ADR_SCENARIOS,
    capture_all,
    load_snapshots,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = REPOSITORY_ROOT / "qa" / "snapshots" / "chat_turn_baseline"
REQUIRED_OUTPUT_FIELDS = {
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
}


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_chat_turn_baseline_snapshots_match_current_behavior() -> None:
    assert len(ADR_SCENARIOS) == 15
    assert [item.name for item in ADDITIONAL_SCENARIOS] == ["conversation_access_denied"]
    assert await capture_all() == load_snapshots(REPOSITORY_ROOT)


def test_chat_turn_baseline_snapshot_and_classification_coverage() -> None:
    snapshots = load_snapshots(REPOSITORY_ROOT)
    scenario_names = {item.name for item in (*ADR_SCENARIOS, *ADDITIONAL_SCENARIOS)}
    assert len(snapshots) == len(scenario_names) * 2
    for relative_path, snapshot in snapshots.items():
        assert set(snapshot["output"]) == REQUIRED_OUTPUT_FIELDS, relative_path
        assert set(snapshot["persistence"]["writes"]) == {
            "add_message",
            "update_message_payload",
        }
        terminal = snapshot["terminal"]
        if snapshot["transport"] == "rest":
            assert terminal["kind"] == "http"
            assert isinstance(terminal["status_code"], int)
        else:
            assert terminal["kind"] == "sse"
            assert terminal["event"] in {"done", "error"}

    classification = json.loads(
        (SNAPSHOT_ROOT / "CLASSIFICATION.json").read_text(encoding="utf-8")
    )
    assert set(classification["scenarios"]) == scenario_names
    for scenario_name, transports in classification["scenarios"].items():
        assert set(transports) == {"rest", "sse"}, scenario_name
        for transport, decision in transports.items():
            assert decision["disposition"] in {"preserve", "correct"}, (
                scenario_name,
                transport,
            )
            assert decision["preserve_paths"], (scenario_name, transport)
            assert isinstance(decision["correct_paths"], list)
