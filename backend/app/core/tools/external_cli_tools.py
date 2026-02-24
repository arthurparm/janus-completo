import structlog
import shutil
import subprocess
from pathlib import Path

from langchain.tools import tool
from pydantic import BaseModel, Field

from app.config import settings
from app.core.tools.action_module import PermissionLevel, ToolCategory, register_tool

logger = structlog.get_logger(__name__)


def _get_cli_path(command: str) -> str | None:
    """
    Resolve o caminho absoluto do executável usando shutil.which.
    Isso garante que estamos usando o binário correto do sistema (Windows/Linux).
    """
    return shutil.which(command)


def _redact_args_for_log(args: list[str]) -> str:
    """
    Redact potentially sensitive or large arguments before logging.
    """
    safe_parts: list[str] = []
    for part in args:
        if not part:
            safe_parts.append(part)
            continue
        if len(part) > 120 or "\n" in part or "\r" in part:
            safe_parts.append(f"<redacted:{len(part)} chars>")
        else:
            safe_parts.append(part)
    return " ".join(safe_parts)


def _run_command(args: list[str], cwd: Path | None = None) -> str:
    if not settings.EXTERNAL_CLI_ENABLED:
        return "Erro: CLI externo desativado por configuração."

    timeout = int(getattr(settings, "EXTERNAL_CLI_TIMEOUT_SECONDS", 600))
    max_chars = int(getattr(settings, "EXTERNAL_CLI_MAX_OUTPUT_CHARS", 20000))

    try:
        # Se args[0] for um caminho absoluto, subprocess.run usa ele diretamente.
        # Isso resolve a ambiguidade em ambientes Windows.
        cmd_str = _redact_args_for_log(args)
        logger.debug("log_debug", message=f"Executando comando externo: {cmd_str}")

        result = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout or ""
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr}"
        if len(output) > max_chars:
            output = output[:max_chars] + "\n...[output truncated]"
        return output.strip()
    except subprocess.TimeoutExpired:
        return f"Erro: comando excedeu {timeout}s."
    except Exception as e:
        return f"Erro ao executar comando: {e!s}"


class CodexExecInput(BaseModel):
    prompt: str = Field(description="Instrução para o Codex executar.")
    model: str | None = Field(default=None, description="Modelo opcional (ex: o3, gpt-4o).")


@tool(args_schema=CodexExecInput)
def codex_exec(prompt: str, model: str | None = None) -> str:
    """
    Executa o Codex CLI de forma não-interativa.
    """
    cli_path = _get_cli_path("codex")
    if not cli_path:
        return "Erro: 'codex' CLI não encontrado no PATH do sistema Windows."

    # Usa o caminho resolvido explicitamente
    args = [cli_path, "exec", "-C", str(Path(settings.WORKSPACE_ROOT).resolve())]
    if model:
        args += ["-m", model]
    args.append(prompt)
    
    logger.info("log_info", message=f"Executando Codex CLI ({cli_path})", extra={"command": "codex exec"})
    return _run_command(args, cwd=Path(settings.WORKSPACE_ROOT).resolve())


class CodexReviewInput(BaseModel):
    prompt: str | None = Field(
        default=None, description="Instruções customizadas para o review."
    )
    base: str | None = Field(default=None, description="Branch base para comparação.")
    commit: str | None = Field(default=None, description="Commit SHA para revisão.")
    uncommitted: bool = Field(default=True, description="Revisar mudanças não commitadas.")


@tool(args_schema=CodexReviewInput)
def codex_review(
    prompt: str | None = None,
    base: str | None = None,
    commit: str | None = None,
    uncommitted: bool = True,
) -> str:
    """
    Executa o Codex review CLI.
    """
    cli_path = _get_cli_path("codex")
    if not cli_path:
        return "Erro: 'codex' CLI não encontrado no PATH do sistema Windows."

    args = [cli_path, "review"]
    if commit:
        args += ["--commit", commit]
    elif base:
        args += ["--base", base]
    elif uncommitted:
        args += ["--uncommitted"]
    if prompt:
        args.append(prompt)

    logger.info("log_info", message=f"Executando Codex review ({cli_path})", extra={"command": "codex review"})
    return _run_command(args, cwd=Path(settings.WORKSPACE_ROOT).resolve())


class JulesNewInput(BaseModel):
    prompt: str = Field(description="Tarefa para o Jules executar.")
    repo: str | None = Field(
        default=None, description="Repositório remoto (ex: org/repo)."
    )


@tool(args_schema=JulesNewInput)
def jules_new(prompt: str, repo: str | None = None) -> str:
    """
    Cria uma nova sessão no Jules.
    """
    cli_path = _get_cli_path("jules")
    if not cli_path:
        return "Erro: 'jules' CLI não encontrado no PATH do sistema Windows."

    args = [cli_path, "new"]
    if repo:
        args += ["--repo", repo]
    args.append(prompt)

    logger.info("log_info", message=f"Executando Jules new ({cli_path})", extra={"command": "jules new"})
    return _run_command(args, cwd=Path(settings.WORKSPACE_ROOT).resolve())


class JulesPullInput(BaseModel):
    session_id: str = Field(description="ID da sessão do Jules para puxar.")


@tool(args_schema=JulesPullInput)
def jules_pull(session_id: str) -> str:
    """
    Puxa o resultado de uma sessão do Jules sem aplicar patch automaticamente.
    """
    cli_path = _get_cli_path("jules")
    if not cli_path:
        return "Erro: 'jules' CLI não encontrado no PATH do sistema Windows."

    args = [cli_path, "remote", "pull", "--session", str(session_id)]
    logger.info("log_info", message=f"Executando Jules remote pull ({cli_path})", extra={"command": "jules remote pull"})
    return _run_command(args, cwd=Path(settings.WORKSPACE_ROOT).resolve())


class CodexLoginInput(BaseModel):
    token: str | None = Field(
        default=None, description="Token de autenticação (opcional). Se omitido, inicia fluxo interativo."
    )


@tool(args_schema=CodexLoginInput)
def codex_login(token: str | None = None) -> str:
    """
    Inicia o processo de login no Codex CLI.
    
    Se um token for fornecido, retorna instrução para usar o fluxo oficial.
    Caso contrário, executa o fluxo padrão via `codex --login`.
    """
    cli_path = _get_cli_path("codex")
    if not cli_path:
        return "Erro: 'codex' CLI não encontrado no PATH do sistema Windows."

    try:
        if token:
            return (
                "Login via token não é suportado pela Codex CLI. "
                "Use 'codex --login'."
            )

        logger.info("Iniciando fluxo de login do Codex...")
        args = [cli_path, "--login"]

        output = _run_command(args, cwd=Path(settings.WORKSPACE_ROOT).resolve())
        return output or "Processo de login finalizado."
    except Exception as e:
        logger.error("log_error", message=f"Erro ao executar codex login: {e}", exc_info=True)
        return f"Erro inesperado no login: {e}"


def register_external_cli_tools():
    register_tool(
        codex_exec,
        category=ToolCategory.SYSTEM,
        permission_level=PermissionLevel.WRITE,
        requires_confirmation=True,
        tags=["external_cli", "codex", "codegen"],
    )
    register_tool(
        codex_review,
        category=ToolCategory.SYSTEM,
        permission_level=PermissionLevel.READ_ONLY,
        requires_confirmation=True,
        tags=["external_cli", "codex", "review"],
    )
    register_tool(
        jules_new,
        category=ToolCategory.SYSTEM,
        permission_level=PermissionLevel.WRITE,
        requires_confirmation=True,
        tags=["external_cli", "jules", "async"],
    )
    register_tool(
        jules_pull,
        category=ToolCategory.SYSTEM,
        permission_level=PermissionLevel.READ_ONLY,
        requires_confirmation=True,
        tags=["external_cli", "jules", "async"],
    )
    register_tool(
        codex_login,
        category=ToolCategory.SYSTEM,
        permission_level=PermissionLevel.WRITE,
        requires_confirmation=True,
        tags=["external_cli", "codex", "auth"],
    )

    logger.info("Ferramentas externas (Codex/Jules) registradas.")
