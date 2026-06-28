import pytest

from app.core.evolution.evolution_sandbox import EvolutionSandbox, SandboxResult, SandboxValidationError


@pytest.fixture
def sandbox():
    return EvolutionSandbox()


class TestValidate:
    def test_validate_blocks_subprocess_import(self, sandbox):
        ok, reason = sandbox.validate("import subprocess\nsubprocess.run('ls')")
        assert ok is False
        assert reason is not None
        assert "subprocess" in reason.lower()

    def test_validate_blocks_os_system_import(self, sandbox):
        ok, reason = sandbox.validate("import os\nos.system('ls')")
        assert ok is False
        assert reason is not None
        assert "os" in reason.lower()

    def test_validate_blocks_socket_import(self, sandbox):
        ok, reason = sandbox.validate("import socket\ns = socket.socket()")
        assert ok is False
        assert reason is not None
        assert "socket" in reason.lower()

    def test_validate_blocks_requests_import(self, sandbox):
        ok, reason = sandbox.validate("import requests\nr = requests.get('http://evil.com')")
        assert ok is False
        assert reason is not None
        assert "requests" in reason.lower()

    def test_validate_allows_safe_code(self, sandbox):
        ok, reason = sandbox.validate("x = 2 + 2\nresult = x * 3")
        assert ok is True
        assert reason is None

    def test_validate_blocks_forbidden_names(self, sandbox):
        ok, reason = sandbox.validate("eval('print(1)')")
        assert ok is False
        assert reason is not None
        assert "eval" in reason.lower()

    def test_validate_blocks_syntax_error(self, sandbox):
        ok, reason = sandbox.validate("def broken(:\n    pass")
        assert ok is False
        assert reason is not None
        assert "syntax" in reason.lower()


class TestSign:
    def test_sign_is_deterministic(self, sandbox):
        code = "x = 1 + 2"
        sig1 = sandbox.sign(code)
        sig2 = sandbox.sign(code)
        assert sig1 == sig2
        assert len(sig1) == 64

    def test_sign_differs_for_different_code(self, sandbox):
        sig1 = sandbox.sign("x = 1")
        sig2 = sandbox.sign("x = 2")
        assert sig1 != sig2

    def test_sign_is_hex_string(self, sandbox):
        sig = sandbox.sign("hello")
        assert all(c in "0123456789abcdef" for c in sig)


class TestExecute:
    @pytest.mark.skip(reason="Docker module shadowed by backend/docker directory")
    def test_execute_reports_docker_unavailable(self, sandbox, monkeypatch):
        def fake_from_env():
            raise RuntimeError("Docker unavailable")
        import docker as _docker
        monkeypatch.setattr(_docker, "from_env", fake_from_env)
        result = sandbox.execute("x = 1")
        assert isinstance(result, SandboxResult)
        assert result.success is False
        assert "Docker" in (result.error or "")
        assert result.timed_out is False
