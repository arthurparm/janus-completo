# app/core/agent_tools.py
import json
from langchain.tools import tool
from pydantic import BaseModel, Field
from typing import Optional

from app.core import filesystem_manager
from app.core import memory_core
from app.core import graph_rag_core

# --- Ferramentas do Sistema de Arquivos ---
class FilePathInput(BaseModel):
    file_path: str = Field(description="O caminho relativo do arquivo dentro do workspace.")

class WriteFileInput(FilePathInput):
    content: str = Field(description="O conteúdo a ser escrito no arquivo.")

@tool(args_schema=FilePathInput)
def read_file(file_path: str) -> str:
    """Lê o conteúdo de um arquivo no workspace."""
    return filesystem_manager.read_file(file_path)

@tool(args_schema=WriteFileInput)
def write_file(file_path: str, content: str) -> str:
    """Escreve ou sobrescreve um arquivo no workspace."""
    return filesystem_manager.write_file(file_path, content)

@tool
def list_directory(path: Optional[str] = ".") -> str:
    """Lista o conteúdo de um diretório no workspace."""
    return filesystem_manager.list_directory(path or ".")

# --- Ferramentas de Memória ---
class RecallInput(BaseModel):
    query: str = Field(description="A consulta em linguagem natural para buscar memórias relevantes.")

@tool(args_schema=RecallInput)
def recall_experiences(query: str) -> str:
    """
    Busca na memória episódica por experiências passadas relevantes para a consulta.
    Útil para lembrar de ações ou observações anteriores.
    """
    experiences = memory_core.memory_core.recall(query=query, n_results=3)
    return json.dumps(experiences, indent=2)

@tool(args_schema=RecallInput)
def knowledge_graph_qa(query: str) -> str:
    """
    Responde a perguntas sobre a estrutura do código-fonte, funções, classes e suas relações.
    Use esta ferramenta para entender como o código funciona.
    """
    return graph_rag_core.query_knowledge_graph(query)

# --- Listas de Ferramentas ---
# Mantemos a lista antiga por compatibilidade
file_system_tools = [read_file, write_file, list_directory]

# Lista unificada para o agente
unified_tools = [
    read_file,
    write_file,
    list_directory,
    recall_experiences,
    knowledge_graph_qa,
]
