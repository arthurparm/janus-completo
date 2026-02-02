from app.core.workers.router_worker import _contains_knowledge_payload
from app.models.schemas import TaskState


def make_state(**kwargs) -> TaskState:
    base = dict(
        original_goal="",
        data_payload={},
        history=[],
        status="success",
    )
    base.update(kwargs)
    return TaskState(**base)


def test_contains_knowledge_tool_output_long_text():
    text = "x" * 300
    state = make_state(data_payload={"tool_output": text})
    assert _contains_knowledge_payload(state) is True


def test_contains_knowledge_sandbox_output_sufficient_and_no_error():
    text = "resultado do sandbox" * 5  # >= 64 chars
    state = make_state(data_payload={"sandbox_output": text, "sandbox_error": ""})
    assert _contains_knowledge_payload(state) is True


def test_contains_knowledge_sandbox_has_error_should_not_trigger():
    text = "resultado do sandbox" * 5
    state = make_state(data_payload={"sandbox_output": text, "sandbox_error": "Traceback..."})
    assert _contains_knowledge_payload(state) is False


def test_contains_knowledge_goal_keywords_pt_en():
    state_pt = make_state(original_goal="Pesquisar artigo PDF sobre context learning")
    state_en = make_state(original_goal="Do research and read docs about RAG")
    assert _contains_knowledge_payload(state_pt) is True
    assert _contains_knowledge_payload(state_en) is True


def test_contains_knowledge_negative_cases():
    # Short tool output, short sandbox, no goal match
    state = make_state(
        original_goal="Implementar função",
        data_payload={"tool_output": "ok", "sandbox_output": "ok"},
    )
    assert _contains_knowledge_payload(state) is False
