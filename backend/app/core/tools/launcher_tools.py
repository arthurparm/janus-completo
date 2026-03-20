import structlog
import platform
import subprocess

from langchain.tools import tool

logger = structlog.get_logger(__name__)


@tool
def launch_app(app_name: str) -> str:
    """
    Inicia um aplicativo ou comando no sistema operacional hospedeiro.

    Tenta identificar o SO e usar o comando nativo apropriado (start, open, gtk-launch).

    Args:
        app_name: Nome do aplicativo ou executável (ex: "calc", "notepad", "chrome", "spotify").
                  Se for um caminho completo, tente usar aspas duplas se houver espaços.

    Returns:
        Mensagem de sucesso ou erro.
    """
    system = platform.system()
    app_name = app_name.strip()

    logger.info("log_info", message=f"Tentando iniciar aplicativo: {app_name} no sistema {system}")

    try:
        if system == "Windows":
            # Usando uma lista e chamando o cmd.exe para evitar shell=True com string formatada
            subprocess.Popen(["cmd.exe", "/c", "start", '""', app_name])
        elif system == "Darwin":  # macOS
            subprocess.Popen(["open", "-a", app_name])
        elif system == "Linux":
            # Fallback genérico: executa direto em background usando shlex para particionar, mas sem shell=True
            import shlex
            cmd = shlex.split(app_name)
            subprocess.Popen(cmd, start_new_session=True)
        else:
            return f"Erro: Sistema operacional '{system}' não suportado para lançamento de apps."

        return f"Comando de lançamento enviado para '{app_name}'."
    except Exception as e:
        logger.error("log_error", message=f"Erro ao lançar app {app_name}: {e}", exc_info=True)
        return f"Erro ao tentar iniciar '{app_name}': {e!s}"
