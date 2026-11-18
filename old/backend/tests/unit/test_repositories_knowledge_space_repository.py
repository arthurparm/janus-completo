from app.repositories.knowledge_space_repository import KnowledgeSpaceRepository


def test_mark_consolidation_accepts_quality_metrics(monkeypatch):
    repo = KnowledgeSpaceRepository()
    captured = {}

    def _fake_update_space(knowledge_space_id, **fields):
        captured["knowledge_space_id"] = knowledge_space_id
        captured["fields"] = fields
        return {"knowledge_space_id": knowledge_space_id, **fields}

    monkeypatch.setattr(repo, "update_space", _fake_update_space)

    result = repo.mark_consolidation(
        "ks-1",
        status="ready",
        summary="ok",
        sections_total=12,
        sections_indexed=9,
        sections_skipped_as_noise=3,
        canonical_frames_total=7,
        consolidation_quality_score=0.77,
    )

    assert result is not None
    assert captured["knowledge_space_id"] == "ks-1"
    assert captured["fields"]["consolidation_status"] == "ready"
    assert captured["fields"]["sections_total"] == 12
    assert captured["fields"]["sections_indexed"] == 9
    assert captured["fields"]["sections_skipped_as_noise"] == 3
    assert captured["fields"]["canonical_frames_total"] == 7
    assert captured["fields"]["consolidation_quality_score"] == "0.77"
