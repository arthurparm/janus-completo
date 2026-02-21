# API Test Playbook (Local and CI)

Date: 2026-02-21  
Scope: Janus backend API (`/api/v1/*`)

## Goal

Provide a repeatable flow to:
- generate and refresh the live endpoint matrix,
- run API smoke and contract checks locally,
- align local validation with CI quality gates.

## Artifacts

- Live endpoint matrix (markdown): `docs/qa/api-endpoint-matrix.md`
- Live endpoint matrix (json): `docs/qa/api-endpoint-matrix.json`
- API inventory (raw): `api_inventory.json`
- Smoke results sample: `api_test_results.json`

## Prerequisites

- Python 3.11+
- Docker + Docker Compose
- Running Janus API at `http://localhost:8000`

## Local Flow

### 1) Start stack

```bash
docker compose up -d
```

Optional infra-only startup (PowerShell):

```powershell
powershell -File scripts/start_services.ps1
```

### 2) Wait for health

```bash
curl -sf http://localhost:8000/health
```

### 3) Refresh live matrix

```bash
python scripts/generate_api_matrix.py
```

This generates:
- `docs/qa/api-endpoint-matrix.json`
- `docs/qa/api-endpoint-matrix.md`

### 4) Run API smoke scenario

```bash
python test_scenario1_apis.py
```

This updates `api_test_results.json`.

### 5) Regenerate matrix after smoke

```bash
python scripts/generate_api_matrix.py
```

### 6) Run critical API contract suite

```bash
cd janus
PYTHONPATH=. pytest -q \
  ../tests/test_api_visibility_endpoints.py \
  ../tests/test_chat_endpoint_contract.py \
  ../tests/test_observability_request_dashboard.py \
  ../tests/test_db_migration_service_contract.py \
  ../tests/test_knowledge_code_query_contract.py
```

### 7) Optional Top-12 docker validation

```powershell
powershell -File scripts/run-top12-tests-docker.ps1
```

## CI Mapping

CI workflow: `.github/workflows/quality-gates.yml`

- `backend-lint`
- `backend-type`
- `backend-tests` (critical suite)
- `ops-validation` (manual trigger only)

Recommended CI extension for DX-011 governance:
1. Run `python scripts/generate_api_matrix.py` in CI.
2. Upload `docs/qa/api-endpoint-matrix.json` and `docs/qa/api-endpoint-matrix.md` as artifacts.
3. Fail the pipeline if smoke baseline endpoints regress (based on `api_test_results.json` contract).

## Definition of Done (DX-011)

- Matrix can be regenerated from current API state with one command.
- Playbook defines deterministic local and CI steps.
- Matrix and playbook paths are documented and versioned in the repo.
