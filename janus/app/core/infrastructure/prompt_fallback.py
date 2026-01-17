"""
Prompt Loader modificado para carregar prompts do banco ou de arquivos.
Fallback: arquivo texto quando muito grande para SQL.
"""

import os
from pathlib import Path
from functools import lru_cache
import structlog

logger = structlog.get_logger(__name__)

# Diretório de prompts em arquivo (fallback para prompts muito grandes)
# Mantido apenas para compatibilidade de definição de caminho, mas não usado para carga
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"
if not PROMPTS_DIR.exists() and Path("/app/app/prompts").exists():
    PROMPTS_DIR = Path("/app/app/prompts")

# Cache de prompts
_file_prompts_cache: dict[str, str] = {}


async def get_prompt_with_fallback(prompt_name: str, **kwargs) -> str:
    """
    Carrega prompt com fallback hierárquico (Async):
    1. Banco de dados (via prompt_loader.get_prompt)
    2. Arquivo local
    """
    from app.core.infrastructure.prompt_loader import get_prompt

    # 1. Tentar banco de dados primeiro
    db_error = None
    try:
        db_prompt = await get_prompt(prompt_name, **kwargs)
        if db_prompt and not db_prompt.startswith("Prompt nao encontrado"):
            return db_prompt
    except Exception as e:
        db_error = e

    # 2. Fallback para arquivo local (Desenvolvimento/Recuperacao)
    if PROMPTS_DIR.exists():
        file_path = PROMPTS_DIR / f"{prompt_name}.txt"
        if file_path.exists():
            try:
                # Cache simples em memoria para evitar I/O constante
                if prompt_name in _file_prompts_cache:
                    if db_error:
                        logger.debug(
                            "Prompt carregado de arquivo apos falha no DB",
                            prompt_name=prompt_name,
                            error=str(db_error),
                        )
                    return _file_prompts_cache[prompt_name]
                
                content = file_path.read_text(encoding="utf-8")
                _file_prompts_cache[prompt_name] = content
                logger.debug("Prompt carregado de arquivo local", prompt_name=prompt_name, path=str(file_path))
                return content
            except Exception as e:
                logger.warning("Erro ao ler arquivo de prompt", prompt_name=prompt_name, error=str(e))

    if db_error:
        logger.warning("Falha ao buscar prompt do DB", prompt_name=prompt_name, error=str(db_error))

    # 3. Retornar None
    logger.warning("Prompt não encontrado em DB ou Arquivo", prompt_name=prompt_name)
    return None


# Mapeamento de nomes de prompt para variáveis hardcoded (fallback final)
# (Removido por solicitação do usuário)
HARDCODED_PROMPTS = {}


async def get_formatted_prompt(prompt_name: str, **format_kwargs) -> str:
    """
    Carrega prompt do banco e aplica formatação (Async).

    Args:
        prompt_name: Nome do prompt (ex: semantic_commit, task_decomposition)
        **format_kwargs: Variáveis para formatar no prompt

    Returns:
        Prompt formatado pronto para uso
    """
    # 1. Tentar DB (via get_prompt_with_fallback)
    prompt = await get_prompt_with_fallback(prompt_name)

    if not prompt:
        raise ValueError(f"Prompt '{prompt_name}' não encontrado no banco de dados.")

    # 2. Formatar se kwargs fornecidos
    if format_kwargs:
        try:
            return prompt.format(**format_kwargs)
        except KeyError as e:
            logger.error("Variável faltando no prompt", prompt_name=prompt_name, missing=str(e))
            # Tenta retornar parcial se possível ou limpo
            return prompt

    return prompt
