# app/core/filesystem_manager.py

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

APP_DIR = Path("/app").resolve()
WORKSPACE_DIR = (APP_DIR / "workspace").resolve()


def _initialize_workspace():
    """Garante que o diretório de workspace exista."""
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)


def _is_path_safe_for_read(resolved_path: Path) -> bool:
    """Verificação de segurança para leitura: o caminho DEVE estar contido em /app."""
    try:
        resolved_path.relative_to(APP_DIR)
        return True
    except ValueError:
        return False


def read_file(file_path: str) -> str:
    """
    Lê o conteúdo de QUALQUER ficheiro dentro do diretório do projeto /app.
    Esta é a implementação da "Liberdade de Leitura".
    O caminho deve ser fornecido a partir da raiz do projeto, ex: 'app/main.py'.
    """
    try:
        absolute_path = (APP_DIR / file_path.lstrip('/')).resolve()

        if not _is_path_safe_for_read(absolute_path):
            raise PermissionError(
                f"Acesso de leitura negado: O caminho '{file_path}' está fora da área segura da aplicação (/app).")

        logger.info(f"Lendo ficheiro de forma segura: {absolute_path}")
        with open(absolute_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Erro: O ficheiro '{file_path}' não foi encontrado."
    except Exception as e:
        return f"Erro ao ler o ficheiro '{file_path}': {e}"


def write_file(file_path: str, content: str) -> str:
    """
    Escreve conteúdo num ficheiro. A escrita é ESTRITAMENTE restrita ao /app/workspace.
    Esta é a implementação da "Escrita Vigiada".
    """
    try:
        # Resolve o caminho sempre a partir do workspace.
        absolute_path = (WORKSPACE_DIR / file_path.lstrip('/')).resolve()

        if not str(absolute_path).startswith(str(WORKSPACE_DIR)):
            raise PermissionError(
                f"Acesso de escrita negado: Apenas é permitido escrever no diretório '{WORKSPACE_DIR}'.")

        logger.info(f"Escrevendo em ficheiro de forma segura: {absolute_path}")
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        with open(absolute_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Ficheiro '{file_path}' escrito com sucesso no workspace."
    except Exception as e:
        return f"Erro ao escrever no ficheiro '{file_path}': {e}"


def list_directory(path: str = ".") -> str:
    """Lista o conteúdo de um diretório. A listagem é ESTRITAMENTE restrita ao /app/workspace."""
    try:
        absolute_path = (APP_DIR / path.lstrip('/')).resolve()

        if not str(absolute_path).startswith(str(WORKSPACE_DIR)):
            raise PermissionError(
                f"Acesso de listagem negado: Apenas é permitido listar o diretório '{WORKSPACE_DIR}'.")

        logger.info(f"Listando diretório de forma segura: {absolute_path}")
        if not absolute_path.is_dir():
            return f"Erro: '{path}' não é um diretório dentro do workspace."

        entries = os.listdir(absolute_path)
        if not entries:
            return f"O diretório '{path}' no workspace está vazio."
        return "\n".join(entries)
    except Exception as e:
        return f"Erro ao listar o diretório '{path}': {e}"


_initialize_workspace()
