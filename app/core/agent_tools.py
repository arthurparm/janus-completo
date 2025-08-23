# app/core/agent_tools.py
from langchain.tools import tool
from pydantic import BaseModel, Field
from typing import Optional
from app.core import filesystem_manager

class FilePathInput(BaseModel):
    file_path: str = Field(description="O caminho relativo do arquivo dentro do workspace.")

class WriteFileInput(FilePathInput):
    content: str = Field(description="O conteúdo a ser escrito no arquivo.")

@tool(args_schema=FilePathInput)
def read_file(file_path: str) -> str:
    """
    Lê o conteúdo de um arquivo no workspace. Use esta ferramenta para examinar arquivos.
    """
    return filesystem_manager.read_file(file_path)

@tool(args_schema=WriteFileInput)
def write_file(file_path: str, content: str) -> str:
    """
    Escreve ou sobrescreve um arquivo no workspace com o conteúdo fornecido. Use esta ferramenta para criar ou modificar arquivos.
    """
    return filesystem_manager.write_file(file_path, content)

@tool
def list_directory(path: Optional[str] = ".") -> str:
    """
    Lista o conteúdo do diretório atual ou de um subdiretório no workspace.
    """
    return filesystem_manager.list_directory(path or ".")

# Agrupamos todas as ferramentas em uma lista para o agente.
file_system_tools = [read_file, write_file, list_directory]
