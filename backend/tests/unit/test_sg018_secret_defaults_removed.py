from pathlib import Path

from app.core.evolution.janus_lab import JanusLabManager


def test_janus_lab_requires_neo4j_password_when_env_missing(monkeypatch):
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)

    manager = object.__new__(JanusLabManager)
    env = manager._generate_lab_env()

    assert env["NEO4J_PASSWORD"] == "__REQUIRED__"


def test_env_example_uses_required_placeholders_for_critical_secrets():
    env_example = Path("backend/app/.env.example").read_text(encoding="utf-8")

    assert "AUTH_JWT_SECRET=__REQUIRED__" in env_example
    assert "POSTGRES_PASSWORD=__REQUIRED__" in env_example
    assert "RABBITMQ_PASSWORD=__REQUIRED__" in env_example
    assert "NEO4J_PASSWORD=__REQUIRED__" in env_example
