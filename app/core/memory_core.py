# app/core/memory_core.py

import logging
from app.db.vector_store import get_or_create_collection
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
            metadata_to_store = experience.metadata.copy()
            metadata_to_store['type'] = experience.type
            metadata_to_store['timestamp'] = experience.timestamp

            self.collection.add(
                ids=[experience.id],
                documents=[experience.content],
                metadatas=[metadata_to_store]
            )
            logger.info(f"Experiência memorizada com sucesso (ID: {experience.id})")
        except Exception as e:
            logger.error(f"Erro ao memorizar a experiência {experience.id}: {e}", exc_info=True)

    def recall(self, query: str, n_results: int = 5) -> list[dict]:
        """
        Recupera as N experiências mais similares a uma consulta e as formata
        para corresponderem ao schema Pydantic 'Experience'.
        """
        if not self.collection:
            logger.error("Não é possível recordar, a coleção de memória não está disponível.")
            return []

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            ids = results.get('ids', [[]])[0]
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]

            logger.info(f"Recordadas {len(ids)} experiências para a consulta: '{query}'")

            recalled_experiences = []
            for i, doc_id in enumerate(ids):
                meta = metadatas[i]

                experience_data = {
                    "id": doc_id,
                    "content": documents[i],
                    "metadata": meta,
                    "type": meta.get('type', 'unknown'), # Pega o 'type' dos metadados
                    "timestamp": meta.get('timestamp', ''), # Pega o 'timestamp' dos metadados
                }
                recalled_experiences.append(experience_data)

            return recalled_experiences
        except Exception as e:
            logger.error(f"Erro ao recordar experiências para a consulta '{query}': {e}", exc_info=True)
            return []

# Instância única para ser usada na aplicação
memory_core = EpisodicMemory()