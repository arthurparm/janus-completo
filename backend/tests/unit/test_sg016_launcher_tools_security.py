import app.core.tools.launcher_tools as launcher_tools
from app.config import settings


def test_launch_app_rejects_command_injection_payload(monkeypatch):
    monkeypatch.setattr(settings, "LAUNCH_APP_ALLOWED_APPS", [])
    response = launcher_tools.launch_app.invoke({"app_name": 'calc.exe & del C:\\*.*'})
    assert "caracteres inválidos" in response


def test_launch_app_rejects_non_allowlisted_app(monkeypatch):
    monkeypatch.setattr(settings, "LAUNCH_APP_ALLOWED_APPS", ["calculator"])
    response = launcher_tools.launch_app.invoke({"app_name": "notepad"})
    assert "allowlist" in response


def test_launch_app_allows_allowlisted_app(monkeypatch):
    monkeypatch.setattr(settings, "LAUNCH_APP_ALLOWED_APPS", ["calculator"])
    monkeypatch.setattr(launcher_tools.platform, "system", lambda: "Linux")

    called = {}

    def _fake_popen(args, start_new_session=False):
        called["args"] = args
        called["start_new_session"] = start_new_session
        return object()

    monkeypatch.setattr(launcher_tools.subprocess, "Popen", _fake_popen)
    response = launcher_tools.launch_app.invoke({"app_name": "calculator"})

    assert "Comando de lançamento enviado" in response
    assert called["args"] == ["calculator"]
    assert called["start_new_session"] is True
