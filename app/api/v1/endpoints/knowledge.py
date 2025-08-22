from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core import code_indexer
from app.db.graph import graph_db

router = APIRouter()


class IndexResponse(BaseModel):
    message: str
    files_indexed: int


class FileListResponse(BaseModel):
    files: List[str]


@router.post(
    "/index",
    response_model=IndexResponse,
    summary="Inicia a indexação da base de código",
    tags=["Knowledge Graph"]
)
def trigger_indexing():
    """
    Dispara o processo de varredura do código-fonte para popular o grafo de conhecimento.
    """
    try:
        result = code_indexer.index_codebase()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/files",
    response_model=FileListResponse,
    summary="Lista todos os arquivos indexados no grafo",
    tags=["Knowledge Graph"]
)
def get_indexed_files():
    """
    Consulta o grafo e retorna uma lista de todos os arquivos .py conhecidos.
    """
    try:
        query_result = graph_db.query("MATCH (f:File) RETURN f.path AS path ORDER BY path")
        # Extrai o caminho de cada registro
        file_paths = [record["path"] for record in query_result]
        return {"files": file_paths}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
