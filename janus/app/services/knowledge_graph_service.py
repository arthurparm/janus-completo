import logging
import asyncio
from typing import Any
from datetime import datetime

from app.db.graph import get_graph_db
from app.core.memory.graph_guardian import graph_guardian
from app.models.schemas import EntityType, RelationType, KnowledgeEntity, KnowledgeRelationship

logger = logging.getLogger(__name__)


class KnowledgeGraphService:
    """
    Serviço responsável por operações de alto nível no Knowledge Graph (Neo4j),
    incluindo persistência de entidades, relacionamentos e validação via GraphGuardian.
    """

    def __init__(self):
        self._graph_db = None

    async def get_db(self):
        if not self._graph_db:
            self._graph_db = await get_graph_db()
        return self._graph_db

    async def persist_extraction(
        self, experience_id: str, extracted_data: dict[str, Any], source_metadata: dict[str, Any]
    ) -> tuple[int, int]:
        """
        Persiste entidades e relacionamentos extraídos no Neo4j, aplicando validação e quarentena.

        Returns:
            Tupla (num_entidades_criadas, num_relacionamentos_criados)
        """
        db = await self.get_db()

        entities = extracted_data.get("entities", [])
        relationships = extracted_data.get("relationships", [])

        created_entities_count = 0
        created_relationships_count = 0

        # Mapeamento local de IDs temporários (do LLM) para eementos reais
        # O LLM pode retornar IDs arbitrários. Precisamos normalizar.

        # 1. Persistir Entidades
        for ent in entities:
            try:
                # Normalização e Validação
                name = ent.get("name", "").strip()
                type_str = ent.get("type", "unknown").lower()

                if not name or len(name) < 2:
                    continue

                # Tentar mapear string para Enum
                try:
                    entity_type = EntityType(type_str)
                except ValueError:
                    entity_type = EntityType.CONCEPT  # Fallback seguro

                # Criar nó
                properties = {
                    "name": name,
                    "description": ent.get("description", ""),
                    "source_experience": experience_id,
                    "confidence": ent.get("confidence", 0.5),
                    "created_at": datetime.now().isoformat(),
                }

                # Merge (cria ou atualiza se já existir pelo nome)
                # Nota: Idealmente usaríamos um ID único, mas para consolidação de conhecimento
                # fusão por nome é frequentemente desejada.
                query = f"""
                MERGE (e:Entity {{name: $name}})
                ON CREATE SET e.type = $type, e += $props
                ON MATCH SET e.last_seen = $now
                RETURN elementId(e) as id
                """

                await db.query(
                    query,
                    {
                        "name": name,
                        "type": entity_type.value,
                        "props": properties,
                        "now": datetime.now().isoformat(),
                    },
                )

                created_entities_count += 1

            except Exception as e:
                logger.error(f"Erro ao persistir entidade '{ent.get('name')}': {e}", exc_info=True)

        # 2. Persistir Relacionamentos
        for rel in relationships:
            try:
                source_name = rel.get("source", "").strip()
                target_name = rel.get("target", "").strip()
                rel_type_str = rel.get("relation", "RELATED_TO").upper().replace(" ", "_")

                if not source_name or not target_name:
                    continue

                # Validação via Graph Guardian (Quarentena)
                if self._should_quarantine(rel):
                    await self._send_to_quarantine(rel, experience_id, "Policy Violation")
                    continue

                # Validar tipo de relacionamento
                try:
                    relation_type = RelationType(rel_type_str)
                except ValueError:
                    # Se não for um tipo conhecido, marca como genérico 'RELATED_TO'
                    # ou tenta inferir.
                    relation_type = RelationType.RELATED_TO

                # Criar aresta
                # Assume que nós já existem (pelo passo 1) ou cria placeholders
                query = f"""
                MATCH (source:Entity {{name: $source_name}})
                MATCH (target:Entity {{name: $target_name}})
                MERGE (source)-[r:{relation_type.value}]->(target)
                ON CREATE SET r.weight = $weight, r.source_exp = $exp_id, r.created_at = $now
                ON MATCH SET r.weight = r.weight + 0.1, r.last_seen = $now
                RETURN type(r)
                """

                result = await db.query(
                    query,
                    {
                        "source_name": source_name,
                        "target_name": target_name,
                        "weight": rel.get("weight", 0.5),
                        "exp_id": experience_id,
                        "now": datetime.now().isoformat(),
                    },
                )

                if result:
                    created_relationships_count += 1
                else:
                    # Se falhou, pode ser que um dos nós não exista (ex: erro de digitação do LLM)
                    logger.warning(
                        f"Relacionamento ignorado (nós não encontrados): {source_name} -> {target_name}"
                    )

            except Exception as e:
                logger.error(f"Erro ao persistir relacionamento: {e}", exc_info=True)

        return created_entities_count, created_relationships_count

    def _should_quarantine(self, rel: dict[str, Any]) -> bool:
        """Verifica se o relacionamento deve ir para quarentena."""
        # Integração com GraphGuardian
        source = rel.get("source")
        target = rel.get("target")
        relation = rel.get("relation")

        # Exemplo de regra simples
        if source == target:
            return True  # Auto-referência suspeita

        # TODO: Chamar graph_guardian.check_policy(...)
        # Por enquanto mantemos lógica simples para não quebrar contrato
        return False

    async def _send_to_quarantine(self, rel: dict[str, Any], context_id: str, reason: str):
        """Envia item para quarentena."""
        await graph_guardian.quarantine_item(
            item_type="relationship", content=rel, source_id=context_id, reason=reason
        )


# Singleton global (opcional)
_service_instance = None


def get_knowledge_graph_service():
    global _service_instance
    if _service_instance is None:
        _service_instance = KnowledgeGraphService()
    return _service_instance
