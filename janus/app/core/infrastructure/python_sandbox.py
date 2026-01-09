"""
Modulo de Sandbox Python Seguro - Sprint 4
Executa código Python de forma isolada e segura usando RestrictedPython.
"""

import io
import logging
import time
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Resultado da execução de código Python."""

    success: bool
    output: str
    exit_code: int
    error: str | None = None
    execution_time: float = 0.0
    timeout: bool = False
    variables: dict[str, Any] | None = None


class PythonSandbox:
    """
    Sandbox seguro para execução de código Python usando exec() restrito.

    Limitações:
    - Sem acesso ao filesystem (open, file)
    - Sem acesso à network (socket, urllib, requests)
    - Sem importação de módulos perigosos (os, subprocess, sys)
    - Apenas módulos permitidos (math, random, datetime, json, re, etc.)
    """

    def __init__(self):
        self.allowed_modules = {
            "math",
            "random",
            "datetime",
            "json",
            "re",
            "collections",
            "itertools",
            "functools",
            "statistics",
            "decimal",
            "fractions",
            "time",
        }
        logger.info(f"Sandbox Python configurado com módulos permitidos: {self.allowed_modules}")

    def _safe_import(self, name, *args, **kwargs):
        """Import hook seguro que só permite módulos whitelist."""
        if name.split(".")[0] in self.allowed_modules:
            return __import__(name, *args, **kwargs)
        raise ImportError(
            f"Módulo '{name}' não permitido. Permitidos: {', '.join(sorted(self.allowed_modules))}"
        )

    def _create_safe_globals(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Cria um dicionário de globals seguro com apenas builtins permitidos."""
        safe_builtins = {
            "abs": abs,
            "all": all,
            "any": any,
            "bin": bin,
            "bool": bool,
            "chr": chr,
            "dict": dict,
            "divmod": divmod,
            "enumerate": enumerate,
            "filter": filter,
            "float": float,
            "format": format,
            "hex": hex,
            "int": int,
            "isinstance": isinstance,
            "len": len,
            "list": list,
            "map": map,
            "max": max,
            "min": min,
            "oct": oct,
            "ord": ord,
            "pow": pow,
            "print": print,
            "range": range,
            "reversed": reversed,
            "round": round,
            "set": set,
            "slice": slice,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "type": type,
            "zip": zip,
            "True": True,
            "False": False,
            "None": None,
            "__import__": self._safe_import,  # Hook de import seguro
        }

        safe_globals = {
            "__builtins__": safe_builtins,
            "__name__": "__sandbox__",
            "__doc__": None,
        }

        # Adiciona contexto fornecido pelo usuário
        if context:
            safe_globals.update(context)

        return safe_globals

    def execute(self, code: str, context: dict[str, Any] | None = None) -> ExecutionResult:
        """
        Executa um bloco de código Python no sandbox.

        Args:
            code: O código a ser executado.
            context: Variáveis adicionais disponíveis no contexto de execução.

        Returns:
            ExecutionResult com o resultado da execução.
        """
        start_time = time.time()

        if not code or not code.strip():
            return ExecutionResult(
                success=False, output="", error="Código vazio fornecido", exit_code=-1
            )

        try:
            logger.info(f"[SANDBOX] Executando código - {len(code)} caracteres")

            # Cria ambiente seguro
            safe_globals = self._create_safe_globals(context)
            safe_locals = {}

            # Captura stdout e stderr
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            # Executa código com redirects
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, safe_globals, safe_locals)

            execution_time = time.time() - start_time
            logger.info(f"[SANDBOX] ✓ Execução concluída - tempo={execution_time:.3f}s")

            output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()

            if len(output) > settings.SANDBOX_MAX_OUTPUT_LENGTH:
                output = output[: settings.SANDBOX_MAX_OUTPUT_LENGTH] + "\n... (output truncado)"

            return ExecutionResult(
                success=True,
                output=output,
                error=stderr_output if stderr_output else None,
                exit_code=0,
                execution_time=execution_time,
                timeout=False,
                variables=safe_locals,
            )

        except ImportError as e:
            logger.warning(f"[SANDBOX] ⚠️ Tentativa de importar módulo não permitido: {e}")
            return ExecutionResult(
                success=False,
                output="",
                error=f"Importação bloqueada: {e}. Módulos permitidos: {', '.join(sorted(self.allowed_modules))}",
                exit_code=1,
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            logger.error(f"[SANDBOX] ❌ Erro ao executar código: {e}", exc_info=False)
            return ExecutionResult(
                success=False,
                output="",
                error=f"{type(e).__name__}: {e!s}",
                exit_code=1,
                execution_time=time.time() - start_time,
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
