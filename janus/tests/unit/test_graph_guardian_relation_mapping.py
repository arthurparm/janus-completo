import pytest

from app.core.memory.graph_guardian import RelationType, graph_guardian


@pytest.mark.parametrize(
    ("raw_relation", "expected"),
    [
        ("HAS_IMPROVEMENT_TYPE", RelationType.HAS_PROPERTY),
        ("TARGETS", RelationType.APPLIED_TO),
        ("FAILED_ON", RelationType.CAUSED_BY),
        ("PROVIDES", RelationType.RETURNS),
        ("REFACTORS", RelationType.SOLVES),
        ("ORIGINATED", RelationType.CAUSED_BY),
        ("CONTAINS_DATA_FOR", RelationType.CONTAINS),
        ("TARGETED", RelationType.APPLIED_TO),
        ("PROVIDED_BY", RelationType.CAUSED_BY),
        ("ORIGINATES_FROM", RelationType.CAUSED_BY),
        ("IS_TYPE_OF", RelationType.IS_A),
        ("LOCATED_IN", RelationType.PART_OF),
        ("QUERIED_FOR", RelationType.USES),
        ("SENT", RelationType.INTERACTS_WITH),
        ("USES_MODEL", RelationType.HAS_MODEL),
        ("originates-from", RelationType.CAUSED_BY),
    ],
)
def test_graph_guardian_normalizes_log_driven_relations(raw_relation: str, expected: RelationType):
    assert graph_guardian.normalize_relation_type(raw_relation) == expected


def test_graph_guardian_unknown_relation_falls_back_to_relates_to():
    assert graph_guardian.normalize_relation_type("TOTALLY_UNKNOWN_RELATION") == RelationType.RELATES_TO
