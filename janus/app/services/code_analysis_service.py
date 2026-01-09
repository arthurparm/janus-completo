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
        self._current_function: str | None = None

    def visit_ClassDef(self, node: ast.ClassDef):
        self.classes.append({"name": node.name, "line": node.lineno})
        self.generic_visit(node)  # Visita nós filhos

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.functions.append({"name": node.name, "line": node.lineno})
        previous_function = self._current_function
        self._current_function = node.name
        self.generic_visit(node)
        self._current_function = previous_function

    def visit_Call(self, node: ast.Call):
        callee_name = None
        if isinstance(node.func, ast.Name):
            callee_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            callee_name = node.func.attr

        if self._current_function and callee_name:
            self.calls.append(
                {
                    "caller": self._current_function,
                    "callee": callee_name,
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
            with open(file_path, encoding="utf-8") as f:
                source_code = f.read()
            tree = ast.parse(source_code)
            parser = CodeParser(file_path)
            parser.visit(tree)
            return parser
        except Exception as e:
            logger.error(f"Falha ao fazer o parse do arquivo {file_path}", exc_info=e)
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
