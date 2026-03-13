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
    assert sections[0]["doc_role"] == "base"
    assert sections[1]["section_role"] == "core_rules"


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


def test_is_heading_rejects_table_and_sentence_like_lines():
    service = KnowledgeSpaceService()

    assert service._is_heading("Capítulo 2") is True
    assert service._is_heading("Regras Opcionais") is True
    assert service._is_heading("Tesouro Nenhum.") is False
    assert service._is_heading("Virotes (20) T$ 2 — — — — 1") is False
    assert service._is_heading("Canalizar Energia. Positiva.") is False


def test_build_structured_sections_merges_repeated_heading_blocks():
    service = KnowledgeSpaceService()

    sections = service._build_structured_sections(
        text=(
            "Capítulo 1\n"
            "Primeira parte.\n"
            "Capítulo 1\n"
            "Segunda parte.\n"
            "Capítulo 2\n"
            "Terceira parte.\n"
        ),
        manifest={"doc_id": "doc-1", "file_name": "livro.pdf"},
        knowledge_space={"knowledge_space_id": "ks-1"},
    )

    assert len(sections) == 2
    assert sections[0]["title"] == "Capítulo 1"
    assert "Primeira parte." in sections[0]["body"]
    assert "Segunda parte." in sections[0]["body"]
    assert sections[0]["evidence_span_ids"] == []


def test_infer_doc_role_detects_supplement_by_filename():
    service = KnowledgeSpaceService()

    role = service._infer_doc_role(
        {"file_name": "T20 - Herois de Arton v1.1.pdf"},
        {"name": "Tormenta20"},
    )

    assert role == "supplement"


def test_detect_answer_strategy_prefers_comparative_and_sequence():
    service = KnowledgeSpaceService()

    assert service._detect_answer_strategy("Como o suplemento amplia a regra base?") == "comparative"
    assert service._detect_answer_strategy("Qual a sequência passo a passo para criar o personagem?") == "sequence"
    assert (
        service._detect_answer_strategy(
            "Qual a sequência para criar um personagem usando o livro base e em que etapa o suplemento adiciona opções?"
        )
        == "sequence"
    )


def test_detect_answer_strategy_prefers_locator_for_trecho_questions():
    service = KnowledgeSpaceService()

    assert service._detect_answer_strategy("Em que trecho ou seção o livro fala sobre novas opções de raças?") == "locator"


def test_build_consolidation_metrics_rewards_useful_sections():
    service = KnowledgeSpaceService()

    metrics = service._build_consolidation_metrics(
        sections=[
            {"section_role": "core_rules"},
            {"section_role": "supplement_rules"},
            {"section_role": "optional_rules"},
        ],
        skipped_sections=2,
    )

    assert metrics["sections_total"] == 5
    assert metrics["sections_indexed"] == 3
    assert metrics["canonical_frames_total"] == 3
    assert metrics["consolidation_quality_score"] > 0.5
