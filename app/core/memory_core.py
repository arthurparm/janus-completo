# app/core/memory_core.py

import json
import logging
from uuid import uuid4
from qdrant_client import QdrantClient, models
from langchain_community.vectorstores import Qdrant  # Reserva para integrações futuras
from langchain_openai import OpenAIEmbeddings  # Exemplo de modelo de embedding

from app.db.vector_store import get_qdrant_client, get_or_create_collection
from app.models.schemas import Experience

logger = logging.getLogger(__name__)

COLLECTION_NAME = "janus_episodic_memory"

# Inicializa a coleção no início para garantir que ela exista
try:
    get_or_create_collection(COLLECTION_NAME)
except ConnectionError as e:
    logger.error(f"Não foi possível inicializar a coleção do Qdrant: {e}")


def _sanitize_metadata(metadata: dict) -> dict:
    # Esta função continua útil para garantir que os metadados são compatíveis com JSON
    # e podem ser armazenados como payload no Qdrant.
    sanitized = {}
    for key, value in metadata.items():
        if isinstance(value, (dict, list)):
            # Qdrant pode lidar com objetos aninhados, mas serializar para JSON é mais seguro
            # para evitar problemas de compatibilidade de tipos.
            try:
                sanitized[key] = json.dumps(value, ensure_ascii=False)
            except (TypeError, OverflowError):
                sanitized[key] = str(value)  # Fallback
        elif isinstance(value, (str, int, float, bool)) or value is None:
            sanitized[key] = value
        else:
            sanitized[key] = str(value)
    return sanitized


class EpisodicMemory:
    def __init__(self):
        try:
            self.client: QdrantClient = get_qdrant_client()
            # Exemplo de como inicializar um modelo de embedding. Em um projeto real,
            # isso viria de um gerenciador centralizado.
            self.encoder = OpenAIEmbeddings()
            logger.info(f"Memória episódica conectada ao Qdrant, coleção '{COLLECTION_NAME}'.")
        except Exception as e:
            self.client = None
            self.encoder = None
            logger.error(f"Falha ao inicializar a memória episódica com Qdrant: {e}", exc_info=True)

    def memorize(self, experience: Experience):
        """Salva uma única experiência no banco de dados vetorial Qdrant."""
        if not self.client or not self.encoder:
            logger.error("Não é possível memorizar, o cliente Qdrant ou o encoder não estão disponíveis.")
            return

        try:
            # Gera o embedding para o conteúdo da experiência
            vector = self.encoder.embed_query(experience.content)

            # Prepara o payload (metadados)
            payload = experience.metadata.copy()
            payload['type'] = experience.type
            payload['timestamp'] = experience.timestamp
            payload['content'] = experience.content  # Armazenamos o conteúdo original no payload
            safe_payload = _sanitize_metadata(payload)

            # Adiciona o ponto ao Qdrant
            self.client.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    models.PointStruct(
                        id=experience.id,
                        vector=vector,
                        payload=safe_payload
                    )
                ],
                wait=True
            )
            logger.info(f"Experiência memorizada com sucesso no Qdrant (ID: {experience.id})")
        except Exception as e:
            logger.error(f"Erro ao memorizar a experiência {experience.id} no Qdrant: {e}", exc_info=True)

    def recall(self, query: str, n_results: int = 5) -> list[dict]:
        """Recupera as N experiências mais similares a uma consulta do Qdrant."""
        if not self.client or not self.encoder:
            logger.error("Não é possível recordar, o cliente Qdrant ou o encoder não estão disponíveis.")
            return []

        try:
            # Gera o embedding para a consulta
            query_vector = self.encoder.embed_query(query)

            # Executa a busca no Qdrant
            search_results = self.client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_vector,
                limit=n_results,
                with_payload=True  # Para recuperar os metadados
            )

            recalled_experiences = []
            for scored_point in search_results:
                experience_data = {
                    "id": scored_point.id,
                    "content": scored_point.payload.get('content', ''),
                    "metadata": {k: v for k, v in scored_point.payload.items() if k != 'content'},
                    "distance": 1 - scored_point.score  # Qdrant score é similaridade, distância é 1 - similaridade
                }
                recalled_experiences.append(experience_data)

            logger.info(f"Recordadas {len(recalled_experiences)} experiências do Qdrant para a consulta: '{query}'")
            return recalled_experiences
        except Exception as e:
            logger.error(f"Erro ao recordar experiências do Qdrant para a consulta '{query}': {e}", exc_info=True)
            return []

# Instância única para ser usada na aplicação
memory_core = EpisodicMemory()
