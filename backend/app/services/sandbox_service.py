from typing import Any

import structlog
from fastapi import Request

from app.config import settings
from app.core.infrastructure.python_sandbox import ExecutionResult, python_sandbox
from app.repositories.sandbox_repository import SandboxRepository, SandboxRepositoryError

logger = structlog.get_logger(__name__)

# --- Custom Service-Layer Exceptions ---


class SandboxError(Exception):
    """Base exception for sandbox service errors."""

    pass


class InvalidInputError(SandboxError):
    """Raised for invalid input, such as empty code."""

    pass


# --- Sandbox Service ---


class SandboxService:
    """
    Camada de serviço para operações de execução de código em sandbox.
    Orquestra a lógica de negócio, recebendo suas dependências via DI.
    """

    def __init__(self, repo: SandboxRepository):
        self._repo = repo

    def execute_code(self, code: str, context: dict[str, Any]) -> ExecutionResult:
        """
        Valida a entrada e delega a execução de código para o repositório.
        """
        logger.info("Orquestrando execução de código via serviço.")
        if not code or not code.strip():
            raise InvalidInputError("O código não pode ser vazio.")

        try:
            return self._repo.execute_code(code, context)
        except SandboxRepositoryError as e:
            logger.error("Erro no repositório de sandbox ao executar código", exc_info=e)
            raise SandboxError("Falha ao executar código no sandbox.") from e

    def evaluate_expression(self, expression: str) -> ExecutionResult:
        """
        Valida a entrada e delega a avaliação de expressão para o repositório.
        """
        logger.info("Orquestrando avaliação de expressão via serviço.")
        if not expression or not expression.strip():
            raise InvalidInputError("A expressão não pode ser vazia.")

        try:
            return self._repo.evaluate_expression(expression)
        except SandboxRepositoryError as e:
            logger.error("Erro no repositório de sandbox ao avaliar expressão", exc_info=e)
            raise SandboxError("Falha ao avaliar expressão no sandbox.") from e

    def get_capabilities(self) -> dict[str, Any]:
        """Retorna as capacidades e restrições do sandbox."""
        logger.info("Buscando capacidades do sandbox via serviço.")
        return {
            "allowed_modules": sorted(python_sandbox.allowed_modules),
            "restrictions": {
                "filesystem_access": False,
                "network_access": False,
                "subprocess": False,
                "timeout_seconds": getattr(settings, "SANDBOX_TIMEOUT_SECONDS", 15),
                "max_output_length": getattr(settings, "SANDBOX_MAX_OUTPUT_LENGTH", 25000),
                "mem_limit_mb": getattr(settings, "SANDBOX_MEM_LIMIT_MB", 256),
                "cpu_limit": getattr(settings, "SANDBOX_CPU_LIMIT", 1.0),
            },
            "features": {
                "print_support": True,
                "variable_inspection": True,
                "context_variables": True,
                "expression_evaluation": True,
                "sandbox_mode": str(getattr(settings, "SANDBOX_MODE", "auto")),
            },
        }


# Padrão de Injeção de Dependência: Getter para o serviço
def get_sandbox_service(request: Request) -> SandboxService:
    return request.app.state.sandbox_service
