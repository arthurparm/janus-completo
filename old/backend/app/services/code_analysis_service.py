import ast
import os
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class CodeParser(ast.NodeVisitor):
    """
    Um NodeVisitor que extrai funções, classes e chamadas de um arquivo Python.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.functions: list[dict[str, Any]] = []
        self.classes: list[dict[str, Any]] = []
        self.calls: list[dict[str, Any]] = []
        self._scope_stack: list[str] = []
        self._current_class: str | None = None
        self._current_function_name: str | None = None
        self._current_function_qualified: str | None = None

    def _qualify_name(self, name: str) -> str:
        if not self._scope_stack:
            return name
        return ".".join([*self._scope_stack, name])

    def _attribute_to_name(self, node: ast.AST) -> str | None:
        parts: list[str] = []
        current = node

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)
            return ".".join(reversed(parts))
        return None

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        function_qualified = self._qualify_name(node.name)
        self.functions.append(
            {"name": node.name, "qualified_name": function_qualified, "line": node.lineno}
        )

        previous_name = self._current_function_name
        previous_qualified = self._current_function_qualified

        self._scope_stack.append(node.name)
        self._current_function_name = node.name
        self._current_function_qualified = function_qualified
        self.generic_visit(node)
        self._scope_stack.pop()

        self._current_function_name = previous_name
        self._current_function_qualified = previous_qualified

    def visit_ClassDef(self, node: ast.ClassDef):
        class_qualified = self._qualify_name(node.name)
        self.classes.append({"name": node.name, "qualified_name": class_qualified, "line": node.lineno})

        previous_class = self._current_class
        self._scope_stack.append(node.name)
        self._current_class = class_qualified
        self.generic_visit(node)
        self._scope_stack.pop()
        self._current_class = previous_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._visit_function(node)

    def visit_Call(self, node: ast.Call):
        callee_name = None
        callee_qualified = None

        if isinstance(node.func, ast.Name):
            callee_name = node.func.id
            callee_qualified = node.func.id
        elif isinstance(node.func, ast.Attribute):
            callee_name = node.func.attr
            attribute_name = self._attribute_to_name(node.func)
            if attribute_name:
                if (
                    self._current_class
                    and (attribute_name.startswith("self.") or attribute_name.startswith("cls."))
                ):
                    _, _, suffix = attribute_name.partition(".")
                    callee_qualified = f"{self._current_class}.{suffix}" if suffix else None
                else:
                    callee_qualified = attribute_name

        if self._current_function_name and callee_name:
            self.calls.append(
                {
                    "caller": self._current_function_name,
                    "caller_qualified": self._current_function_qualified
                    or self._current_function_name,
                    "callee": callee_name,
                    "callee_qualified": callee_qualified or callee_name,
                }
            )

        self.generic_visit(node)


class CodeAnalysisService:
    """
    Serviço responsável por analisar arquivos de código-fonte.
    Sua única responsabilidade é entender e extrair informações do código.
    """

    def parse_python_file(self, file_path: str) -> CodeParser | None:
        """Lê e analisa um único arquivo Python, retornando o objeto parser."""
        logger.debug("Analisando arquivo Python", file_path=file_path)
        try:
            # Supports UTF-8 with/without BOM to avoid SyntaxError on ast.parse.
            with open(file_path, encoding="utf-8-sig") as f:
                source_code = f.read()
            tree = ast.parse(source_code, filename=file_path)
            parser = CodeParser(file_path)
            parser.visit(tree)
            return parser
        except Exception as e:
            logger.error("log_error", message=f"Falha ao fazer o parse do arquivo {file_path}", exc_info=e)
            return None

    def find_python_files(self, directory: str) -> list[str]:
        """Encontra todos os arquivos .py em um diretório."""
        python_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))
        return python_files


# Instância única do serviço
code_analysis_service = CodeAnalysisService()
