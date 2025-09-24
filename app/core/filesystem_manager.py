# app/core/filesystem_manager.py

import logging
import os
import time
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

APP_DIR = Path("/app").resolve()
WORKSPACE_DIR = (APP_DIR / "workspace").resolve()

# Policies / guardrails
ALLOWED_WRITE_ROOTS = [WORKSPACE_DIR]
BLOCKED_EXTENSIONS = {".sh", ".py", ".env", ".exe", ".bat", ".ps1"}
MAX_CONTENT_SIZE = 1_000_000  # 1MB

# Circuit breaker state (very simple)
_CB_FAILURES = 0
_CB_OPEN_UNTIL: Optional[float] = None
_CB_THRESHOLD = 3
_CB_COOLDOWN_SEC = 30.0


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


def _is_path_allowed_for_write(resolved_path: Path) -> bool:
    try:
        return any(str(resolved_path).startswith(str(root)) for root in ALLOWED_WRITE_ROOTS)
    except Exception:
        return False


def _check_circuit() -> Optional[str]:
    global _CB_OPEN_UNTIL
    if _CB_OPEN_UNTIL and time.time() < _CB_OPEN_UNTIL:
        return f"Circuit breaker aberto até {_CB_OPEN_UNTIL}. Ação de escrita temporariamente bloqueada."
    return None


def _record_failure():
    global _CB_FAILURES, _CB_OPEN_UNTIL
    _CB_FAILURES += 1
    if _CB_FAILURES >= _CB_THRESHOLD:
        _CB_OPEN_UNTIL = time.time() + _CB_COOLDOWN_SEC
        logger.warning("Circuit breaker de write_file ativado.")


def _record_success():
    global _CB_FAILURES, _CB_OPEN_UNTIL
    _CB_FAILURES = 0
    _CB_OPEN_UNTIL = None


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


def write_file(file_path: str, content: str, overwrite: bool = False) -> str:
    """
    Escreve conteúdo num ficheiro. A escrita é ESTRITAMENTE restrita ao /app/workspace.
    Políticas:
    - Caminho normalizado dentro da allowlist (WORKSPACE)
    - Extensões bloqueadas (ex.: .sh, .py, .env)
    - Conteúdo obrigatório e <= 1MB
    - overwrite deve ser True para substituir um ficheiro existente
    - DRY_RUN: registra intenção e não escreve
    - Circuit breaker simples e retries rápidos
    """
    start = time.time()

    # Circuit breaker
    cb_msg = _check_circuit()
    if cb_msg:
        logger.error(cb_msg)
        return f"Erro: {cb_msg}"

    try:
        # Resolve o caminho sempre a partir do workspace.
        relative = file_path.lstrip('/')
        if '..' in Path(relative).parts:
            raise ValueError("path traversal não permitido ('..' encontrado)")
        absolute_path = (WORKSPACE_DIR / relative).resolve()

        if not _is_path_allowed_for_write(absolute_path):
            raise PermissionError(
                f"Acesso de escrita negado: Apenas é permitido escrever no diretório '{WORKSPACE_DIR}'.")

        ext = absolute_path.suffix.lower()
        if ext in BLOCKED_EXTENSIONS:
            raise PermissionError(f"Extensão bloqueada para escrita: {ext}")

        if not isinstance(content, str) or len(content) == 0:
            raise ValueError("'content' é obrigatório e não pode ser vazio. Se binário, use base64.")
        if len(content.encode('utf-8')) > MAX_CONTENT_SIZE:
            raise ValueError(f"'content' excede o limite de {MAX_CONTENT_SIZE} bytes")

        if absolute_path.exists() and not overwrite:
            raise FileExistsError("Ficheiro já existe. Defina overwrite=true para substituir.")

        if settings.DRY_RUN:
            logger.info(
                {
                    "event": "write_file_dry_run",
                    "path": str(absolute_path),
                    "bytes": len(content.encode('utf-8')),
                    "overwrite": overwrite,
                }
            )
            _record_success()
            elapsed = (time.time() - start) * 1000
            return f"[DRY_RUN] Intenção registrada: escrever {len(content)} chars em '{absolute_path}'. ({elapsed:.1f}ms)"

        logger.info(f"Escrevendo em ficheiro de forma segura: {absolute_path}")
        absolute_path.parent.mkdir(parents=True, exist_ok=True)

        # Retry simples até 2 tentativas
        attempt = 0
        last_err: Optional[Exception] = None
        while attempt < 2:
            try:
                with open(absolute_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                _record_success()
                elapsed = (time.time() - start) * 1000
                logger.info({
                    "event": "write_file_success",
                    "path": str(absolute_path),
                    "bytes": len(content.encode('utf-8')),
                    "overwrite": overwrite,
                    "latency_ms": round(elapsed, 1)
                })
                return f"Ficheiro '{file_path}' escrito com sucesso no workspace."
            except Exception as e:
                last_err = e
                attempt += 1
                time.sleep(0.05 * attempt)

        # Se chegou aqui, falhou
        _record_failure()
        raise last_err if last_err else RuntimeError("Falha desconhecida na escrita")

    except Exception as e:
        _record_failure()
        elapsed = (time.time() - start) * 1000
        logger.error({
            "event": "write_file_error",
            "path": file_path,
            "error": str(e),
            "latency_ms": round(elapsed, 1)
        })
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
