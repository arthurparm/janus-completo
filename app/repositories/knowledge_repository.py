import structlog
from typing import List, Dict, Any, Optional

from app.db.graph import graph_db
from app.services.code_analysis_service import CodeParser  # Importar para type hint

logger = structlog.get_logger(__name__)


class KnowledgeRepository:
    """
    Camada de Repositório para o Grafo de Conhecimento.
    Abstrai todas as queries Cypher e interações diretas com o `graph_db`.
    """

    async def get_node_and_relationship_stats(self) -> Dict[str, List]:
        logger.info("Buscando estatísticas de nós e relacionamentos no repositório.")
        node_stats_query = "MATCH (n) RETURN labels(n)[0] as type, count(n) as count ORDER BY count DESC"
        rel_stats_query = "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC"

        node_stats = await graph_db.query(node_stats_query, operation="repo_get_node_stats")
        rel_stats = await graph_db.query(rel_stats_query, operation="repo_get_rel_stats")
        return {"nodes": node_stats, "relationships": rel_stats}

    async def find_code_entities(self, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        logger.info("Buscando entidades de código no repositório", file_path=file_path)
        if file_path:
            query = "MATCH (f:File {path: $file_path})-[:CONTAINS]->(e) WHERE e:Function OR e:Class RETURN labels(e)[0] as type, e.name as name, e.file_path as file_path ORDER BY type, name"
            params = {"file_path": file_path}
        else:
            query = "MATCH (e) WHERE e:Function OR e:Class RETURN labels(e)[0] as type, e.name as name, e.file_path as file_path ORDER BY file_path, type, name"
            params = {}
        return await graph_db.query(query, params, operation="repo_find_code_entities")

    async def find_function_calls(self, function_name: Optional[str] = None) -> List[Dict[str, Any]]:
        logger.info("Buscando chamadas de função no repositório", function_name=function_name)
        if function_name:
            query = "MATCH (caller:Function {name: $function_name})-[r:CALLS]->(callee:Function) RETURN caller.name as caller_function, caller.file_path as caller_file, callee.name as callee_function ORDER BY callee_function"
            params = {"function_name": function_name}
        else:
            query = "MATCH (caller:Function)-[r:CALLS]->(callee:Function) RETURN caller.name as caller_function, caller.file_path as caller_file, callee.name as callee_function ORDER BY caller_function, callee_function"
            params = {}
        return await graph_db.query(query, params, operation="repo_find_function_calls")

    async def find_entity_details(self, entity_name: str) -> Optional[Dict[str, Any]]:
        logger.info("Buscando detalhes de entidade no repositório", entity_name=entity_name)
        entity_query = "MATCH (e) WHERE e.name = $name RETURN labels(e)[0] as type, properties(e) as properties LIMIT 1"
        entity = await graph_db.query(entity_query, {"name": entity_name}, operation="repo_find_entity_properties")
        if not entity:
            return None

        relationships_query = "MATCH (e {name: $name})-[r]-(related) RETURN type(r) as relationship, related.name as related_entity, labels(related)[0] as related_type LIMIT 20"
        relationships = await graph_db.query(relationships_query, {"name": entity_name},
                                             operation="repo_find_entity_relationships")
        return {"entity": entity[0], "relationships": relationships}

    async def save_code_structure(self, parser: CodeParser):
        """Salva a estrutura de código (arquivo, funções, classes) de um parser em uma única transação."""
        logger.debug("Salvando estrutura de código no repositório", file_path=parser.file_path)
        driver = await graph_db.get_driver()
        async with driver.session() as session:
            async with session.begin_transaction() as tx:
                file_id = await graph_db.merge_node(tx, label="File:CodeFile", name=parser.file_path)
                for func in parser.functions:
                    # Adiciona file_path ao nome para desambiguação
                    func_name_with_path = f"{parser.file_path}::{func['name']}"
                    func_id = await graph_db.merge_node(tx, label="Function:CodeFunction", name=func_name_with_path)
                    await graph_db.merge_relationship(tx, source_id=file_id, target_id=func_id, rel_type="CONTAINS")
                for cls in parser.classes:
                    cls_name_with_path = f"{parser.file_path}::{cls['name']}"
                    cls_id = await graph_db.merge_node(tx, label="Class:CodeClass", name=cls_name_with_path)
                    await graph_db.merge_relationship(tx, source_id=file_id, target_id=cls_id, rel_type="CONTAINS")

    async def clear_all_data(self) -> int:
        logger.warning("Limpando todos os dados do grafo via repositório.")
        await graph_db.execute("MATCH (n) DETACH DELETE n", operation="repo_clear_graph")
        count_result = await graph_db.query("MATCH (n) RETURN count(n) as total", operation="repo_count_after_clear")
        return count_result[0]["total"] if count_result else 0

    async def clear_code_entities(self):
        logger.info("Limpando entidades de código do grafo via repositório.")
        await graph_db.execute("MATCH (n) WHERE n:CodeFunction OR n:CodeClass OR n:CodeFile DETACH DELETE n",
                               operation="repo_cleanup_code")

    async def bulk_merge_calls(self, calls: List[Dict[str, Any]]):
        logger.info(f"Mesclando {len(calls)} chamadas de função em massa via repositório.")
        if not calls:
            return
        # Query atualizada para usar nomes desambiguados
        query = """
        UNWIND $calls as call
        MATCH (caller:Function {name: call.file_path + '::' + call.caller_name})
        MATCH (callee:Function {name: call.callee_name}) // Callee pode ser de outro arquivo, busca global
        MERGE (caller)-[r:CALLS]->(callee)
        """
        await graph_db.execute(query, {"calls": calls}, operation="repo_bulk_merge_calls")


# Instância única do repositório
knowledge_repository = KnowledgeRepository()
