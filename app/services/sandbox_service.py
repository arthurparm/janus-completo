import structlog
from typing import Dict, Any

from app.repositories.sandbox_repository import sandbox_repository, SandboxRepositoryError
from app.core.infrastructure.python_sandbox import SandboxResult

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
    Orquestra a lógica de negócio, delegando o acesso à infraestrutura para o repositório.
    """

    def execute_code(self, code: str, context: Dict[str, Any]) -> SandboxResult:
        """
        Valida a entrada e delega a execução de código para o repositório.
        """
        logger.info("Orquestrando execução de código via serviço.")
        if not code or not code.strip():
            raise InvalidInputError("O código não pode ser vazio.")

        try:
            return sandbox_repository.execute_code(code, context)
        except SandboxRepositoryError as e:
            logger.error("Erro no repositório de sandbox ao executar código", exc_info=e)
            raise SandboxError("Falha ao executar código no sandbox.") from e

    def evaluate_expression(self, expression: str) -> SandboxResult:
        """
        Valida a entrada e delega a avaliação de expressão para o repositório.
        """
        logger.info("Orquestrando avaliação de expressão via serviço.")
        if not expression or not expression.strip():
            raise InvalidInputError("A expressão não pode ser vazia.")

        try:
            return sandbox_repository.evaluate_expression(expression)
        except SandboxRepositoryError as e:
            logger.error("Erro no repositório de sandbox ao avaliar expressão", exc_info=e)
            raise SandboxError("Falha ao avaliar expressão no sandbox.") from e

    def get_capabilities(self) -> Dict[str, Any]:
        """Retorna as capacidades e restrições do sandbox."""
        logger.info("Buscando capacidades do sandbox via serviço.")
        # Esta lógica é estática e não precisa de um repositório, mas é mantida no serviço por consistência.
        return {
            "allowed_modules": [
                "math", "random", "datetime", "json", "re",
                "collections", "itertools", "functools",
                "statistics", "decimal", "fractions"
            ],
            "restrictions": {
                "filesystem_access": False,
                "network_access": False,
                "subprocess": False,
                "timeout_seconds": 5,
                "max_output_length": 10000
            },
            "features": {
                "print_support": True,
                "variable_inspection": True,
                "context_variables": True,
                "expression_evaluation": True
            }
        }


# Instância única do serviço
sandbox_service = SandboxService()
