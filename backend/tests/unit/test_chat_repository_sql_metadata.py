from app.repositories.chat_repository_sql import ChatRepositorySQL


def test_chat_repository_sql_preserves_knowledge_space_metadata_in_fallback():
    repo = ChatRepositorySQL()
    conversation_id = repo.start_conversation("assistant", None, None)

    saved = repo.add_message(
        conversation_id=conversation_id,
        role="assistant",
        text="Base consolidada indica: ...",
        metadata={
            "knowledge_space_id": "ks-1",
            "mode_used": "canonical_answer",
            "base_used": "consolidated",
            "source_scope": {"knowledge_space_id": "ks-1", "consolidation_status": "ready"},
            "gaps_or_conflicts": ["Múltiplas edições detectadas."],
        },
    )

    assert saved["knowledge_space_id"] == "ks-1"
    assert saved["mode_used"] == "canonical_answer"
    assert saved["base_used"] == "consolidated"
    assert saved["source_scope"]["consolidation_status"] == "ready"
    assert saved["gaps_or_conflicts"] == ["Múltiplas edições detectadas."]

    updated = repo.update_message_payload(
        conversation_id=conversation_id,
        message_id=int(saved["id"]),
        patch={
            "mode_used": "quick_lookup",
            "base_used": "chunk_only",
            "gaps_or_conflicts": ["Knowledge space sem consolidação pronta."],
        },
    )

    assert updated["mode_used"] == "quick_lookup"
    assert updated["base_used"] == "chunk_only"
    assert updated["gaps_or_conflicts"] == ["Knowledge space sem consolidação pronta."]
