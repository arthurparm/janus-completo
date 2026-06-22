---
tipo: codigo
dominio: backend
camada: scripts
gerado: true
origem: "backend/scripts/neo4j_noise_maintenance.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# neo4j_noise_maintenance

## Arquivos-fonte
- `backend/scripts/neo4j_noise_maintenance.py`

## Símbolos
- function: `_get_graph_guardian()`
- function: `_utc_stamp()` -> `str`
- function: `_reports_dir()` -> `Path`
- function: `_write_json_report(prefix: str, payload: dict[str, Any], output: str | None = None)` -> `Path`
- function: `_parse_iso_like(value: Any)` -> `tuple[int, str]`
- function: `_coerce_weight(value: Any)` -> `float | None`
- function: `_canonicalize_entity_name(name: Any)` -> `str`
- function: `_sanitize_rel_type(rel_type: str)` -> `str`
- class: `EntityRow`
- class: `Neo4jNoiseMaintenance`
- method: `Neo4jNoiseMaintenance.__init__(self)`
- method: `Neo4jNoiseMaintenance.db(self)`
- method: `Neo4jNoiseMaintenance._query(self, cypher: str, params: dict[str, Any] | None = None, operation: str | None = None)`
- method: `Neo4jNoiseMaintenance._execute(self, cypher: str, params: dict[str, Any] | None = None, operation: str | None = None)`
- method: `Neo4jNoiseMaintenance._fetch_entities(self)` -> `list[EntityRow]`
- method: `Neo4jNoiseMaintenance.audit(self, *, output: str | None = None, low_degree_threshold: int = 0)` -> `dict[str, Any]`
- method: `Neo4jNoiseMaintenance.backfill_entity_canonical_and_aliases(self, *, limit: int | None = None)` -> `dict[str, Any]`
- method: `Neo4jNoiseMaintenance.merge_entities_by_canonical_name(self, *, limit_groups: int | None = None)` -> `dict[str, Any]`
- method: `Neo4jNoiseMaintenance._rank_merge_group(self, rows: list[EntityRow])` -> `list[EntityRow]`
- method: `Neo4jNoiseMaintenance._merge_entity_into_keep(self, *, keep_id: str, dup_id: str)` -> `None`
- method: `Neo4jNoiseMaintenance._merge_edge(self, source_id: str, target_id: str, rel_type: str, props: dict[str, Any] | None)` -> `None`
- method: `Neo4jNoiseMaintenance.dedupe_relationships(self, *, limit_groups: int | None = None)` -> `dict[str, Any]`
- method: `Neo4jNoiseMaintenance.remove_generic_self_loops(self, *, dry_run: bool = False)` -> `dict[str, Any]`
- method: `Neo4jNoiseMaintenance.ensure_entity_constraints_and_indexes(self)` -> `dict[str, Any]`
- method: `Neo4jNoiseMaintenance.export_distinct_graph(self, *, output: str | None = None)` -> `dict[str, Any]`
- function: `_run(args: argparse.Namespace)` -> `dict[str, Any]`
- function: `_build_parser()` -> `argparse.ArgumentParser`
- function: `main()` -> `None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
