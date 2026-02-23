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

    async def vector_search(self, query: str, k: int = 10, min_score: float = 0.7, label: str = "Concept") -> list[dict[str, Any]]:
        """
        Realiza busca vetorial direta no Neo4j.
        Suporta múltiplos índices por label.
        """
        try:
            vector = await aembed_text(query)
            if not vector:
                return []
            
            db = await self._db_getter()
            if not db:
                return []

            # Determine index name based on label
            index_name = f"{label.lower()}_embeddings"
            
            # Neo4j 5.11+ syntax
            results = await db.query(
                f"""
                CALL db.index.vector.queryNodes($index_name, $k, $vector)
                YIELD node, score
                WHERE score >= $min_score
                RETURN node, score, id(node) as id, labels(node) as labels
                """,
                {"index_name": index_name, "k": k, "vector": vector, "min_score": min_score},
            )
            return results
        except Exception as e:
            logger.error(f"Erro na busca vetorial no Neo4j (Index: {index_name}): {e}")
            return []

    async def fulltext_search(self, query: str, k: int = 10) -> list[dict[str, Any]]:
        """
        Realiza busca Full-Text (Lexical) no índice universal 'keyword_search'.
        """
        try:
            db = await self._db_getter()
            if not db:
                return []
            
            # Lucene query syntax approximation
            # Adding wildcards or fuzziness could be an enhancement
            search_query = f"{query}*" 

            results = await db.query(
                """
                CALL db.index.fulltext.queryNodes("keyword_search", $query, {limit: $k})
                YIELD node, score
                RETURN node, score, id(node) as id, labels(node) as labels
                """,
                {"query": search_query, "k": k}
            )
            return results
        except Exception as e:
            logger.error(f"Erro na busca Full-Text no Neo4j: {e}")
            return []

    async def hybrid_search(self, query: str, k: int = 10) -> list[dict[str, Any]]:
        """
        Realiza busca Híbrida (Vector + Lexical) combinando resultados.
        Estratégia: RRF (Reciprocal Rank Fusion) simplificada ou Weighted Merge.
        Aqui usamos Weighted Merge simples.
        """
        # 1. Vector Search (Primary Context - Concept)
        # TODO: Expandir para buscar em múltiplos índices vetoriais se necessário (Tech, Tool...)
        # Por enquanto, foca em Concept como entrada semântica principal.
        vec_results = await self.vector_search(query, k=k, label="Concept")
        
        # 2. Key entities from query (Technology/Tool) might be better found via separate vector search?
        # Let's try to search ALL vector indexes? Too slow.
        # Fallback: FullText Search (covers ALL labels)
        ft_results = await self.fulltext_search(query, k=k)

        # 3. Merge Strategies
        # Normalizar scores? Vector (0-1), Lucene (unbounded, often > 1)
        # Simplificação: Usar ID para deduplicar e boostar.
        
        merged = {}
        
        # Process Vector Results (Weight 1.0)
        for res in vec_results:
            nid = res["id"]
            merged[nid] = {
                "node": res["node"],
                "score": res["score"],
                "source": "vector",
                "labels": res["labels"],
                "id": nid
            }

        # Process FullText Results (Weight 0.5 normalize?)
        # Lucene score is arbitrary. Let's trust Neo4j rank.
        for res in ft_results:
            nid = res["id"]
            if nid in merged:
                # Boost existing
                merged[nid]["score"] += (res["score"] * 0.2) # Small boost if matching both
                merged[nid]["source"] = "hybrid"
            else:
                merged[nid] = {
                    "node": res["node"],
                    "score": res["score"] * 0.5, # Penalize lexical only slightly
                    "source": "text",
                    "labels": res["labels"],
                    "id": nid
                }
        
        # Sort by score desc
        final_list = list(merged.values())
        final_list.sort(key=lambda x: x["score"], reverse=True)
        return final_list[:k]

    async def reindex_graph(self, batch_size: int = 50, labels: list[str] = None):
        """
        Job de migração/correção: Varre nós sem embedding e gera (Universal).
        Labels suportadas: Concept, Technology, Tool, Pattern, Solution, Error.
        """
        target_labels = labels or ["Concept", "Technology", "Tool", "Pattern", "Solution", "Error"]
        logger.info(f"Iniciando reindexação universal para labels: {target_labels}")
        
        db = await self._db_getter()
        if not db:
            return 0

        total_updated = 0
        
        for label in target_labels:
            logger.info(f"Processando label: {label}...")
            while True:
                # Busca lote de nós sem embedding
                nodes = await db.query(
                    f"""
                    MATCH (n:{label})
                    WHERE n.embedding IS NULL AND n.name IS NOT NULL
                    RETURN id(n) as id, n.name as text
                    LIMIT $limit
                    """,
                    {"limit": batch_size},
                )

                if not nodes:
                    break

                updates = []
                # Prepare batch text list
                texts = [node["text"] for node in nodes]
                
                # Batch Embed
                vectors = await self.embed_batch(texts)
                
                for i, node in enumerate(nodes):
                    if i < len(vectors) and vectors[i]:
                        updates.append({"id": node["id"], "vector": vectors[i]})

                if updates:
                    await db.execute(
                        """
                        UNWIND $updates as row
                        MATCH (n) WHERE id(n) = row.id
                        SET n.embedding = row.vector
                        """,
                        {"updates": updates}
                    )
                    total_updated += len(updates)
                    logger.info(f"Label {label}: Reindexados {len(updates)} nós...")
                else:
                    # Se falhou em gerar, break loop to avoid infinite loop on bad nodes
                    # Ou marcar como falha? Por simplicidade, break se não conseguiu updates
                    # Mas se tiver muito erro, vai parar cedo.
                    # Ideal: marcar n.embedding_failed = true.
                    # MVP: break
                    break
        
        logger.info(f"Reindexação universal concluída. Total: {total_updated}")
        return total_updated
