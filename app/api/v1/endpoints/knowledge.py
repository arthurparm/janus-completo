
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core import knowledge_graph_manager
from app.db.graph import graph_db

router = APIRouter()


class IndexResponse(BaseModel):
    message: str
    summary: str


class CodeEntity(BaseModel):
    type: str
    name: str
    file_path: str


class CallRelationship(BaseModel):
    caller_function: str
    caller_file: str
    callee_function: str


@router.post(
    "/index",
    response_model=IndexResponse,
    summary="Inicia a indexação e análise da base de código",
    tags=["Knowledge Graph"]
)
def trigger_indexing():
    """
    Dispara o processo de varredura do código-fonte para popular o grafo com
    entidades de código como Funções e Classes.
    """
    try:
        result = knowledge_graph_manager.index_codebase()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/consolidate",
    response_model=IndexResponse,
    summary="Inicia a consolidação de experiências no grafo de conhecimento",
    tags=["Knowledge Graph"]
)
def trigger_consolidation():
    """
    Busca experiências da memória episódica e as transforma em conhecimento
    estruturado no grafo semântico.
    """
    try:
        result = knowledge_graph_manager.consolidate_experiences_into_graph()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/entities",
    response_model=List[CodeEntity],
    summary="Lista entidades de código (funções, classes)",
    tags=["Knowledge Graph"]
)
def get_code_entities(file_path: Optional[str] = Query(None, description="Filtra entidades por caminho de arquivo.")):
    """
    Consulta o grafo por nós de Função ou Classe.
    Pode ser filtrado por um caminho de arquivo específico.
    """
    try:
        if file_path:
            query = """
                MATCH (f:File {path: $file_path})-[:CONTAINS]->(e)
                WHERE e:Function OR e:Class
                RETURN labels(e)[0] as type, e.name as name, e.file_path as file_path
                ORDER BY type, name
            """
            params = {"file_path": file_path}
        else:
            query = """
                MATCH (e) WHERE e:Function OR e:Class
                RETURN labels(e)[0] as type, e.name as name, e.file_path as file_path
                ORDER BY file_path, type, name
            """
            params = {}

        return graph_db.query(query, params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/calls",
    response_model=List[CallRelationship],
    summary="Lista relações de chamadas de função",
    tags=["Knowledge Graph"]
)
def get_function_calls(
        function_name: Optional[str] = Query(None, description="Filtra chamadas feitas por uma função específica.")):
    """
    Consulta o grafo por relações :CALLS entre Funções.
    Pode ser filtrado pelo nome da função chamadora.
    """
    try:
        if function_name:
            query = """
                MATCH (caller:Function {name: $function_name})-[r:CALLS]->(callee:Function)
                RETURN caller.name as caller_function, caller.file_path as caller_file, callee.name as callee_function
                ORDER BY callee_function
            """
            params = {"function_name": function_name}
        else:
            query = """
                MATCH (caller:Function)-[r:CALLS]->(callee:Function)
                RETURN caller.name as caller_function, caller.file_path as caller_file, callee.name as callee_function
                ORDER BY caller_function, callee_function
            """
            params = {}

        return graph_db.query(query, params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
