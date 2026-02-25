from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_APP_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_APP_ROOT) not in sys.path:
    sys.path.append(str(REPO_APP_ROOT))

_SAFE_REL_TYPE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_GRAPH_GUARDIAN_SINGLETON = None


def _get_graph_guardian():
    global _GRAPH_GUARDIAN_SINGLETON
    if _GRAPH_GUARDIAN_SINGLETON is not None:
        return _GRAPH_GUARDIAN_SINGLETON

    try:
        from app.core.memory.graph_guardian import graph_guardian as _guardian

        _GRAPH_GUARDIAN_SINGLETON = _guardian
        return _guardian
    except Exception:
        # Fallback para ambientes sem dependências completas (ex.: python < 3.11 apenas para análise/export local).
        module_path = REPO_APP_ROOT / "app" / "core" / "memory" / "graph_guardian.py"
        spec = importlib.util.spec_from_file_location("_graph_guardian_standalone", module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[attr-defined]
            _GRAPH_GUARDIAN_SINGLETON = getattr(module, "graph_guardian")
            return _GRAPH_GUARDIAN_SINGLETON
        raise


def _utc_stamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d-%H%M%S")


def _reports_dir() -> Path:
    path = Path("reports")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json_report(prefix: str, payload: dict[str, Any], output: str | None = None) -> Path:
    path = Path(output) if output else (_reports_dir() / f"{prefix}-{_utc_stamp()}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _parse_iso_like(value: Any) -> tuple[int, str]:
    raw = str(value or "").strip()
    if not raw:
        return (1, "")
    return (0, raw)


def _coerce_weight(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _canonicalize_entity_name(name: Any) -> str:
    return _get_graph_guardian().normalize_entity_name(str(name or ""))


def _sanitize_rel_type(rel_type: str) -> str:
    candidate = str(rel_type or "").strip().upper()
    if not _SAFE_REL_TYPE.match(candidate):
        raise ValueError(f"Unsafe relationship type: {rel_type!r}")
    return candidate


@dataclass
class EntityRow:
    element_id: str
    name: str
    canonical_name: str
    aliases: list[str]
    created_at: str
    last_seen: str
    source_experience: str
    source_experiences: list[str]


class Neo4jNoiseMaintenance:
    def __init__(self):
        self._db = None

    async def db(self):
        if self._db is None:
            from app.db.graph import get_graph_db

            self._db = await get_graph_db()
        return self._db

    async def _query(self, cypher: str, params: dict[str, Any] | None = None, operation: str | None = None):
        db = await self.db()
        return await db.query(cypher, params or {}, operation=operation)

    async def _execute(self, cypher: str, params: dict[str, Any] | None = None, operation: str | None = None):
        db = await self.db()
        return await db.execute(cypher, params or {}, operation=operation)

    async def _fetch_entities(self) -> list[EntityRow]:
        rows = await self._query(
            """
            MATCH (e:Entity)
            RETURN
              elementId(e) AS element_id,
              coalesce(e.name, '') AS name,
              coalesce(e.canonical_name, '') AS canonical_name,
              coalesce(e.aliases, []) AS aliases,
              coalesce(e.created_at, '') AS created_at,
              coalesce(e.last_seen, '') AS last_seen,
              coalesce(e.source_experience, '') AS source_experience,
              coalesce(e.source_experiences, []) AS source_experiences
            """,
            operation="noise_fetch_entities",
        )
        out: list[EntityRow] = []
        for row in rows or []:
            aliases = [str(a) for a in (row.get("aliases") or []) if str(a or "").strip()]
            source_experiences = [
                str(a) for a in (row.get("source_experiences") or []) if str(a or "").strip()
            ]
            out.append(
                EntityRow(
                    element_id=str(row.get("element_id") or ""),
                    name=str(row.get("name") or ""),
                    canonical_name=str(row.get("canonical_name") or ""),
                    aliases=aliases,
                    created_at=str(row.get("created_at") or ""),
                    last_seen=str(row.get("last_seen") or ""),
                    source_experience=str(row.get("source_experience") or ""),
                    source_experiences=source_experiences,
                )
            )
        return out

    async def audit(self, *, output: str | None = None, low_degree_threshold: int = 0) -> dict[str, Any]:
        entities = await self._fetch_entities()
        node_counts = await self._query(
            "MATCH (n) RETURN count(n) AS total_nodes",
            operation="noise_audit_nodes_total",
        )
        rel_counts = await self._query(
            "MATCH ()-[r]->() RETURN count(r) AS total_relationships",
            operation="noise_audit_rels_total",
        )
        rel_type_rows = await self._query(
            "MATCH ()-[r]->() RETURN type(r) AS rel_type, count(*) AS count ORDER BY count DESC",
            operation="noise_audit_rel_type_distribution",
        )
        duplicate_edge_rows = await self._query(
            """
            MATCH (a)-[r]->(b)
            WITH elementId(a) AS source_id, type(r) AS rel_type, elementId(b) AS target_id,
                 collect({
                   rel_id: elementId(r),
                   weight: r.weight,
                   created_at: r.created_at,
                   last_seen: r.last_seen,
                   source_exp: r.source_exp
                 }) AS rels
            WHERE size(rels) > 1
            RETURN source_id, rel_type, target_id, rels, size(rels) AS count
            ORDER BY count DESC
            """,
            operation="noise_audit_duplicate_edges",
        )
        self_loop_rows = await self._query(
            """
            MATCH (n)-[r:RELATED_TO]->(n)
            RETURN elementId(r) AS rel_id, coalesce(n.name, '') AS name, coalesce(n.canonical_name, '') AS canonical_name
            ORDER BY name
            """,
            operation="noise_audit_self_loops",
        )
        low_degree_rows = await self._query(
            """
            MATCH (e:Entity)
            OPTIONAL MATCH (e)-[r]-()
            WITH e, count(r) AS degree
            WHERE degree <= $threshold
            RETURN elementId(e) AS element_id, coalesce(e.name, '') AS name, coalesce(e.canonical_name, '') AS canonical_name, degree
            ORDER BY degree ASC, name ASC
            LIMIT 200
            """,
            {"threshold": int(low_degree_threshold)},
            operation="noise_audit_low_degree_entities",
        )

        groups: dict[str, list[EntityRow]] = defaultdict(list)
        alias_counter: Counter[str] = Counter()
        for row in entities:
            computed = _canonicalize_entity_name(row.name)
            canonical = row.canonical_name or computed
            if canonical:
                groups[canonical].append(row)
            for alias in row.aliases:
                alias_counter[alias] += 1

        merge_candidates = []
        for canonical, rows in groups.items():
            if len(rows) <= 1:
                continue
            merge_candidates.append(
                {
                    "canonical_name": canonical,
                    "count": len(rows),
                    "variants": sorted({r.name for r in rows if r.name}),
                    "element_ids": [r.element_id for r in rows],
                }
            )
        merge_candidates.sort(key=lambda item: (-int(item["count"]), str(item["canonical_name"])))

        relationship_type_distribution = [
            {"rel_type": str(r.get("rel_type") or ""), "count": int(r.get("count") or 0)}
            for r in (rel_type_rows or [])
        ]
        total_rels = int((rel_counts[0]["total_relationships"] if rel_counts else 0) or 0)
        related_to_count = sum(
            item["count"] for item in relationship_type_distribution if item["rel_type"] == "RELATED_TO"
        )

        payload = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "summary": {
                "total_nodes": int((node_counts[0]["total_nodes"] if node_counts else 0) or 0),
                "total_relationships": total_rels,
                "entity_nodes": len(entities),
                "merge_candidate_groups": len(merge_candidates),
                "entity_nodes_in_merge_candidate_groups": sum(int(c["count"]) for c in merge_candidates),
                "duplicate_edge_groups": len(duplicate_edge_rows or []),
                "duplicate_edge_extra_instances": sum(max(0, int(r.get("count", 0)) - 1) for r in (duplicate_edge_rows or [])),
                "generic_related_to_ratio": (related_to_count / total_rels) if total_rels else 0.0,
                "related_to_count": related_to_count,
                "self_loops_related_to": len(self_loop_rows or []),
            },
            "relationship_type_distribution": relationship_type_distribution,
            "entity_merge_candidates_top": merge_candidates[:200],
            "duplicate_edge_groups_top": duplicate_edge_rows[:200] if duplicate_edge_rows else [],
            "self_loops_related_to_top": self_loop_rows[:200] if self_loop_rows else [],
            "low_degree_entities_top": low_degree_rows[:200] if low_degree_rows else [],
            "top_aliases": [{"alias": k, "count": v} for k, v in alias_counter.most_common(100)],
        }
        report_path = _write_json_report("neo4j-noise-audit", payload, output)
        payload["report_path"] = str(report_path)
        return payload

    async def backfill_entity_canonical_and_aliases(self, *, limit: int | None = None) -> dict[str, Any]:
        entities = await self._fetch_entities()
        updated = 0
        unchanged = 0
        errors: list[dict[str, str]] = []
        for row in entities[: limit or None]:
            canonical_name = row.canonical_name or _canonicalize_entity_name(row.name)
            aliases = [a for a in row.aliases if a]
            if row.name and row.name not in aliases:
                aliases.append(row.name)
            aliases = list(dict.fromkeys(aliases))
            if (row.canonical_name or "") == canonical_name and aliases == row.aliases:
                unchanged += 1
                continue
            try:
                await self._execute(
                    """
                    MATCH (e:Entity) WHERE elementId(e) = $element_id
                    SET e.canonical_name = $canonical_name,
                        e.aliases = $aliases
                    """,
                    {"element_id": row.element_id, "canonical_name": canonical_name, "aliases": aliases},
                    operation="noise_backfill_entity_canonical",
                )
                updated += 1
            except Exception as exc:
                errors.append({"element_id": row.element_id, "error": str(exc)})
        return {"updated": updated, "unchanged": unchanged, "errors": errors[:100]}

    async def merge_entities_by_canonical_name(self, *, limit_groups: int | None = None) -> dict[str, Any]:
        entities = await self._fetch_entities()
        groups: dict[str, list[EntityRow]] = defaultdict(list)
        for row in entities:
            canonical = row.canonical_name or _canonicalize_entity_name(row.name)
            if canonical:
                groups[canonical].append(row)

        candidates = [(k, v) for k, v in groups.items() if len(v) > 1]
        candidates.sort(key=lambda item: (-len(item[1]), item[0]))
        if limit_groups:
            candidates = candidates[:limit_groups]

        report: dict[str, Any] = {"groups_processed": 0, "nodes_removed": 0, "groups": [], "errors": []}
        for canonical, rows in candidates:
            ranked = await self._rank_merge_group(rows)
            keep = ranked[0]
            removed_ids: list[str] = []
            group_errors: list[str] = []
            for dup in ranked[1:]:
                try:
                    await self._merge_entity_into_keep(keep_id=keep.element_id, dup_id=dup.element_id)
                    removed_ids.append(dup.element_id)
                    report["nodes_removed"] += 1
                except Exception as exc:
                    group_errors.append(f"{dup.element_id}: {exc}")
                    report["errors"].append({"canonical_name": canonical, "dup_id": dup.element_id, "error": str(exc)})
            report["groups"].append(
                {
                    "canonical_name": canonical,
                    "keep_id": keep.element_id,
                    "removed_ids": removed_ids,
                    "errors": group_errors,
                    "variants": sorted({r.name for r in rows if r.name}),
                }
            )
            report["groups_processed"] += 1
        return report

    async def _rank_merge_group(self, rows: list[EntityRow]) -> list[EntityRow]:
        ids = [r.element_id for r in rows if r.element_id]
        degree_rows = await self._query(
            """
            MATCH (e:Entity)
            WHERE elementId(e) IN $ids
            OPTIONAL MATCH (e)-[rel]-()
            RETURN elementId(e) AS element_id, count(rel) AS degree
            """,
            {"ids": ids},
            operation="noise_merge_rank_group_degrees",
        )
        degree_map = {str(r.get("element_id") or ""): int(r.get("degree") or 0) for r in (degree_rows or [])}
        ranked = list(rows)
        ranked.sort(key=lambda r: r.element_id)
        ranked.sort(key=lambda r: _parse_iso_like(r.created_at))
        ranked.sort(key=lambda r: (1 if str(r.last_seen or "").strip() else 0, str(r.last_seen or "")), reverse=True)
        ranked.sort(key=lambda r: degree_map.get(r.element_id, 0), reverse=True)
        return ranked

    async def _merge_entity_into_keep(self, *, keep_id: str, dup_id: str) -> None:
        if keep_id == dup_id:
            return
        dup_meta_rows = await self._query(
            """
            MATCH (dup:Entity) WHERE elementId(dup) = $dup_id
            RETURN
              coalesce(dup.name, '') AS name,
              coalesce(dup.aliases, []) AS aliases,
              coalesce(dup.source_experience, '') AS source_experience,
              coalesce(dup.source_experiences, []) AS source_experiences,
              coalesce(dup.canonical_name, '') AS canonical_name
            """,
            {"dup_id": dup_id},
            operation="noise_merge_fetch_dup_meta",
        )
        if not dup_meta_rows:
            return
        dup_meta = dup_meta_rows[0]
        alias_candidates = [str(a) for a in (dup_meta.get("aliases") or []) if str(a or "").strip()]
        dup_name = str(dup_meta.get("name") or "").strip()
        if dup_name and dup_name not in alias_candidates:
            alias_candidates.append(dup_name)
        source_exp_candidates = [
            str(a) for a in (dup_meta.get("source_experiences") or []) if str(a or "").strip()
        ]
        dup_source_experience = str(dup_meta.get("source_experience") or "").strip()
        if dup_source_experience and dup_source_experience not in source_exp_candidates:
            source_exp_candidates.append(dup_source_experience)

        await self._execute(
            """
            MATCH (keep:Entity) WHERE elementId(keep) = $keep_id
            WITH keep,
                 CASE
                   WHEN keep.aliases IS NULL THEN CASE WHEN coalesce(keep.name,'') = '' THEN [] ELSE [keep.name] END
                   ELSE keep.aliases
                 END AS base_aliases,
                 CASE
                   WHEN keep.source_experiences IS NULL THEN CASE WHEN coalesce(keep.source_experience,'') = '' THEN [] ELSE [keep.source_experience] END
                   ELSE keep.source_experiences
                 END AS base_source_exps
            SET keep.aliases = reduce(acc = base_aliases, a IN $alias_candidates |
              CASE WHEN a IN acc THEN acc ELSE acc + a END
            )
            SET keep.source_experiences = reduce(acc = base_source_exps, x IN $source_exp_candidates |
              CASE WHEN x IN acc THEN acc ELSE acc + x END
            )
            SET keep.source_experience = CASE
              WHEN coalesce(keep.source_experience, '') = '' AND size($source_exp_candidates) > 0 THEN $source_exp_candidates[0]
              ELSE keep.source_experience
            END
            """,
            {
                "keep_id": keep_id,
                "alias_candidates": alias_candidates,
                "source_exp_candidates": source_exp_candidates,
            },
            operation="noise_merge_merge_meta",
        )

        outgoing = await self._query(
            """
            MATCH (dup)-[r]->(target)
            WHERE elementId(dup) = $dup_id
            RETURN type(r) AS rel_type, elementId(target) AS target_id, properties(r) AS props
            """,
            {"dup_id": dup_id},
            operation="noise_merge_outgoing_edges",
        )
        incoming = await self._query(
            """
            MATCH (source)-[r]->(dup)
            WHERE elementId(dup) = $dup_id
            RETURN type(r) AS rel_type, elementId(source) AS source_id, properties(r) AS props
            """,
            {"dup_id": dup_id},
            operation="noise_merge_incoming_edges",
        )

        for row in outgoing or []:
            rel_type = _sanitize_rel_type(str(row.get("rel_type") or "RELATED_TO"))
            props = dict(row.get("props") or {})
            target_id = str(row.get("target_id") or "")
            if target_id == dup_id:
                target_id = keep_id
            if not target_id:
                continue
            await self._merge_edge(keep_id, target_id, rel_type, props)

        for row in incoming or []:
            rel_type = _sanitize_rel_type(str(row.get("rel_type") or "RELATED_TO"))
            props = dict(row.get("props") or {})
            source_id = str(row.get("source_id") or "")
            if source_id == dup_id:
                source_id = keep_id
            if not source_id:
                continue
            await self._merge_edge(source_id, keep_id, rel_type, props)

        await self._execute(
            "MATCH (dup:Entity) WHERE elementId(dup) = $dup_id DETACH DELETE dup",
            {"dup_id": dup_id},
            operation="noise_merge_delete_dup_entity",
        )

    async def _merge_edge(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        props: dict[str, Any] | None,
    ) -> None:
        safe_rel_type = _sanitize_rel_type(rel_type)
        props = dict(props or {})
        weight = _coerce_weight(props.get("weight"))
        created_at = str(props.get("created_at") or "")
        last_seen = str(props.get("last_seen") or "")
        source_exp = str(props.get("source_exp") or "")
        cypher = f"""
        MATCH (a) WHERE elementId(a) = $source_id
        MATCH (b) WHERE elementId(b) = $target_id
        MERGE (a)-[r:{safe_rel_type}]->(b)
        ON CREATE SET r += $props
        ON MATCH SET
          r.weight = CASE
            WHEN $weight IS NULL THEN r.weight
            WHEN r.weight IS NULL THEN $weight
            WHEN r.weight >= $weight THEN r.weight
            ELSE $weight
          END,
          r.created_at = CASE
            WHEN coalesce(r.created_at, '') = '' THEN $created_at
            WHEN coalesce($created_at, '') = '' THEN r.created_at
            WHEN r.created_at <= $created_at THEN r.created_at
            ELSE $created_at
          END,
          r.last_seen = CASE
            WHEN coalesce(r.last_seen, '') = '' THEN $last_seen
            WHEN coalesce($last_seen, '') = '' THEN r.last_seen
            WHEN r.last_seen >= $last_seen THEN r.last_seen
            ELSE $last_seen
          END,
          r.source_exp = CASE
            WHEN coalesce(r.source_exp, '') = '' THEN $source_exp
            ELSE r.source_exp
          END
        """
        await self._execute(
            cypher,
            {
                "source_id": source_id,
                "target_id": target_id,
                "props": props,
                "weight": weight,
                "created_at": created_at,
                "last_seen": last_seen,
                "source_exp": source_exp,
            },
            operation="noise_merge_edge",
        )

    async def dedupe_relationships(self, *, limit_groups: int | None = None) -> dict[str, Any]:
        dup_groups = await self._query(
            """
            MATCH (a)-[r]->(b)
            WITH elementId(a) AS source_id, type(r) AS rel_type, elementId(b) AS target_id, collect(r) AS rels
            WHERE size(rels) > 1
            RETURN source_id, rel_type, target_id,
                   [x IN rels | {rel_id: elementId(x), props: properties(x)}] AS rels
            ORDER BY size(rels) DESC
            """,
            operation="noise_dedupe_relationships_scan",
        )
        if limit_groups:
            dup_groups = (dup_groups or [])[:limit_groups]

        processed_groups = 0
        removed_relationships = 0
        group_reports: list[dict[str, Any]] = []

        for group in dup_groups or []:
            rels = list(group.get("rels") or [])
            if len(rels) <= 1:
                continue
            keep = rels[0]
            extras = rels[1:]
            keep_props = dict(keep.get("props") or {})
            weights = []
            createds = []
            last_seens = []
            source_exps = []
            for rel in rels:
                props = dict(rel.get("props") or {})
                w = _coerce_weight(props.get("weight"))
                if w is not None:
                    weights.append(w)
                c = str(props.get("created_at") or "").strip()
                if c:
                    createds.append(c)
                ls = str(props.get("last_seen") or "").strip()
                if ls:
                    last_seens.append(ls)
                se = str(props.get("source_exp") or "").strip()
                if se:
                    source_exps.append(se)

            if weights:
                keep_props["weight"] = max(weights)
            if createds:
                keep_props["created_at"] = min(createds)
            if last_seens:
                keep_props["last_seen"] = max(last_seens)
            if source_exps and not keep_props.get("source_exp"):
                keep_props["source_exp"] = source_exps[0]

            await self._execute(
                """
                MATCH ()-[r]->() WHERE elementId(r) = $rel_id
                SET r = $props
                """,
                {"rel_id": str(keep.get("rel_id") or ""), "props": keep_props},
                operation="noise_dedupe_relationships_update_keep",
            )
            for extra in extras:
                await self._execute(
                    "MATCH ()-[r]->() WHERE elementId(r) = $rel_id DELETE r",
                    {"rel_id": str(extra.get("rel_id") or "")},
                    operation="noise_dedupe_relationships_delete_extra",
                )
                removed_relationships += 1

            group_reports.append(
                {
                    "source_id": group.get("source_id"),
                    "rel_type": group.get("rel_type"),
                    "target_id": group.get("target_id"),
                    "kept_rel_id": keep.get("rel_id"),
                    "removed_rel_ids": [r.get("rel_id") for r in extras],
                }
            )
            processed_groups += 1

        return {
            "groups_processed": processed_groups,
            "removed_relationships": removed_relationships,
            "groups": group_reports[:200],
        }

    async def remove_generic_self_loops(self, *, dry_run: bool = False) -> dict[str, Any]:
        rows = await self._query(
            """
            MATCH (n)-[r:RELATED_TO]->(n)
            RETURN elementId(r) AS rel_id, coalesce(n.name, '') AS name, coalesce(n.canonical_name, '') AS canonical_name
            ORDER BY name
            """,
            operation="noise_remove_self_loops_scan",
        )
        if not dry_run:
            for row in rows or []:
                await self._execute(
                    "MATCH ()-[r]->() WHERE elementId(r) = $rel_id DELETE r",
                    {"rel_id": str(row.get("rel_id") or "")},
                    operation="noise_remove_self_loops_delete",
                )
        return {"dry_run": dry_run, "count": len(rows or []), "items": rows[:200] if rows else []}

    async def ensure_entity_constraints_and_indexes(self) -> dict[str, Any]:
        statements = [
            (
                "entity_canonical_name_unique",
                "CREATE CONSTRAINT entity_canonical_name_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.canonical_name IS UNIQUE",
            ),
            (
                "entity_name_idx",
                "CREATE INDEX entity_name_idx IF NOT EXISTS FOR (e:Entity) ON (e.name)",
            ),
            (
                "entity_canonical_name_idx",
                "CREATE INDEX entity_canonical_name_idx IF NOT EXISTS FOR (e:Entity) ON (e.canonical_name)",
            ),
        ]
        created: list[str] = []
        errors: list[dict[str, str]] = []
        for name, stmt in statements:
            try:
                await self._execute(stmt, operation=f"noise_schema_{name}")
                created.append(name)
            except Exception as exc:
                errors.append({"name": name, "error": str(exc)})
        return {"applied": created, "errors": errors}

    async def export_distinct_graph(self, *, output: str | None = None) -> dict[str, Any]:
        nodes = await self._query(
            """
            MATCH (n)
            RETURN elementId(n) AS elementId, labels(n) AS labels, properties(n) AS properties
            ORDER BY elementId
            """,
            operation="noise_export_nodes",
        )
        rels = await self._query(
            """
            MATCH (a)-[r]->(b)
            RETURN DISTINCT elementId(r) AS elementId,
                            type(r) AS type,
                            elementId(a) AS startNodeElementId,
                            elementId(b) AS endNodeElementId,
                            properties(r) AS properties
            ORDER BY elementId
            """,
            operation="noise_export_relationships",
        )
        payload = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "nodes": nodes or [],
            "relationships": rels or [],
            "counts": {"nodes": len(nodes or []), "relationships": len(rels or [])},
        }
        report_path = _write_json_report("neo4j-graph-distinct", payload, output)
        payload["report_path"] = str(report_path)
        return payload


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    service = Neo4jNoiseMaintenance()
    try:
        if args.command == "audit":
            return await service.audit(output=args.output, low_degree_threshold=args.low_degree_threshold)
        if args.command == "backfill-entity-canonical":
            return await service.backfill_entity_canonical_and_aliases(limit=args.limit)
        if args.command == "merge-entities":
            return await service.merge_entities_by_canonical_name(limit_groups=args.limit_groups)
        if args.command == "dedupe-edges":
            return await service.dedupe_relationships(limit_groups=args.limit_groups)
        if args.command == "remove-self-loops":
            return await service.remove_generic_self_loops(dry_run=bool(args.dry_run))
        if args.command == "ensure-constraints":
            return await service.ensure_entity_constraints_and_indexes()
        if args.command == "export-distinct":
            return await service.export_distinct_graph(output=args.output)
        raise ValueError(f"Unknown command: {args.command}")
    finally:
        try:
            from app.db.graph import close_graph_db

            await close_graph_db()
        except Exception:
            pass


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ferramenta de auditoria e limpeza conservadora de ruído no Neo4j (Entity graph)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_audit = sub.add_parser("audit", help="Gera relatório de ruído (dry-run).")
    p_audit.add_argument("--output", default=None, help="Caminho opcional do JSON de saída.")
    p_audit.add_argument("--low-degree-threshold", type=int, default=0)

    p_backfill = sub.add_parser("backfill-entity-canonical", help="Backfill de canonical_name/aliases em :Entity.")
    p_backfill.add_argument("--limit", type=int, default=None)

    p_merge = sub.add_parser("merge-entities", help="Mescla nós :Entity por canonical_name.")
    p_merge.add_argument("--limit-groups", type=int, default=None)

    p_dedupe = sub.add_parser("dedupe-edges", help="Remove arestas duplicadas por (start,type,end).")
    p_dedupe.add_argument("--limit-groups", type=int, default=None)

    p_loops = sub.add_parser(
        "remove-self-loops",
        help="Remove auto-loops genéricos RELATED_TO; com --dry-run apenas lista.",
    )
    p_loops.add_argument("--dry-run", action="store_true")

    sub.add_parser("ensure-constraints", help="Cria constraint/índices para :Entity(canonical_name).")

    p_export = sub.add_parser("export-distinct", help="Exporta nós e relações distintos (sem duplicação por paths).")
    p_export.add_argument("--output", default=None, help="Caminho opcional do JSON de saída.")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    result = asyncio.run(_run(args))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
