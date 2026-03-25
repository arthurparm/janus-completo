import contextvars
import json

from app.core.tools import productivity_tools


def _reset_context_stores() -> None:
    productivity_tools._calendar_events_ctx.set(None)
    productivity_tools._notes_ctx.set(None)


def test_calendar_events_are_isolated_by_context() -> None:
    _reset_context_stores()
    base_ctx = contextvars.copy_context()
    worker_ctx = contextvars.copy_context()

    def _events_for(title: str) -> list[dict[str, int | str]]:
        productivity_tools.create_calendar_event.func(user_id="user-a", title=title, when_ts_ms=123)
        raw = productivity_tools.list_calendar_events.func(user_id="user-a")
        return json.loads(raw)

    base_events = base_ctx.run(lambda: _events_for("Evento base"))
    worker_events = worker_ctx.run(lambda: _events_for("Evento worker"))

    assert base_events == [{"title": "Evento base", "when_ts_ms": 123}]
    assert worker_events == [{"title": "Evento worker", "when_ts_ms": 123}]


def test_send_email_log_is_redacted(monkeypatch) -> None:
    _reset_context_stores()
    captured: dict[str, object] = {}

    def fake_info(event: str, **kwargs):
        captured["event"] = event
        captured["kwargs"] = kwargs

    monkeypatch.setattr(productivity_tools.logger, "info", fake_info)

    result = productivity_tools.send_email.func(
        user_id="user-1",
        to="alice@example.com",
        subject="Invoice 2026-03",
        body="body",
    )

    payload = json.loads(result)
    assert payload["status"] == "queued"

    assert captured["event"] == "email_queued"
    kwargs = captured["kwargs"]
    assert kwargs["user_id"] == "user-1"
    assert kwargs["to_domain"] == "example.com"
    assert kwargs["subject_fingerprint"] == "len:15"
    assert "to" not in kwargs
    assert "subject" not in kwargs
