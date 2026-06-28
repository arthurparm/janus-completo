import os
import sys
from types import SimpleNamespace

sys.path.append(os.path.join(os.getcwd(), "backend"))


def test_summarize_action_risk_high():
    from app.api.v1.endpoints.pending_actions import _summarize_action_risk

    level, _ = _summarize_action_risk("rm -rf", "{}")
    assert level == "high"


def test_summarize_action_risk_medium_by_keyword():
    from app.api.v1.endpoints.pending_actions import _summarize_action_risk

    level, _ = _summarize_action_risk("write_system_file", "{}")
    assert level == "medium"


def test_summarize_action_risk_low_prefix():
    from app.api.v1.endpoints.pending_actions import _summarize_action_risk

    level, _ = _summarize_action_risk("read_system_file", None)
    assert level == "low"


def test_summarize_action_risk_medium_args_dict():
    from app.api.v1.endpoints.pending_actions import _summarize_action_risk

    level, _ = _summarize_action_risk(None, '{"k":"v"}')
    assert level == "medium"


def test_sanitize_pending_args_json_variants():
    from app.api.v1.endpoints.pending_actions import _sanitize_pending_args_json

    assert _sanitize_pending_args_json(None) is None
    assert _sanitize_pending_args_json("   ").strip() == ""
    assert isinstance(_sanitize_pending_args_json('{"a":1}'), str)
    assert isinstance(_sanitize_pending_args_json("not-json"), str)


def test_extract_pending_scope_variants():
    from app.api.v1.endpoints.pending_actions import _extract_pending_scope

    assert _extract_pending_scope(None) == (None, None)
    assert _extract_pending_scope("not-json") == (None, None)
    assert _extract_pending_scope("[]") == (None, None)
    scope, targets = _extract_pending_scope('{"scope_summary":"x","scope_targets":["a", " "]}')
    assert scope == "x"
    assert targets == ["a"]


def test_waiting_for_human_approval_variants():
    from app.api.v1.endpoints.pending_actions import _is_waiting_for_human_approval

    assert _is_waiting_for_human_approval("human_approval") is True
    assert _is_waiting_for_human_approval(["human_approval"]) is True
    assert _is_waiting_for_human_approval(True) is True


def test_extract_request_and_trace_headers_variants():
    from app.api.v1.endpoints.pending_actions import (
        _detail_to_text,
        _extract_request_id,
        _extract_traceparent_trace_id,
    )

    http = SimpleNamespace(
        headers={
            "X-Request-ID": "req-123",
            "traceparent": "00-11111111111111111111111111111111-2222222222222222-01",
        }
    )
    assert _extract_request_id(http) == "req-123"
    assert _extract_traceparent_trace_id(http) == "11111111111111111111111111111111"
    assert _detail_to_text({"message": "blocked"}) == "blocked"
    assert _detail_to_text("blocked") == "blocked"

