# API Test Playbook (Local and CI)

Date: 2026-02-21  
Scope: Janus backend API (`/api/v1/*`)

## Goal

Provide a repeatable flow to:
- generate and refresh the live endpoint matrix,
- run API smoke and contract checks locally,
- align local validation with CI quality gates.

## Artifacts

- Live endpoint matrix (markdown): `documentation/qa/api-endpoint-matrix.md`
- Live endpoint matrix (json): `documentation/qa/api-endpoint-matrix.json`
- API inventory (raw): `outputs/qa/api_inventory.json`
- Smoke results sample: `outputs/qa/api_test_results.json`
- OQ-011 coverage report (json): `outputs/qa/api_coverage_report.json`
- OQ-011 coverage report (markdown): `outputs/qa/api_coverage_report.md`
- Docker evidence (json): `outputs/qa/docker_evidence.json`
- Docker evidence (API log tail): `outputs/qa/janus_api_log_tail.txt`
- Domain SLO runbook: `documentation/qa/domain-slo-alerts.md`
- MR-013 offline eval runs: `outputs/qa/technical-qa/runs/*/score.json`

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
powershell -File tooling/start_services.ps1
```

### 2) Wait for health

```bash
curl -sf http://localhost:8000/health
```

### 3) Refresh live matrix

```bash
python tooling/generate_api_matrix.py
```

This generates:
- `documentation/qa/api-endpoint-matrix.json`
- `documentation/qa/api-endpoint-matrix.md`

### 4) Run API smoke scenario

```bash
python test_scenario1_apis.py
```

This updates `outputs/qa/api_test_results.json`.

### 5) Regenerate matrix after smoke

```bash
python tooling/generate_api_matrix.py
```

### 6) Run critical API contract suite

```bash
cd backend
PYTHONPATH=. pytest -q \
  ../qa/test_api_visibility_endpoints.py \
  ../qa/test_chat_endpoint_contract.py \
  ../qa/test_observability_request_dashboard.py \
  ../qa/test_db_migration_service_contract.py \
  ../qa/test_knowledge_code_query_contract.py
```

### 7) Generate OQ-011 API coverage report + Docker evidence

```bash
python tooling/generate_api_coverage_report.py \
  --collect-docker-evidence \
  --output-json outputs/qa/api_coverage_report.json \
  --output-md outputs/qa/api_coverage_report.md \
  --docker-evidence-json outputs/qa/docker_evidence.json \
  --docker-log-tail-file outputs/qa/janus_api_log_tail.txt
```

This report tracks:
- observed endpoint count (target tracked: 229),
- coverage status per endpoint (`runtime_validated`, `runtime_failed`, `test_referenced`, `not_covered`),
- uncovered endpoint backlog,
- Docker/compose evidence snapshot.

### 8) Validate OQ-002 domain SLO endpoint

```bash
curl -sf "http://localhost:8000/api/v1/observability/slo/domains?window_minutes=15&min_events=20"
```

Expected:
- response with `status`, `domains`, `active_alerts`,
- one entry per domain: `chat`, `rag`, `tools`, `workers`.

### 9) Optional Top-12 docker validation

```powershell
powershell -File tooling/run-top12-tests-docker.ps1
```

### 10) Run MR-013 offline baseline gate (pre-merge compatible)

```bash
python backend/scripts/eval_technical_qa.py \
  --mode offline-codebase \
  --repo-root . \
  --dataset backend/evals/technical-qa/datasets/technical-qa.v1.json \
  --runs-root outputs/qa/technical-qa/runs \
  --baselines-root backend/evals/technical-qa/baselines \
  --compare-baseline \
  --gate-on-regression \
  --require-baseline
```

Expected:
- writes a new `score.json` and `summary.md`,
- compares with versioned baseline,
- exits non-zero if regression thresholds are violated.

## CI Mapping

CI workflow: `.github/workflows/quality-gates.yml`

- `backend-lint`
- `backend-type`
- `backend-tests` (critical suite + MR-013 offline eval gate)
- `ops-validation` (manual trigger only, includes OQ-011/OQ-002 artifacts)

## Definition of Done (DX-011)

- Matrix can be regenerated from current API state with one command.
- Playbook defines deterministic local and CI steps.
- Matrix and playbook paths are documented and versioned in the repo.

## Definition of Done (OQ-011)

- Coverage report generated automatically for all discovered `/api/v1/*` endpoints.
- JSON + Markdown report artifacts produced with module-level coverage summary.
- Docker evidence snapshot generated in the same run (compose status + API log tail).
