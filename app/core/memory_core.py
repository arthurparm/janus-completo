# app/core/memory_core.py

import json
import logging

from app.db.vector_store import get_or_create_collection
from app.models.schemas import Experience

logger = logging.getLogger(__name__)

COLLECTION_NAME = "janus_episodic_memory"


def _sanitize_metadata(metadata: dict) -> dict:
    """
    Garante que todos os valores no dicionário de metadados sejam de tipos primitivos
    suportados pelo ChromaDB (str, int, float, bool). Converte tipos complexos
    (dict, list) para strings JSON.
    """
    sanitized = {}
    for key, value in metadata.items():
        if isinstance(value, (dict, list)):
            sanitized[key] = json.dumps(value, ensure_ascii=False)
        elif isinstance(value, (str, int, float, bool)) or value is None:
            sanitized[key] = value
        else:
            # Converte qualquer outro tipo para string como uma salvaguarda.
            sanitized[key] = str(value)
    return sanitized


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
            # Junta os metadados do objeto com as suas propriedades de nível superior.
            metadata_to_store = experience.metadata.copy()
            metadata_to_store['type'] = experience.type
            metadata_to_store['timestamp'] = experience.timestamp

            # --- CORREÇÃO CRÍTICA ---
            # Sanitiza os metadados para garantir a compatibilidade com o ChromaDB.
            safe_metadata = _sanitize_metadata(metadata_to_store)

            self.collection.add(
                ids=[experience.id],
                documents=[experience.content],
                metadatas=[safe_metadata]
            )
            logger.info(f"Experiência memorizada com sucesso (ID: {experience.id})")
        except Exception as e:
            logger.error(f"Erro ao memorizar a experiência {experience.id}: {e}", exc_info=True)

    def recall(self, query: str, n_results: int = 5) -> list[dict]:
        """
        Recupera as N experiências mais similares a uma consulta, incluindo a distância.
        """
        if not self.collection:
            logger.error("Não é possível recordar, a coleção de memória não está disponível.")
            return []

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["metadatas", "documents", "distances"]  # Garante que a distância seja incluída
            )

            ids = results.get('ids', [[]])[0]
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]

            logger.info(f"Recordadas {len(ids)} experiências para a consulta: '{query}'")

            recalled_experiences = []
            for i, doc_id in enumerate(ids):
                # --- CORREÇÃO CRÍTICA ---
                # A estrutura agora corresponde ao `RecallResponse` da API, incluindo a distância.
                experience_data = {
                    "id": doc_id,
                    "content": documents[i],
                    "metadata": metadatas[i] or {},
                    "distance": distances[i]
                }
                recalled_experiences.append(experience_data)

            return recalled_experiences
        except Exception as e:
            logger.error(f"Erro ao recordar experiências para a consulta '{query}': {e}", exc_info=True)
            return []


# Instância única para ser usada na aplicação
memory_core = EpisodicMemory()
