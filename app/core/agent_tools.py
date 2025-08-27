# app/core/agent_tools.py
import json
from typing import List

from langchain.tools import tool, BaseTool
from pydantic import BaseModel, Field

from app.core import filesystem_manager
from app.core.memory_core import memory_core
from app.db.graph import graph_db


# --- Ferramentas do Sistema de Arquivos (Descrições Aprimoradas) ---

class WriteFileInput(BaseModel):
    file_path: str = Field(
        description="O nome do ficheiro a ser escrito. DEVE ser um caminho relativo dentro do workspace, por exemplo: 'meu_plano.txt'.")
    content: str = Field(description="O conteúdo a ser escrito no ficheiro.")


@tool(args_schema=WriteFileInput)
def write_file(file_path: str, content: str) -> str:
    """Use esta capacidade para escrever ou criar um ficheiro de texto no diretório 'workspace'."""
    return filesystem_manager.write_file(file_path, content)


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


# --- Lista de Ferramentas Unificada e Final ---
unified_tools: List[BaseTool] = [
    write_file,
    read_file,
    list_directory,
    recall_experiences,
    find_function_calls,
    find_file_of_function,
]
