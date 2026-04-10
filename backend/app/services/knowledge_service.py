import hashlib
import re
import time
import asyncio
from typing import Any

import structlog
from fastapi import Request

from app.db.graph import get_graph_db
from app.core.memory.rag_telemetry import emit_step_telemetry
from app.core.memory.graph_rag_core import query_knowledge_graph
from app.core.workers.knowledge_consolidator_worker import knowledge_consolidator
from app.repositories.knowledge_repository import KnowledgeRepository
from app.services.code_analysis_service import code_analysis_service

logger = structlog.get_logger(__name__)

CODEBASE_DIR = "/app"


# --- Custom Service-Layer Exceptions ---
from app.core.memory.graph_embeddings import GraphEmbeddingsManager


class KnowledgeServiceError(Exception):
    """Base exception for knowledge service errors."""

    pass


class KnowledgeService:
    """
    Camada de serviço para o Grafo de Conhecimento.
    Orquestra a lógica de negócio, recebendo suas dependências via DI.
    """

    def __init__(self, repo: KnowledgeRepository):
        self._repo = repo
        self._index_lock = asyncio.Lock()
        self._index_task: asyncio.Task[dict[str, Any]] | None = None

    async def get_stats(self) -> dict[str, Any]:
        try:
            stats = await self._repo.get_node_and_relationship_stats()
            return {
                "total_nodes": sum(i.get("count", 0) for i in stats["nodes"]),
                "total_relationships": sum(i.get("count", 0) for i in stats["relationships"]),
                "node_types": stats["nodes"],
                "relationship_types": stats["relationships"],
            }
        except Exception as e:
            logger.error("Error retrieving knowledge stats", exc_info=e)
            return {
                "total_nodes": 0,
                "total_relationships": 0,
                "node_types": [],
                "relationship_types": [],
                "error": str(e),
            }

    async def get_code_entities(self, file_path: str | None = None) -> list[dict[str, Any]]:
        return await self._repo.find_code_entities(file_path)

    async def get_entity_details(self, entity_name: str) -> dict[str, Any] | None:
        details = await self._repo.find_entity_details(entity_name)
        if not details:
            return None
        return details

    async def get_entity_relationships(
        self,
        entity_name: str,
        rel_type: str | None = None,
        direction: str = "both",
        max_depth: int = 1,
        limit: int = 20,
        skip: int = 0,
    ) -> list[dict[str, Any]]:
        return await self._repo.find_entity_relationships(
            entity_name=entity_name,
            rel_type=rel_type,
            direction=direction,
            max_depth=max_depth,
            limit=limit,
            skip=skip,
        )

    async def get_functions_calling(self, function_name: str) -> list[dict[str, Any]]:
        return await self._repo.find_functions_calling(function_name=function_name)

    async def get_files_importing(self, module: str) -> list[dict[str, Any]]:
        return await self._repo.find_files_importing(module=module)

    async def get_classes_implementing(self, protocol: str) -> list[dict[str, Any]]:
        return await self._repo.find_classes_implementing(protocol=protocol)

    async def trigger_consolidation(self, limit: int, min_score: float = 0.0) -> dict[str, Any]:
        # Utiliza consolidação em lote para alinhar com Sprint 8
        stats = await knowledge_consolidator.consolidate_batch(limit=limit, min_score=min_score)
        return stats

    @staticmethod
    def _build_graph_path_candidates(rel_path: str) -> list[str]:
        rel = str(rel_path or "").strip().lstrip("./")
        if not rel:
            return []

        candidates: set[str] = {rel, f"/{rel}", f"/app/{rel}"}
        if rel.startswith("backend/"):
            stripped = rel[len("backend/") :]
            if stripped:
                candidates.update({stripped, f"/{stripped}", f"/app/{stripped}"})
        if rel.startswith("app/"):
            backend_variant = f"backend/{rel}"
            candidates.update({backend_variant, f"/{backend_variant}", f"/app/{rel}"})
            if rel.startswith("app/app/"):
                backend_stripped = f"backend/{rel[len('app/') :]}"
                candidates.update({backend_stripped, f"/{backend_stripped}"})
        if rel.startswith("frontend/"):
            candidates.add(f"/app/{rel}")
        return [candidate for candidate in candidates if candidate]

    @staticmethod
    def _preferred_graph_owner_path(rel_path: str, path_candidates: list[str]) -> str:
        for candidate in path_candidates:
            if candidate.startswith("/app/"):
                return candidate
        rel = str(rel_path or "").strip().lstrip("./")
        if rel.startswith("backend/"):
            return f"/app/{rel[len('backend/') :]}"
        if rel:
            return f"/app/{rel}" if not rel.startswith("/app/") else rel
        return "/app"

    @staticmethod
    def _build_self_memory_key(
        rel_path: str,
        *,
        summary_version: str | None,
        sha_after: str | None,
    ) -> str:
        normalized_path = str(rel_path or "").strip().lstrip("./")
        normalized_version = str(summary_version or "legacy").strip() or "legacy"
        normalized_sha = str(sha_after or "").strip()
        prefix = "selfmemory" if normalized_sha else "selfmemory-legacy"
        raw = f"{normalized_path}|{normalized_version}|{normalized_sha or 'legacy'}"
        return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"

    @staticmethod
    def _normalize_symbol_names(raw_symbols: Any) -> list[str]:
        symbol_names: list[str] = []
        seen: set[str] = set()
        for symbol in raw_symbols or []:
            value = str(symbol or "").strip()
            if not value or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", value):
                continue
            if value in seen:
                continue
            seen.add(value)
            symbol_names.append(value)
        return symbol_names

    async def _repair_single_self_memory(
        self,
        *,
        row: dict[str, Any],
        is_current: bool,
    ) -> dict[str, int]:
        graph = await get_graph_db()
        node_id = str(row.get("node_id") or "").strip()
        rel_path = str(row.get("file_path") or "").strip().lstrip("./")
        if not node_id or not rel_path:
            return {"owner_links": 0, "symbol_links": 0, "provenance_links": 0}

        summary_version = str(row.get("summary_version") or "").strip() or "legacy"
        sha_after = str(row.get("sha_after") or "").strip() or None
        source_experience_id = str(row.get("source_experience_id") or "").strip() or None
        symbol_names = self._normalize_symbol_names(row.get("symbols") or [])
        memory_key = self._build_self_memory_key(
            rel_path,
            summary_version=summary_version,
            sha_after=sha_after,
        )
        path_candidates = self._build_graph_path_candidates(rel_path)
        primary_owner_path = self._preferred_graph_owner_path(rel_path, path_candidates)

        await graph.query(
            """
            MATCH (m) WHERE elementId(m) = $node_id
            SET m.memory_key = $memory_key,
                m.file_path = $file_path,
                m.summary_version = $summary_version,
                m.sha_after = CASE WHEN $sha_after IS NULL OR $sha_after = '' THEN m.sha_after ELSE $sha_after END,
                m.is_current = $is_current,
                m.is_legacy = $is_legacy,
                m.updated_at = coalesce(m.updated_at, timestamp())
            RETURN m.memory_key AS memory_key
            """,
            {
                "node_id": node_id,
                "memory_key": memory_key,
                "file_path": rel_path,
                "summary_version": summary_version,
                "sha_after": sha_after,
                "is_current": is_current,
                "is_legacy": not bool(sha_after),
            },
            operation="knowledge_self_memory_meta_upsert",
        )

        await graph.query(
            """
            MATCH (other:SelfMemory {file_path: $file_path})
            WHERE elementId(other) <> $node_id
            SET other.is_current = false
            RETURN count(other) AS demoted
            """,
            {"file_path": rel_path, "node_id": node_id},
            operation="knowledge_self_memory_current_demote",
        )

        await graph.query(
            """
            MATCH (m) WHERE elementId(m) = $node_id
            MATCH (m)-[r:RELATES_TO]->(owner)
            WHERE (owner:File OR owner:CodeFile) AND NOT owner.path IN $path_candidates
            DELETE r
            RETURN count(r) AS removed_links
            """,
            {"node_id": node_id, "path_candidates": path_candidates},
            operation="knowledge_self_memory_owner_cleanup",
        )
        await graph.query(
            """
            MATCH (m) WHERE elementId(m) = $node_id
            MATCH (m)-[r:DEFINES]->(symbol)
            WHERE (symbol:CodeFunction OR symbol:CodeClass)
              AND NOT (
                symbol.file_path IN $path_candidates
                AND (size($symbol_names) = 0 OR symbol.name IN $symbol_names)
              )
            DELETE r
            RETURN count(r) AS removed_links
            """,
            {
                "node_id": node_id,
                "path_candidates": path_candidates,
                "symbol_names": symbol_names,
            },
            operation="knowledge_self_memory_symbol_cleanup",
        )

        owner_rows = await graph.query(
            """
            MATCH (m) WHERE elementId(m) = $node_id
            MATCH (owner)
            WHERE (owner:File OR owner:CodeFile) AND owner.path IN $path_candidates
            MERGE (m)-[:RELATES_TO]->(owner)
            RETURN count(DISTINCT owner) AS owner_links
            """,
            {"node_id": node_id, "path_candidates": path_candidates},
            operation="knowledge_self_memory_owner_link_existing",
        )
        owner_links = int((owner_rows or [{}])[0].get("owner_links", 0) or 0)
        if owner_links <= 0:
            owner_rows = await graph.query(
                """
                MATCH (m) WHERE elementId(m) = $node_id
                MERGE (owner:File {path: $primary_owner_path})
                SET owner.name = coalesce(owner.name, $primary_owner_path),
                    owner.file_path = coalesce(owner.file_path, $primary_owner_path),
                    owner.source = coalesce(owner.source, 'self_study')
                MERGE (m)-[:RELATES_TO]->(owner)
                RETURN count(owner) AS owner_links
                """,
                {"node_id": node_id, "primary_owner_path": primary_owner_path},
                operation="knowledge_self_memory_owner_link_fallback",
            )
            owner_links = int((owner_rows or [{}])[0].get("owner_links", 0) or 0)

        function_rows = await graph.query(
            """
            MATCH (m) WHERE elementId(m) = $node_id
            MATCH (fn:CodeFunction)
            WHERE fn.file_path IN $path_candidates
              AND (size($symbol_names) = 0 OR fn.name IN $symbol_names)
            MERGE (m)-[:DEFINES]->(fn)
            RETURN count(DISTINCT fn) AS symbol_links
            """,
            {
                "node_id": node_id,
                "path_candidates": path_candidates,
                "symbol_names": symbol_names,
            },
            operation="knowledge_self_memory_function_link",
        )
        class_rows = await graph.query(
            """
            MATCH (m) WHERE elementId(m) = $node_id
            MATCH (cl:CodeClass)
            WHERE cl.file_path IN $path_candidates
              AND (size($symbol_names) = 0 OR cl.name IN $symbol_names)
            MERGE (m)-[:DEFINES]->(cl)
            RETURN count(DISTINCT cl) AS symbol_links
            """,
            {
                "node_id": node_id,
                "path_candidates": path_candidates,
                "symbol_names": symbol_names,
            },
            operation="knowledge_self_memory_class_link",
        )
        provenance_links = 0
        if source_experience_id:
            await graph.query(
                """
                MERGE (exp:Experience {id: $experience_id})
                ON CREATE SET exp.created_at = timestamp()
                SET exp.type = coalesce(exp.type, 'episodic'),
                    exp.origin = coalesce(exp.origin, 'self_study'),
                    exp.file_path = coalesce(exp.file_path, $file_path),
                    exp.updated_at = timestamp()
                RETURN exp.id AS id
                """,
                {
                    "experience_id": source_experience_id,
                    "file_path": rel_path,
                },
                operation="knowledge_self_memory_experience_upsert",
            )
            provenance_rows = await graph.query(
                """
                MATCH (m) WHERE elementId(m) = $node_id
                MATCH (exp:Experience {id: $experience_id})
                MERGE (m)-[:EXTRACTED_FROM]->(exp)
                RETURN count(exp) AS provenance_links
                """,
                {
                    "node_id": node_id,
                    "experience_id": source_experience_id,
                },
                operation="knowledge_self_memory_provenance_link",
            )
            provenance_links = int(
                (provenance_rows or [{}])[0].get("provenance_links", 0) or 0
            )

        return {
            "owner_links": owner_links,
            "symbol_links": int((function_rows or [{}])[0].get("symbol_links", 0) or 0)
            + int((class_rows or [{}])[0].get("symbol_links", 0) or 0),
            "provenance_links": provenance_links,
        }

    async def repair_self_memory_graph(self, *, limit: int | None = None) -> dict[str, Any]:
        graph = await get_graph_db()
        query = """
        MATCH (m:SelfMemory)
        RETURN elementId(m) AS node_id,
               m.file_path AS file_path,
               m.summary_version AS summary_version,
               m.sha_after AS sha_after,
               m.source_experience_id AS source_experience_id,
               m.symbols AS symbols,
               coalesce(m.updated_at, 0) AS updated_at
        ORDER BY updated_at DESC, file_path ASC
        """
        params: dict[str, Any] = {}
        if limit is not None:
            query += "\nLIMIT $limit"
            params["limit"] = int(limit)
        rows = await graph.query(query, params, operation="knowledge_self_memory_fetch")

        repaired = 0
        connected = 0
        provenance = 0
        symbol_links = 0
        seen_paths: set[str] = set()
        for row in rows or []:
            rel_path = str(row.get("file_path") or "").strip().lstrip("./")
            is_current = rel_path not in seen_paths
            if rel_path:
                seen_paths.add(rel_path)
            result = await self._repair_single_self_memory(row=row, is_current=is_current)
            repaired += 1
            connected += 1 if result["owner_links"] > 0 else 0
            provenance += result["provenance_links"]
            symbol_links += result["symbol_links"]

        return {
            "repaired": repaired,
            "connected": connected,
            "provenance_links": provenance,
            "symbol_links": symbol_links,
        }

    async def get_self_memory_neo4j_audit(self, *, orphan_limit: int = 25) -> dict[str, Any]:
        graph = await get_graph_db()
        totals = await graph.query(
            """
            MATCH (m:SelfMemory)
            OPTIONAL MATCH (m)-[:RELATES_TO]->(owner)
            WHERE owner:File OR owner:CodeFile
            OPTIONAL MATCH (m)-[:EXTRACTED_FROM]->(exp:Experience)
            RETURN count(DISTINCT m) AS total_self_memory,
                   count(DISTINCT CASE WHEN owner IS NOT NULL THEN m END) AS connected_self_memory,
                   count(DISTINCT CASE WHEN exp IS NULL THEN m END) AS self_memory_without_extracted_from,
                   count(DISTINCT CASE WHEN m.sha_after IS NULL OR trim(toString(m.sha_after)) = '' THEN m END) AS self_memory_without_sha_after
            """,
            operation="knowledge_self_memory_audit_totals",
        )
        orphan_rows = await graph.query(
            """
            MATCH (m:SelfMemory)
            WHERE NOT EXISTS {
              MATCH (m)-[:RELATES_TO]->(owner)
              WHERE owner:File OR owner:CodeFile
            }
            RETURN m.file_path AS file_path, count(*) AS count
            ORDER BY count DESC, file_path ASC
            LIMIT $limit
            """,
            {"limit": int(orphan_limit)},
            operation="knowledge_self_memory_audit_orphans",
        )
        row = (totals or [{}])[0]
        return {
            "total_self_memory": int(row.get("total_self_memory", 0) or 0),
            "connected_self_memory": int(row.get("connected_self_memory", 0) or 0),
            "self_memory_without_extracted_from": int(
                row.get("self_memory_without_extracted_from", 0) or 0
            ),
            "self_memory_without_sha_after": int(
                row.get("self_memory_without_sha_after", 0) or 0
            ),
            "orphan_self_memory_by_path": orphan_rows or [],
        }

    async def _index_codebase_impl(self) -> dict[str, Any]:
        logger.info("log_info", message=f"Iniciando orquestração de indexação da base de código em '{CODEBASE_DIR}'...")
        await self._repo.clear_code_entities()

        python_files = code_analysis_service.find_python_files(CODEBASE_DIR)
        total_files, total_funcs, total_classes, all_calls = 0, 0, 0, []

        for file_path in python_files:
            parser = code_analysis_service.parse_python_file(file_path)
            if parser:
                await self._repo.save_code_structure(parser)
                for call in parser.calls:
                    all_calls.append(
                        {
                            "caller_name": call["caller"],
                            "caller_qualified": call.get("caller_qualified"),
                            "callee_name": call["callee"],
                            "callee_qualified": call.get("callee_qualified"),
                            "file_path": file_path,
                        }
                    )
                total_files += 1
                total_funcs += len(parser.functions)
                total_classes += len(parser.classes)

        await self._repo.bulk_merge_calls(all_calls)
        repair_stats = await self.repair_self_memory_graph()

        summary = (
            "Indexação concluída. "
            f"{total_files} arquivos | {total_funcs} funções | {total_classes} classes | "
            f"{len(all_calls)} chamadas internas criadas | "
            f"{repair_stats['connected']}/{repair_stats['repaired']} SelfMemory religadas."
        )
        return {
            "message": "Indexação da base de código concluída.",
            "summary": summary,
            "repair": repair_stats,
        }

    async def index_codebase(self) -> dict[str, Any]:
        async with self._index_lock:
            if self._index_task and not self._index_task.done():
                task = self._index_task
            else:
                task = asyncio.create_task(self._index_codebase_impl())
                self._index_task = task
        try:
            return await task
        finally:
            async with self._index_lock:
                if self._index_task is task and task.done():
                    self._index_task = None

    async def clear_graph(self) -> int:
        return await self._repo.clear_all_data()

    # --- Sprint 8 Operations ---

    async def semantic_query(self, question: str, limit: int = 10) -> str:
        started_at = time.perf_counter()
        try:
            answer = await query_knowledge_graph(question, limit=limit)
            normalized = str(answer or "").strip().lower()
            has_error_prefix = normalized.startswith("error")
            no_context = normalized in {"", "no context found.", "graph rag not initialized."}
            confidence = 0.0 if has_error_prefix or no_context else 1.0
            emit_step_telemetry(
                endpoint="/knowledge/query",
                step="semantic_query",
                source="graph_rag",
                db="neo4j",
                latency_ms=(time.perf_counter() - started_at) * 1000,
                confidence=confidence,
                error_code=None,
                extra={"limit": int(limit)},
            )
            return answer
        except Exception as e:
            emit_step_telemetry(
                endpoint="/knowledge/query",
                step="semantic_query",
                source="graph_rag",
                db="neo4j",
                latency_ms=(time.perf_counter() - started_at) * 1000,
                confidence=0.0,
                error_code=type(e).__name__,
                extra={"limit": int(limit)},
            )
            raise

    @staticmethod
    def _extract_code_tokens(question: str) -> list[str]:
        raw_tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_./:-]*", question.lower())
        stopwords = {
            "de",
            "da",
            "do",
            "das",
            "dos",
            "e",
            "em",
            "no",
            "na",
            "nos",
            "nas",
            "o",
            "a",
            "os",
            "as",
            "um",
            "uma",
            "sobre",
            "para",
            "com",
            "por",
            "how",
            "what",
            "where",
            "when",
            "which",
            "the",
            "and",
            "or",
            "to",
            "in",
            "on",
        }
        deduped: list[str] = []
        seen: set[str] = set()
        for token in raw_tokens:
            if len(token) < 2 or token in stopwords:
                continue
            if token not in seen:
                deduped.append(token)
                seen.add(token)
        return deduped[:20]

    async def ask_code_with_citations(
        self, question: str, limit: int = 10, citation_limit: int = 8
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        try:
            answer = await self.semantic_query(question, limit=limit)
            tokens = self._extract_code_tokens(question)
            citations = await self._repo.find_code_citations(tokens=tokens, limit=citation_limit)
            if not citations:
                answer = (
                    "Nao encontrei citacoes rastreaveis para responder com seguranca sobre codigo. "
                    "Reformule a pergunta ou indexe/reindexe a base."
                )
            confidence = 1.0 if citations else 0.0
            emit_step_telemetry(
                endpoint="/knowledge/query/code",
                step="code_citations",
                source="knowledge_service",
                db="neo4j",
                latency_ms=(time.perf_counter() - started_at) * 1000,
                confidence=confidence,
                error_code=None,
                extra={
                    "citation_count": len(citations),
                    "token_count": len(tokens),
                    "limit": int(limit),
                    "citation_limit": int(citation_limit),
                },
            )
            return {"answer": answer, "citations": citations}
        except Exception as e:
            emit_step_telemetry(
                endpoint="/knowledge/query/code",
                step="code_citations",
                source="knowledge_service",
                db="neo4j",
                latency_ms=(time.perf_counter() - started_at) * 1000,
                confidence=0.0,
                error_code=type(e).__name__,
                extra={"limit": int(limit), "citation_limit": int(citation_limit)},
            )
            raise

    async def consolidate_document(
        self, doc_id: str, limit: int = 50
    ) -> dict[str, Any]:
        return await knowledge_consolidator.consolidate_document(
            doc_id=doc_id, limit=limit
        )

    async def find_related_concepts(
        self, concept: str, max_depth: int = 2, limit: int = 10, skip: int = 0
    ) -> list[dict[str, Any]]:
        return await self._repo.find_related_concepts(
            concept=concept, max_depth=max_depth, limit=limit, skip=skip
        )

    async def get_node_types(self) -> list[str]:
        return await self._repo.get_node_types()

    async def get_health_status(self) -> dict[str, Any]:
        try:
            stats = await self._repo.get_node_and_relationship_stats()
            total_nodes = sum(i.get("count", 0) for i in stats["nodes"]) if stats else 0
            total_relationships = (
                sum(i.get("count", 0) for i in stats["relationships"]) if stats else 0
            )

            # Check memory/Qdrant health
            from app.core.memory.memory_core import get_memory_db

            memory_db = await get_memory_db()
            qdrant_healthy = memory_db.health_check()

            # Determine overall status
            if qdrant_healthy and total_nodes > 0:
                status = "ok"
            elif qdrant_healthy or total_nodes > 0:
                status = "partial"
            else:
                status = "degraded"

            return {
                "status": status,
                "neo4j_connected": total_nodes > 0,
                "qdrant_connected": qdrant_healthy,
                "circuit_breaker_open": not qdrant_healthy,  # Se Qdrant não está saudável, circuit breaker está aberto
                "total_nodes": total_nodes,
                "total_relationships": total_relationships,
            }
        except Exception as e:
            logger.warning("Erro ao verificar status de saúde do conhecimento", exc_info=e)
            return {
                "status": "degraded",
                "neo4j_connected": False,
                "qdrant_connected": False,
                "circuit_breaker_open": True,
                "total_nodes": 0,
                "total_relationships": 0,
            }

    async def reindex_graph(self, batch_size: int = 50, labels: list[str] = None) -> int:
        manager = GraphEmbeddingsManager()
        return await manager.reindex_graph(batch_size=batch_size, labels=labels)

    # --- Governança / HITL ---

    async def register_relationship_type(self, name: str) -> dict[str, Any]:
        from app.db.graph import get_graph_db

        db = await get_graph_db()
        async with await db.get_session() as session:
            await db.register_relationship_type(session, name)
        return {"status": "registered", "name": name}

    async def list_quarantine_items(self, limit: int = 50) -> list[dict[str, Any]]:
        from app.db.graph import get_graph_db

        db = await get_graph_db()
        rows = await db.query(
            """
            MATCH (q:Quarantine)-[:EXTRACTED_FROM]->(e:Experience)
            RETURN q.reason AS reason, q.type AS type, q.from_name AS from_name, q.to_name AS to_name,
                   e.id AS experience_id, e.timestamp AS timestamp
            LIMIT $limit
            """,
            params={"limit": int(limit)},
            operation="list_quarantine",
        )
        return rows or []

    async def promote_quarantine_relationship(
        self, from_name: str, to_name: str, rel_type: str, source_experience: str
    ) -> dict[str, Any]:
        from app.db.graph import get_graph_db

        db = await get_graph_db()
        async with await db.get_session() as session:
            tx = await session.begin_transaction()
            try:
                await db.register_relationship_type(tx, rel_type)
                await tx.run(
                    f"""
                    MATCH (a {{name: $from_name}})
                    MATCH (b {{name: $to_name}})
                    MERGE (a)-[r:`{rel_type}`]->(b)
                    SET r.source_experience = $source_experience,
                        r.promoted_at = datetime()
                    """,
                    from_name=from_name,
                    to_name=to_name,
                    source_experience=source_experience,
                )
                await tx.run(
                    """
                    MATCH (q:Quarantine {from_name: $from_name, to_name: $to_name, type: $type})
                    DETACH DELETE q
                    """,
                    from_name=from_name,
                    to_name=to_name,
                    type=rel_type,
                )
                await tx.commit()
                return {"status": "promoted", "from": from_name, "to": to_name, "type": rel_type}
            finally:
                await tx.close()


# Padrão de Injeção de Dependência: Getter para o serviço
def get_knowledge_service(request: Request) -> KnowledgeService:
    return request.app.state.knowledge_service
