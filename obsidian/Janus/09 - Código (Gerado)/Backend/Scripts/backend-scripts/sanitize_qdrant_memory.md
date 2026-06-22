---
tipo: codigo
dominio: backend
camada: scripts
gerado: true
origem: "backend/scripts/sanitize_qdrant_memory.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# sanitize_qdrant_memory

## Arquivos-fonte
- `backend/scripts/sanitize_qdrant_memory.py`

## Símbolos
- function: `_parse_args()` -> `argparse.Namespace`
- function: `_normalize_base_url(value: str | None)` -> `str`
- function: `_http_post_json(url: str, body: dict[str, Any], *, bearer_token: str | None = None)` -> `dict[str, Any]`
- function: `_list_collection_names(client: AsyncQdrantClient)` -> `list[str]`
- function: `_scroll_all_points(client: AsyncQdrantClient, collection_name: str)` -> `list[models.Record]`
- function: `_snapshot_collections(client: AsyncQdrantClient)` -> `dict[str, dict[str, Any]]`
- function: `_classify_legacy_target(payload: dict[str, Any])` -> `str`
- function: `_normalize_timestamp_ms(payload: dict[str, Any], meta: dict[str, Any])` -> `int`
- function: `_normalize_payload_for_target(*, user_id: str, payload: dict[str, Any], target: str)` -> `tuple[str, dict[str, Any]]`
- function: `_migrate_legacy_collection(client: AsyncQdrantClient, legacy_name: str, *, drop_legacy: bool)` -> `dict[str, Any]`
- function: `_purge_self_study_points(client: AsyncQdrantClient)` -> `int`
- function: `_cleanup_neo4j_self_study(uri: str, user: str, password: str)` -> `dict[str, int]`
- function: `_trigger_self_study(url: str, bearer_token: str | None, mode: str)` -> `dict[str, Any]`
- function: `_async_main(args: argparse.Namespace)` -> `dict[str, Any]`
- function: `main()` -> `None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
