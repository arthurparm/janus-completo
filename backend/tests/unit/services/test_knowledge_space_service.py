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
    assert (
        service._detect_answer_strategy(
            "Na criação de personagem, o que o livro base define primeiro e em que ponto Heróis de Arton acrescenta opções novas?"
        )
        == "sequence"
    )


def test_detect_answer_strategy_prefers_locator_for_trecho_questions():
    service = KnowledgeSpaceService()

    assert service._detect_answer_strategy("Em que trecho ou seção o livro fala sobre novas opções de raças?") == "locator"


def test_build_query_profile_flags_task_execution_for_grounded_creation():
    service = KnowledgeSpaceService()

    profile = service._build_query_profile(
        "Crie uma ficha completa usando somente as regras aprendidas do livro e explique as escolhas."
    )

    assert profile["asks_for_task_execution"] is True


def test_select_canonical_candidates_keeps_supplement_for_sequence_questions():
    service = KnowledgeSpaceService()
    query_profile = service._build_query_profile(
        "Qual a sequência para criar um personagem e em que etapa o suplemento adiciona opções?"
    )
    points = [
        SimpleNamespace(
            id="base-marketing",
            score=0.85,
            payload={
                "content": "Seu aventureiro para criar centenas de combinações únicas.",
                "metadata": {
                    "section_id": "base-marketing",
                    "doc_id": "base-doc",
                    "doc_role": "base",
                    "section_role": "core_rules",
                    "section_order": 1,
                    "section_title": "35 ORIGENS. Decida o passado de",
                    "applies_to": ["workflow"],
                    "concepts": ["personagem"],
                    "usefulness_score": 0.7,
                    "heading_quality_score": 0.7,
                    "content_density_score": 0.7,
                    "noise_score": 0.1,
                },
            },
        ),
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
                    "section_order": 2,
                    "section_title": "Capítulo Um",
                    "applies_to": ["workflow", "base_creation"],
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
    assert selected[0]["title"] == "Capítulo Um"
    assert any(item["doc_role"] == "supplement" for item in selected)


def test_render_sequence_answer_lists_base_before_supplement_extensions():
    service = KnowledgeSpaceService()

    answer = service._render_sequence_answer(
        [
            {
                "doc_role": "supplement",
                "section_order": 1,
                "rerank_score": 0.8,
                "title": "Capítulo 1: Campeões de Arton",
                "content": "Amplia com novas opções.",
            },
            {
                "doc_role": "base",
                "section_order": 9,
                "rerank_score": 0.7,
                "title": "9. Toques Finais",
                "content": "Fecha a criação do personagem.",
            },
        ]
    )

    lines = answer.splitlines()
    assert "[Base]" in lines[1]
    assert "[Suplemento]" in lines[2]


def test_select_quick_lookup_points_boosts_explicit_supplement_match():
    service = KnowledgeSpaceService()
    query_profile = service._build_query_profile("Em que trecho Heróis de Arton fala sobre novas raças?")
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
                "metadata": {"doc_role": "supplement", "file_name": "T20 - Herois de Arton v1.1.pdf"},
            },
        ),
        SimpleNamespace(
            id="supp-noisy",
            score=0.62,
            payload={
                "content": "Como pensa e age um Cavaleiro do Corvo. E isso é valioso para qualquer ser humano.",
                "metadata": {"doc_role": "supplement", "file_name": "T20 - Herois de Arton v1.1.pdf"},
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
    assert all(item.id != "supp-noisy" for item in selected[:1])


def test_select_quick_lookup_points_prefers_exact_topic_phrase_when_available():
    service = KnowledgeSpaceService()
    query_profile = service._build_query_profile("Em que trecho Heróis de Arton fala sobre novas raças?")
    points = [
        SimpleNamespace(
            id="generic-racas",
            score=0.88,
            payload={
                "content": "As raças moldam a personalidade e a história dos heróis.",
                "metadata": {"doc_role": "supplement", "file_name": "T20 - Herois de Arton v1.1.pdf"},
            },
        ),
        SimpleNamespace(
            id="exact-novas-racas",
            score=0.63,
            payload={
                "content": "Nov as Raças 9 Campeões de Arton traz novas raças para personagens jogadores.",
                "metadata": {"doc_role": "supplement", "file_name": "T20 - Herois de Arton v1.1.pdf"},
            },
        ),
        SimpleNamespace(
            id="toc-novas-racas",
            score=0.74,
            payload={
                "content": "Capitulo 1: Campeões de Arton .... 6 Novas Raças .... 8 Duende .... 8 Eiradaan .... 12",
                "metadata": {"doc_role": "supplement", "file_name": "T20 - Herois de Arton v1.1.pdf"},
            },
        ),
    ]

    selected = service._select_quick_lookup_points(
        points=points,
        question="Em que trecho Heróis de Arton fala sobre novas raças?",
        query_profile=query_profile,
        limit=2,
    )

    assert [item.id for item in selected] == ["exact-novas-racas"]


def test_table_of_contents_chunk_is_detected_as_noise_for_locator():
    service = KnowledgeSpaceService()

    assert service._looks_like_table_of_contents_chunk(
        title="T20 - Herois de Arton v1.1.pdf",
        content="Capitulo 1: Campeões de Arton .... 6 Novas Raças .... 8 Duende .... 8 Eiradaan .... 12",
    ) is True


def test_build_query_profile_separates_source_and_topic_terms():
    service = KnowledgeSpaceService()

    profile = service._build_query_profile("Em que trecho Heróis de Arton fala sobre novas raças?")

    assert "herois" in profile["source_terms"]
    assert "arton" in profile["source_terms"]
    assert "novas" in profile["topic_terms"]
    assert "racas" in profile["topic_terms"]
    assert "fala" not in profile["topic_terms"]
    assert "herois de arton" not in profile["topic_phrases"]
    assert "novas racas" in profile["topic_phrases"]
    assert profile["strict_topic_phrases"] == {"novas racas"}


def test_phrase_overlap_handles_ocr_split_tokens():
    service = KnowledgeSpaceService()

    overlap = service._phrase_overlap(
        text="Nov as Raças 9 Campeões de Arton",
        title="T20 - Herois de Arton v1.1.pdf",
        query_phrases={"novas racas"},
    )

    assert overlap == 1


def test_low_trust_sequence_title_penalizes_marketing_blocks():
    service = KnowledgeSpaceService()

    assert service._is_low_trust_sequence_title("35 ORIGENS. Decida o passado de") is True
    assert service._is_low_trust_sequence_title("Capítulo Um") is False


def test_editorial_content_is_detected_as_noise():
    service = KnowledgeSpaceService()

    assert service._looks_like_editorial_content(
        title="America em 2008) e Tormenta",
        body="É editor executivo da revista Dragão Brasil e editor sênior da Jambô Editora. Leonel Caldela romancista e RPGista.",
    ) is True


def test_sequence_anchor_identifies_base_and_supplement_chapters():
    service = KnowledgeSpaceService()

    assert service._is_sequence_anchor(
        title="Capítulo Um",
        content="Este capítulo traz as regras para a construção de personagens jogadores — como determinar seus atributos, raça, classe e origem.",
        doc_role="base",
    ) is True
    assert service._is_sequence_anchor(
        title="Capítulo 1: Campeões de Arton",
        content="Este capítulo apresenta diversas novas opções para construir seu personagem.",
        doc_role="supplement",
    ) is True


def test_looks_like_specific_option_chunk_identifies_itemized_rules():
    service = KnowledgeSpaceService()

    assert service._looks_like_specific_option_chunk(
        title="Equipamento Real",
        content="Pré-requisito: Int 3. • Engenhoqueiro. • Farmacêutico.",
    ) is True


def test_creation_foundation_signal_rejects_editorial_and_accepts_character_creation():
    service = KnowledgeSpaceService()

    assert service._has_creation_foundation_signal(
        title="Capítulo Um",
        content="Este capítulo traz a criação de personagem com atributos, raça, classe e origem.",
        doc_role="base",
    ) is True
    assert service._has_creation_foundation_signal(
        title="America em 2008) e Tormenta",
        content="Leonel Caldela é editor executivo da revista Dragão Brasil e editor sênior da Jambô Editora.",
        doc_role="base",
    ) is False


def test_base_creation_foundation_section_rejects_flavor_and_accepts_real_creation_flow():
    service = KnowledgeSpaceService()

    assert service._is_base_creation_foundation_section(
        title="2. Grupo de Heróis",
        content="Tormenta20 é sobre um grupo de heróis e suas aventuras no cenário.",
        section_role="core_rules",
        applies_to=["workflow", "base_creation"],
    ) is False
    assert service._is_base_creation_foundation_section(
        title="Capítulo Um",
        content="Criação de personagem: defina atributos, escolha raça, classe e origem para montar seu personagem.",
        section_role="core_rules",
        applies_to=["workflow", "base_creation"],
    ) is True


def test_supplement_creation_extension_section_rejects_optional_and_accepts_character_options():
    service = KnowledgeSpaceService()

    assert service._is_supplement_creation_extension_section(
        title="4 Regras Opcionais",
        content="Este é o último capítulo do livro e traz regras opcionais para aventuras variadas.",
        section_role="optional_rules",
        applies_to=["workflow", "character_options"],
    ) is False
    assert service._is_supplement_creation_extension_section(
        title="Capítulo 1: Campeões de Arton",
        content="Este capítulo apresenta novas opções para construir seu personagem, com novas raças e classes variantes.",
        section_role="supplement_rules",
        applies_to=["workflow", "character_options"],
    ) is True


def test_filter_points_by_doc_ids_drops_stale_space_points():
    service = KnowledgeSpaceService()
    points = [
        SimpleNamespace(payload={"metadata": {"doc_id": "doc-current"}}),
        SimpleNamespace(payload={"metadata": {"doc_id": "doc-stale"}}),
    ]

    filtered = service._filter_points_by_doc_ids(points, active_doc_ids={"doc-current"})

    assert len(filtered) == 1
    assert filtered[0].payload["metadata"]["doc_id"] == "doc-current"


def test_should_scroll_canonical_point_type_focuses_by_strategy():
    service = KnowledgeSpaceService()

    assert service._should_scroll_canonical_point_type(
        point_type="knowledge_flow_step",
        query_profile={"asks_for_sequence": True},
        answer_strategy="sequence",
    ) is True
    assert service._should_scroll_canonical_point_type(
        point_type="knowledge_canonical_summary",
        query_profile={"asks_for_sequence": True},
        answer_strategy="sequence",
    ) is False
    assert service._should_scroll_canonical_point_type(
        point_type="knowledge_evidence_anchor",
        query_profile={"expects_exact_evidence": True},
        answer_strategy="locator",
    ) is True


def test_select_canonical_candidates_rejects_editorial_base_for_creation_sequence():
    service = KnowledgeSpaceService()
    query_profile = service._build_query_profile(
        "Na criação de personagem de Tormenta20, o que o livro base define primeiro e em que ponto Heróis de Arton acrescenta opções novas?"
    )
    points = [
        SimpleNamespace(
            id="base-editorial",
            score=0.92,
            payload={
                "content": "O Despertar Rubro (2023), a primeira produção audiovisual do cenário. É editor executivo da revista Dragão Brasil e editor sênior da Jambô Editora. Leonel Caldela romancista e RPGista.",
                "metadata": {
                    "section_id": "base-editorial",
                    "doc_id": "base-doc",
                    "doc_role": "base",
                    "section_role": "optional_rules",
                    "section_order": 1,
                    "section_title": "America em 2008) e Tormenta",
                    "applies_to": ["workflow", "base_creation"],
                    "concepts": ["personagem"],
                    "usefulness_score": 0.82,
                    "heading_quality_score": 0.62,
                    "content_density_score": 0.71,
                    "noise_score": 0.12,
                },
            },
        ),
        SimpleNamespace(
            id="base-good",
            score=0.71,
            payload={
                "content": "Capítulo de criação de personagem: primeiro defina atributos, depois escolha raça, classe e origem.",
                "metadata": {
                    "section_id": "base-good",
                    "doc_id": "base-doc",
                    "doc_role": "base",
                    "section_role": "core_rules",
                    "section_order": 2,
                    "section_title": "Capítulo Um",
                    "applies_to": ["workflow", "base_creation"],
                    "concepts": ["atributos", "raça", "classe", "origem"],
                    "usefulness_score": 0.86,
                    "heading_quality_score": 0.82,
                    "content_density_score": 0.79,
                    "noise_score": 0.08,
                },
            },
        ),
        SimpleNamespace(
            id="supp-good",
            score=0.65,
            payload={
                "content": "Heróis de Arton acrescenta novas opções para construir o personagem, com novas raças e classes variantes.",
                "metadata": {
                    "section_id": "supp-good",
                    "doc_id": "supp-doc",
                    "doc_role": "supplement",
                    "section_role": "supplement_rules",
                    "section_order": 1,
                    "section_title": "Capítulo 1: Campeões de Arton",
                    "applies_to": ["workflow", "character_options"],
                    "concepts": ["novas opções", "raças"],
                    "usefulness_score": 0.84,
                    "heading_quality_score": 0.86,
                    "content_density_score": 0.76,
                    "noise_score": 0.07,
                },
            },
        ),
    ]

    selected = service._select_canonical_candidates(
        points=points,
        question="Na criação de personagem de Tormenta20, o que o livro base define primeiro e em que ponto Heróis de Arton acrescenta opções novas?",
        query_profile=query_profile,
        answer_strategy="sequence",
        limit=2,
    )

    assert len(selected) == 2
    assert selected[0]["section_id"] == "base-good"
    assert all(item["section_id"] != "base-editorial" for item in selected)


def test_select_canonical_candidates_rejects_flavor_base_for_creation_sequence():
    service = KnowledgeSpaceService()
    query_profile = service._build_query_profile(
        "Na criação de personagem de Tormenta20, o que o livro base define primeiro e em que ponto Heróis de Arton acrescenta opções novas?"
    )
    points = [
        SimpleNamespace(
            id="base-flavor",
            score=0.93,
            payload={
                "content": "Tormenta20 é sobre um grupo de heróis. O jogo apresenta personagem, raça, classe e origem como conceitos gerais.",
                "metadata": {
                    "section_id": "base-flavor",
                    "doc_id": "base-doc",
                    "doc_role": "base",
                    "section_role": "core_rules",
                    "section_order": 1,
                    "section_title": "2. Grupo de Heróis",
                    "applies_to": ["workflow", "base_creation"],
                    "concepts": ["personagem", "raça", "classe", "origem"],
                    "usefulness_score": 0.81,
                    "heading_quality_score": 0.74,
                    "content_density_score": 0.72,
                    "noise_score": 0.06,
                },
            },
        ),
        SimpleNamespace(
            id="base-good",
            score=0.78,
            payload={
                "content": "Criação de personagem: primeiro defina atributos, depois escolha raça, classe e origem.",
                "metadata": {
                    "section_id": "base-good",
                    "doc_id": "base-doc",
                    "doc_role": "base",
                    "section_role": "core_rules",
                    "section_order": 5,
                    "section_title": "Capítulo Um",
                    "applies_to": ["workflow", "base_creation"],
                    "concepts": ["atributos", "raça", "classe", "origem"],
                    "usefulness_score": 0.88,
                    "heading_quality_score": 0.83,
                    "content_density_score": 0.79,
                    "noise_score": 0.05,
                },
            },
        ),
        SimpleNamespace(
            id="supp-good",
            score=0.66,
            payload={
                "content": "Heróis de Arton acrescenta novas opções para criar o personagem, como novas raças.",
                "metadata": {
                    "section_id": "supp-good",
                    "doc_id": "supp-doc",
                    "doc_role": "supplement",
                    "section_role": "supplement_rules",
                    "section_order": 1,
                    "section_title": "Capítulo 1: Campeões de Arton",
                    "applies_to": ["workflow", "character_options"],
                    "concepts": ["novas opções", "raças"],
                    "usefulness_score": 0.84,
                    "heading_quality_score": 0.86,
                    "content_density_score": 0.76,
                    "noise_score": 0.07,
                },
            },
        ),
    ]

    selected = service._select_canonical_candidates(
        points=points,
        question="Na criação de personagem de Tormenta20, o que o livro base define primeiro e em que ponto Heróis de Arton acrescenta opções novas?",
        query_profile=query_profile,
        answer_strategy="sequence",
        limit=2,
    )

    assert len(selected) == 2
    assert selected[0]["section_id"] == "base-good"
    assert all(item["section_id"] != "base-flavor" for item in selected)


def test_select_canonical_candidates_prefers_creation_supplement_over_optional_rules():
    service = KnowledgeSpaceService()
    query_profile = service._build_query_profile(
        "Na criação de personagem de Tormenta20, o que o livro base define primeiro e em que ponto Heróis de Arton acrescenta opções novas?"
    )
    points = [
        SimpleNamespace(
            id="base-good",
            score=0.78,
            payload={
                "content": "Criação de personagem: primeiro defina atributos, depois escolha raça, classe e origem.",
                "metadata": {
                    "section_id": "base-good",
                    "doc_id": "base-doc",
                    "doc_role": "base",
                    "section_role": "core_rules",
                    "section_order": 5,
                    "section_title": "Capítulo Um",
                    "applies_to": ["workflow", "base_creation"],
                    "concepts": ["atributos", "raça", "classe", "origem"],
                    "usefulness_score": 0.88,
                    "heading_quality_score": 0.83,
                    "content_density_score": 0.79,
                    "noise_score": 0.05,
                },
            },
        ),
        SimpleNamespace(
            id="supp-optional",
            score=0.91,
            payload={
                "content": "Este é o último capítulo do livro e traz regras opcionais para aventuras variadas e diferentes.",
                "metadata": {
                    "section_id": "supp-optional",
                    "doc_id": "supp-doc",
                    "doc_role": "supplement",
                    "section_role": "optional_rules",
                    "section_order": 4,
                    "section_title": "4 Regras Opcionais",
                    "applies_to": ["workflow", "character_options"],
                    "concepts": ["regras opcionais"],
                    "usefulness_score": 0.82,
                    "heading_quality_score": 0.74,
                    "content_density_score": 0.75,
                    "noise_score": 0.05,
                },
            },
        ),
        SimpleNamespace(
            id="supp-good",
            score=0.66,
            payload={
                "content": "Heróis de Arton acrescenta novas opções para criar o personagem, como novas raças e classes variantes.",
                "metadata": {
                    "section_id": "supp-good",
                    "doc_id": "supp-doc",
                    "doc_role": "supplement",
                    "section_role": "supplement_rules",
                    "section_order": 1,
                    "section_title": "Capítulo 1: Campeões de Arton",
                    "applies_to": ["workflow", "character_options"],
                    "concepts": ["novas opções", "raças"],
                    "usefulness_score": 0.84,
                    "heading_quality_score": 0.86,
                    "content_density_score": 0.76,
                    "noise_score": 0.07,
                },
            },
        ),
    ]

    selected = service._select_canonical_candidates(
        points=points,
        question="Na criação de personagem de Tormenta20, o que o livro base define primeiro e em que ponto Heróis de Arton acrescenta opções novas?",
        query_profile=query_profile,
        answer_strategy="sequence",
        limit=2,
    )

    assert len(selected) == 2
    assert selected[1]["section_id"] == "supp-good"


def test_upsert_points_resilient_splits_large_batches_on_failure():
    service = KnowledgeSpaceService()

    class FakeClient:
        def __init__(self):
            self.calls = []

        async def upsert(self, *, collection_name, points):
            self.calls.append(len(points))
            if len(points) > 2:
                raise RuntimeError("too big")

    client = FakeClient()
    points = [SimpleNamespace(id=str(index)) for index in range(6)]

    asyncio.run(
        service._upsert_points_resilient(
            client=client,
            collection_name="col",
            points=points,
            min_batch_size=2,
        )
    )

    assert client.calls[0] == 6
    assert all(size <= 3 for size in client.calls[1:])


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


def test_select_sections_for_llm_enrichment_prioritizes_roles_and_quality():
    service = KnowledgeSpaceService()

    selected = service._select_sections_for_llm_enrichment(
        [
            {
                "section_id": "base-weak",
                "doc_role": "base",
                "section_role": "core_rules",
                "body": "palavras " * 50,
                "usefulness_score": 0.48,
                "heading_quality_score": 0.40,
                "order": 3,
            },
            {
                "section_id": "base-strong",
                "doc_role": "base",
                "section_role": "core_rules",
                "body": "palavras " * 70,
                "usefulness_score": 0.88,
                "heading_quality_score": 0.90,
                "order": 1,
            },
            {
                "section_id": "supp-strong",
                "doc_role": "supplement",
                "section_role": "supplement_rules",
                "body": "palavras " * 70,
                "usefulness_score": 0.86,
                "heading_quality_score": 0.85,
                "order": 2,
            },
            {
                "section_id": "noise",
                "doc_role": "base",
                "section_role": "noise",
                "body": "palavras " * 70,
                "usefulness_score": 0.99,
                "heading_quality_score": 0.99,
                "order": 4,
            },
        ],
        max_sections=2,
    )

    assert [item["section_id"] for item in selected] == ["base-strong", "supp-strong"]


def test_enrich_sections_with_llm_returns_original_sections_on_timeout():
    service = KnowledgeSpaceService(llm_service=SimpleNamespace())

    async def fake_invoke_llm(**kwargs):
        await asyncio.sleep(0.05)
        return {"response": "{}"}

    service._llm.invoke_llm = fake_invoke_llm
    sections = [
        {
            "section_id": "base-1",
            "doc_role": "base",
            "section_role": "core_rules",
            "body": "palavras " * 80,
            "usefulness_score": 0.8,
            "heading_quality_score": 0.8,
            "order": 1,
            "title": "Capítulo 1",
            "canonical_summary": "Resumo",
            "body_excerpt": "Trecho",
        }
    ]

    previous = os.environ.get("KNOWLEDGE_SPACE_LLM_ENRICH_TIMEOUT_SECONDS")
    os.environ["KNOWLEDGE_SPACE_LLM_ENRICH_TIMEOUT_SECONDS"] = "0.01"
    try:
        result = asyncio.run(
            service._enrich_sections_with_llm(
                sections,
                knowledge_space={"knowledge_space_id": "ks-1", "name": "KS"},
            )
        )
    finally:
        if previous is None:
            os.environ.pop("KNOWLEDGE_SPACE_LLM_ENRICH_TIMEOUT_SECONDS", None)
        else:
            os.environ["KNOWLEDGE_SPACE_LLM_ENRICH_TIMEOUT_SECONDS"] = previous

    assert result == sections


def test_enrich_sections_with_llm_forces_ollama_only_policy():
    captured = {}
    service = KnowledgeSpaceService(llm_service=SimpleNamespace())

    async def fake_invoke_llm(**kwargs):
        captured.update(kwargs)
        return {"response": '{"canonical_summary":"Resumo fiel","section_role":"core_rules"}'}

    service._llm.invoke_llm = fake_invoke_llm
    sections = [
        {
            "section_id": "base-1",
            "doc_role": "base",
            "section_role": "core_rules",
            "body": "palavras " * 80,
            "usefulness_score": 0.8,
            "heading_quality_score": 0.8,
            "order": 1,
            "title": "Capítulo 1",
            "canonical_summary": "Resumo",
            "body_excerpt": "Trecho",
        }
    ]

    result = asyncio.run(
        service._enrich_sections_with_llm(
            sections,
            knowledge_space={"knowledge_space_id": "ks-1", "name": "KS"},
        )
    )

    assert result[0]["canonical_summary"] == "Resumo fiel"
    assert captured["priority"].value == "local_only"
    assert captured["policy_overrides"]["provider"] == "ollama"
    assert captured["policy_overrides"]["strict_provider"] is True
    assert captured["policy_overrides"]["disable_failover"] is True
    assert captured["policy_overrides"]["disable_response_cache"] is True


def test_render_operational_answer_uses_ollama_only_and_returns_llm_response():
    captured = {}
    service = KnowledgeSpaceService(llm_service=SimpleNamespace())

    async def fake_invoke_llm(**kwargs):
        captured.update(kwargs)
        return {"response": "Ficha final baseada nas evidências."}

    async def fake_collect_support_points(**kwargs):
        return [
            SimpleNamespace(
                payload={
                    "content": "Trecho de apoio com escolhas e atributos.",
                    "metadata": {"doc_role": "base", "file_name": "livro.pdf", "chunk_index": 12},
                }
            )
        ]

    service._llm.invoke_llm = fake_invoke_llm
    service._collect_operational_support_points = fake_collect_support_points  # type: ignore[method-assign]

    result = asyncio.run(
        service._render_operational_answer(
                selected=[
                    {
                        "doc_role": "base",
                        "title": "Capítulo Um",
                        "section_role": "core_rules",
                        "content": "Regras para construção de personagem.",
                        "section_order": 1,
                        "rerank_score": 0.8,
                    }
                ],
            retrieval_strategy="sequence",
            knowledge_space={"knowledge_space_id": "ks-1", "name": "KS"},
            user_id="user-1",
            question="Crie uma ficha completa usando as regras do livro.",
            limit=4,
            active_doc_ids={"doc-1"},
        )
    )

    assert result == "Ficha final baseada nas evidências."
    assert captured["priority"].value == "local_only"
    assert captured["policy_overrides"]["provider"] == "ollama"
    assert captured["policy_overrides"]["strict_provider"] is True
    assert captured["policy_overrides"]["disable_failover"] is True
    assert captured["policy_overrides"]["disable_response_cache"] is True


def test_query_canonical_returns_task_strategy_for_execution_queries():
    service = KnowledgeSpaceService(llm_service=SimpleNamespace())

    async def fake_collect_support_points(**kwargs):
        return []

    async def fake_render_operational_answer(**kwargs):
        return "Artefato final grounded."

    service._collect_operational_support_points = fake_collect_support_points  # type: ignore[method-assign]
    service._render_operational_answer = fake_render_operational_answer  # type: ignore[method-assign]
    service._select_canonical_candidates = lambda **kwargs: [  # type: ignore[method-assign]
        {
            "point": SimpleNamespace(
                id="p-1",
                payload={
                    "content": "Regras para construção de personagem.",
                    "metadata": {
                        "doc_id": "doc-1",
                        "file_name": "livro.pdf",
                        "section_title": "Capítulo Um",
                        "doc_role": "base",
                        "section_role": "core_rules",
                    },
                },
                score=0.77,
            ),
            "doc_role": "base",
            "section_role": "core_rules",
            "title": "Capítulo Um",
            "content": "Regras para construção de personagem.",
            "lexical_overlap": 2,
        }
    ]

    class FakeClient:
        async def query_points(self, **kwargs):
            return SimpleNamespace(points=[])

    import app.services.knowledge_space_service as module

    original_get_client = module.get_async_qdrant_client
    original_get_collection = module.aget_or_create_collection
    original_embed = module.aembed_text
    try:
        module.get_async_qdrant_client = lambda: FakeClient()
        async def fake_get_collection(name):
            return "col"
        async def fake_embed(text):
            return [0.0] * 3
        module.aget_or_create_collection = fake_get_collection
        module.aembed_text = fake_embed
        service._scroll_points = fake_collect_support_points  # type: ignore[method-assign]

        result = asyncio.run(
            service._query_canonical(
                knowledge_space={"knowledge_space_id": "ks-1", "name": "KS"},
                user_id="user-1",
                question="Crie uma ficha completa usando as regras do livro.",
                limit=4,
                active_doc_ids={"doc-1"},
            )
        )
    finally:
        module.get_async_qdrant_client = original_get_client
        module.aget_or_create_collection = original_get_collection
        module.aembed_text = original_embed

    assert result["answer"] == "Artefato final grounded."
    assert result["answer_strategy"] == "task"


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


def test_query_space_uses_extended_timeout_for_task_execution_queries():
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
        return {
            "answer": "artefato grounded",
            "mode_used": "canonical_answer",
            "base_used": "consolidated",
            "answer_strategy": "task",
            "source_scope": {"knowledge_space_id": "ks-1"},
            "citations": [{"doc_id": "doc-1"}],
            "confidence": 0.8,
            "gaps_or_conflicts": [],
            "evidence_count": 1,
            "source_roles_used": ["base"],
        }

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

    previous_timeout = os.environ.get("KNOWLEDGE_SPACE_CANONICAL_TIMEOUT_SECONDS")
    previous_task_timeout = os.environ.get("KNOWLEDGE_SPACE_TASK_TIMEOUT_SECONDS")
    os.environ["KNOWLEDGE_SPACE_CANONICAL_TIMEOUT_SECONDS"] = "0.01"
    os.environ["KNOWLEDGE_SPACE_TASK_TIMEOUT_SECONDS"] = "0.2"
    try:
        result = asyncio.run(
            service.query_space(
                knowledge_space_id="ks-1",
                user_id="user-1",
                question="Crie uma ficha completa usando as regras do livro.",
                mode="canonical_answer",
                limit=5,
            )
        )
    finally:
        if previous_timeout is None:
            os.environ.pop("KNOWLEDGE_SPACE_CANONICAL_TIMEOUT_SECONDS", None)
        else:
            os.environ["KNOWLEDGE_SPACE_CANONICAL_TIMEOUT_SECONDS"] = previous_timeout
        if previous_task_timeout is None:
            os.environ.pop("KNOWLEDGE_SPACE_TASK_TIMEOUT_SECONDS", None)
        else:
            os.environ["KNOWLEDGE_SPACE_TASK_TIMEOUT_SECONDS"] = previous_task_timeout

    assert result["mode_used"] == "canonical_answer"
    assert result["answer_strategy"] == "task"


def test_reconcile_ready_processing_space_promotes_space_without_active_documents():
    service = KnowledgeSpaceService()
    service._space_repo = SimpleNamespace(
        mark_consolidation=lambda knowledge_space_id, **kwargs: {
            "knowledge_space_id": knowledge_space_id,
            "consolidation_status": kwargs["status"],
            "consolidation_summary": kwargs["summary"],
            "sections_total": kwargs["sections_total"],
            "sections_indexed": kwargs["sections_indexed"],
            "sections_skipped_as_noise": kwargs["sections_skipped_as_noise"],
            "canonical_frames_total": kwargs["canonical_frames_total"],
            "consolidation_quality_score": float(kwargs["consolidation_quality_score"]),
        }
    )

    reconciled = service._reconcile_ready_processing_space(
        knowledge_space={
            "knowledge_space_id": "ks-1",
            "consolidation_status": "processing",
            "consolidation_summary": "Consolidação estrutural em andamento.",
            "sections_total": 10,
            "sections_indexed": 7,
            "sections_skipped_as_noise": 3,
            "canonical_frames_total": 5,
            "consolidation_quality_score": 0.81,
        },
        documents_processing=0,
        documents_queued=0,
    )

    assert reconciled["consolidation_status"] == "ready"
