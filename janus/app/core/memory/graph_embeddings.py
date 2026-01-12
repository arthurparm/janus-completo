import logging
import asyncio
from typing import Any

from app.core.embeddings.embedding_manager import aembed_text, aembed_texts
from app.db.graph import get_graph_db

logger = logging.getLogger(__name__)

class GraphEmbeddingsManager:
    """
    Gerencia a geração e sincronização de embeddings para nós do Grafo (Neo4j).
    Permite busca vetorial e híbrida via Neo4j Vector Index.
    """

    def __init__(self):
        self._db_getter = get_graph_db

    async def embed_node(self, node_id: int, text_content: str) -> list[float] | None:
        """
        Gera embedding para um texto e atualiza o nó correspondente no Neo4j.
        Retorna o vetor gerado.
        """
        try:
            vector = await aembed_text(text_content)
            if not vector:
                return None

            db = await self._db_getter()
            if not db:
                return None

            await db.execute(
                """
                MATCH (n) WHERE id(n) = $id
                SET n.embedding = $vector
                RETURN n
                """,
                {"id": node_id, "vector": vector},
            )
            return vector
            return vector
        except Exception as e:
            logger.error(f"Erro ao gerar/salvar embedding para nó {node_id}: {e}")
            return None

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Gera embeddings em lote para uma lista de textos.
        Retorna lista de vetores correspondentes.
        """
        if not texts:
            return []
        try:
            return await aembed_texts(texts)
        except Exception as e:
            logger.error(f"Erro ao gerar batch embeddings: {e}")
            return []

    async def vector_search(self, query: str, k: int = 10, min_score: float = 0.7) -> list[dict[str, Any]]:
        """
        Realiza busca vetorial direta no Neo4j usando o índice `concept_embeddings`.
        Requer que o índice tenha sido criado previamente.
        """
        try:
            vector = await aembed_text(query)
            db = await self._db_getter()
            if not db:
                return []

            # Neo4j 5.11+ syntax
            results = await db.query(
                """
                CALL db.index.vector.queryNodes('concept_embeddings', $k, $vector)
                YIELD node, score
                WHERE score >= $min_score
                RETURN node, score, id(node) as id, labels(node) as labels
                """,
                {"k": k, "vector": vector, "min_score": min_score},
            )
            return results
        except Exception as e:
            logger.error(f"Erro na busca vetorial no Neo4j: {e}")
            return []

    async def reindex_concepts(self, batch_size: int = 50):
        """
        Job de migração: Varre nós Concept sem embedding e gera eles.
        """
        logger.info("Iniciando reindexação de conceitos para Vector Search...")
        db = await self._db_getter()
        if not db:
            return

        total_updated = 0
        while True:
            # Busca lote de nós sem embedding
            nodes = await db.query(
                """
                MATCH (n:Concept)
                WHERE n.embedding IS NULL AND n.name IS NOT NULL
                RETURN id(n) as id, n.name as text
                LIMIT $limit
                """,
                {"limit": batch_size},
            )

            if not nodes:
                break

            updates = []
            for node in nodes:
                try:
                    vec = await aembed_text(node["text"])
                    if vec:
                        updates.append({"id": node["id"], "vector": vec})
                except Exception:
                    pass

            if updates:
                # Batch update (requires UNWIND)
                await db.execute(
                    """
                    UNWIND $updates as row
                    MATCH (n) WHERE id(n) = row.id
                    SET n.embedding = row.vector
                    """,
                    {"updates": updates}
                )
                total_updated += len(updates)
                logger.info(f"Reindexados {len(updates)} conceitos...")
            else:
                break
        
        logger.info(f"Reindexação concluída. Total de nós atualizados: {total_updated}")
        return total_updated
