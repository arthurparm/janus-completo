"""
Modulo de Sandbox Python Seguro - Sprint 4
Executa código Python de forma isolada e segura usando RestrictedPython.
"""

import base64
import io
import json
import logging
import time
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_SAFE_BUILTIN_NAMES = [
    "abs",
    "all",
    "any",
    "bin",
    "bool",
    "chr",
    "dict",
    "divmod",
    "enumerate",
    "filter",
    "float",
    "format",
    "hex",
    "int",
    "isinstance",
    "len",
    "list",
    "map",
    "max",
    "min",
    "oct",
    "ord",
    "pow",
    "print",
    "range",
    "reversed",
    "round",
    "set",
    "slice",
    "sorted",
    "str",
    "sum",
    "tuple",
    "type",
    "zip",
]


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
        self._mode = str(getattr(settings, "SANDBOX_MODE", "auto") or "auto").strip().lower()
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

    def _safe_json_payload(self, value: Any) -> str:
        try:
            return json.dumps(value or {}, ensure_ascii=True)
        except Exception:
            if isinstance(value, dict):
                fallback = {k: str(v) for k, v in value.items()}
            else:
                fallback = {"value": str(value)}
            return json.dumps(fallback, ensure_ascii=True)

    def _safe_builtins_literal(self) -> str:
        entries = [f"'{name}': {name}" for name in _SAFE_BUILTIN_NAMES]
        entries.extend(["'True': True", "'False': False", "'None': None"])
        return "{\n" + ",\n".join(entries) + "\n}"

    def _build_docker_wrapper(
        self,
        code: str,
        context: dict[str, Any] | None,
        call_function: str | None,
        call_args: dict[str, Any] | None,
    ) -> str:
        encoded_code = base64.b64encode(code.encode("utf-8")).decode("ascii")
        allowed_modules_literal = self._safe_json_payload(sorted(self.allowed_modules))
        context_literal = self._safe_json_payload(context or {})
        call_args_literal = self._safe_json_payload(call_args or {})
        function_name_literal = json.dumps(call_function) if call_function else "null"
        max_output_len = int(getattr(settings, "SANDBOX_MAX_OUTPUT_LENGTH", 25000))
        safe_builtins_literal = self._safe_builtins_literal()

        lines = [
            "import base64",
            "import io",
            "import json",
            "import time",
            "from contextlib import redirect_stdout, redirect_stderr",
            f"_ALLOWED = json.loads({json.dumps(allowed_modules_literal)})",
            "def _safe_import(name, *args, **kwargs):",
            "    if name.split('.')[0] in _ALLOWED:",
            "        return __import__(name, *args, **kwargs)",
            "    raise ImportError(\"Module '%s' not allowed. Allowed: %s\" % (",
            "        name, ', '.join(sorted(_ALLOWED))",
            "    ))",
            f"_SAFE_BUILTINS = {safe_builtins_literal}",
            "_SAFE_BUILTINS['__import__'] = _safe_import",
            "_GLOBALS = {'__builtins__': _SAFE_BUILTINS, '__name__': '__sandbox__', '__doc__': None}",
            "_LOCALS = {}",
            f"_CTX = json.loads({json.dumps(context_literal)})",
            "if isinstance(_CTX, dict) and _CTX:",
            "    _GLOBALS.update(_CTX)",
            f"_CODE = base64.b64decode('{encoded_code}').decode('utf-8')",
            "_start = time.time()",
            "_out_buf = io.StringIO()",
            "_err_buf = io.StringIO()",
            "_call_result = None",
            "_call_error = None",
            "try:",
            "    with redirect_stdout(_out_buf), redirect_stderr(_err_buf):",
            "        exec(_CODE, _GLOBALS, _LOCALS)",
            f"        _fn_name = {function_name_literal}",
            "        if _fn_name:",
            "            _fn = _LOCALS.get(_fn_name) or _GLOBALS.get(_fn_name)",
            "            if callable(_fn):",
            f"                _args = json.loads({json.dumps(call_args_literal)})",
            "                if isinstance(_args, dict):",
            "                    _call_result = _fn(**_args)",
            "                else:",
            "                    _call_result = _fn()",
            "            else:",
            "                _call_error = f\"Function '{_fn_name}' not found.\"",
            "    _success = True",
            "    _error = None",
            "except Exception as e:",
            "    _success = False",
            "    _error = f\"{type(e).__name__}: {e}\"",
            "_elapsed = time.time() - _start",
            "_output = _out_buf.getvalue()",
            "_stderr = _err_buf.getvalue()",
            "if _call_result is not None:",
            "    _output = str(_call_result)",
            "if _call_error and not _output:",
            "    _success = False",
            "    _error = _call_error",
            "if _error is None and _stderr:",
            "    _error = _stderr",
            f"_max_len = {max_output_len}",
            "if _output and len(_output) > _max_len:",
            "    _output = _output[:_max_len] + \"\\n... (output truncated)\"",
            "if _error and len(_error) > _max_len:",
            "    _error = _error[:_max_len] + \"\\n... (error truncated)\"",
            "_vars = {k: str(v) for k, v in _LOCALS.items()}",
            "print(json.dumps({",
            "    'success': bool(_success),",
            "    'output': _output or '',",
            "    'error': _error,",
            "    'execution_time': float(_elapsed),",
            "    'timeout': False,",
            "    'variables': _vars,",
            "}, ensure_ascii=True))",
        ]

        return "\n".join(lines)

    def _run_in_docker(self, wrapper_code: str, timeout_seconds: float) -> tuple[str, bool]:
        try:
            from docker.errors import APIError, ContainerError, ImageNotFound
            import docker
        except Exception as e:
            raise RuntimeError(f"Docker unavailable: {e}")

        client = docker.from_env()
        image = getattr(settings, "SANDBOX_DOCKER_IMAGE", "python:3.11-slim")
        mem_limit_mb = int(getattr(settings, "SANDBOX_MEM_LIMIT_MB", 256))
        cpu_limit = float(getattr(settings, "SANDBOX_CPU_LIMIT", 1.0))
        mem_limit = f"{mem_limit_mb}m"
        nano_cpus = max(1, int(cpu_limit * 1_000_000_000))

        encoded = base64.b64encode(wrapper_code.encode("utf-8")).decode("ascii")
        cmd = [
            "python",
            "-c",
            (
                "import base64;"
                "code=base64.b64decode('" + encoded + "').decode('utf-8');"
                "globals_dict={'__name__':'__main__'};"
                "exec(code, globals_dict)"
            ),
        ]

        try:
            container = client.containers.run(
                image=image,
                command=cmd,
                remove=False,
                network_mode="none",
                mem_limit=mem_limit,
                nano_cpus=nano_cpus,
                stderr=True,
                stdout=True,
                detach=True,
            )
        except ImageNotFound:
            client.images.pull(image)
            container = client.containers.run(
                image=image,
                command=cmd,
                remove=False,
                network_mode="none",
                mem_limit=mem_limit,
                nano_cpus=nano_cpus,
                stderr=True,
                stdout=True,
                detach=True,
            )
        except APIError as e:
            raise RuntimeError(
                f"Docker API error: {e.explanation if hasattr(e, 'explanation') else str(e)}"
            )

        timed_out = False
        try:
            container.wait(timeout=timeout_seconds)
            logs = container.logs(stdout=True, stderr=True)
        except Exception:
            timed_out = True
            try:
                container.kill()
            except Exception:
                pass
            logs = b""
        finally:
            try:
                container.remove(force=True)
            except Exception:
                pass

        output = (
            logs.decode("utf-8", errors="replace")
            if isinstance(logs, (bytes, bytearray))
            else str(logs)
        )
        return output, timed_out

    def _parse_docker_result(self, raw_output: str) -> dict[str, Any] | None:
        if not raw_output:
            return None
        for line in reversed(raw_output.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if isinstance(data, dict) and "success" in data and "output" in data:
                    return data
            except Exception:
                continue
        return None

    def execute(
        self,
        code: str,
        context: dict[str, Any] | None = None,
        call_function: str | None = None,
        call_args: dict[str, Any] | None = None,
    ) -> ExecutionResult:
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

            timeout_seconds = float(getattr(settings, "SANDBOX_TIMEOUT_SECONDS", 15))
            use_docker = self._mode in ("docker", "auto")
            if use_docker:
                wrapper = self._build_docker_wrapper(
                    code=code,
                    context=context,
                    call_function=call_function,
                    call_args=call_args,
                )
                try:
                    raw_output, timed_out = self._run_in_docker(wrapper, timeout_seconds)
                except Exception as e:
                    if self._mode == "docker":
                        return ExecutionResult(
                            success=False,
                            output="",
                            error=f"Docker sandbox failed: {e}",
                            exit_code=1,
                            execution_time=time.time() - start_time,
                        )
                    logger.warning(f"[SANDBOX] Docker fallback to process: {e}")
                else:
                    if timed_out:
                        return ExecutionResult(
                            success=False,
                            output="",
                            error="Execution timed out",
                            exit_code=1,
                            execution_time=time.time() - start_time,
                            timeout=True,
                        )
                    parsed = self._parse_docker_result(raw_output)
                    if parsed is None:
                        return ExecutionResult(
                            success=False,
                            output="",
                            error=raw_output or "Sandbox execution failed",
                            exit_code=1,
                            execution_time=time.time() - start_time,
                        )
                    return ExecutionResult(
                        success=bool(parsed.get("success")),
                        output=str(parsed.get("output") or ""),
                        error=parsed.get("error"),
                        exit_code=0 if parsed.get("success") else 1,
                        execution_time=float(parsed.get("execution_time") or 0.0),
                        timeout=bool(parsed.get("timeout") or False),
                        variables=parsed.get("variables") or None,
                    )

            # Cria ambiente seguro
            safe_globals = self._create_safe_globals(context)
            safe_locals = {}

            # Captura stdout e stderr
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            # Executa código com redirects
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, safe_globals, safe_locals)

            call_result = None
            call_error = None
            if call_function:
                try:
                    fn = safe_locals.get(call_function) or safe_globals.get(call_function)
                    if callable(fn):
                        args = call_args if isinstance(call_args, dict) else {}
                        call_result = fn(**args)
                    else:
                        call_error = f"Function '{call_function}' not found."
                except Exception as e:
                    call_error = f"{type(e).__name__}: {e}"

            execution_time = time.time() - start_time
            logger.info(f"[SANDBOX] ✓ Execução concluída - tempo={execution_time:.3f}s")

            output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()
            error_msg = None

            if call_result is not None:
                output = str(call_result)

            if call_error and not output:
                error_msg = call_error

            if len(output) > settings.SANDBOX_MAX_OUTPUT_LENGTH:
                output = output[: settings.SANDBOX_MAX_OUTPUT_LENGTH] + "\n... (output truncado)"

            return ExecutionResult(
                success=error_msg is None,
                output=output,
                error=error_msg or (stderr_output if stderr_output else None),
                exit_code=0 if error_msg is None else 1,
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
