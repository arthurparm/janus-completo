from __future__ import annotations

import json
from pathlib import Path

import pytest

from qa.chat_turn_baseline.comparator import (
    build_comparison_report,
    compare_snapshot_to_baseline,
    compare_transport_pair,
    load_classification,
)
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
async def test_chat_turn_current_capture_keeps_golden_scenario_inventory() -> None:
    assert len(ADR_SCENARIOS) == 15
    assert [item.name for item in ADDITIONAL_SCENARIOS] == ["conversation_access_denied"]
    assert set(await capture_all()) == set(load_snapshots(REPOSITORY_ROOT))


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


def test_snapshot_comparator_distinguishes_corrections_from_regressions() -> None:
    baseline = load_snapshots(REPOSITORY_ROOT)
    classification = load_classification(REPOSITORY_ROOT)
    relative_path = "light_chat/rest.json"
    decision = classification["scenarios"]["light_chat"]["rest"]

    corrected = json.loads(json.dumps(baseline[relative_path]))
    corrected["execution"]["llm_requests"][0]["user_id"] = "user-1"
    correction_differences = compare_snapshot_to_baseline(
        current=corrected,
        baseline=baseline[relative_path],
        decision=decision,
    )
    assert {item["classification"] for item in correction_differences} == {
        "intentional_correction"
    }

    regressed = json.loads(json.dumps(baseline[relative_path]))
    regressed["output"]["response"] = "unintended response change"
    regression_differences = compare_snapshot_to_baseline(
        current=regressed,
        baseline=baseline[relative_path],
        decision=decision,
    )
    assert {item["classification"] for item in regression_differences} == {"regression"}


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_normalized_comparator_accepts_only_classified_corrections() -> None:
    baseline = load_snapshots(REPOSITORY_ROOT)
    report = build_comparison_report(
        current=await capture_all(),
        baseline=baseline,
        classification=load_classification(REPOSITORY_ROOT),
    )
    assert report["summary"]["regressions"] == 0
    assert report["summary"]["intentional_corrections"] > 0
    assert report["snapshot_differences"]

    assert {
        scenario
        for scenario, differences in report["normalized_parity"].items()
        if differences
    } == {"sse_disconnect_resume"}

    operational_fields = {
        item["field"]
        for item in compare_transport_pair(
            baseline["operational_non_light/rest.json"],
            baseline["operational_non_light/sse.json"],
        )
    }
    assert {"strategy", "response", "provider", "model"} <= operational_fields
