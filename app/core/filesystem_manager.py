# app/core/filesystem_manager.py
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Todas as operações são restritas a este diretório dentro do container.
WORKSPACE_DIR = Path("/app/workspace")

def _initialize_workspace():
    """Garante que o diretório de workspace exista."""
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

def _get_safe_path(file_path: str) -> Path:
    """
    Valida e resolve um caminho de arquivo para garantir que ele esteja dentro do WORKSPACE_DIR.
    Esta é a nossa principal medida de segurança.
    """
    # Converte para um caminho absoluto dentro do nosso contexto.
    absolute_path = (WORKSPACE_DIR / file_path).resolve()
    
    # A verificação de segurança crucial: o caminho resolvido ainda está dentro do nosso workspace?
    if WORKSPACE_DIR not in absolute_path.parents and absolute_path != WORKSPACE_DIR:
        raise PermissionError(f"Acesso negado: O caminho '{file_path}' está fora do workspace seguro.")
    
    return absolute_path

def read_file(file_path: str) -> str:
    """Lê o conteúdo de um arquivo de forma segura."""
    safe_path = _get_safe_path(file_path)
    logger.info(f"Lendo arquivo de forma segura: {safe_path}")
    try:
        with open(safe_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Erro: O arquivo '{file_path}' não foi encontrado."
    except Exception as e:
        return f"Erro ao ler o arquivo '{file_path}': {e}"

def write_file(file_path: str, content: str) -> str:
    """Escreve conteúdo em um arquivo de forma segura."""
    safe_path = _get_safe_path(file_path)
    logger.info(f"Escrevendo em arquivo de forma segura: {safe_path}")
    try:
        # Garante que os diretórios pais existam
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Arquivo '{file_path}' escrito com sucesso."
    except Exception as e:
        return f"Erro ao escrever no arquivo '{file_path}': {e}"

def list_directory(path: str = ".") -> str:
    """Lista o conteúdo de um diretório de forma segura."""
    safe_path = _get_safe_path(path)
    logger.info(f"Listando diretório de forma segura: {safe_path}")
    try:
        if not safe_path.is_dir():
            return f"Erro: '{path}' não é um diretório."
        
        entries = os.listdir(safe_path)
        if not entries:
            return f"O diretório '{path}' está vazio."
        return "\n".join(entries)
    except Exception as e:
        return f"Erro ao listar o diretório '{path}': {e}"

# Garante que o workspace exista quando o módulo for carregado.
_initialize_workspace()
