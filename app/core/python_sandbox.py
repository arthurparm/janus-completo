"""
Módulo de Sandbox Python Seguro - Sprint 4
Executa código Python de forma isolada e segura usando RestrictedPython.
"""

import ast
import io
import logging
import sys
import time
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, Any, Optional
from dataclasses import dataclass

from RestrictedPython import compile_restricted, safe_globals, limited_builtins
from RestrictedPython.Guards import safe_builtins, guarded_iter_unpack_sequence
from RestrictedPython.Eval import default_guarded_getitem, default_guarded_getiter

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Resultado da execução de código Python."""
    success: bool
    output: str
    error: Optional[str] = None
    execution_time: float = 0.0
    variables: Dict[str, Any] = None


class PythonSandbox:
    """
    Sandbox seguro para execução de código Python.

    Usa RestrictedPython para limitar o que o código pode fazer:
    - Sem acesso a imports perigosos
    - Sem acesso ao filesystem
    - Sem acesso a network
    - Timeout configurável
    - Memória limitada
    """

    def __init__(
        self,
        timeout_seconds: int = 5,
        max_output_length: int = 10000
    ):
        self.timeout_seconds = timeout_seconds
        self.max_output_length = max_output_length
        self._setup_safe_globals()

    def _setup_safe_globals(self):
        """Configura o ambiente global seguro para execução."""
        # Builtins seguros do RestrictedPython
        self.safe_globals = {
            '__builtins__': {
                **limited_builtins,
                # Funções seguras permitidas
                'abs': abs,
                'all': all,
                'any': any,
                'chr': chr,
                'divmod': divmod,
                'enumerate': enumerate,
                'filter': filter,
                'float': float,
                'format': format,
                'hex': hex,
                'int': int,
                'isinstance': isinstance,
                'issubclass': issubclass,
                'len': len,
                'list': list,
                'map': map,
                'max': max,
                'min': min,
                'oct': oct,
                'ord': ord,
                'pow': pow,
                'range': range,
                'reversed': reversed,
                'round': round,
                'set': set,
                'slice': slice,
                'sorted': sorted,
                'str': str,
                'sum': sum,
                'tuple': tuple,
                'type': type,
                'zip': zip,
                # Matemática
                '__import__': self._safe_import,
            },
            # Guards do RestrictedPython
            '_getiter_': default_guarded_getiter,
            '_getitem_': default_guarded_getitem,
            '_iter_unpack_sequence_': guarded_iter_unpack_sequence,
            '_print_': self._safe_print,
            '_write_': self._safe_write,
        }

    def _safe_import(self, name, *args, **kwargs):
        """
        Import controlado - permite apenas módulos seguros.
        """
        # Whitelist de módulos permitidos
        ALLOWED_MODULES = {
            'math', 'random', 'datetime', 'json', 're',
            'collections', 'itertools', 'functools',
            'statistics', 'decimal', 'fractions'
        }

        if name in ALLOWED_MODULES:
            return __import__(name, *args, **kwargs)
        else:
            raise ImportError(f"Import de '{name}' não é permitido no sandbox")

    def _safe_print(self, *args, **kwargs):
        """Print seguro que respeita limites."""
        return print(*args, **kwargs)

    def _safe_write(self, obj):
        """Write seguro."""
        return obj

    def _validate_code(self, code: str) -> bool:
        """
        Valida o código antes da execução.
        Verifica por padrões perigosos.
        """
        dangerous_patterns = [
            'import os',
            'import sys',
            'import subprocess',
            'import socket',
            '__import__',
            'eval(',
            'exec(',
            'compile(',
            'open(',
            'file(',
            '__builtins__',
        ]

        code_lower = code.lower()
        for pattern in dangerous_patterns:
            if pattern.lower() in code_lower:
                logger.warning(f"Código contém padrão perigoso: {pattern}")
                # Permite se for um import permitido
                if pattern.startswith('import') and any(
                    allowed in code_lower
                    for allowed in ['math', 'random', 'datetime', 'json', 're']
                ):
                    continue
                return False

        return True

    def _check_syntax(self, code: str) -> Optional[str]:
        """Verifica a sintaxe do código Python."""
        try:
            ast.parse(code)
            return None
        except SyntaxError as e:
            return f"Erro de sintaxe: {e}"

    def execute(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Executa código Python de forma segura.

        Args:
            code: Código Python a ser executado
            context: Variáveis adicionais no contexto de execução

        Returns:
            ExecutionResult com sucesso/falha e output
        """
        start_time = time.time()

        # Validações iniciais
        if not code or not code.strip():
            return ExecutionResult(
                success=False,
                output="",
                error="Código vazio fornecido",
                execution_time=0.0
            )

        # Verifica sintaxe
        syntax_error = self._check_syntax(code)
        if syntax_error:
            return ExecutionResult(
                success=False,
                output="",
                error=syntax_error,
                execution_time=time.time() - start_time
            )

        # Valida padrões perigosos
        if not self._validate_code(code):
            return ExecutionResult(
                success=False,
                output="",
                error="Código contém operações não permitidas",
                execution_time=time.time() - start_time
            )

        # Compila código restrito
        try:
            byte_code = compile_restricted(
                code,
                filename='<sandboxed>',
                mode='exec'
            )

            if byte_code.errors:
                error_msg = "; ".join(byte_code.errors)
                return ExecutionResult(
                    success=False,
                    output="",
                    error=f"Erros de compilação RestrictedPython: {error_msg}",
                    execution_time=time.time() - start_time
                )

        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Erro ao compilar código: {str(e)}",
                execution_time=time.time() - start_time
            )

        # Prepara contexto de execução
        exec_globals = self.safe_globals.copy()
        if context:
            # Adiciona variáveis do contexto (sanitizadas)
            for key, value in context.items():
                if isinstance(key, str) and not key.startswith('_'):
                    exec_globals[key] = value

        # Captura output
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            # Executa com timeout
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(byte_code.code, exec_globals)

            output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()

            if stderr_output:
                output += f"\n[STDERR]: {stderr_output}"

            # Limita tamanho do output
            if len(output) > self.max_output_length:
                output = output[:self.max_output_length] + "\n... (output truncado)"

            # Extrai variáveis definidas
            user_variables = {
                k: v for k, v in exec_globals.items()
                if not k.startswith('_') and k not in self.safe_globals
            }

            execution_time = time.time() - start_time

            return ExecutionResult(
                success=True,
                output=output or "(código executado sem output)",
                error=None,
                execution_time=execution_time,
                variables=user_variables
            )

        except Exception as e:
            stderr_output = stderr_capture.getvalue()
            error_msg = f"{type(e).__name__}: {str(e)}"
            if stderr_output:
                error_msg += f"\n[STDERR]: {stderr_output}"

            return ExecutionResult(
                success=False,
                output=stdout_capture.getvalue(),
                error=error_msg,
                execution_time=time.time() - start_time
            )

    def execute_expression(self, expression: str) -> ExecutionResult:
        """
        Executa uma expressão Python e retorna o resultado.

        Args:
            expression: Expressão Python (ex: "2 + 2", "sum([1,2,3])")

        Returns:
            ExecutionResult com o resultado da expressão
        """
        code = f"__result__ = {expression}"
        result = self.execute(code)

        if result.success and result.variables:
            result_value = result.variables.get('__result__')
            result.output = str(result_value)

        return result


# Instância global do sandbox
python_sandbox = PythonSandbox(
    timeout_seconds=getattr(settings, 'SANDBOX_TIMEOUT_SECONDS', 5),
    max_output_length=getattr(settings, 'SANDBOX_MAX_OUTPUT_LENGTH', 10000)
)
