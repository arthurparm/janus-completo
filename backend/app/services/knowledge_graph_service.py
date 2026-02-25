import structlog
import asyncio
from typing import Any
from datetime import datetime

from app.db.graph import get_graph_db
from app.core.infrastructure.resilience import CircuitOpenError
from app.core.memory.graph_guardian import graph_guardian
from app.models.schemas import EntityType, RelationType, KnowledgeEntity, KnowledgeRelationship, Experience

logger = structlog.get_logger(__name__)


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

    async def persist_experience_node(
        self, experience: Experience, user_id: str | None = None
    ) -> str | None:
        """
        Cria um nó de Experience no grafo e o conecta ao fluxo de memória (NEXT).
        Implementa o 'Memory Stream' de Park et al. (2023).
        """
        db = await self.get_db()

        # Propriedades do nó
        props = {
            "id": experience.id,
            "content": experience.content[:500] if experience.content else "",  # Truncate content for graph
            "type": experience.type,
            "timestamp": experience.timestamp,
            "importance": experience.metadata.importance or 0.0,
            "created_at": datetime.now().isoformat(),
        }
        try:
            meta = experience.metadata.model_dump() if hasattr(experience.metadata, "model_dump") else dict(experience.metadata or {})
        except Exception:
            meta = {}
        if meta:
            props["origin"] = meta.get("origin")
            props["metadata_type"] = meta.get("type")
            props["memory_subtype"] = meta.get("memory_subtype")
            props["preference_kind"] = meta.get("preference_kind")
            props["preference_scope"] = meta.get("scope")
            props["preference_confidence"] = meta.get("confidence")
            props["user_id"] = str(meta.get("user_id")) if meta.get("user_id") is not None else None
            props["conversation_id"] = str(meta.get("conversation_id")) if meta.get("conversation_id") is not None else None
            if meta.get("instruction_text"):
                props["instruction_text"] = str(meta.get("instruction_text"))[:500]

        params = {"props": props}
        
        # Cria o nó
        cypher = """
        MERGE (e:Experience {id: $props.id})
        SET e += $props
        """

        if user_id:
            params["user_id"] = user_id
            # Conectar ao User e ao fluxo (NEXT)
            cypher += """
            WITH e
            MERGE (u:User {name: $user_id})
            MERGE (u)-[:HAS_EXPERIENCE]->(e)
            WITH e, u
            MATCH (u)-[:HAS_EXPERIENCE]->(prev:Experience)
            WHERE prev.id <> e.id AND prev.timestamp < e.timestamp
            WITH e, prev
            ORDER BY prev.timestamp DESC
            LIMIT 1
            MERGE (prev)-[:NEXT]->(e)
            """

        cypher += " RETURN elementId(e) as id"

        try:
            result = await db.query(cypher, params)
            if result:
                return result[0]["id"]
            return None
        except Exception as ex:
            logger.error("log_error", message=f"Erro ao persistir nó de experiência: {ex}")
            return None

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
        for idx, ent in enumerate(entities):
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

            except CircuitOpenError as e:
                remaining = max(0, len(entities) - idx)
                logger.warning(
                    "Circuit breaker aberto durante persistencia de entidades; "
                    f"abortando lote (restantes={remaining}): {e}"
                )
                break
            except Exception as e:
                logger.error("log_error", message=f"Erro ao persistir entidade '{ent.get('name')}': {e}", exc_info=True)

        # 2. Persistir Relacionamentos
        for idx, rel in enumerate(relationships):
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
                    logger.warning("log_warning", message=f"Relacionamento ignorado (nós não encontrados): {source_name} -> {target_name}"
                    )

            except CircuitOpenError as e:
                remaining = max(0, len(relationships) - idx)
                logger.warning(
                    "Circuit breaker aberto durante persistencia de relacionamentos; "
                    f"abortando lote (restantes={remaining}): {e}"
                )
                break
            except Exception as e:
                logger.error("log_error", message=f"Erro ao persistir relacionamento: {e}", exc_info=True)

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

        # Validação de política
        # Usamos CONCEPT como tipo genérico já que não temos o tipo da entidade aqui
        if not graph_guardian.check_policy("CONCEPT", relation):
            return True

        return False

    async def _send_to_quarantine(self, rel: dict[str, Any], context_id: str, reason: str):
        """Envia item para quarentena."""
        await graph_guardian.quarantine_item(
            item_type="relationship", content=rel, source_id=context_id, reason=reason
        )

    async def get_subgraph_from_context(self, node_names: list[str], hops: int = 1) -> dict[str, Any]:
        """
        Retorna um subgrafo contendo os nós especificados e seus vizinhos até 'hops' de distância.
        Otimizado para visualização contextual no frontend.
        """
        if not node_names:
            return {"nodes": [], "edges": []}

        db = await self.get_db()
        
        # Query otimizada para buscar vizinhança
        # Limita a 50 nós para não travar a UI
        cypher = f"""
        MATCH (start:Entity)
        WHERE start.name IN $names
        CALL apoc.path.subgraphAll(start, {{
            maxLevel: $hops,
            limit: 50
        }})
        YIELD nodes, relationships
        RETURN nodes, relationships
        """
        
        # Fallback se APOC não estiver disponível (query nativa mais simples)
        # cypher_native = ... (omitted for brevity, assume APOC or standard traversal)
        
        # Usa travessia padrão Cypher para operar sem dependência de APOC
        cypher_standard = """
        MATCH (n:Entity)
        WHERE n.name IN $names
        OPTIONAL MATCH (n)-[r]-(m)
        RETURN collect(distinct n) + collect(distinct m) as nodes, collect(distinct r) as edges
        LIMIT 100
        """

        try:
            result = await db.query(cypher_standard, {"names": node_names})
            if not result:
                return {"nodes": [], "edges": []}

            raw_nodes = result[0].get("nodes", [])
            raw_edges = result[0].get("edges", [])

            # Formatar para Cytoscape JSON
            # Nodes: { data: { id: "x", label: "x", type: "Person" } }
            # Edges: { data: { source: "a", target: "b", label: "KNOWS" } }
            
            nodes_out = []
            edges_out = []
            seen_nodes = set()

            for n in raw_nodes:
                # Neo4j Node object access depends on driver wrapper. 
                # Assuming wrapper returns dict-like with 'elementId' or 'id' and properties.
                # Adjust based on actual graph db wrapper implementation.
                
                # Se for objeto Neo4j, extrair props. Se for dict, usar direto.
                props = dict(n) if hasattr(n, 'items') else {}
                # Tentar pegar ID. Se não, usar name.
                nid = props.get("elementId") or props.get("name")
                if not nid or nid in seen_nodes:
                    continue
                
                seen_nodes.add(nid)
                nodes_out.append({
                    "data": {
                        "id": nid,
                        "label": props.get("name", "Unknown"),
                        "type": props.get("type", "Entity"),
                        "color": "#4F46E5" if props.get("name") in node_names else "#9CA3AF" # Highlight context nodes
                    }
                })

            for r in raw_edges:
                # Neo4j Relationship object
                # Need start_node and end_node IDs (names in our case if mapped above)
                # This part is tricky without knowing the exact DB wrapper return type.
                # Assuming standard neo4j python driver behavior where start_node/end_node are accessible
                # BUT our `db.query` wrapper might return serialized dicts.
                
                # Se o wrapper retornar dict com 'start', 'end', 'type':
                r_props = dict(r) if hasattr(r, 'items') else {}
                
                # Se o DB wrapper não resolver os IDs de start/end, essa query precisa retornar explicitamente
                # start.name e end.name. Vamos ajustar a query para ser mais segura.
                pass
            
            # Re-executando com query explícita para facilitar parsing
            cypher_explicit = """
            MATCH (n:Entity)
            WHERE n.name IN $names
            OPTIONAL MATCH (n)-[r]-(m:Entity)
            RETURN 
                n.name as source_name, 
                n.type as source_type, 
                type(r) as rel_type, 
                m.name as target_name, 
                m.type as target_type
            LIMIT 100
            """
            
            rows = await db.query(cypher_explicit, {"names": node_names})
            
            nodes_map = {}
            edges_list = []
            
            for row in rows:
                s_name = row.get("source_name")
                t_name = row.get("target_name")
                
                if s_name:
                    nodes_map[s_name] = {"id": s_name, "label": s_name, "type": row.get("source_type", "Entity")}
                
                if t_name:
                    nodes_map[t_name] = {"id": t_name, "label": t_name, "type": row.get("target_type", "Entity")}
                    
                if s_name and t_name and row.get("rel_type"):
                    edges_list.append({
                        "data": {
                            "source": s_name,
                            "target": t_name,
                            "label": row.get("rel_type")
                        }
                    })
            
            # Formatar output final
            final_nodes = [{"data": {**v, "color": "#4F46E5" if v["id"] in node_names else "#9CA3AF"}} for v in nodes_map.values()]
            
            return {
                "nodes": final_nodes,
                "edges": edges_list
            }

        except Exception as e:
            logger.error("log_error", message=f"Erro ao buscar subgrafo contextual: {e}", exc_info=True)
            return {"nodes": [], "edges": []}


# Singleton global (opcional)
_service_instance = None


def get_knowledge_graph_service():
    global _service_instance
    if _service_instance is None:
        _service_instance = KnowledgeGraphService()
    return _service_instance
