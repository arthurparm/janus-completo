import sys
import types

import pytest

from app.core.workers.sandbox_agent_worker import _run_in_docker


class FakeContainers:
    def __init__(self):
        self.last_kwargs = None

    def run(
        self, image, command, remove, network_mode, mem_limit, nano_cpus, stderr, stdout, detach
    ):
        # Guarda argumentos para validação
        self.last_kwargs = {
            "image": image,
            "command": command,
            "remove": remove,
            "network_mode": network_mode,
            "mem_limit": mem_limit,
            "nano_cpus": nano_cpus,
            "stderr": stderr,
            "stdout": stdout,
            "detach": detach,
        }
        return b"OK"


class FakeImages:
    def pull(self, image):
        return None


class FakeDockerClient:
    def __init__(self):
        self.containers = FakeContainers()
        self.images = FakeImages()


@pytest.fixture
def fake_docker(monkeypatch):
    # Cria módulo fake 'docker' e submódulo 'docker.errors'
    docker_module = types.ModuleType("docker")
    errors_module = types.ModuleType("docker.errors")

    class ImageNotFound(Exception):
        pass

    class ContainerError(Exception):
        def __init__(self):
            self.stderr = b"error"

    class APIError(Exception):
        def __init__(self):
            self.explanation = "api error"

    errors_module.ImageNotFound = ImageNotFound
    errors_module.ContainerError = ContainerError
    errors_module.APIError = APIError

    docker_module.errors = errors_module

    client = FakeDockerClient()

    def from_env():
        return client

    docker_module.from_env = from_env

    # Injeta nos módulos
    monkeypatch.setitem(sys.modules, "docker", docker_module)
    monkeypatch.setitem(sys.modules, "docker.errors", errors_module)

    return client


def test_run_in_docker_enforces_secure_flags(fake_docker):
    stdout, stderr = _run_in_docker("print('hello')")

    # Deve ter sucesso e sem stderr (no nosso fake)
    assert stderr == ""
    assert "OK" in stdout

    # Valida flags de segurança
    kwargs = fake_docker.containers.last_kwargs
    assert kwargs is not None
    assert kwargs["network_mode"] == "none"
    assert kwargs["mem_limit"] == "256m"
    assert kwargs["detach"] is False
    assert kwargs["nano_cpus"] == 1_000_000_000
