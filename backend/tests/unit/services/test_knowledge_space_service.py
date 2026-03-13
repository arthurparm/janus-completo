import asyncio
import os
import sys
from types import SimpleNamespace

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


def test_select_canonical_candidates_keeps_supplement_for_sequence_questions():
    service = KnowledgeSpaceService()
    query_profile = service._build_query_profile(
        "Qual a sequência para criar um personagem e em que etapa o suplemento adiciona opções?"
    )
    points = [
        SimpleNamespace(
            id="base-1",
            score=0.8,
            payload={
                "content": "Passo base de criação.",
                "metadata": {
                    "section_id": "base-1",
                    "doc_id": "base-doc",
                    "doc_role": "base",
                    "section_role": "core_rules",
                    "section_order": 1,
                    "section_title": "Capítulo Um",
                    "applies_to": ["workflow"],
                    "concepts": ["personagem"],
                    "usefulness_score": 0.8,
                    "heading_quality_score": 0.7,
                    "content_density_score": 0.7,
                    "noise_score": 0.1,
                },
            },
        ),
        SimpleNamespace(
            id="base-2",
            score=0.75,
            payload={
                "content": "Outro passo base.",
                "metadata": {
                    "section_id": "base-2",
                    "doc_id": "base-doc",
                    "doc_role": "base",
                    "section_role": "core_rules",
                    "section_order": 2,
                    "section_title": "Toques Finais",
                    "applies_to": ["workflow"],
                    "concepts": ["ficha"],
                    "usefulness_score": 0.7,
                    "heading_quality_score": 0.6,
                    "content_density_score": 0.6,
                    "noise_score": 0.1,
                },
            },
        ),
        SimpleNamespace(
            id="supp-1",
            score=0.5,
            payload={
                "content": "Suplemento adiciona novas opções nesta etapa.",
                "metadata": {
                    "section_id": "supp-1",
                    "doc_id": "supp-doc",
                    "doc_role": "supplement",
                    "section_role": "supplement_rules",
                    "section_order": 3,
                    "section_title": "Campeões de Arton",
                    "applies_to": ["workflow", "character_options"],
                    "concepts": ["opções"],
                    "usefulness_score": 0.8,
                    "heading_quality_score": 0.8,
                    "content_density_score": 0.7,
                    "noise_score": 0.1,
                },
            },
        ),
    ]

    selected = service._select_canonical_candidates(
        points=points,
        question="Qual a sequência para criar um personagem e em que etapa o suplemento adiciona opções?",
        query_profile=query_profile,
        answer_strategy="sequence",
        limit=2,
    )

    assert len(selected) == 2
    assert any(item["doc_role"] == "supplement" for item in selected)


def test_select_quick_lookup_points_boosts_explicit_supplement_match():
    service = KnowledgeSpaceService()
    query_profile = service._build_query_profile("Em que trecho o livro fala sobre novas opções de raças?")
    points = [
        SimpleNamespace(
            id="base",
            score=0.7,
            payload={
                "content": "Escolha sua raça e classe para começar.",
                "metadata": {"doc_role": "base", "file_name": "base.pdf"},
            },
        ),
        SimpleNamespace(
            id="supp",
            score=0.55,
            payload={
                "content": "Novas raças: duende, eiradaan, meio-elfo, sátiro e galokk.",
                "metadata": {"doc_role": "supplement", "file_name": "supp.pdf"},
            },
        ),
    ]

    selected = service._select_quick_lookup_points(
        points=points,
        question="Em que trecho o livro fala sobre novas opções de raças?",
        query_profile=query_profile,
        limit=1,
    )

    assert selected[0].id == "supp"


def test_finalize_sections_filters_noise_and_keeps_useful_rule():
    service = KnowledgeSpaceService()

    sections, skipped = service._finalize_sections(
        [
            {
                "title": "Capítulo 1",
                "body": "Escolha seus atributos, origem, raça e classe para montar o personagem.",
                "section_role": "core_rules",
                "order": 1,
                "evidence_span_ids": ["a", "b"],
            },
            {
                "title": "SUMÁRIO",
                "body": "Capítulo 1 ........ 3 Capítulo 2 ........ 9",
                "section_role": "front_matter",
                "order": 2,
                "evidence_span_ids": ["c"],
            },
        ]
    )

    assert len(sections) == 1
    assert skipped == 1
    assert sections[0]["is_useful"] is True
    assert sections[0]["usefulness_score"] > 0.4


def test_build_consolidation_metrics_rewards_useful_sections():
    service = KnowledgeSpaceService()

    metrics = service._build_consolidation_metrics(
        sections=[
            {"section_role": "core_rules", "usefulness_score": 0.82},
            {"section_role": "supplement_rules", "usefulness_score": 0.77},
            {"section_role": "optional_rules", "usefulness_score": 0.61},
        ],
        skipped_sections=2,
    )

    assert metrics["sections_total"] == 5
    assert metrics["sections_indexed"] == 3
    assert metrics["canonical_frames_total"] == 3
    assert metrics["consolidation_quality_score"] > 0.6


def test_query_space_skips_auto_canonical_when_ready_space_has_no_canonical_metrics():
    service = KnowledgeSpaceService()
    service.get_space = lambda **kwargs: {  # type: ignore[method-assign]
        "knowledge_space_id": "ks-1",
        "consolidation_status": "ready",
        "canonical_frames_total": 0,
        "sections_indexed": 0,
    }
    service._manifest_repo = SimpleNamespace(list_manifests=lambda **kwargs: [])
    called = {"canonical": False}

    async def fake_canonical(**kwargs):
        called["canonical"] = True
        return {"mode_used": "canonical_answer", "citations": [{"doc_id": "doc-1"}]}

    async def fake_quick(**kwargs):
        return {
            "answer": "quick",
            "mode_used": "quick_lookup",
            "base_used": "chunk_only",
            "answer_strategy": "locator",
            "source_scope": {"knowledge_space_id": "ks-1"},
            "citations": [],
            "confidence": 0.4,
            "gaps_or_conflicts": [],
        }

    service._query_canonical = fake_canonical  # type: ignore[method-assign]
    service._query_quick_lookup = fake_quick  # type: ignore[method-assign]

    result = asyncio.run(
        service.query_space(
            knowledge_space_id="ks-1",
            user_id="user-1",
            question="Como o suplemento amplia a regra base?",
            mode="auto",
            limit=5,
        )
    )

    assert result["mode_used"] == "quick_lookup"
    assert called["canonical"] is False


def test_query_space_falls_back_when_canonical_times_out():
    service = KnowledgeSpaceService()
    service.get_space = lambda **kwargs: {  # type: ignore[method-assign]
        "knowledge_space_id": "ks-1",
        "consolidation_status": "ready",
        "canonical_frames_total": 4,
        "sections_indexed": 8,
    }
    service._manifest_repo = SimpleNamespace(list_manifests=lambda **kwargs: [])

    async def fake_canonical(**kwargs):
        await asyncio.sleep(0.05)
        return {"mode_used": "canonical_answer", "citations": [{"doc_id": "doc-1"}]}

    async def fake_quick(**kwargs):
        return {
            "answer": "quick",
            "mode_used": "quick_lookup",
            "base_used": "chunk_only",
            "answer_strategy": "locator",
            "source_scope": {"knowledge_space_id": "ks-1"},
            "citations": [],
            "confidence": 0.4,
            "gaps_or_conflicts": [],
        }

    service._query_canonical = fake_canonical  # type: ignore[method-assign]
    service._query_quick_lookup = fake_quick  # type: ignore[method-assign]

    previous = os.environ.get("KNOWLEDGE_SPACE_CANONICAL_TIMEOUT_SECONDS")
    os.environ["KNOWLEDGE_SPACE_CANONICAL_TIMEOUT_SECONDS"] = "0.01"
    try:
        result = asyncio.run(
            service.query_space(
                knowledge_space_id="ks-1",
                user_id="user-1",
                question="Modo canônico explícito",
                mode="canonical_answer",
                limit=5,
            )
        )
    finally:
        if previous is None:
            os.environ.pop("KNOWLEDGE_SPACE_CANONICAL_TIMEOUT_SECONDS", None)
        else:
            os.environ["KNOWLEDGE_SPACE_CANONICAL_TIMEOUT_SECONDS"] = previous

    assert result["mode_used"] == "quick_lookup"
    assert any("tempo limite" in item for item in result["gaps_or_conflicts"])
