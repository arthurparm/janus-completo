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
            # 'start' é um comando interno do shell cmd.exe
            # start "" "app_name" é a sintaxe segura
            subprocess.Popen(f'start "" "{app_name}"', shell=True)
        elif system == "Darwin":  # macOS
            subprocess.Popen(["open", "-a", app_name])
        elif system == "Linux":
            # Tenta encontrar no path ou usar gtk-launch se disponível
            # Fallback genérico: executa direto em background
            subprocess.Popen([app_name], start_new_session=True)
        else:
            return f"Erro: Sistema operacional '{system}' não suportado para lançamento de apps."

        return f"Comando de lançamento enviado para '{app_name}'."
    except Exception as e:
        logger.error("log_error", message=f"Erro ao lançar app {app_name}: {e}", exc_info=True)
        return f"Erro ao tentar iniciar '{app_name}': {e!s}"
