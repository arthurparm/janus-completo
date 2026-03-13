import os
import sys

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.knowledge_space_service import KnowledgeSpaceService


def test_build_structured_sections_uses_headings_and_order():
    service = KnowledgeSpaceService()

    sections = service._build_structured_sections(
        text=(
            "CAPITULO 1\n"
            "Introducao ao tema.\n"
            "Mais detalhes.\n"
            "2. Regras Basicas\n"
            "Teste principal.\n"
        ),
        manifest={"doc_id": "doc-1", "file_name": "livro.pdf"},
        knowledge_space={"knowledge_space_id": "ks-1"},
    )

    assert len(sections) == 2
    assert sections[0]["title"] == "CAPITULO 1"
    assert sections[0]["order"] == 1
    assert sections[1]["title"] == "2. Regras Basicas"
    assert sections[1]["order"] == 2


def test_detect_scope_conflicts_reports_multiple_editions():
    service = KnowledgeSpaceService()

    conflicts = service._detect_scope_conflicts(
        space={"parent_collection_id": "col-1"},
        manifests=[
            {"edition_or_version": "1e"},
            {"edition_or_version": "2e"},
        ],
    )

    assert any("Múltiplas edições/versões" in item for item in conflicts)
    assert any("coleção" in item for item in conflicts)
