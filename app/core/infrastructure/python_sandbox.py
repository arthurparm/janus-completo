"""
Modulo de Sandbox Python Seguro - Sprint 4
Executa código Python de forma isolada e segura usando epicbox.
"""

import logging
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional

import epicbox

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Resultado da execução de código Python."""
    success: bool
    output: str
    exit_code: int
    error: Optional[str] = None
    execution_time: float = 0.0
    timeout: bool = False


class PythonSandbox:
    """
    Sandbox seguro para execução de código Python usando Docker via epicbox.
    
    Isso fornece isolamento de processo, filesystem e network.
    """

    def __init__(self):
        self.profile_name = "janus_sandbox"
        epicbox.configure(profiles=[
            epicbox.Profile(self.profile_name,
                            settings.SANDBOX_DOCKER_IMAGE,
                            network_disabled=True)
        ])
        logger.info(
            f"Sandbox epicbox configurado com perfil '{self.profile_name}' e imagem '{settings.SANDBOX_DOCKER_IMAGE}'.")

    def execute(self, code: str) -> ExecutionResult:
        """
        Executa um bloco de código Python no sandbox.

        Args:
            code: O código a ser executado.

        Returns:
            ExecutionResult com o resultado da execução.
        """
        start_time = time.time()

        if not code or not code.strip():
            return ExecutionResult(success=False, output="", error="Código vazio fornecido", exit_code=-1)

        try:
            result = epicbox.run(self.profile_name,
                                 command=f"python -c '''{code}'''",
                                 timeout=settings.SANDBOX_TIMEOUT_SECONDS)

            execution_time = time.time() - start_time
            output = result['stdout'].decode('utf-8', errors='ignore')
            stderr = result['stderr'].decode('utf-8', errors='ignore')

            if len(output) > settings.SANDBOX_MAX_OUTPUT_LENGTH:
                output = output[:settings.SANDBOX_MAX_OUTPUT_LENGTH] + "\n... (output truncado)"

            success = result['exit_code'] == 0 and not result['timeout']
            error_message = stderr if stderr else None
            if result['timeout']:
                error_message = "Timeout: A execução do código excedeu o tempo limite."

            return ExecutionResult(
                success=success,
                output=output,
                error=error_message,
                exit_code=result['exit_code'],
                execution_time=execution_time,
                timeout=result['timeout']
            )

        except Exception as e:
            logger.error(f"Erro inesperado ao executar sandbox: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                output="",
                error=f"Erro do sistema de sandbox: {e}",
                exit_code=-1,
                execution_time=time.time() - start_time
            )

    def execute_expression(self, expression: str) -> ExecutionResult:
        """
        Avalia uma única expressão Python e retorna o resultado.
        """
        # Envolve a expressão em um print para capturar o resultado no stdout
        code = f"print({expression})"
        return self.execute(code)


# Instância global do sandbox
python_sandbox = PythonSandbox()
