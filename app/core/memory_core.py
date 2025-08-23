# app/core/memory_core.py
from app.db.vector_store import get_or_create_collection
import logging

from app.models.schemas import Experience

logger = logging.getLogger(__name__)

COLLECTION_NAME = "janus_episodic_memory"

class EpisodicMemory:
    def __init__(self):
        try:
            self.collection = get_or_create_collection(COLLECTION_NAME)
            logger.info(f"Memória episódica conectada à coleção '{COLLECTION_NAME}'.")
        except Exception as e:
            self.collection = None
            logger.error(f"Falha ao inicializar a memória episódica: {e}", exc_info=True)

    def memorize(self, experience: Experience):
        """Salva uma única experiência no banco de dados vetorial."""
        if not self.collection:
            logger.error("Não é possível memorizar, a coleção de memória não está disponível.")
            return

        try:
            self.collection.add(
                ids=[experience.id],
                documents=[experience.content],
                metadatas=[experience.metadata]
            )
            logger.info(f"Experiência memorizada com sucesso (ID: {experience.id})")
        except Exception as e:
            logger.error(f"Erro ao memorizar a experiência {experience.id}: {e}", exc_info=True)

    def recall(self, query: str, n_results: int = 5) -> list[dict]:
        """Recupera as N experiências mais similares a uma consulta."""
        if not self.collection:
            logger.error("Não é possível recordar, a coleção de memória não está disponível.")
            return []

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            logger.info(f"Recordadas {len(results.get('ids', [[]])[0])} experiências para a consulta: '{query}'")

            # Formata a saída para ser mais útil
            recalled_experiences = []
            for i, doc_id in enumerate(results.get('ids', [[]])[0]):
                recalled_experiences.append({
                    "id": doc_id,
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i]
                })
            return recalled_experiences
        except Exception as e:
            logger.error(f"Erro ao recordar experiências para a consulta '{query}': {e}", exc_info=True)
            return []

# Instância única para ser usada na aplicação
memory_core = EpisodicMemory()