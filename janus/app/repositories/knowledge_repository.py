import structlog
from typing import List, Dict, Any, Optional
from fastapi import Depends

from app.db.graph import GraphDatabase, get_graph_db
from app.services.code_analysis_service import CodeParser
from app.models.schemas import GraphLabel, GraphRelationship  # Importa os Enums

logger = structlog.get_logger(__name__)

class KnowledgeRepository:
    """
    Camada de Repositório para o Grafo de Conhecimento.
    Usa Enums para todas as constantes do grafo, evitando "magic strings".
    """
    def __init__(self, db: GraphDatabase):
        self._db = db

    async def get_node_and_relationship_stats(self) -> Dict[str, List]:
        node_stats_query = "MATCH (n) RETURN labels(n)[0] as type, count(n) as count ORDER BY count DESC"
        rel_stats_query = "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC"
        node_stats = await self._db.query(node_stats_query, operation="repo_get_node_stats")
        rel_stats = await self._db.query(rel_stats_query, operation="repo_get_rel_stats")
        return {"nodes": node_stats, "relationships": rel_stats}

    async def find_code_entities(self, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        if file_path:
            query = f"""MATCH (f:{GraphLabel.FILE.value} {{path: $file_path}})-[:{GraphRelationship.CONTAINS.value}]->(e)
                         WHERE e:{GraphLabel.FUNCTION.value} OR e:{GraphLabel.CLASS.value}
                         RETURN labels(e)[0] as type, e.name as name, e.file_path as file_path ORDER BY type, name"""
            params = {"file_path": file_path}
        else:
            query = f"""MATCH (e) WHERE e:{GraphLabel.FUNCTION.value} OR e:{GraphLabel.CLASS.value}
                         RETURN labels(e)[0] as type, e.name as name, e.file_path as file_path ORDER BY file_path, type, name"""
            params = {}
        return await self._db.query(query, params, operation="repo_find_code_entities")

    async def find_entity_details(self, entity_name: str) -> Optional[Dict[str, Any]]:
        entity_query = "MATCH (e) WHERE e.name = $name RETURN labels(e)[0] as type, properties(e) as properties LIMIT 1"
        entity = await self._db.query(entity_query, {"name": entity_name}, operation="repo_find_entity_properties")
        if not entity:
            return None
        relationships_query = "MATCH (e {name: $name})-[r]-(related) RETURN type(r) as relationship, related.name as related_entity, labels(related)[0] as related_type LIMIT 20"
        relationships = await self._db.query(relationships_query, {"name": entity_name},
                                             operation="repo_find_entity_relationships")
        return {"entity": entity[0], "relationships": relationships}

    async def save_code_structure(self, parser: CodeParser):
        logger.debug("Salvando estrutura de código no repositório", file_path=parser.file_path)
        async with await self._db.get_session() as session:
            tx = await session.begin_transaction()
            try:
                file_label = f"{GraphLabel.FILE.value}:{GraphLabel.CODE_FILE.value}"
                func_label = f"{GraphLabel.FUNCTION.value}:{GraphLabel.CODE_FUNCTION.value}"
                cls_label = f"{GraphLabel.CLASS.value}:{GraphLabel.CODE_CLASS.value}"

                file_id = await self._db.merge_node(tx, label=file_label, name=parser.file_path)
                for func in parser.functions:
                    func_name_with_path = f"{parser.file_path}::{func['name']}"
                    func_id = await self._db.merge_node(tx, label=func_label, name=func_name_with_path)
                    await self._db.merge_relationship(tx, source_id=file_id, target_id=func_id,
                                                      rel_type=GraphRelationship.CONTAINS.value)
                for cls in parser.classes:
                    cls_name_with_path = f"{parser.file_path}::{cls['name']}"
                    cls_id = await self._db.merge_node(tx, label=cls_label, name=cls_name_with_path)
                    await self._db.merge_relationship(tx, source_id=file_id, target_id=cls_id,
                                                      rel_type=GraphRelationship.CONTAINS.value)
                await tx.commit()
            finally:
                await tx.close()

    async def clear_all_data(self) -> int:
        await self._db.execute("MATCH (n) DETACH DELETE n", operation="repo_clear_graph")
        count_result = await self._db.query("MATCH (n) RETURN count(n) as total", operation="repo_count_after_clear")
        return count_result[0]["total"] if count_result else 0

    async def clear_code_entities(self):
        query = f"MATCH (n) WHERE n:{GraphLabel.CODE_FUNCTION.value} OR n:{GraphLabel.CODE_CLASS.value} OR n:{GraphLabel.CODE_FILE.value} DETACH DELETE n"
        await self._db.execute(query, operation="repo_cleanup_code")

    async def bulk_merge_calls(self, calls: List[Dict[str, Any]]):
        if not calls:
            return
        query = f"""UNWIND $calls as call
                     MATCH (caller:{GraphLabel.FUNCTION.value} {{name: call.file_path + '::' + call.caller_name}})
                     MATCH (callee:{GraphLabel.FUNCTION.value} {{name: call.callee_name}})
                     MERGE (caller)-[r:{GraphRelationship.CALLS.value}]->(callee)"""
        await self._db.execute(query, {"calls": calls}, operation="repo_bulk_merge_calls")

    # --- Sprint 8: Consultas semânticas ---

    async def find_related_concepts(self, concept: str, max_depth: int = 2, limit: int = 10, skip: int = 0) -> List[Dict[str, Any]]:
        # Usa label Concept para navegar por conceitos relacionados
        query = f"""
        MATCH path = (c:{GraphLabel.CONCEPT.value} {{name: $concept}})-[*1..{max_depth}]-(related)
        RETURN related.name as concept,
               type(last(relationships(path))) as relationship,
               length(path) as distance
        ORDER BY distance
        SKIP $skip
        LIMIT $limit
        """
        params = {"concept": concept, "limit": limit, "skip": skip}
        return await self._db.query(query, params, operation="repo_find_related_concepts")

    async def find_entity_relationships(self, entity_name: str, rel_type: Optional[str] = None, direction: str = "both", max_depth: int = 1, limit: int = 20, skip: int = 0) -> List[Dict[str, Any]]:
        # Navega relacionamentos a partir de uma entidade com direção e profundidade configuráveis
        # direction: "out" (saída), "in" (entrada), "both" (ambas)
        if direction not in ("out", "in", "both"):
            direction = "both"
        if direction == "out":
            path = f"(e {{name: $name}})-[r*1..{max_depth}]->(related)"
        elif direction == "in":
            path = f"(e {{name: $name}})<-[r*1..{max_depth}]-(related)"
        else:
            path = f"(e {{name: $name}})-[r*1..{max_depth}]-(related)"

        query = f"""
        MATCH path = {path}
        WHERE $rel_type IS NULL OR type(last(relationships(path))) = $rel_type
        RETURN related.name as related_entity,
               labels(related)[0] as related_type,
               type(last(relationships(path))) as relationship,
               length(path) as distance
        SKIP $skip
        LIMIT $limit
        """
        params = {"name": entity_name, "rel_type": rel_type, "skip": skip, "limit": limit}
        return await self._db.query(query, params, operation="repo_find_entity_relationships_nav")

    async def get_node_types(self) -> List[str]:
        # Lista todos os labels distintos presentes no grafo
        query = """
        MATCH (n)
        UNWIND labels(n) AS label
        RETURN DISTINCT label AS type
        ORDER BY type
        """
        rows = await self._db.query(query, operation="repo_get_node_types")
        return [row.get("type", "") for row in rows]

    async def find_functions_calling(self, function_name: str) -> List[Dict[str, Any]]:
        query = f"""
        MATCH (t) WHERE t.name = $name AND (t:{GraphLabel.FUNCTION.value} OR t:{GraphLabel.CODE_FUNCTION.value})
        MATCH (f)-[:{GraphRelationship.CALLS.value}]->(t)
        RETURN labels(f)[0] as type, f.name as name, coalesce(f.file_path, f.path, '') as file_path
        ORDER BY name
        """
        params = {"name": function_name}
        return await self._db.query(query, params, operation="repo_find_functions_calling")

    async def find_files_importing(self, module: str) -> List[Dict[str, Any]]:
        query = f"""
        MATCH (f) WHERE (f:{GraphLabel.CODE_FILE.value} OR f:{GraphLabel.FILE.value})
        MATCH (f)-[:{GraphRelationship.IMPORTS.value}]->(m)
        WHERE m.name = $module OR m.path = $module
        RETURN labels(f)[0] as type, coalesce(f.name, '') as name, coalesce(f.file_path, f.path, '') as file_path
        ORDER BY file_path
        """
        params = {"module": module}
        return await self._db.query(query, params, operation="repo_find_files_importing")

    async def find_classes_implementing(self, protocol: str) -> List[Dict[str, Any]]:
        query = f"""
        MATCH (p {{name: $protocol}})
        MATCH (c)-[:{GraphRelationship.IMPLEMENTS.value}]->(p)
        WHERE (c:{GraphLabel.CLASS.value} OR c:{GraphLabel.CODE_CLASS.value})
        RETURN labels(c)[0] as type, c.name as name, coalesce(c.file_path, '') as file_path
        ORDER BY name
        """
        params = {"protocol": protocol}
        return await self._db.query(query, params, operation="repo_find_classes_implementing")

    async def find_entity_relationships(self, entity_name: str, rel_type: Optional[str] = None, direction: str = "both",
                                        max_depth: int = 1, limit: int = 20, skip: int = 0) -> List[Dict[str, Any]]:
        # Navega relacionamentos a partir de uma entidade com direção e profundidade configuráveis
        # direction: "out" (saída), "in" (entrada), "both" (ambas)
        if direction not in ("out", "in", "both"):
            direction = "both"
        if direction == "out":
            path = f"(e {{name: $name}})-[r*1..{max_depth}]->(related)"
        elif direction == "in":
            path = f"(e {{name: $name}})<-[r*1..{max_depth}]-(related)"
        else:
            path = f"(e {{name: $name}})-[r*1..{max_depth}]-(related)"

        query = f"""
        MATCH path = {path}
        WHERE $rel_type IS NULL OR type(last(relationships(path))) = $rel_type
        RETURN related.name as related_entity,
               labels(related)[0] as related_type,
               type(last(relationships(path))) as relationship,
               length(path) as distance
        SKIP $skip
        LIMIT $limit
        """
        params = {"name": entity_name, "rel_type": rel_type, "skip": skip, "limit": limit}
        return await self._db.query(query, params, operation="repo_find_entity_relationships_nav")

    async def get_node_types(self) -> List[str]:
        # Lista todos os labels distintos presentes no grafo
        query = """
        MATCH (n)
        UNWIND labels(n) AS label
        RETURN DISTINCT label AS type
        ORDER BY type
        """
        rows = await self._db.query(query, operation="repo_get_node_types")
        return [row.get("type", "") for row in rows]

# Padrão de Injeção de Dependência: Getter para o repositório
def get_knowledge_repository(db: GraphDatabase = Depends(get_graph_db)) -> "KnowledgeRepository":
    return KnowledgeRepository(db)
