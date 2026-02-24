import structlog
from pathlib import Path

from langchain.tools import tool

from app.config import settings
from app.core.tools.command_sandbox import run_restricted_command
from app.core.tools.action_module import PermissionLevel, ToolCategory, register_tool

logger = structlog.get_logger(__name__)


@tool
def execute_system_command(command: str) -> str:
    """
    EXECUTAR COMANDO DE SHELL SEM RESTRIÇÕES.

    Esta ferramenta permite executar QUALQUER comando no sistema operacional (Windows/Linux).
    NÃO há lista de bloqueio. USE COM EXTREMA CAUTELA.

    Permite:
    - Instalar pacotes (pip, npm, apt, choco)
    - Gerenciar serviços (systemctl, sc)
    - Operações de arquivo sistema (mv, rm, cp em qualquer lugar)
    - Diagnóstico de rede (ping, curl, netstat)

    Args:
        command: O comando shell a ser executado.

    Returns:
        Stdout combinado com Stderr ou mensagem de erro.
    """
    logger.warning("Executando comando do sistema em modo restrito", extra={"command": command})
    return run_restricted_command(
        command,
        timeout_seconds=300,
        cwd=Path(getattr(settings, "WORKSPACE_ROOT", "/app/workspace")).resolve(),
    )


@tool
def write_system_file(path: str, content: str) -> str:
    """
    Escreve um arquivo em QUALQUER lugar do sistema de arquivos.

    Args:
        path: Caminho absoluto ou relativo.
        content: Conteúdo do arquivo.
    """
    try:
        p = Path(path).resolve()
        logger.warning("log_warning", message=f"⚠️ ESCREVENDO ARQUIVO SISTEMA: {p}")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Arquivo escrito com sucesso em: {p}"
    except Exception as e:
        return f"Erro ao escrever arquivo: {e}"


@tool
def read_system_file(path: str) -> str:
    """
    Lê um arquivo de QUALQUER lugar do sistema de arquivos.
    """
    try:
        p = Path(path).resolve()
        logger.info("log_info", message=f"Lendo arquivo sistema: {p}")
        if not p.exists():
            return "Erro: Arquivo não existe."
        if p.stat().st_size > 10 * 1024 * 1024:  # 10MB limit
            return "Erro: Arquivo muito grande (>10MB)."
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"Erro ao ler arquivo: {e}"


@tool
def list_directory(path: str | None = None, directory: str | None = None) -> str:
    """
    Lista o conteúdo de um diretório no sistema de arquivos.

    Args:
        path: Caminho do diretório (preferencial).
        directory: Alias para path (opcional).
    """
    target_path = path or directory

    if not target_path:
        return "Erro: Parâmetro 'path' ou 'directory' é obrigatório."

    try:
        p = Path(target_path).resolve()
        logger.info("log_info", message=f"Listando diretório: {p}")
        if not p.exists():
            return "Erro: Diretório não existe."
        if not p.is_dir():
            return "Erro: O caminho não é um diretório."

        items = []
        for item in p.iterdir():
            type_str = "<DIR>" if item.is_dir() else "<FILE>"
            items.append(f"{type_str:<7} {item.name}")

        return "\n".join(items) if items else "(Diretório vazio)"
    except Exception as e:
        return f"Erro ao listar diretório: {e}"


def register_os_tools():
    """Registra as ferramentas de SO no ActionModule com nível PERIGOSO."""

    register_tool(
        execute_system_command,
        category=ToolCategory.SYSTEM,
        permission_level=PermissionLevel.DANGEROUS,
        tags=["os", "shell", "admin", "unrestricted"],
    )

    register_tool(
        write_system_file,
        category=ToolCategory.FILESYSTEM,
        permission_level=PermissionLevel.DANGEROUS,
        tags=["os", "fs", "admin", "unrestricted"],
    )

    register_tool(
        read_system_file,
        category=ToolCategory.FILESYSTEM,
        permission_level=PermissionLevel.DANGEROUS,
        tags=["os", "fs", "admin", "unrestricted"],
    )

    register_tool(
        list_directory,
        category=ToolCategory.FILESYSTEM,
        permission_level=PermissionLevel.DANGEROUS,
        tags=["os", "fs", "ls"],
    )

    logger.info("Ferramentas de SO (DANGEROUS) registradas.")
