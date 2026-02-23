from app.core.memory import rag_telemetry


def test_confidence_from_scores_uses_max_valid_score():
    confidence = rag_telemetry.confidence_from_scores([None, -1, 0.35, 1.5, "0.7"])
    assert confidence == 1.0


def test_build_step_telemetry_has_required_fields_and_clamps_values():
    payload = rag_telemetry.build_step_telemetry(
        step="retrieval",
        source="vector",
        db="qdrant",
        latency_ms=-10,
        confidence=1.8,
        error_code="TimeoutError",
        extra={"result_count": 3},
    )

    assert payload["step"] == "retrieval"
    assert payload["source"] == "vector"
    assert payload["db"] == "qdrant"
    assert payload["latency_ms"] == 0
    assert payload["confidence"] == 1.0
    assert payload["error_code"] == "TimeoutError"
    assert payload["extra"]["result_count"] == 3


def test_emit_step_telemetry_records_audit_payload(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_record(event):
        captured.update(event)

    monkeypatch.setattr(rag_telemetry, "record_audit_event_direct", _fake_record)

    payload = rag_telemetry.emit_step_telemetry(
        endpoint="/api/v1/rag/search",
        step="retrieval",
        source="vector",
        db="qdrant",
        latency_ms=42,
        confidence=0.81,
        error_code=None,
        extra={"result_count": 2},
        user_id="123",
        trace_id="trace-1",
    )

    assert payload["source"] == "vector"
    assert payload["db"] == "qdrant"
    assert payload["latency_ms"] == 42
    assert payload["confidence"] == 0.81
    assert captured["action"] == "rag_step_telemetry"
    assert captured["status"] == "success"
    assert captured["detail"]["source"] == "vector"
