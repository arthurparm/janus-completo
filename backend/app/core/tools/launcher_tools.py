import os
import structlog
import platform
import re
import subprocess

from langchain.tools import tool

from app.config import settings

logger = structlog.get_logger(__name__)
_DISALLOWED_CHARS = set("&;|`$><\n\r")
_APP_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._/\- :]{1,256}$")


def _is_allowed_app_name(app_name: str) -> bool:
    if not app_name:
        return False
    if any(char in _DISALLOWED_CHARS for char in app_name):
        return False
    if not _APP_NAME_PATTERN.fullmatch(app_name):
        return False
    return True


def _is_allowlisted_app(app_name: str) -> bool:
    allowed = getattr(settings, "LAUNCH_APP_ALLOWED_APPS", []) or []
    normalized = {str(item).strip().lower() for item in allowed if str(item).strip()}
    if not normalized:
        return True
    base_name = os.path.basename(app_name).lower()
    return app_name.lower() in normalized or base_name in normalized


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
    if not _is_allowed_app_name(app_name):
        return "Erro: app_name contém caracteres inválidos ou potencialmente perigosos."
    if not _is_allowlisted_app(app_name):
        return "Erro: app_name não está na allowlist configurada para lançamento."

    try:
        if system == "Windows":
            os.startfile(app_name)  # type: ignore[attr-defined]
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
