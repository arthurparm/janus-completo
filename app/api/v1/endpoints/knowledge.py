from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.memory import knowledge_graph_manager
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
async def trigger_consolidation():
    """
    Busca experiências da memória episódica e as transforma em conhecimento
    estruturado no grafo semântico.
    """
    try:
        result = await knowledge_graph_manager.aconsolidate_experiences_into_graph()
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


# ==================== SPRINT 8: Memória Semântica ====================

class KnowledgeQueryRequest(BaseModel):
    query: str
    limit: int = 10


class ConsolidateRequest(BaseModel):
    limit: int = 100
    batch_size: int = 10


class RelatedConceptsRequest(BaseModel):
    concept: str
    max_depth: int = 2


class EntityDetailsRequest(BaseModel):
    entity_name: str


@router.post("/query", summary="Consulta o grafo de conhecimento", tags=["Knowledge Graph - Sprint 8"])
async def query_knowledge_graph(request: KnowledgeQueryRequest):
    try:
        query_lower = request.query.lower()
        if "relacionado" in query_lower or "related" in query_lower:
            words = request.query.split()
            concept = words[-1].strip("?.")
            cypher = "MATCH (c:Concept {name: $concept})-[r]-(related) RETURN related.name as name, type(r) as relationship, labels(related)[0] as type LIMIT $limit"
            params = {"concept": concept, "limit": request.limit}
        elif "erro" in query_lower or "error" in query_lower:
            cypher = "MATCH (e:Error) RETURN e.name as name, e.description as description, e.timestamp as timestamp ORDER BY e.timestamp DESC LIMIT $limit"
            params = {"limit": request.limit}
        else:
            cypher = "MATCH (n) WHERE n.name IS NOT NULL RETURN labels(n)[0] as type, n.name as name LIMIT $limit"
            params = {"limit": request.limit}
        results = graph_db.query(cypher, params)
        return {"query": request.query, "results_count": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/concepts/related", summary="Busca conceitos relacionados", tags=["Knowledge Graph - Sprint 8"])
async def get_related_concepts(request: RelatedConceptsRequest):
    try:
        cypher = f"MATCH path = (c:Concept {{name: $concept}})-[*1..{request.max_depth}]-(related) WHERE related:Concept OR related:Tool OR related:Agent RETURN DISTINCT related.name as name, labels(related)[0] as type, length(path) as distance ORDER BY distance, name LIMIT 50"
        results = graph_db.query(cypher, {"concept": request.concept})
        return {"concept": request.concept, "max_depth": request.max_depth, "related_count": len(results),
                "related_concepts": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/entity/details", summary="Obtém detalhes de entidade", tags=["Knowledge Graph - Sprint 8"])
async def get_entity_details(request: EntityDetailsRequest):
    try:
        entity = graph_db.query(
            "MATCH (e) WHERE e.name = $entity_name RETURN labels(e)[0] as type, properties(e) as properties LIMIT 1",
            {"entity_name": request.entity_name})
        if not entity:
            raise HTTPException(status_code=404, detail=f"Entidade não encontrada")
        relationships = graph_db.query(
            "MATCH (e {name: $entity_name})-[r]-(related) RETURN type(r) as relationship, related.name as related_entity, labels(related)[0] as related_type LIMIT 20",
            {"entity_name": request.entity_name})
        return {"entity": entity[0], "relationships": relationships}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", summary="Estatísticas do grafo", tags=["Knowledge Graph - Sprint 8"])
async def get_knowledge_stats():
    try:
        node_stats = graph_db.query("MATCH (n) RETURN labels(n)[0] as type, count(n) as count ORDER BY count DESC", {})
        rel_stats = graph_db.query("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC", {})
        return {"total_nodes": sum(i["count"] for i in node_stats),
                "total_relationships": sum(i["count"] for i in rel_stats), "node_types": node_stats,
                "relationship_types": rel_stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/node-types", summary="Lista tipos de nós", tags=["Knowledge Graph - Sprint 8"])
async def get_node_types():
    try:
        types = graph_db.query("CALL db.labels() YIELD label RETURN label as type ORDER BY label", {})
        return {"node_types": [t["type"] for t in types], "count": len(types)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", summary="Health check", tags=["Knowledge Graph - Sprint 8"])
async def knowledge_health():
    try:
        graph_db.query("RETURN 1 as test", {})
        count_result = graph_db.query("MATCH (n) RETURN count(n) as total", {})
        return {"status": "healthy", "module": "knowledge_graph", "neo4j_connected": True,
                "total_nodes": count_result[0]["total"] if count_result else 0, "sprint": 8}
    except Exception as e:
        raise HTTPException(status_code=503, detail={"status": "unhealthy", "error": str(e)})
