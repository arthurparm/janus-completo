# app/core/filesystem_manager.py
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Define os dois diretórios principais
APP_DIR = Path("/app").resolve()
WORKSPACE_DIR = (APP_DIR / "workspace").resolve()


def _initialize_workspace():
    """Garante que o diretório de workspace exista."""
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)


def _is_path_safe(resolved_path: Path, base_dir: Path) -> bool:
    """Verifica se um caminho resolvido está contido em um diretório base."""
    # Garante que o caminho resolvido é descendente ou o próprio diretório base.
    try:
        resolved_path.relative_to(base_dir)
        return True
    except ValueError:
        return False


def read_file(file_path: str, base_dir: str = "workspace") -> str:
    """
    Lê o conteúdo de um arquivo. Por padrão, lê de dentro do WORKSPACE.
    Para ler da raiz do código, use base_dir='app'.
    """
    try:
        base_path = WORKSPACE_DIR if base_dir == "workspace" else APP_DIR

        absolute_path = (base_path / file_path.strip("/")).resolve()

        if not _is_path_safe(absolute_path, base_path):
            raise PermissionError(f"Acesso de leitura negado: O caminho '{file_path}' está fora do diretório permitido ('{base_dir}').")

        logger.info(f"Lendo arquivo de forma segura: {absolute_path}")
        with open(absolute_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Erro: O arquivo '{file_path}' não foi encontrado."
    except Exception as e:
        return f"Erro ao ler o arquivo '{file_path}': {e}"


def write_file(file_path: str, content: str) -> str:
    """
    Escreve conteúdo em um arquivo. A escrita é ESTRITAMENTE restrita ao /app/workspace.
    """
    try:
        absolute_path = (WORKSPACE_DIR / file_path.strip("/")).resolve()

        if not _is_path_safe(absolute_path, WORKSPACE_DIR):
            raise PermissionError(f"Acesso de escrita negado: O caminho '{file_path}' está fora do workspace seguro.")

        logger.info(f"Escrevendo em arquivo de forma segura: {absolute_path}")
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        with open(absolute_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Arquivo '{file_path}' escrito com sucesso no workspace."
    except Exception as e:
        return f"Erro ao escrever no arquivo '{file_path}': {e}"


def list_directory(path: str = ".") -> str:
    """
    Lista o conteúdo de um diretório. A listagem é ESTRITAMENTE restrita ao /app/workspace.
    """
    try:
        absolute_path = (WORKSPACE_DIR / path.strip("/")).resolve()

        if not _is_path_safe(absolute_path, WORKSPACE_DIR):
            raise PermissionError(f"Acesso de listagem negado: O caminho '{path}' está fora do workspace seguro.")

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