import pytest

from app.core.workers.knowledge_consolidator_worker import KnowledgeConsolidator


def test_chunk_text_handles_non_string_and_short_text():
    kc = KnowledgeConsolidator()
    assert kc._chunk_text(None) == []
    assert kc._chunk_text(123) == []
    assert kc._chunk_text("abc") == ["abc"]


def test_chunk_text_splits_with_overlap():
    kc = KnowledgeConsolidator()
    base = "0123456789" * 300  # 3000 chars
    chunks = kc._chunk_text(base, chunk_size=1000, overlap=200)
    assert len(chunks) >= 3
    # First chunk size
    assert len(chunks[0]) == 1000
    # Overlap: last 200 of chunk[0] must equal first 200 of chunk[1]
    assert chunks[0][-200:] == chunks[1][:200]
    # Last chunk may be shorter or equal to chunk_size
    assert len(chunks[-1]) <= 1000


def test_chunk_text_exact_boundary_and_end_condition():
    kc = KnowledgeConsolidator()
    text = "A" * 2000
    chunks = kc._chunk_text(text, chunk_size=2000, overlap=200)
    assert chunks == [text]

    text2 = "B" * 2100
    chunks2 = kc._chunk_text(text2, chunk_size=2000, overlap=200)
    # Expect two chunks: 2000 + 300 (with 200 overlap window applied internally)
    assert len(chunks2) == 2
    assert chunks2[0][-200:] == chunks2[1][:200]