import asyncio
import re
from collections import OrderedDict
from datetime import datetime
from typing import Any

import structlog
from prometheus_client import Counter

from app.db.graph import get_graph_db
from app.core.infrastructure.resilience import CircuitOpenError
from app.core.memory.graph_guardian import graph_guardian
from app.models.schemas import EntityType, RelationType, KnowledgeEntity, KnowledgeRelationship, Experience

logger = structlog.get_logger(__name__)

_GRAPH_ENTITIES_NORMALIZED_TOTAL = Counter(
    "graph_entities_normalized_total",
    "Total de entidades normalizadas antes da persistencia no grafo",
)
_GRAPH_ENTITY_ALIAS_ADDED_TOTAL = Counter(
    "graph_entity_alias_added_total",
    "Total de aliases adicionados em nós Entity",
)
_GRAPH_RELATIONSHIPS_DEDUPED_IN_BATCH_TOTAL = Counter(
    "graph_relationships_deduped_in_batch_total",
    "Total de relacionamentos deduplicados dentro do mesmo lote de extração",
)
_GRAPH_RELATIONSHIPS_FALLBACK_GENERIC_TOTAL = Counter(
    "graph_relationships_fallback_generic_total",
    "Total de relacionamentos mapeados para o fallback genérico RELATED_TO",
)
_GRAPH_RELATIONSHIPS_QUARANTINED_TOTAL = Counter(
    "graph_relationships_quarantined_total",
    "Total de relacionamentos enviados para quarentena",
)


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

    async def _run_rows(self, target: Any, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if hasattr(target, "run"):
            result = await target.run(query, **(params or {}))
            return [record.data() async for record in result]
        return await target.query(query, params or {})

    async def _ensure_experience_node(
        self,
        target: Any,
        *,
        experience_id: str,
        source_metadata: dict[str, Any],
    ) -> None:
        now = datetime.now().isoformat()
        await self._run_rows(
            target,
            """
            MERGE (exp:Experience {id: $experience_id})
            SET exp.created_at = coalesce(exp.created_at, $now),
                exp.updated_at = $now,
                exp.origin = coalesce($origin, exp.origin),
                exp.source_kind = coalesce($source_kind, exp.source_kind),
                exp.content_kind = coalesce($content_kind, exp.content_kind),
                exp.file_path = coalesce($file_path, exp.file_path),
                exp.sha_after = coalesce($sha_after, exp.sha_after),
                exp.consolidation_hash = coalesce($consolidation_hash, exp.consolidation_hash),
                exp.captured_at = coalesce($captured_at, exp.captured_at)
            RETURN exp.id AS id
            """,
            {
                "experience_id": experience_id,
                "now": now,
                "origin": source_metadata.get("origin"),
                "source_kind": source_metadata.get("source_kind"),
                "content_kind": source_metadata.get("content_kind") or source_metadata.get("type"),
                "file_path": source_metadata.get("file_path"),
                "sha_after": source_metadata.get("sha_after"),
                "consolidation_hash": source_metadata.get("consolidation_hash"),
                "captured_at": source_metadata.get("captured_at"),
            },
        )

    async def _link_self_memory_provenance(self, target: Any, experience_id: str) -> None:
        await self._run_rows(
            target,
            """
            MATCH (m:SelfMemory {source_experience_id: $experience_id})
            MATCH (exp:Experience {id: $experience_id})
            MERGE (m)-[:EXTRACTED_FROM]->(exp)
            RETURN count(m) AS linked
            """,
            {"experience_id": experience_id},
        )

    async def persist_experience_node(
        self, experience: Experience
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
            props["conversation_id"] = str(meta.get("conversation_id")) if meta.get("conversation_id") is not None else None
            if meta.get("instruction_text"):
                props["instruction_text"] = str(meta.get("instruction_text"))[:500]

        params = {"props": props}
        
        # Cria o nó
        cypher = """
        MERGE (e:Experience {id: $props.id})
        SET e += $props
        RETURN elementId(e) as id
        """

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
        prepared_entities = self._prepare_entities_batch(entities)
        prepared_relationships = self._prepare_relationships_batch(relationships)

        created_entities_count = 0
        created_relationships_count = 0
        source_metadata = dict(source_metadata or {})
        consolidation_hash = str(source_metadata.get("consolidation_hash") or "").strip()
        session = None
        tx = None
        target: Any = db
        if hasattr(db, "get_session"):
            try:
                session = await db.get_session()
                tx = await session.begin_transaction()
                target = tx
            except Exception:
                target = db
                tx = None
                session = None

        try:
            try:
                await self._ensure_experience_node(
                    target,
                    experience_id=experience_id,
                    source_metadata=source_metadata,
                )
            except CircuitOpenError as e:
                logger.warning(
                    "Circuit breaker aberto durante persistencia de proveniencia; "
                    f"abortando lote completo: {e}"
                )
                return 0, 0

            for idx, ent in enumerate(prepared_entities):
                try:
                    now = datetime.now().isoformat()
                    result = await self._run_rows(
                        target,
                        """
                        MERGE (e:Entity {canonical_name: $canonical_name})
                        ON CREATE SET
                            e.type = $type,
                            e.name = $display_name,
                            e.description = $description,
                            e.source_experience = $exp_id,
                            e.source_experiences = CASE WHEN $exp_id IS NULL THEN [] ELSE [$exp_id] END,
                            e.confidence = $confidence,
                            e.created_at = $now,
                            e.canonical_name = $canonical_name,
                            e.summary = coalesce($description, '')
                        ON MATCH SET
                            e.last_seen = $now,
                            e.canonical_name = coalesce(e.canonical_name, $canonical_name),
                            e.type = coalesce(e.type, $type),
                            e.source_experience = coalesce(e.source_experience, $exp_id),
                            e.confidence = CASE
                                WHEN coalesce(e.confidence, 0.0) >= $confidence THEN e.confidence
                                ELSE $confidence
                            END,
                            e.description = CASE
                                WHEN coalesce(e.description, '') = '' AND coalesce($description, '') <> '' THEN $description
                                ELSE e.description
                            END,
                            e.summary = CASE
                                WHEN coalesce(e.summary, '') = '' AND coalesce($description, '') <> '' THEN $description
                                ELSE e.summary
                            END
                        WITH e,
                             CASE
                                WHEN e.aliases IS NULL THEN CASE WHEN coalesce(e.name, '') = '' THEN [] ELSE [e.name] END
                                ELSE e.aliases
                             END AS current_aliases,
                             [a IN $aliases WHERE a IS NOT NULL AND trim(a) <> ''] AS alias_candidates,
                             CASE
                                WHEN e.source_experiences IS NULL THEN CASE WHEN $exp_id IS NULL THEN [] ELSE [$exp_id] END
                                ELSE e.source_experiences
                             END AS current_source_experiences
                        WITH e, current_aliases, alias_candidates, current_source_experiences,
                             size([a IN alias_candidates WHERE NOT a IN current_aliases]) AS alias_added_count
                        SET e.aliases = reduce(acc = current_aliases, a IN alias_candidates |
                            CASE WHEN a IN acc THEN acc ELSE acc + a END
                        )
                        SET e.source_experiences = reduce(acc = current_source_experiences, x IN CASE WHEN $exp_id IS NULL THEN [] ELSE [$exp_id] END |
                            CASE WHEN x IN acc THEN acc ELSE acc + x END
                        )
                        WITH e, alias_added_count
                        MATCH (exp:Experience {id: $exp_id})
                        MERGE (e)-[:EXTRACTED_FROM]->(exp)
                        RETURN elementId(e) as id, alias_added_count
                        """,
                        {
                            "canonical_name": ent["canonical_name"],
                            "display_name": ent["display_name"],
                            "aliases": ent["aliases"],
                            "type": ent["type"],
                            "description": ent.get("description", ""),
                            "confidence": ent.get("confidence", 0.5),
                            "exp_id": experience_id,
                            "now": now,
                        },
                    )
                    if result:
                        try:
                            alias_added = int(result[0].get("alias_added_count", 0) or 0)
                            if alias_added > 0:
                                _GRAPH_ENTITY_ALIAS_ADDED_TOTAL.inc(alias_added)
                        except Exception:
                            pass
                    created_entities_count += 1

                except CircuitOpenError as e:
                    remaining = max(0, len(prepared_entities) - idx)
                    logger.warning(
                        "Circuit breaker aberto durante persistencia de entidades; "
                        f"abortando lote (restantes={remaining}): {e}"
                    )
                    break
                except Exception as e:
                    logger.error(
                        "log_error",
                        message=f"Erro ao persistir entidade '{ent.get('display_name')}': {e}",
                        exc_info=True,
                    )

            for idx, rel in enumerate(prepared_relationships):
                try:
                    if self._should_quarantine(rel):
                        _GRAPH_RELATIONSHIPS_QUARANTINED_TOTAL.inc()
                        await self._send_to_quarantine(rel, experience_id, "Policy Violation")
                        continue

                    relation_type, used_generic_fallback = self._coerce_relation_type(rel.get("normalized_type"))
                    if used_generic_fallback:
                        _GRAPH_RELATIONSHIPS_FALLBACK_GENERIC_TOTAL.inc()
                    if hasattr(db, "register_relationship_type") and tx is not None:
                        await db.register_relationship_type(tx, relation_type.value)

                    result = await self._run_rows(
                        target,
                        f"""
                        MATCH (source:Entity)
                        WHERE source.canonical_name = $source_canonical
                           OR source.name = $source_canonical
                           OR source.name = $source_name
                        WITH source,
                             CASE
                                WHEN source.canonical_name = $source_canonical THEN 0
                                WHEN source.name = $source_canonical THEN 1
                                ELSE 2
                             END AS source_rank
                        ORDER BY source_rank ASC
                        LIMIT 1
                        MATCH (target:Entity)
                        WHERE target.canonical_name = $target_canonical
                           OR target.name = $target_canonical
                           OR target.name = $target_name
                        WITH source, target,
                             CASE
                                WHEN target.canonical_name = $target_canonical THEN 0
                                WHEN target.name = $target_canonical THEN 1
                                ELSE 2
                             END AS target_rank
                        ORDER BY target_rank ASC
                        LIMIT 1
                        MERGE (source)-[r:{relation_type.value}]->(target)
                        ON CREATE SET
                            r.weight = $weight,
                            r.source_exp = $exp_id,
                            r.created_at = $now,
                            r.first_seen = $now,
                            r.last_seen = $now,
                            r.support_count = CASE WHEN $consolidation_hash = '' THEN 0 ELSE 1 END,
                            r.source_hashes = CASE WHEN $consolidation_hash = '' THEN [] ELSE [$consolidation_hash] END
                        ON MATCH SET
                            r.last_seen = $now,
                            r.support_count = CASE
                                WHEN $consolidation_hash = '' OR $consolidation_hash IN coalesce(r.source_hashes, []) THEN coalesce(r.support_count, 0)
                                ELSE coalesce(r.support_count, 0) + 1
                            END,
                            r.source_hashes = CASE
                                WHEN $consolidation_hash = '' OR $consolidation_hash IN coalesce(r.source_hashes, []) THEN coalesce(r.source_hashes, [])
                                ELSE coalesce(r.source_hashes, []) + $consolidation_hash
                            END,
                            r.weight = CASE
                                WHEN coalesce(r.weight, 0.0) >= $weight THEN coalesce(r.weight, 0.0)
                                ELSE $weight
                            END
                        RETURN type(r) AS rel_type
                        """,
                        {
                            "source_name": rel["source"],
                            "target_name": rel["target"],
                            "source_canonical": rel["source_canonical"],
                            "target_canonical": rel["target_canonical"],
                            "weight": rel.get("weight", 0.5),
                            "exp_id": experience_id,
                            "now": datetime.now().isoformat(),
                            "consolidation_hash": consolidation_hash,
                        },
                    )
                    if result:
                        created_relationships_count += 1
                    else:
                        logger.warning(
                            "log_warning",
                            message=(
                                "Relacionamento ignorado (nós não encontrados): "
                                f"{rel.get('source')} -> {rel.get('target')}"
                            ),
                        )

                except CircuitOpenError as e:
                    remaining = max(0, len(prepared_relationships) - idx)
                    logger.warning(
                        "Circuit breaker aberto durante persistencia de relacionamentos; "
                        f"abortando lote (restantes={remaining}): {e}"
                    )
                    break
                except Exception as e:
                    logger.error("log_error", message=f"Erro ao persistir relacionamento: {e}", exc_info=True)

            await self._link_self_memory_provenance(target, experience_id)
            if tx is not None:
                await tx.commit()
        finally:
            if tx is not None:
                await tx.close()
            if session is not None:
                await session.close()

        return created_entities_count, created_relationships_count

    def _prepare_entities_batch(self, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: OrderedDict[str, dict[str, Any]] = OrderedDict()
        for ent in entities or []:
            raw_name = str(ent.get("name") or "").strip()
            if len(raw_name) < 2:
                continue
            if self._is_noise_entity_name(raw_name):
                logger.info("graph_entity_rejected_noise", name=raw_name)
                continue
            raw_type = str(ent.get("type") or "unknown")
            try:
                normalized = graph_guardian.validate_and_normalize_entity(raw_name, raw_type, ent)
            except Exception as exc:
                logger.warning(
                    "log_warning",
                    message=f"Entidade ignorada por erro de normalização '{raw_name}': {exc}",
                )
                continue

            canonical_name = str(normalized.get("name") or "").strip()
            if not canonical_name:
                continue
            if self._is_noise_entity_name(canonical_name):
                logger.info("graph_entity_rejected_noise", name=canonical_name)
                continue

            if raw_name != canonical_name:
                _GRAPH_ENTITIES_NORMALIZED_TOTAL.inc()

            schema_type = self._coerce_entity_type(normalized.get("type"))
            item = grouped.get(canonical_name)
            description = str(ent.get("description") or "").strip()
            confidence = float(ent.get("confidence", 0.5) or 0.5)
            if item is None:
                grouped[canonical_name] = {
                    "canonical_name": canonical_name,
                    "display_name": raw_name,
                    "aliases": [raw_name],
                    "type": schema_type.value,
                    "description": description,
                    "confidence": confidence,
                }
                continue

            if raw_name and raw_name not in item["aliases"]:
                item["aliases"].append(raw_name)
            if description and not item.get("description"):
                item["description"] = description
            try:
                item["confidence"] = max(float(item.get("confidence", 0.5) or 0.5), confidence)
            except Exception:
                item["confidence"] = item.get("confidence", 0.5)
        return list(grouped.values())

    def _is_noise_entity_name(self, value: str) -> bool:
        candidate = str(value or "").strip()
        if not candidate:
            return True
        lower = candidate.lower()
        if lower.startswith("dedupe key"):
            return True
        if re.search(r"^\*\.[a-z0-9]+$", lower):
            return True
        if "/" in candidate or "\\" in candidate:
            return True
        if re.search(r"\.(py|ts|tsx|js|jsx|scss|css|md|json|log|html?)$", lower):
            return True
        if lower.endswith(" directory") or lower in {"tmp", "var/tmp"}:
            return True
        if re.fullmatch(r"[@#/._-]+", candidate):
            return True
        return False

    def _prepare_relationships_batch(self, relationships: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: OrderedDict[tuple[str, str, str], dict[str, Any]] = OrderedDict()
        deduped_in_batch = 0

        for rel in relationships or []:
            source_name = str(rel.get("source") or "").strip()
            target_name = str(rel.get("target") or "").strip()
            raw_rel_type = str(rel.get("relation") or "RELATED_TO")
            if not source_name or not target_name:
                continue

            normalized = graph_guardian.validate_and_normalize_relationship(
                source_name, target_name, raw_rel_type, rel.get("properties")
            )
            if not normalized:
                # Mantemos o item inválido de fora; a validação já faz logging.
                continue

            source_canonical = str(normalized.get("from") or "").strip()
            target_canonical = str(normalized.get("to") or "").strip()
            normalized_type = str(normalized.get("type") or "").strip()
            if not source_canonical or not target_canonical or not normalized_type:
                continue

            key = (source_canonical, normalized_type, target_canonical)
            if key in grouped:
                deduped_in_batch += 1
                existing = grouped[key]
                try:
                    existing["weight"] = max(
                        float(existing.get("weight", 0.5) or 0.5),
                        float(rel.get("weight", 0.5) or 0.5),
                    )
                except Exception:
                    pass
                continue

            grouped[key] = {
                "source": source_name,
                "target": target_name,
                "source_canonical": source_canonical,
                "target_canonical": target_canonical,
                "relation": raw_rel_type,
                "normalized_type": normalized_type,
                "weight": rel.get("weight", 0.5),
                "properties": rel.get("properties") or {},
            }

        if deduped_in_batch > 0:
            _GRAPH_RELATIONSHIPS_DEDUPED_IN_BATCH_TOTAL.inc(deduped_in_batch)

        return list(grouped.values())

    def _coerce_entity_type(self, type_str: Any) -> EntityType:
        raw = str(type_str or "").strip()
        if not raw:
            return EntityType.CONCEPT
        try:
            return EntityType(raw)
        except ValueError:
            pass
        normalized = raw.lower()
        try:
            return EntityType(normalized)
        except ValueError:
            return EntityType.CONCEPT

    def _coerce_relation_type(self, normalized_rel_type: Any) -> tuple[RelationType, bool]:
        raw = str(normalized_rel_type or "").strip().upper().replace(" ", "_").replace("-", "_")
        if not raw:
            return RelationType.RELATED_TO, True
        if raw == "RELATES_TO":
            return RelationType.RELATED_TO, False
        try:
            return RelationType(raw), False
        except ValueError:
            return RelationType.RELATED_TO, True

    def _should_quarantine(self, rel: dict[str, Any]) -> bool:
        """Verifica se o relacionamento deve ir para quarentena."""
        # Integração com GraphGuardian
        source = str(rel.get("source") or "")
        target = str(rel.get("target") or "")
        relation = str(rel.get("normalized_type") or rel.get("relation") or "")

        normalized_source = graph_guardian.normalize_entity_name(source)
        normalized_target = graph_guardian.normalize_entity_name(target)

        # Exemplo de regra simples
        if normalized_source and normalized_source == normalized_target:
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
           OR start.canonical_name IN $names
           OR any(a IN coalesce(start.aliases, []) WHERE a IN $names)
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
           OR n.canonical_name IN $names
           OR any(a IN coalesce(n.aliases, []) WHERE a IN $names)
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
               OR n.canonical_name IN $names
               OR any(a IN coalesce(n.aliases, []) WHERE a IN $names)
            OPTIONAL MATCH (n)-[r]-(m:Entity)
            RETURN 
                n.name as source_name, 
                n.canonical_name as source_canonical_name,
                n.type as source_type, 
                type(r) as rel_type, 
                m.name as target_name, 
                m.canonical_name as target_canonical_name,
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
                    source_id = row.get("source_canonical_name") or s_name
                    nodes_map[source_id] = {"id": source_id, "label": s_name, "type": row.get("source_type", "Entity")}
                
                if t_name:
                    target_id = row.get("target_canonical_name") or t_name
                    nodes_map[target_id] = {"id": target_id, "label": t_name, "type": row.get("target_type", "Entity")}
                    
                if s_name and t_name and row.get("rel_type"):
                    source_id = row.get("source_canonical_name") or s_name
                    target_id = row.get("target_canonical_name") or t_name
                    edges_list.append({
                        "data": {
                            "source": source_id,
                            "target": target_id,
                            "label": row.get("rel_type")
                        }
                    })
            
            # Formatar output final
            requested_names = set(node_names)
            final_nodes = [
                {
                    "data": {
                        **v,
                        "color": "#4F46E5"
                        if (v["id"] in requested_names or v.get("label") in requested_names)
                        else "#9CA3AF",
                    }
                }
                for v in nodes_map.values()
            ]
            
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
