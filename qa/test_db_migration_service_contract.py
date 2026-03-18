from types import SimpleNamespace

from app.services.db_migration_service import DBMigrationService


class _FakeSession:
    def __init__(self, dialect_name: str):
        self._dialect_name = dialect_name
        self.executed_sql: list[str] = []

    def get_bind(self):
        return SimpleNamespace(dialect=SimpleNamespace(name=self._dialect_name))

    def execute(self, stmt):
        self.executed_sql.append(str(stmt))

    def close(self):
        return None


def _force_all_missing(monkeypatch, svc: DBMigrationService) -> None:
    monkeypatch.setattr(svc, "_index_exists", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(svc, "_constraint_exists", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(svc, "_column_exists", lambda *_args, **_kwargs: False)


def test_migrate_schema_uses_postgres_sql_and_consent_table(monkeypatch):
    svc = DBMigrationService()
    fake = _FakeSession("postgresql")
    monkeypatch.setattr(svc, "_get_session", lambda: fake)
    _force_all_missing(monkeypatch, svc)

    result = svc.migrate_schema()

    assert result["status"] == "applied"
    assert any("ALTER TABLE users ADD CONSTRAINT unique_user_email UNIQUE (email)" in q for q in fake.executed_sql)
    assert all("UNIQUE KEY" not in q for q in fake.executed_sql)
    assert any("ALTER TABLE user_privacy_consents ADD CONSTRAINT unique_user_privacy_scope_consent UNIQUE (user_id, scope)" in q for q in fake.executed_sql)
    assert any("CREATE INDEX idx_privacy_consent_user_scope ON user_privacy_consents (user_id, scope)" in q for q in fake.executed_sql)
    assert any("ALTER TABLE audit_events ADD COLUMN details_json JSONB NULL" in q for q in fake.executed_sql)


def test_migrate_schema_uses_mysql_specific_unique_key_and_text_json(monkeypatch):
    svc = DBMigrationService()
    fake = _FakeSession("mysql")
    monkeypatch.setattr(svc, "_get_session", lambda: fake)
    _force_all_missing(monkeypatch, svc)

    result = svc.migrate_schema()

    assert result["status"] == "applied"
    assert any("UNIQUE KEY" in q for q in fake.executed_sql)
    assert any("ALTER TABLE audit_events ADD COLUMN details_json TEXT NULL" in q for q in fake.executed_sql)


def test_validate_schema_checks_consent_table_with_model_names(monkeypatch):
    svc = DBMigrationService()
    fake = _FakeSession("postgresql")
    monkeypatch.setattr(svc, "_get_session", lambda: fake)

    constraint_calls: list[tuple[str, str]] = []
    index_calls: list[tuple[str, str]] = []

    def _constraint(_s, table: str, name: str) -> bool:
        constraint_calls.append((table, name))
        return True

    def _index(_s, table: str, name: str) -> bool:
        index_calls.append((table, name))
        return True

    monkeypatch.setattr(svc, "_constraint_exists", _constraint)
    monkeypatch.setattr(svc, "_index_exists", _index)
    monkeypatch.setattr(svc, "_column_exists", lambda *_args, **_kwargs: True)

    result = svc.validate_schema()

    assert result["status"] == "ok"
    assert ("user_privacy_consents", "unique_user_privacy_scope_consent") in constraint_calls
    assert ("user_privacy_consents", "idx_privacy_consent_user_scope") in index_calls
