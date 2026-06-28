from types import SimpleNamespace

import pytest

from app.core.autonomy.goal_conflict_detector import GoalConflictDetector, ConflictReport


@pytest.fixture
def detector():
    return GoalConflictDetector()


def _make_goal(id: str, title: str, description: str = ""):
    return SimpleNamespace(id=id, title=title, description=description)


class TestSameResource:
    def test_detects_same_resource(self, detector):
        a = _make_goal("g1", "Atualizar índices do Neo4j")
        b = _make_goal("g2", "Migrar dados do Neo4j para nova versão")
        reports = detector.detect_conflicts(a, [b])
        assert len(reports) >= 1
        assert any(r.conflict_type == "same_resource" for r in reports)

    def test_no_conflict_different_resources(self, detector):
        a = _make_goal("g1", "Atualizar índices do Neo4j")
        b = _make_goal("g2", "Limpar cache do Redis")
        reports = detector.detect_conflicts(a, [b])
        same_resource = [r for r in reports if r.conflict_type == "same_resource"]
        assert len(same_resource) == 0

    def test_affected_resources_extracts_keywords(self, detector):
        goal = _make_goal("g1", "Atualizar grafo de conhecimento no Neo4j", "Reindexar knowledge graph")
        resources = detector._affected_resources(goal)
        assert "neo4j" in resources
        assert "knowledge" in resources
        assert "graph" in resources


class TestOppositeIntent:
    def test_detects_opposite_intent(self, detector):
        a = _make_goal("g1", "Create new memory index")
        b = _make_goal("g2", "Delete old memory index")
        reports = detector.detect_conflicts(a, [b])
        assert any(r.conflict_type == "opposite_intent" for r in reports)

    def test_no_conflict_same_intent(self, detector):
        a = _make_goal("g1", "Create Neo4j constraint")
        b = _make_goal("g2", "Add Neo4j index")
        reports = detector.detect_conflicts(a, [b])
        opposite = [r for r in reports if r.conflict_type == "opposite_intent"]
        assert len(opposite) == 0
