import re
import time
from typing import Any

import structlog
from fastapi import Request

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

    async def index_codebase(self) -> dict[str, Any]:
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

        summary = f"Indexação concluída. {total_files} arquivos | {total_funcs} funções | {total_classes} classes | {len(all_calls)} chamadas internas criadas."
        return {"message": "Indexação da base de código concluída.", "summary": summary}

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
        self, user_id: str, doc_id: str, limit: int = 50
    ) -> dict[str, Any]:
        return await knowledge_consolidator.consolidate_document(
            user_id=user_id, doc_id=doc_id, limit=limit
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
