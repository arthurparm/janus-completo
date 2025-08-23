# app/core/agent_tools.py
import json
from langchain.tools import tool
from pydantic import BaseModel, Field
from typing import Optional

from app.core import filesystem_manager
from app.core.memory_core import memory_core
from app.core import graph_rag_core

# --- Ferramentas do Sistema de Arquivos ---
class FilePathInput(BaseModel):
    file_path: str = Field(description="O caminho completo do arquivo a ser lido, a partir da raiz do projeto (ex: app/core/reasoning_core.py).")

class WriteFileInput(BaseModel):
    file_path: str = Field(description="O nome do arquivo a ser escrito DENTRO do workspace (ex: meu_arquivo.txt).")
    content: str = Field(description="O conteúdo a ser escrito no arquivo.")

class ListDirectoryInput(BaseModel):
    path: str = Field(default=".", description="O caminho do subdiretório DENTRO do workspace a ser listado.")

@tool(args_schema=FilePathInput)
def read_file(file_path: str) -> str:
    """Lê o conteúdo de qualquer arquivo dentro da base de código do projeto (/app)."""
    return filesystem_manager.read_file(file_path)

@tool(args_schema=WriteFileInput)
def write_file(file_path: str, content: str) -> str:
    """Cria ou sobrescreve um arquivo APENAS dentro do diretório seguro '/app/workspace'."""
    return filesystem_manager.write_file(file_path, content)

@tool(args_schema=ListDirectoryInput)
def list_directory(path: str = ".") -> str:
    """Lista o conteúdo de um diretório APENAS dentro do diretório seguro '/app/workspace'."""
    return filesystem_manager.list_directory(path)

# --- Ferramentas de Memória ---
class RecallInput(BaseModel):
    query: str = Field(description="A consulta em linguagem natural para buscar memórias relevantes.")

@tool(args_schema=RecallInput)
def recall_experiences(query: str) -> str:
    """
    Busca na memória episódica por experiências passadas relevantes para a consulta.
    """
    # Esta chamada agora funciona porque 'memory_core' é a instância correta.
    experiences = memory_core.recall(query=query, n_results=3)
    return json.dumps(experiences, indent=2, ensure_ascii=False)

@tool(args_schema=RecallInput)
def knowledge_graph_qa(query: str) -> str:
    """
    Responde a perguntas sobre a estrutura do código-fonte, funções, classes e suas relações.
    """
    return graph_rag_core.query_knowledge_graph(query)

# --- Lista de Ferramentas Unificada ---
unified_tools = [
    read_file,
    write_file,
    list_directory,
    recall_experiences,
    knowledge_graph_qa,
]