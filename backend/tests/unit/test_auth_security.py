from app.core.infrastructure.auth import get_actor_user_id


class _Req:
    def __init__(self, headers: dict[str, str]):
        self.headers = headers


def test_get_actor_ignores_x_user_id_by_default(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "development")

    assert get_actor_user_id(_Req(headers={"X-User-Id": "12"})) is None
