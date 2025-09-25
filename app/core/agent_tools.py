# app/core/agent_tools.py

import json
from pathlib import Path
from typing import List

from langchain.tools import tool, BaseTool
from pydantic import BaseModel, Field, validator

from app.core import filesystem_manager
from app.core.memory_core import memory_core
from app.db.graph import graph_db

# --- Ferramentas do Sistema de Arquivos (Descrições Aprimoradas) ---

WORKSPACE_ROOT = Path("/app/workspace").resolve()
ALLOWED_EXTENSIONS = {".txt", ".py", ".json", ".md", ".csv"}
MAX_FILE_SIZE = 1024 * 1024  # 1 MB


class WriteFileInput(BaseModel):
    file_path: str = Field(
        description="O caminho do arquivo, relativo ao workspace (ex: 'meu_plano.txt')."
    )
    content: str = Field(description="O conteúdo a ser escrito no arquivo.")
    overwrite: bool = Field(default=False, description="Se deve sobrescrever o arquivo caso já exista.")
    dry_run: bool = Field(default=False, description="Se True, simula a operação sem escrever no disco.")

    # --- MELHORIA: VALIDAÇÃO DE SEGURANÇA NO MODELO PYDANTIC ---
    @validator("file_path")
    def validate_path_is_safe(cls, v: str) -> str:
        if not v:
            raise ValueError("O caminho do arquivo não pode ser vazio.")

        # Constrói o caminho absoluto e resolve (remove '..')
        absolute_path = (WORKSPACE_ROOT / v).resolve()

        # Verifica se o caminho final ainda está dentro do diretório seguro usando relative_to
        try:
            absolute_path.relative_to(WORKSPACE_ROOT)
        except ValueError:
            raise ValueError(f"Acesso negado. O caminho '{v}' está fora do diretório permitido.")

        return v  # Retorna o caminho original relativo se for válido


@tool(args_schema=WriteFileInput)
def write_file(
        file_path: str,
        content: str,
        overwrite: bool = False,
        dry_run: bool = False,
) -> str:
    """
    Escreve conteúdo em um arquivo dentro de um diretório seguro (workspace).
    Valida o caminho do arquivo, a extensão e o tamanho do conteúdo.
    """
    try:
        # A validação principal já foi feita pelo Pydantic via args_schema
        target_path = (WORKSPACE_ROOT / file_path).resolve()

        # Garante que o caminho está dentro do workspace
        try:
            target_path.relative_to(WORKSPACE_ROOT)
        except ValueError:
            return f"Erro de validação: Acesso negado. O caminho '{file_path}' está fora do diretório permitido."

        if target_path.suffix not in ALLOWED_EXTENSIONS:
            return f"Erro: Extensão de arquivo não permitida. Permitidas: {', '.join(sorted(ALLOWED_EXTENSIONS))}"

        if len(content.encode("utf-8")) > MAX_FILE_SIZE:
            return f"Erro: O conteúdo do arquivo excede o tamanho máximo de {MAX_FILE_SIZE} bytes."

        if target_path.exists() and not overwrite:
            return f"Erro: O arquivo '{file_path}' já existe. Use overwrite=True para sobrescrevê-lo."

        if dry_run:
            return f"DRY RUN: O arquivo '{file_path}' seria escrito com sucesso em '{target_path}'."

        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"Arquivo '{file_path}' salvo com sucesso."
    except ValueError as e:  # Captura erros de validação do Pydantic
        return f"Erro de validação: {e}"
    except Exception as e:
        return f"Erro inesperado ao salvar o arquivo: {e}"


class ReadFileInput(BaseModel):
    file_path: str = Field(
        description="O caminho do ficheiro a ser lido, a partir da raiz do projeto, por exemplo: 'app/main.py' ou 'workspace/meu_plano.txt'.")


@tool(args_schema=ReadFileInput)
def read_file(file_path: str) -> str:
    """Use esta capacidade para ler o conteúdo de QUALQUER ficheiro dentro do projeto. A ferramenta lida com a resolução de caminhos de forma segura."""
    return filesystem_manager.read_file(file_path)


class ListDirectoryInput(BaseModel):
    path: str = Field(default=".",
                      description="O subdiretório DENTRO do 'workspace' a ser listado. Use '.' para a raiz do workspace.")


@tool(args_schema=ListDirectoryInput)
def list_directory(path: str = ".") -> str:
    """Use esta capacidade para listar ficheiros e pastas dentro do 'workspace'."""
    return filesystem_manager.list_directory(path)


# --- Ferramentas de Memória ---

class RecallInput(BaseModel):
    query: str = Field(description="A pergunta em linguagem natural para buscar memórias relevantes.")


@tool(args_schema=RecallInput)
def recall_experiences(query: str) -> str:
    """Busca na memória episódica por experiências passadas relevantes para uma tarefa atual."""
    experiences = memory_core.recall(query=query, n_results=3)
    return json.dumps(experiences, indent=2, ensure_ascii=False)


# --- NOVAS Ferramentas do Grafo de Conhecimento (Especializadas) ---

class FunctionInput(BaseModel):
    function_name: str = Field(description="O nome exato da função a ser procurada.")


@tool(args_schema=FunctionInput)
def find_function_calls(function_name: str) -> str:
    """Use esta capacidade para descobrir quais outras funções uma função específica chama diretamente."""
    query = """
        MATCH (caller:Function {name: $function_name})-[:CALLS]->(callee:Function)
        RETURN caller.name as caller_function, callee.name as callee_function
    """
    results = graph_db.query(query, params={"function_name": function_name})
    return json.dumps(results) if results else f"Nenhuma chamada encontrada para a função '{function_name}'."


@tool(args_schema=FunctionInput)
def find_file_of_function(function_name: str) -> str:
    """Use esta capacidade para encontrar em qual ficheiro uma função específica está definida."""
    query = """
        MATCH (f:File)-[:CONTAINS]->(func:Function {name: $function_name})
        RETURN f.path as file_path
    """
    results = graph_db.query(query, params={"function_name": function_name})
    return json.dumps(results) if results else f"Função '{function_name}' não encontrada no grafo."


class AnalyzeMemoryInput(BaseModel):
    last_n_experiences: int = Field(default=20, description="O número de experiências recentes a serem analisadas.")


@tool(args_schema=AnalyzeMemoryInput)
def analyze_memory_for_failures(last_n_experiences: int) -> str:
    """
    Examina as N experiências mais recentes na memória episódica para identificar e resumir padrões de falhas.
    Esta ferramenta é essencial para a auto-otimização do sistema.
    """
    # logger not available here; keep simple prints or rely on memory_core logs
    experiences = memory_core.recall(query="falha de ação do agente", n_results=last_n_experiences)
    failures = [
        exp for exp in experiences
        if exp.get("metadata", {}).get("type") == "action_failure"
    ]
    if not failures:
        return "Análise concluída. Nenhuma falha de ação significativa foi encontrada nas experiências recentes."
    summary = f"Análise concluída. Foram encontradas {len(failures)} falhas nas últimas {last_n_experiences} experiências:\n"
    for fail in failures:
        tool_used = fail.get("metadata", {}).get("tool_used", "N/A")
        error_observation = fail.get("content", "Erro desconhecido").split("O resultado foi: '")[-1].replace("'", "")
        summary += f"- Ferramenta '{tool_used}' falhou com o erro: {error_observation}\n"
    return summary


# --- Lista de Ferramentas Unificada e Final ---
unified_tools: List[BaseTool] = [
    write_file,
    read_file,
    list_directory,
    recall_experiences,
    find_function_calls,
    find_file_of_function,
]
