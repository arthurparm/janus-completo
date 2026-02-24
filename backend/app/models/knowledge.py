from pydantic import BaseModel, Field


class CodeEntity(BaseModel):
    """
    DTO para entidades de código presentes no grafo (funções e classes).
    """

    type: str = Field(..., description="Tipo da entidade (Function ou Class)")
    name: str = Field(..., description="Nome da entidade")
    file_path: str = Field(..., description="Caminho do arquivo onde a entidade está definida")
