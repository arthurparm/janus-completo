---
tipo: codigo
dominio: backend
camada: scripts
gerado: true
origem: "tooling/extract_api_inventory.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# extract_api_inventory

## Objetivo
API Inventory Extraction Script
Fetches OpenAPI spec from running Janus backend and generates structured inventory.

## Arquivos-fonte
- `tooling/extract_api_inventory.py`

## Símbolos
- function: `fetch_openapi_spec(base_url: str = 'http://localhost:8000')` -> `Dict[str, Any]`
  - Fetch OpenAPI specification from running backend.
- function: `extract_endpoints(openapi_spec: Dict[str, Any])` -> `List[Dict[str, Any]]`
  - Extract structured endpoint information from OpenAPI spec.
- function: `generate_statistics(endpoints: List[Dict[str, Any]])` -> `Dict[str, Any]`
  - Generate summary statistics from endpoints.
- function: `save_inventory(endpoints: List[Dict[str, Any]], output_path: Path)`
  - Save inventory to JSON file.
- function: `print_summary(stats: Dict[str, Any])`
  - Print human-readable summary.
- function: `main()`
  - Main execution flow.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
