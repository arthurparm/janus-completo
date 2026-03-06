import asyncio
from typing import Any

import structlog
from fastapi import Depends
from neo4j.exceptions import TransientError

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

    @staticmethod
    def _is_retryable_transient(exc: Exception) -> bool:
        if not isinstance(exc, TransientError):
            return False
        code = str(getattr(exc, "code", "") or "")
        return "DeadlockDetected" in code or "TransientError" in code

    async def get_node_and_relationship_stats(self) -> dict[str, list]:
        node_stats_query = (
            "MATCH (n) RETURN head(labels(n)) as type, count(n) as count ORDER BY count DESC"
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
                         RETURN head(labels(e)) as type, e.name as name, e.file_path as file_path ORDER BY type, name"""
            params = {"file_path": file_path}
        else:
            query = f"""MATCH (e) WHERE e:{GraphLabel.FUNCTION.value} OR e:{GraphLabel.CLASS.value}
                         RETURN head(labels(e)) as type, e.name as name, e.file_path as file_path ORDER BY file_path, type, name"""
            params = {}
        return await self._db.query(query, params, operation="repo_find_code_entities")

    async def find_entity_details(self, entity_name: str) -> dict[str, Any] | None:
        entity_query = "MATCH (e) WHERE e.name = $name RETURN head(labels(e)) as type, properties(e) as properties LIMIT 1"
        entity = await self._db.query(
            entity_query, {"name": entity_name}, operation="repo_find_entity_properties"
        )
        if not entity:
            return None
        relationships_query = "MATCH (e {name: $name})-[r]-(related) RETURN type(r) as relationship, related.name as related_entity, head(labels(related)) as related_type LIMIT 20"
        relationships = await self._db.query(
            relationships_query, {"name": entity_name}, operation="repo_find_entity_relationships"
        )
        return {"entity": entity[0], "relationships": relationships}

    async def save_code_structure(self, parser: CodeParser):
        logger.debug("Salvando estrutura de codigo no repositorio", file_path=parser.file_path)
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            async with await self._db.get_session() as session:
                tx = await session.begin_transaction()
                committed = False
                try:
                    func_label = f"{GraphLabel.FUNCTION.value}:{GraphLabel.CODE_FUNCTION.value}"
                    cls_label = f"{GraphLabel.CLASS.value}:{GraphLabel.CODE_CLASS.value}"

                    file_props = {
                        "name": parser.file_path,
                        "path": parser.file_path,
                        "file_path": parser.file_path,
                    }
                    file_id = await self._db.merge_node(
                        tx,
                        label=GraphLabel.FILE.value,
                        name=parser.file_path,
                        properties=file_props,
                        merge_keys=["path"],
                    )
                    await tx.run(
                        f"""
                        MATCH (f:{GraphLabel.FILE.value})
                        WHERE elementId(f) = $file_id
                        SET f:{GraphLabel.CODE_FILE.value}
                        SET f += $props
                        RETURN elementId(f) AS file_id
                        """,
                        file_id=file_id,
                        props=file_props,
                    )
                    for func in parser.functions:
                        func_name = func["name"]
                        func_qualified = func.get("qualified_name") or func_name
                        func_props = {
                            "name": func_name,
                            "file_path": parser.file_path,
                            "full_name": f"{parser.file_path}::{func_qualified}",
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
                        cls_qualified = cls.get("qualified_name") or cls_name
                        cls_props = {
                            "name": cls_name,
                            "file_path": parser.file_path,
                            "full_name": f"{parser.file_path}::{cls_qualified}",
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
                    committed = True
                    return
                except Exception as exc:
                    if not self._is_retryable_transient(exc) or attempt >= max_attempts:
                        raise
                    logger.warning(
                        "repo_save_code_structure_retry_transient",
                        file_path=parser.file_path,
                        attempt=attempt,
                        error=str(exc),
                    )
                    await asyncio.sleep(0.2 * attempt)
                finally:
                    if not committed:
                        try:
                            await tx.rollback()
                        except Exception:
                            pass
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
        # Deduplicate semantic duplicates to reduce write pressure during indexing.
        deduped_calls = self._dedupe_calls(calls)

        query = f"""UNWIND $calls as call
                     MATCH (caller:{GraphLabel.FUNCTION.value} {{file_path: call.file_path}})
                     WHERE (call.caller_qualified IS NOT NULL AND caller.full_name = call.file_path + "::" + call.caller_qualified)
                        OR caller.name = call.caller_name
                     WITH call, head(collect(caller)) as caller
                     WHERE caller IS NOT NULL
                     OPTIONAL MATCH (callee_same_full:{GraphLabel.FUNCTION.value} {{file_path: call.file_path}})
                     WHERE call.callee_qualified IS NOT NULL
                       AND callee_same_full.full_name = call.file_path + "::" + call.callee_qualified
                     WITH call, caller, head(collect(callee_same_full)) as callee_same_full
                     OPTIONAL MATCH (callee_same_name:{GraphLabel.FUNCTION.value} {{name: call.callee_name, file_path: call.file_path}})
                     WITH call, caller, callee_same_full, head(collect(callee_same_name)) as callee_same_name
                     OPTIONAL MATCH (callee_any_name:{GraphLabel.FUNCTION.value} {{name: call.callee_name}})
                     WITH caller, callee_same_full, callee_same_name, head(collect(callee_any_name)) as callee_any_name
                     WITH caller, coalesce(callee_same_full, callee_same_name, callee_any_name) as callee
                     WHERE callee IS NOT NULL
                     MERGE (caller)-[r:`{GraphRelationship.CALLS.value}`]->(callee)"""

        base_batch_size = 100
        index = 0
        while index < len(deduped_calls):
            batch_size = min(base_batch_size, len(deduped_calls) - index)
            while True:
                batch = deduped_calls[index : index + batch_size]
                try:
                    await self._db.execute(query, {"calls": batch}, operation="repo_bulk_merge_calls")
                    index += batch_size
                    break
                except TimeoutError:
                    if batch_size == 1:
                        raise
                    reduced = max(1, batch_size // 2)
                    logger.warning(
                        "bulk_merge_calls_timeout_retry_smaller_batch",
                        attempted_batch_size=batch_size,
                        next_batch_size=reduced,
                        processed=index,
                        total=len(deduped_calls),
                    )
                    batch_size = reduced
                except Exception as exc:
                    if not self._is_retryable_transient(exc):
                        raise
                    logger.warning(
                        "bulk_merge_calls_retry_transient",
                        attempted_batch_size=batch_size,
                        processed=index,
                        total=len(deduped_calls),
                        error=str(exc),
                    )
                    await asyncio.sleep(0.2)
        try:
            record_audit_event_direct(
                {"action": "bulk_merge_calls", "count": len(calls), "deduped_count": len(deduped_calls)}
            )
        except Exception:
            pass

    @staticmethod
    def _dedupe_calls(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for call in calls:
            file_path = str(call.get("file_path") or "").strip()
            caller = str(call.get("caller_qualified") or call.get("caller_name") or "").strip()
            callee = str(call.get("callee_qualified") or call.get("callee_name") or "").strip()
            if not file_path or not caller or not callee:
                continue
            key = (file_path, caller, callee)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(call)
        return deduped

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
               head(labels(related)) as related_type,
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
        RETURN head(labels(f)) as type, f.name as name, coalesce(f.file_path, f.path, '') as file_path
        ORDER BY name
        """
        params = {"name": function_name}
        return await self._db.query(query, params, operation="repo_find_functions_calling")

    async def find_files_importing(self, module: str) -> list[dict[str, Any]]:
        query = f"""
        MATCH (f) WHERE (f:{GraphLabel.CODE_FILE.value} OR f:{GraphLabel.FILE.value})
        MATCH (f)-[:{GraphRelationship.IMPORTS.value}]->(m)
        WHERE m.name = $module OR m.path = $module
        RETURN head(labels(f)) as type, coalesce(f.name, '') as name, coalesce(f.file_path, f.path, '') as file_path
        ORDER BY file_path
        """
        params = {"module": module}
        return await self._db.query(query, params, operation="repo_find_files_importing")

    async def find_classes_implementing(self, protocol: str) -> list[dict[str, Any]]:
        query = f"""
        MATCH (p {{name: $protocol}})
        MATCH (c)-[:{GraphRelationship.IMPLEMENTS.value}]->(p)
        WHERE (c:{GraphLabel.CLASS.value} OR c:{GraphLabel.CODE_CLASS.value})
        RETURN head(labels(c)) as type, c.name as name, coalesce(c.file_path, '') as file_path
        ORDER BY name
        """
        params = {"protocol": protocol}
        return await self._db.query(query, params, operation="repo_find_classes_implementing")

    async def find_code_citations(
        self, tokens: list[str], limit: int = 10
    ) -> list[dict[str, Any]]:
        if not tokens:
            return []

        query = f"""
        MATCH (e)
        WHERE (e:{GraphLabel.FUNCTION.value} OR e:{GraphLabel.CODE_FUNCTION.value}
            OR e:{GraphLabel.CLASS.value} OR e:{GraphLabel.CODE_CLASS.value})
          AND any(t IN $tokens
              WHERE toLower(coalesce(e.name, '')) CONTAINS t
                 OR toLower(coalesce(e.full_name, '')) CONTAINS t
                 OR toLower(coalesce(e.file_path, '')) CONTAINS t)
        WITH e, reduce(score = 0, t IN $tokens |
            score
            + CASE WHEN toLower(coalesce(e.name, '')) = t THEN 5 ELSE 0 END
            + CASE WHEN toLower(coalesce(e.name, '')) CONTAINS t THEN 2 ELSE 0 END
            + CASE WHEN toLower(coalesce(e.full_name, '')) CONTAINS t THEN 1 ELSE 0 END
            + CASE WHEN toLower(coalesce(e.file_path, '')) CONTAINS t THEN 1 ELSE 0 END
          ) AS relevance
        RETURN head(labels(e)) as type,
               coalesce(e.name, '') as name,
               coalesce(e.file_path, e.path, '') as file_path,
               toInteger(coalesce(e.line, 1)) as line,
               coalesce(e.full_name, e.name, '') as full_name,
               relevance
        ORDER BY relevance DESC, file_path ASC, line ASC, name ASC
        LIMIT $limit
        """
        params = {"tokens": tokens, "limit": int(limit)}
        return await self._db.query(query, params, operation="repo_find_code_citations")

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
