from typing import Any

import structlog

from app.core.infrastructure.python_sandbox import ExecutionResult, python_sandbox

logger = structlog.get_logger(__name__)


class SandboxRepositoryError(Exception):
    """Base exception for sandbox repository errors."""

    pass


class SandboxRepository:
    """
    Camada de Repositório para o Sandbox Python.
    Abstrai todas as interações diretas com a infraestrutura de execução de código.
    """

    def execute_code(self, code: str, context: dict[str, Any]) -> ExecutionResult:
        """Executa um bloco de código através da infraestrutura de sandbox."""
        logger.debug("Executando código no repositório de sandbox.")
        try:
            return python_sandbox.execute(code, context=context or None)
        except Exception as e:
            logger.error("Erro no repositório ao executar código no sandbox", exc_info=e)
            raise SandboxRepositoryError("Falha ao executar código no sandbox.") from e

    def evaluate_expression(self, expression: str) -> ExecutionResult:
        """Avalia uma expressão através da infraestrutura de sandbox."""
        logger.debug("Avaliando expressão no repositório de sandbox.")
        try:
            return python_sandbox.execute_expression(expression)
        except Exception as e:
            logger.error("Erro no repositório ao avaliar expressão no sandbox", exc_info=e)
            raise SandboxRepositoryError("Falha ao avaliar expressão no sandbox.") from e


# Padrão de Injeção de Dependência: Getter para o repositório
def get_sandbox_repository() -> SandboxRepository:
    return SandboxRepository()
