from typing import Any

import structlog
from fastapi import Depends

from app.db.graph import GraphDatabase, get_graph_db
from app.models.schemas import GraphLabel, GraphRelationship  # Importa os Enums
from app.repositories.observability_repository import record_audit_event_direct
from app.services.code_analysis_service import CodeParser

logger = structlog.get_logger(__name__)


class KnowledgeRepository:
    """
    Camada de RepositÃ³rio para o Grafo de Conhecimento.
    Usa Enums para todas as constantes do grafo, evitando "magic strings".
    """

    def __init__(self, db: GraphDatabase):
        self._db = db

    async def get_node_and_relationship_stats(self) -> dict[str, list]:
        node_stats_query = (
            "MATCH (n) RETURN labels(n)[0] as type, count(n) as count ORDER BY count DESC"
        )
        rel_stats_query = (
            "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC"
        )
        node_stats = await self._db.query(node_stats_query, operation="repo_get_node_stats")
        rel_stats = await self._db.query(rel_stats_query, operation="repo_get_rel_stats")
        return {"nodes": node_stats, "relationships": rel_stats}

    async def find_code_entities(self, file_path: str | None = None) -> list[dict[str, Any]]:
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

    async def find_entity_details(self, entity_name: str) -> dict[str, Any] | None:
        entity_query = "MATCH (e) WHERE e.name = $name RETURN labels(e)[0] as type, properties(e) as properties LIMIT 1"
        entity = await self._db.query(
            entity_query, {"name": entity_name}, operation="repo_find_entity_properties"
        )
        if not entity:
            return None
        relationships_query = "MATCH (e {name: $name})-[r]-(related) RETURN type(r) as relationship, related.name as related_entity, labels(related)[0] as related_type LIMIT 20"
        relationships = await self._db.query(
            relationships_query, {"name": entity_name}, operation="repo_find_entity_relationships"
        )
        return {"entity": entity[0], "relationships": relationships}

    async def save_code_structure(self, parser: CodeParser):
        logger.debug("Salvando estrutura de código no repositório", file_path=parser.file_path)
        async with await self._db.get_session() as session:
            tx = await session.begin_transaction()
            try:
                file_label = f"{GraphLabel.FILE.value}:{GraphLabel.CODE_FILE.value}"
                func_label = f"{GraphLabel.FUNCTION.value}:{GraphLabel.CODE_FUNCTION.value}"
                cls_label = f"{GraphLabel.CLASS.value}:{GraphLabel.CODE_CLASS.value}"

                file_props = {
                    "name": parser.file_path,
                    "path": parser.file_path,
                    "file_path": parser.file_path,
                }
                file_id = await self._db.merge_node(
                    tx,
                    label=file_label,
                    name=parser.file_path,
                    properties=file_props,
                    merge_keys=["path"],
                )
                for func in parser.functions:
                    func_name = func["name"]
                    func_props = {
                        "name": func_name,
                        "file_path": parser.file_path,
                        "full_name": f"{parser.file_path}::{func_name}",
                        "line": func.get("line"),
                    }
                    func_id = await self._db.merge_node(
                        tx,
                        label=func_label,
                        name=func_name,
                        properties=func_props,
                        merge_keys=["name", "file_path"],
                    )
                    await self._db.merge_relationship(
                        tx,
                        source_id=file_id,
                        target_id=func_id,
                        rel_type=GraphRelationship.CONTAINS.value,
                    )
                for cls in parser.classes:
                    cls_name = cls["name"]
                    cls_props = {
                        "name": cls_name,
                        "file_path": parser.file_path,
                        "full_name": f"{parser.file_path}::{cls_name}",
                        "line": cls.get("line"),
                    }
                    cls_id = await self._db.merge_node(
                        tx,
                        label=cls_label,
                        name=cls_name,
                        properties=cls_props,
                        merge_keys=["name", "file_path"],
                    )
                    await self._db.merge_relationship(
                        tx,
                        source_id=file_id,
                        target_id=cls_id,
                        rel_type=GraphRelationship.CONTAINS.value,
                    )
                await tx.commit()
            finally:
                await tx.close()

    async def clear_all_data(self) -> int:
        await self._db.execute("MATCH (n) DETACH DELETE n", operation="repo_clear_graph")
        count_result = await self._db.query(
            "MATCH (n) RETURN count(n) as total", operation="repo_count_after_clear"
        )
        return count_result[0]["total"] if count_result else 0

    async def delete_user_data(self, user_id: int) -> int:
        """Remove todos os nÃ³s associados a um user_id especÃ­fico."""
        query = "MATCH (n {user_id: $user_id}) DETACH DELETE n"
        await self._db.execute(query, {"user_id": user_id}, operation="repo_delete_user_data")
        return 0

    async def clear_code_entities(self):
        query = f"MATCH (n) WHERE n:{GraphLabel.CODE_FUNCTION.value} OR n:{GraphLabel.CODE_CLASS.value} OR n:{GraphLabel.CODE_FILE.value} DETACH DELETE n"
        await self._db.execute(query, operation="repo_cleanup_code")

    async def bulk_merge_calls(self, calls: list[dict[str, Any]]):
        if not calls:
            return
        query = f"""UNWIND $calls as call
                     MATCH (caller:{GraphLabel.FUNCTION.value} {{name: call.caller_name, file_path: call.file_path}})
                     OPTIONAL MATCH (callee_same:{GraphLabel.FUNCTION.value} {{name: call.callee_name, file_path: call.file_path}})
                     WITH caller, call, head(collect(callee_same)) as callee_same
                     OPTIONAL MATCH (callee_any:{GraphLabel.FUNCTION.value} {{name: call.callee_name}})
                     WITH caller, coalesce(callee_same, head(collect(callee_any))) as callee
                     WHERE callee IS NOT NULL
                     MERGE (caller)-[r:`{GraphRelationship.CALLS.value}`]->(callee)"""
        await self._db.execute(query, {"calls": calls}, operation="repo_bulk_merge_calls")
        try:
            record_audit_event_direct({"action": "bulk_merge_calls", "count": len(calls)})
        except Exception:
            pass

    async def dedupe_functions_and_classes(self) -> dict[str, int]:
        """Deduplica nÃ³s Function/Class mantendo relacionamentos chave."""
        functions_fixed = 0
        classes_fixed = 0

        # FunÃ§Ãµes duplicadas por (name, file_path)
        func_scan = f"""
        MATCH (f:{GraphLabel.FUNCTION.value})
        WITH f.name as name, f.file_path as fp, collect(elementId(f)) as fs
        WHERE size(fs) > 1
        RETURN name, fp, fs
        """
        rows = await self._db.query(func_scan, operation="repo_dedupe_functions_scan")
        for row in rows or []:
            ids = list(row.get("fs") or [])
            if len(ids) < 2:
                continue
            keep = str(ids[0])
            for dup_id in ids[1:]:
                params = {"keep": keep, "dup": str(dup_id)}
                merge_query = f"""
                MATCH (keep) WHERE elementId(keep) = $keep
                MATCH (dup) WHERE elementId(dup) = $dup
                OPTIONAL MATCH (dup)-[:`{GraphRelationship.CALLS.value}`]->(t)
                MERGE (keep)-[:`{GraphRelationship.CALLS.value}`]->(t)
                OPTIONAL MATCH (s)-[:`{GraphRelationship.CALLS.value}`]->(dup)
                MERGE (s)-[:`{GraphRelationship.CALLS.value}`]->(keep)
                OPTIONAL MATCH (dup)<-[:`{GraphRelationship.CONTAINS.value}`]-(f)
                MERGE (f)-[:`{GraphRelationship.CONTAINS.value}`]->(keep)
                DETACH DELETE dup
                """
                await self._db.execute(
                    merge_query, params, operation="repo_dedupe_functions_merge"
                )
                functions_fixed += 1

        # Classes duplicadas por (name, file_path)
        class_scan = f"""
        MATCH (c:{GraphLabel.CLASS.value})
        WITH c.name as name, c.file_path as fp, collect(elementId(c)) as cs
        WHERE size(cs) > 1
        RETURN name, fp, cs
        """
        rows = await self._db.query(class_scan, operation="repo_dedupe_classes_scan")
        for row in rows or []:
            ids = list(row.get("cs") or [])
            if len(ids) < 2:
                continue
            keep = str(ids[0])
            for dup_id in ids[1:]:
                params = {"keep": keep, "dup": str(dup_id)}
                merge_query = f"""
                MATCH (keep) WHERE elementId(keep) = $keep
                MATCH (dup) WHERE elementId(dup) = $dup
                OPTIONAL MATCH (dup)-[:`{GraphRelationship.IMPLEMENTS.value}`]->(t)
                MERGE (keep)-[:`{GraphRelationship.IMPLEMENTS.value}`]->(t)
                OPTIONAL MATCH (s)-[:`{GraphRelationship.IMPLEMENTS.value}`]->(dup)
                MERGE (s)-[:`{GraphRelationship.IMPLEMENTS.value}`]->(keep)
                OPTIONAL MATCH (dup)<-[:`{GraphRelationship.CONTAINS.value}`]-(f)
                MERGE (f)-[:`{GraphRelationship.CONTAINS.value}`]->(keep)
                DETACH DELETE dup
                """
                await self._db.execute(
                    merge_query, params, operation="repo_dedupe_classes_merge"
                )
                classes_fixed += 1

        try:
            record_audit_event_direct(
                {
                    "action": "dedupe_functions_and_classes",
                    "functions_fixed": functions_fixed,
                    "classes_fixed": classes_fixed,
                }
            )
        except Exception:
            pass

        return {"functions_fixed": functions_fixed, "classes_fixed": classes_fixed}

    async def dedupe_concepts(self) -> dict[str, int]:
        """Deduplica conceitos por nome e mantÃ©m RELATES_TO."""
        fixed = 0
        scan = f"""
        MATCH (c:{GraphLabel.CONCEPT.value})
        WITH c.name as name, collect(elementId(c)) as cs
        WHERE size(cs) > 1
        RETURN name, cs
        """
        rows = await self._db.query(scan, operation="repo_dedupe_concepts_scan")
        for row in rows or []:
            ids = list(row.get("cs") or [])
            if len(ids) < 2:
                continue
            keep = str(ids[0])
            for dup_id in ids[1:]:
                params = {"keep": keep, "dup": str(dup_id)}
                merge_query = f"""
                MATCH (keep) WHERE elementId(keep) = $keep
                MATCH (dup) WHERE elementId(dup) = $dup
                OPTIONAL MATCH (dup)-[:`{GraphRelationship.RELATES_TO.value}`]->(t)
                MERGE (keep)-[:`{GraphRelationship.RELATES_TO.value}`]->(t)
                OPTIONAL MATCH (s)-[:`{GraphRelationship.RELATES_TO.value}`]->(dup)
                MERGE (s)-[:`{GraphRelationship.RELATES_TO.value}`]->(keep)
                DETACH DELETE dup
                """
                await self._db.execute(
                    merge_query, params, operation="repo_dedupe_concepts_merge"
                )
                fixed += 1

        try:
            record_audit_event_direct({"action": "dedupe_concepts", "fixed": fixed})
        except Exception:
            pass

        return {"fixed": fixed}

    async def dedupe_files(self) -> dict[str, int]:
        """Deduplica arquivos por path e mantÃ©m RELATES_TO."""
        files_fixed = 0
        scan = f"""
        MATCH (f:{GraphLabel.FILE.value})
        WITH f.path as p, collect(elementId(f)) as fs
        WHERE size(fs) > 1
        RETURN p, fs
        """
        rows = await self._db.query(scan, operation="repo_dedupe_files_scan")
        for row in rows or []:
            ids = list(row.get("fs") or [])
            if len(ids) < 2:
                continue
            keep = str(ids[0])
            for dup_id in ids[1:]:
                params = {"keep": keep, "dup": str(dup_id)}
                merge_query = f"""
                MATCH (keep) WHERE elementId(keep) = $keep
                MATCH (dup) WHERE elementId(dup) = $dup
                OPTIONAL MATCH (dup)-[:`{GraphRelationship.RELATES_TO.value}`]->(t)
                MERGE (keep)-[:`{GraphRelationship.RELATES_TO.value}`]->(t)
                OPTIONAL MATCH (s)-[:`{GraphRelationship.RELATES_TO.value}`]->(dup)
                MERGE (s)-[:`{GraphRelationship.RELATES_TO.value}`]->(keep)
                OPTIONAL MATCH (dup)-[:`{GraphRelationship.CONTAINS.value}`]->(t2)
                MERGE (keep)-[:`{GraphRelationship.CONTAINS.value}`]->(t2)
                OPTIONAL MATCH (s2)-[:`{GraphRelationship.CONTAINS.value}`]->(dup)
                MERGE (s2)-[:`{GraphRelationship.CONTAINS.value}`]->(keep)
                DETACH DELETE dup
                """
                await self._db.execute(merge_query, params, operation="repo_dedupe_files_merge")
                files_fixed += 1

        try:
            record_audit_event_direct({"action": "dedupe_files", "files_fixed": files_fixed})
        except Exception:
            pass

        return {"files_fixed": files_fixed}

    # --- Sprint 8: Consultas semÃ¢nticas ---

    async def find_related_concepts(
        self, concept: str, max_depth: int = 2, limit: int = 10, skip: int = 0
    ) -> list[dict[str, Any]]:
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

    async def find_entity_relationships(
        self,
        entity_name: str,
        rel_type: str | None = None,
        direction: str = "both",
        max_depth: int = 1,
        limit: int = 20,
        skip: int = 0,
    ) -> list[dict[str, Any]]:
        # Navega relacionamentos a partir de uma entidade com direÃ§Ã£o e profundidade configurÃ¡veis
        # direction: "out" (saÃ­da), "in" (entrada), "both" (ambas)
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
        WHERE ($rel_type IS NULL OR type(last(relationships(path))) = $rel_type)
          AND coalesce(last(relationships(path)).valid_to, datetime()) >= datetime()
          AND coalesce(related.valid_to, datetime()) >= datetime()
        RETURN related.name as related_entity,
               labels(related)[0] as related_type,
               type(last(relationships(path))) as relationship,
               length(path) as distance
        SKIP $skip
        LIMIT $limit
        """
        params = {"name": entity_name, "rel_type": rel_type, "skip": skip, "limit": limit}
        return await self._db.query(query, params, operation="repo_find_entity_relationships_nav")

    async def get_node_types(self) -> list[str]:
        # Lista todos os labels distintos presentes no grafo
        query = """
        MATCH (n)
        UNWIND labels(n) AS label
        RETURN DISTINCT label AS type
        ORDER BY type
        """
        rows = await self._db.query(query, operation="repo_get_node_types")
        return [row.get("type", "") for row in rows]

    async def find_functions_calling(self, function_name: str) -> list[dict[str, Any]]:
        query = f"""
        MATCH (t) WHERE t.name = $name AND (t:{GraphLabel.FUNCTION.value} OR t:{GraphLabel.CODE_FUNCTION.value})
        MATCH (f)-[:{GraphRelationship.CALLS.value}]->(t)
        RETURN labels(f)[0] as type, f.name as name, coalesce(f.file_path, f.path, '') as file_path
        ORDER BY name
        """
        params = {"name": function_name}
        return await self._db.query(query, params, operation="repo_find_functions_calling")

    async def find_files_importing(self, module: str) -> list[dict[str, Any]]:
        query = f"""
        MATCH (f) WHERE (f:{GraphLabel.CODE_FILE.value} OR f:{GraphLabel.FILE.value})
        MATCH (f)-[:{GraphRelationship.IMPORTS.value}]->(m)
        WHERE m.name = $module OR m.path = $module
        RETURN labels(f)[0] as type, coalesce(f.name, '') as name, coalesce(f.file_path, f.path, '') as file_path
        ORDER BY file_path
        """
        params = {"module": module}
        return await self._db.query(query, params, operation="repo_find_files_importing")

    async def find_classes_implementing(self, protocol: str) -> list[dict[str, Any]]:
        query = f"""
        MATCH (p {{name: $protocol}})
        MATCH (c)-[:{GraphRelationship.IMPLEMENTS.value}]->(p)
        WHERE (c:{GraphLabel.CLASS.value} OR c:{GraphLabel.CODE_CLASS.value})
        RETURN labels(c)[0] as type, c.name as name, coalesce(c.file_path, '') as file_path
        ORDER BY name
        """
        params = {"protocol": protocol}
        return await self._db.query(query, params, operation="repo_find_classes_implementing")

    # --- ConsolidaÃ§Ã£o inicial de conhecimento a partir de experiÃªncias ---
    async def merge_experience_mentions(
        self, experience: dict[str, Any], concepts: list[str]
    ) -> None:
        if not experience:
            return
        exp_id = experience.get("id") or experience.get("experience_id") or ""
        content = experience.get("content") or ""
        ts = experience.get("ts_ms") or experience.get("timestamp") or None
        async with await self._db.get_session() as session:
            tx = await session.begin_transaction()
            try:
                exp_label = (
                    GraphLabel.REFLECTION.value
                    if (experience.get("type") == "reflection")
                    else GraphLabel.ENTITY.value
                )
                # Usa Experience como label primÃ¡rio para auditabilidade
                exp_node_label = f"Experience:{exp_label}"
                exp_key = exp_id or (content[:64] if content else "exp")
                exp_node_id = await self._db.merge_node(tx, label=exp_node_label, name=str(exp_key))
                # Atualiza propriedades bÃ¡sicas
                await self._db.execute(
                    """
                    MATCH (e:Experience {name: $name})
                    SET e.content = COALESCE($content, e.content),
                        e.ts_ms = COALESCE($ts_ms, e.ts_ms)
                    """,
                    {
                        "name": str(exp_key),
                        "content": content[:2000] if isinstance(content, str) else None,
                        "ts_ms": ts,
                    },
                    operation="repo_update_experience_props",
                )

                for c in concepts:
                    cname = c.strip()
                    if not cname or len(cname) < 2:
                        continue
                    concept_id = await self._db.merge_node(
                        tx, label=GraphLabel.CONCEPT.value, name=cname
                    )
                    await self._db.merge_relationship(
                        tx,
                        source_id=exp_node_id,
                        target_id=concept_id,
                        rel_type=GraphRelationship.MENTIONS.value,
                    )
                await tx.commit()
            finally:
                await tx.close()


# PadrÃ£o de InjeÃ§Ã£o de DependÃªncia: Getter para o repositÃ³rio
def get_knowledge_repository(db: GraphDatabase = Depends(get_graph_db)) -> "KnowledgeRepository":
    return KnowledgeRepository(db)


