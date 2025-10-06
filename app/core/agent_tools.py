
import json
from pathlib import Path
from typing import List

from langchain.tools import tool, BaseTool
from pydantic import BaseModel, Field, validator

from app.core import filesystem_manager
from app.core.enums import AgentType  # <-- Corrigido
from app.core.memory_core import memory_core
from app.core.context_manager import context_manager
from app.db.graph import graph_db

WORKSPACE_ROOT = Path("/app/workspace").resolve()
ALLOWED_EXTENSIONS = {".txt", ".py", ".json", ".md", ".csv"}
MAX_FILE_SIZE = 1024 * 1024  # 1 MB


class WriteFileInput(BaseModel):
    file_path: str = Field(description="O caminho do arquivo, relativo ao workspace.")
    content: str = Field(description="O conteúdo a ser escrito no arquivo.")
    overwrite: bool = Field(default=False, description="Se deve sobrescrever o arquivo.")

    @validator("file_path")
    def validate_path_is_safe(cls, v: str) -> str:
        absolute_path = (WORKSPACE_ROOT / v).resolve()
        try:
            absolute_path.relative_to(WORKSPACE_ROOT)
            return v
        except ValueError:
            raise ValueError(f"Acesso negado. O caminho '{v}' está fora do diretório permitido.")

@tool(args_schema=WriteFileInput)
def write_file(file_path: str, content: str, overwrite: bool = False) -> str:
    """Escreve conteúdo em um arquivo dentro do workspace seguro."""
    try:
        target_path = (WORKSPACE_ROOT / file_path).resolve()
        target_path.relative_to(WORKSPACE_ROOT) # Re-valida para segurança

        if target_path.suffix not in ALLOWED_EXTENSIONS:
            return f"Erro: Extensão de arquivo não permitida. Permitidas: {', '.join(ALLOWED_EXTENSIONS)}"
        if len(content.encode("utf-8")) > MAX_FILE_SIZE:
            return f"Erro: Conteúdo excede o tamanho máximo de {MAX_FILE_SIZE} bytes."
        if target_path.exists() and not overwrite:
            return f"Erro: O arquivo '{file_path}' já existe. Use overwrite=True."

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        return f"Arquivo '{file_path}' salvo com sucesso."
    except ValueError as e:
        return f"Erro de validação: {e}"
    except Exception as e:
        return f"Erro inesperado: {e}"

# ... (outras ferramentas permanecem as mesmas) ...

@tool
def read_file(file_path: str) -> str:
    """Lê o conteúdo de um arquivo no projeto."""
    return filesystem_manager.read_file(file_path)

@tool
def list_directory(path: str = ".") -> str:
    """Lista arquivos e pastas no workspace."""
    return filesystem_manager.list_directory(path)

@tool
def recall_experiences(query: str) -> str:
    """Busca na memória por experiências passadas relevantes."""
    experiences = memory_core.recall(query=query, n_results=3)
    return json.dumps(experiences, indent=2, ensure_ascii=False)

@tool
def analyze_memory_for_failures(last_n_experiences: int = 20) -> str:
    """Examina as N experiências mais recentes para identificar padrões de falhas."""
    experiences = memory_core.recall(query="falha", n_results=last_n_experiences)
    failures = [exp for exp in experiences if exp.get("metadata", {}).get("type") == "action_failure"]
    if not failures:
        return "Análise concluída. Nenhuma falha significativa encontrada."
    summary = f"Análise de {len(failures)} falhas recentes:\n"
    for fail in failures:
        tool_used = fail.get("metadata", {}).get("tool_used", "N/A")
        error = fail.get("content", "Erro desconhecido")
        summary += f"- Ferramenta '{tool_used}' falhou com o erro: {error}\n"
    return summary

# --- Sprint 3: Ferramentas de Contexto Ambiental ---

@tool
def get_current_datetime() -> str:
    """Retorna a data e hora atual."""
    ctx = context_manager.get_current_context()
    return json.dumps(ctx.datetime_info, indent=2, ensure_ascii=False)

@tool
def get_system_info() -> str:
    """Retorna informações sobre o sistema operacional e ambiente."""
    ctx = context_manager.get_current_context()
    return json.dumps({
        "system": ctx.system_info,
        "environment": ctx.environment
    }, indent=2, ensure_ascii=False)

@tool
def search_web(query: str, max_results: int = 3) -> str:
    """
    Busca informações na web usando Tavily.
    Útil para obter informações atualizadas e contexto externo.
    """
    result = context_manager.search_web(query, max_results=max_results)
    return json.dumps(result.model_dump(), indent=2, ensure_ascii=False)

@tool
def get_enriched_context(query: str = "", include_web: bool = False) -> str:
    """
    Retorna contexto completo: data/hora, sistema e opcionalmente busca web.
    Use quando precisar de contexto ambiental completo para tomar decisões.
    """
    ctx = context_manager.get_enriched_context(
        query=query if query else None,
        include_web_search=include_web,
        max_web_results=3
    )
    return json.dumps(ctx, indent=2, ensure_ascii=False)

# --- Fábrica de Ferramentas ---

unified_tools: List[BaseTool] = [
    write_file,
    read_file,
    list_directory,
    recall_experiences,
    get_current_datetime,
    get_system_info,
    search_web,
    get_enriched_context
]

meta_agent_tools: List[BaseTool] = [
    analyze_memory_for_failures,
    recall_experiences,
    get_current_datetime
]

def get_tools_for_agent(agent_type: AgentType) -> List[BaseTool]:
    """Retorna a lista de ferramentas apropriada para o tipo de agente."""
    if agent_type == AgentType.META_AGENT:
        return meta_agent_tools
    return unified_tools
