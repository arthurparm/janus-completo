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
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

# Cache de prompts carregados de arquivo
_file_prompts_cache: dict[str, str] = {}


def _load_prompt_from_file(prompt_name: str) -> str | None:
    """Carrega um prompt de arquivo .txt se existir."""
    if prompt_name in _file_prompts_cache:
        return _file_prompts_cache[prompt_name]

    file_path = PROMPTS_DIR / f"{prompt_name}.txt"
    if file_path.exists():
        try:
            content = file_path.read_text(encoding="utf-8")
            _file_prompts_cache[prompt_name] = content
            logger.info("Prompt carregado de arquivo", prompt_name=prompt_name, chars=len(content))
            return content
        except Exception as e:
            logger.error(
                "Erro ao carregar prompt de arquivo", prompt_name=prompt_name, error=str(e)
            )

    return None


def get_prompt_with_fallback(prompt_name: str, **kwargs) -> str:
    """
    Carrega prompt com fallback hierárquico:
    1. Banco de dados (via prompt_loader.get_prompt)
    2. Arquivo .txt em /prompts/
    3. Constante hardcoded (se existir)
    """
    from app.core.infrastructure.prompt_loader import get_prompt

    # 1. Tentar banco de dados primeiro
    try:
        db_prompt = get_prompt(prompt_name, **kwargs)
        if db_prompt and not db_prompt.startswith("Prompt não encontrado"):
            return db_prompt
    except Exception as e:
        logger.warning("Falha ao buscar prompt do DB", prompt_name=prompt_name, error=str(e))

    # 2. Tentar arquivo
    file_prompt = _load_prompt_from_file(prompt_name)
    if file_prompt:
        return file_prompt

    # 3. Retornar None para usar constante hardcoded como fallback final
    logger.warning("Prompt não encontrado em DB ou arquivo", prompt_name=prompt_name)
    return None


# Mapeamento de nomes de prompt para variáveis hardcoded (fallback final)
# Se o nome não estiver aqui, assume-se o nome em UPPERCASE no módulo de prompts
HARDCODED_PROMPTS = {
    "tool_specification": "TOOL_SPECIFICATION_PROMPT",
    "tool_generation": "TOOL_GENERATION_PROMPT",
    "tool_validation": "tool_validation_prompt",
    "semantic_commit": "SEMANTIC_COMMIT_PROMPT",
    "hyde_generation": "HYDE_PROMPT",
    "rerank": "RERANK_PROMPT",
    "knowledge_extraction": "EXTRACTION_PROMPT",
    "meta_agent": "META_AGENT_PROMPT",
}


def get_formatted_prompt(prompt_name: str, **format_kwargs) -> str:
    """
    Carrega prompt com fallback completo e formatação opcional.

    Args:
        prompt_name: Nome do prompt (ex: semantic_commit, task_decomposition)
        **format_kwargs: Variáveis para formatar no prompt

    Returns:
        Prompt formatado pronto para uso
    """
    # 1. Tentar DB ou arquivo (via get_prompt_with_fallback)
    prompt = get_prompt_with_fallback(prompt_name)

    # 2. Fallback para hardcoded se não encontrado acima
    if not prompt:
        # Tenta carregar dos módulos conhecidos de prompts
        from app.core.evolution import prompts as evo_prompts
        from app.core.infrastructure import prompt_loader as loader_defaults

        var_name = HARDCODED_PROMPTS.get(prompt_name)

        # Tenta em ordem de prioridade nos módulos
        if var_name:
            prompt = getattr(evo_prompts, var_name, None)
            if not prompt:
                # Tenta no loader_defaults.PROMPTS se existir
                prompt = loader_defaults.PROMPTS.get(prompt_name)
        else:
            # Tenta o nome em UPPERCASE
            prompt = getattr(evo_prompts, prompt_name.upper(), None)

        if prompt:
            logger.debug("Usando prompt hardcoded como fallback final", prompt_name=prompt_name)

    if not prompt:
        raise ValueError(
            f"Prompt '{prompt_name}' não encontrado em nenhuma fonte (DB, Arquivo ou Memória)"
        )

    # 3. Formatar se kwargs fornecidos
    if format_kwargs:
        try:
            return prompt.format(**format_kwargs)
        except KeyError as e:
            logger.error("Variável faltando no prompt", prompt_name=prompt_name, missing=str(e))
            # Tenta retornar parcial se possível ou limpo
            return prompt

    return prompt
