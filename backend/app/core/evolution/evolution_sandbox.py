import ast
import base64
import hashlib
import subprocess
from dataclasses import dataclass
from typing import Any

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

BLOCKED_IMPORTS = frozenset({
    "subprocess",
    "os",
    "os.system",
    "os.popen",
    "socket",
    "requests",
    "shutil.rmtree",
    "shutil",
    "builtins.open",
    "__import__",
    "importlib",
    "ctypes",
    "code",
    "compile",
    "eval",
    "exec",
})

FORBIDDEN_NAMES = frozenset({
    "__import__",
    "eval",
    "exec",
    "compile",
    "open",
    "getattr",
    "setattr",
    "delattr",
    "__subclasses__",
    "__bases__",
    "__mro__",
    "__class__",
    "__globals__",
    "__builtins__",
})


class SandboxValidationError(Exception):
    pass


@dataclass
class SandboxResult:
    success: bool
    output: str
    error: str | None = None
    signature: str | None = None
    execution_time: float = 0.0
    timed_out: bool = False


class _ImportVisitor(ast.NodeVisitor):
    def __init__(self):
        self.blocked: list[str] = []

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.name.split(".")[0]
            if name in BLOCKED_IMPORTS:
                self.blocked.append(f"import {alias.name}")

    def visit_ImportFrom(self, node):
        if node.module:
            name = node.module.split(".")[0]
            if name in BLOCKED_IMPORTS:
                self.blocked.append(f"from {node.module} import ...")

    def visit_Attribute(self, node):
        if isinstance(node.attr, str) and node.attr in FORBIDDEN_NAMES:
            self.blocked.append(f"attribute access: .{node.attr}")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in BLOCKED_IMPORTS:
            self.blocked.append(f"call to {node.func.id}")
        self.generic_visit(node)


class EvolutionSandbox:
    def __init__(self):
        self._image = getattr(settings, "SANDBOX_DOCKER_IMAGE", "python:3.11-slim")
        self._mem_limit = f"{int(getattr(settings, 'SANDBOX_MEM_LIMIT_MB', 256))}m"

    def validate(self, code: str) -> tuple[bool, str | None]:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        visitor = _ImportVisitor()
        visitor.visit(tree)

        if visitor.blocked:
            return False, f"Blocked imports/calls: {', '.join(visitor.blocked)}"

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
                return False, f"Forbidden name: {node.id}"

        return True, None

    def sign(self, code: str) -> str:
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    def execute(self, code: str, test_input: dict[str, Any] | None = None, timeout: int = 30) -> SandboxResult:
        import time
        start = time.time()

        ok, reason = self.validate(code)
        if not ok:
            return SandboxResult(success=False, output="", error=reason, timed_out=False)

        sig = self.sign(code)

        encoded = base64.b64encode(code.encode("utf-8")).decode("ascii")
        test_input_json = _safe_json(test_input or {})

        wrapper_lines = [
            "import base64, json, io, time",
            "from contextlib import redirect_stdout, redirect_stderr",
            f"_CODE = base64.b64decode('{encoded}').decode('utf-8')",
            f"_INPUT = json.loads({json.dumps(test_input_json)})",
            "_out = io.StringIO()",
            "_err = io.StringIO()",
            "_start = time.time()",
            "try:",
            "    with redirect_stdout(_out), redirect_stderr(_err):",
            "        exec(_CODE, {'__builtins__': __builtins__, '__name__': '__sandbox__'})",
            "    _success = True",
            "    _error = None",
            "except Exception as e:",
            "    _success = False",
            "    _error = f'{type(e).__name__}: {e}'",
            "_elapsed = time.time() - _start",
            "_output = _out.getvalue()",
            "_stderr = _err.getvalue()",
            "print(json.dumps({",
            "    'success': _success,",
            "    'output': _output or '',",
            "    'error': _error or (_stderr if _stderr else None),",
            "    'elapsed': _elapsed,",
            "}, ensure_ascii=True))",
        ]
        wrapper = "\n".join(wrapper_lines)
        wrapped_encoded = base64.b64encode(wrapper.encode("utf-8")).decode("ascii")

        cmd = [
            "python", "-c",
            f"import base64; code=base64.b64decode('{wrapped_encoded}').decode('utf-8'); exec(code)"
        ]

        try:
            import docker
            client = docker.from_env()
            container = client.containers.run(
                image=self._image,
                command=cmd,
                remove=True,
                network_mode="none",
                mem_limit=self._mem_limit,
                read_only=True,
                tmpfs={"/tmp": "size=64M"},
                stderr=True,
                stdout=True,
                detach=True,
            )
        except Exception as e:
            return SandboxResult(
                success=False, output="", error=f"Docker unavailable: {e}", signature=sig
            )

        timed_out = False
        try:
            container.wait(timeout=timeout)
            logs = container.logs(stdout=True, stderr=True)
        except Exception:
            timed_out = True
            try:
                container.kill()
            except Exception:
                pass
            logs = b""

        raw = logs.decode("utf-8", errors="replace") if isinstance(logs, (bytes, bytearray)) else str(logs)

        parsed = _parse_docker_output(raw)
        if parsed is None:
            return SandboxResult(
                success=False, output=raw[:2000], error="Failed to parse sandbox output",
                signature=sig, timed_out=timed_out, execution_time=time.time() - start
            )

        return SandboxResult(
            success=bool(parsed.get("success")),
            output=str(parsed.get("output", "")),
            error=parsed.get("error"),
            signature=sig,
            execution_time=float(parsed.get("elapsed", 0)),
            timed_out=timed_out,
        )


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value or {}, ensure_ascii=True)
    except Exception:
        return "{}"


def _parse_docker_output(raw: str) -> dict[str, Any] | None:
    if not raw:
        return None
    for line in reversed(raw.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if isinstance(data, dict) and "success" in data:
                return data
        except Exception:
            continue
    return None


evolution_sandbox = EvolutionSandbox()
