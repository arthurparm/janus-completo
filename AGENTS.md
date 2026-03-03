# AGENTS.md

## Purpose
Operational command and workflow reference for this repository.

## Trusted Sources (for commands in this file)
- `README.md`
- `frontend/README.md`
- `backend/README.md`
- `frontend/package.json`
- `frontend/CONTRIBUTING.md`
- `.github/workflows/quality-gates.yml`
- `.github/workflows/action-locaweb.yml`
- `documentation/development-guide-frontend.md`
- `documentation/development-guide-backend.md`
- `documentation/deployment-guide.md`
- `documentation/contribution-guide.md`
- `documentation/qa/api-test-playbook.md`
- `documentation/qa/async-operational-slo.md`
- `documentation/qa/domain-slo-alerts.md`
- `backend/evals/technical-qa/README.md`
- `tooling/*.py`, `tooling/*.ps1`, `backend/scripts/*.py`, `backend/scripts/init-ollama.sh`

## Repo Scope
Monorepo with two main parts:
- Frontend: `frontend/` (Angular 20)
- Backend: `backend/` (FastAPI)

## Baseline Prerequisites
- Node.js 20
- Python 3.11+
- Docker + Docker Compose
- PowerShell (for `tooling/*.ps1` workflows)

## Quick Start Workflows

### One-Command Local Bootstrap (recommended)
```bash
python tooling/dev.py up
```

Auxiliary commands:
```bash
python tooling/dev.py setup
python tooling/dev.py qa
python tooling/dev.py down
```

### Full Stack (recommended)
```bash
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d
```

### Frontend Local
```bash
cd frontend
npm install
npm start
```

### Backend Local
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Backend Tests (basic)
```bash
cd backend
pytest
```

## Frontend Command Catalog (`frontend/`)
From `frontend/package.json` and docs.

Install dependencies:
```bash
cd frontend
npm install
```

CI-style install (when lockfile exists):
```bash
cd frontend
npm ci
```

Dev server:
```bash
cd frontend
npm start
npm run start:tailscale
```

Builds:
```bash
cd frontend
npm run build
npm run build -- --configuration development
npm run build -- --configuration production --base-href /
npm run watch
```

Tests:
```bash
cd frontend
npm run test
npm run test:watch
```

Lint/format:
```bash
cd frontend
npm run lint
npm run lint:fix
npm run format
```

## Backend Command Catalog (`backend/`)

Install and run API:
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Run repository root tests (used in CI critical suite):
```bash
PYTHONPATH=backend pytest -q \
  qa/test_api_visibility_endpoints.py \
  qa/test_tool_executor_policy_guards.py \
  qa/test_chat_agent_loop_content_safety.py \
  qa/test_memory_quota_enforcement.py \
  qa/test_generative_memory_llm_role_priority.py \
  qa/test_chat_endpoint_contract.py \
  qa/test_observability_request_dashboard.py \
  qa/test_db_migration_service_contract.py \
  qa/test_knowledge_code_query_contract.py
```

Run API contract subset from playbook:
```bash
cd backend
PYTHONPATH=. pytest -q \
  ../qa/test_api_visibility_endpoints.py \
  ../qa/test_chat_endpoint_contract.py \
  ../qa/test_observability_request_dashboard.py \
  ../qa/test_db_migration_service_contract.py \
  ../qa/test_knowledge_code_query_contract.py
```

## Docker Operations
From `documentation/deployment-guide.md`.

Start stack:
```bash
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d
```

Status:
```bash
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 ps
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 ps
```

Logs:
```bash
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 logs -f janus-api
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 logs -f neo4j
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 logs -f qdrant
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 logs -f ollama
```

Health checks:
```bash
curl -sf http://localhost:8000/health
curl -sf http://localhost:8000/healthz
curl -sf http://localhost:8000/api/v1/system/status
curl -sf http://localhost:8000/api/v1/workers/status
```

## CI Workflow Parity
Primary source: `.github/workflows/quality-gates.yml`

### Backend Lint Gate
```bash
ruff check --config backend/pyproject.toml \
  backend/app/services/db_migration_service.py \
  qa/test_api_visibility_endpoints.py \
  qa/test_tool_executor_policy_guards.py \
  qa/test_chat_endpoint_contract.py \
  qa/test_observability_request_dashboard.py \
  qa/test_db_migration_service_contract.py
```

### Backend Type Gate
```bash
mypy --config-file backend/pyproject.toml --follow-imports=skip \
  backend/app/services/db_migration_service.py
```

### Frontend Quality Gate
```bash
cd frontend
npm run lint
npm run test
npm run build -- --configuration development
```

### MR-013 Offline Eval Gate (CI command)
```bash
python backend/scripts/eval_technical_qa.py \
  --mode offline-codebase \
  --repo-root . \
  --dataset backend/evals/technical-qa/datasets/technical-qa.v1.json \
  --runs-root outputs/qa/technical-qa/runs \
  --baselines-root backend/evals/technical-qa/baselines \
  --compare-baseline \
  --gate-on-regression \
  --require-baseline \
  --max-pass-rate-drop 0.02 \
  --max-citation-coverage-drop 0.02 \
  --max-p95-latency-increase-ms 250
```

### Ops Validation Job (manual in CI)
```bash
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d

# wait for API health
for i in {1..90}; do
  if curl -sf http://localhost:8000/health >/dev/null; then
    echo "API is healthy"
    break
  fi
  sleep 2
done

docker compose -f docker-compose.pc1.yml --env-file .env.pc1 ps
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 ps
python tooling/generate_api_matrix.py
python tooling/generate_api_coverage_report.py \
  --collect-docker-evidence \
  --output-json outputs/qa/api_coverage_report.json \
  --output-md outputs/qa/api_coverage_report.md \
  --docker-evidence-json outputs/qa/docker_evidence.json \
  --docker-log-tail-file outputs/qa/janus_api_log_tail.txt
mkdir -p outputs/qa
curl -sf "http://localhost:8000/api/v1/observability/slo/domains?window_minutes=15&min_events=20" \
  > outputs/qa/domain_slo_report.json
python tooling/async_ops_validation.py \
  --base-url http://localhost:8000 \
  --users 8 \
  --timeout 45 \
  --chaos-timeout 90
```

## Deploy Workflow Notes
From `.github/workflows/action-locaweb.yml`.

Frontend production build used before FTP deploy:
```bash
cd frontend
npm ci  # or npm install if lockfile is absent
echo "VITE_API_BASE_URL=<backend-url>" > .env.production
npm run build -- --configuration production --base-href /
```

Build output path expected by deploy workflow:
- `frontend/dist/janus-angular/browser/`

## API/QA Workflows (Manual)
Primary source: `documentation/qa/api-test-playbook.md`.

### Full API QA sequence
```bash
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d
curl -sf http://localhost:8000/health
python tooling/generate_api_matrix.py
python test_scenario1_apis.py
cd backend
PYTHONPATH=. pytest -q \
  ../qa/test_api_visibility_endpoints.py \
  ../qa/test_chat_endpoint_contract.py \
  ../qa/test_observability_request_dashboard.py \
  ../qa/test_db_migration_service_contract.py \
  ../qa/test_knowledge_code_query_contract.py
cd ..
python tooling/generate_api_coverage_report.py \
  --collect-docker-evidence \
  --output-json outputs/qa/api_coverage_report.json \
  --output-md outputs/qa/api_coverage_report.md \
  --docker-evidence-json outputs/qa/docker_evidence.json \
  --docker-log-tail-file outputs/qa/janus_api_log_tail.txt
curl -sf "http://localhost:8000/api/v1/observability/slo/domains?window_minutes=15&min_events=20"
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

### Generate API inventory from OpenAPI
```bash
python tooling/extract_api_inventory.py
```

### Regenerate endpoint matrix
```bash
python tooling/generate_api_matrix.py
```

### Generate coverage report (advanced flags)
```bash
python tooling/generate_api_coverage_report.py \
  --matrix-json documentation/qa/api-endpoint-matrix.json \
  --output-json outputs/qa/api_coverage_report.json \
  --output-md outputs/qa/api_coverage_report.md \
  --expected-endpoints 229 \
  --collect-docker-evidence \
  --docker-evidence-json outputs/qa/docker_evidence.json \
  --docker-log-tail-file outputs/qa/janus_api_log_tail.txt \
  --docker-log-tail-lines 200
```

Optional hard-fail flags in coverage script:
```bash
python tooling/generate_api_coverage_report.py --fail-on-target-gap --fail-on-uncovered
```

### Async operational validation
CI-style parameters:
```bash
python tooling/async_ops_validation.py \
  --base-url http://localhost:8000 \
  --users 8 \
  --timeout 45 \
  --chaos-timeout 90
```

Playbook/SLO doc style parameters:
```bash
python tooling/async_ops_validation.py \
  --base-url http://localhost:8000 \
  --users 10 \
  --timeout 45 \
  --chaos-timeout 90
```

Custom output path support:
```bash
python tooling/async_ops_validation.py --report-path outputs/qa/async_ops_validation_report.json
```

### Domain SLO endpoint check
```bash
curl "http://localhost:8000/api/v1/observability/slo/domains?window_minutes=15&min_events=20"
```

## Technical QA Baseline Workflows
Source: `backend/evals/technical-qa/README.md` and CI workflow.

Run compare baseline (from `backend/`):
```bash
cd backend
python scripts/eval_technical_qa.py --compare-baseline
```

Offline recurring run:
```bash
cd backend
python scripts/eval_technical_qa.py \
  --mode offline-codebase \
  --repo-root .. \
  --compare-baseline \
  --gate-on-regression \
  --require-baseline
```

Publish new baseline:
```bash
cd backend
python scripts/eval_technical_qa.py \
  --mode offline-codebase \
  --repo-root .. \
  --publish-baseline \
  --compare-baseline
```

## Windows Workflows (`tooling/*.ps1`)

Start infra dependencies only:
```powershell
powershell -File tooling/start_services.ps1
```

Equivalent direct command used by the script:
```bash
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d redis rabbitmq postgres
```

Run local backend setup + launch (Windows):
```powershell
powershell -File tooling/run_windows.ps1
```

Manual equivalent steps (from script internals):
```powershell
python -m pip install --user uv
cd backend
uv venv .venv
uv pip install -e .
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Seed reproducible scenarios inside API container:
```powershell
powershell -File tooling/seed-repro-scenarios.ps1 -ContainerName janus_api -UserId seed-admin
powershell -File tooling/seed-repro-scenarios.ps1 -ContainerName janus_api -UserId seed-admin -NoReset
```

Equivalent direct command used by the script:
```bash
docker exec janus_api sh -lc "cd /app && PYTHONPATH=/app python /app/scripts/seed_repro_scenarios.py --user-id 'seed-admin'"
```

Top-12 validation tests in Docker image:
```powershell
powershell -File tooling/run-top12-tests-docker.ps1
powershell -File tooling/run-top12-tests-docker.ps1 -SkipBuild
powershell -File tooling/run-top12-tests-docker.ps1 -ImageTag janus-completo-janus-api:test
```

Equivalent direct build/run commands used by the script:
```bash
docker build --target test -f backend/docker/Dockerfile -t janus-completo-janus-api:test backend
docker run --rm \
  -v "$(pwd):/repo" \
  -w /repo \
  --env-file backend/app/.env \
  -e PYTHONPATH=/repo/backend \
  janus-completo-janus-api:test \
  /bin/sh -lc "/opt/venv/bin/python -m pytest -q qa/test_api_visibility_endpoints.py qa/test_tool_executor_policy_guards.py qa/test_chat_agent_loop_content_safety.py qa/test_memory_quota_enforcement.py qa/test_generative_memory_llm_role_priority.py qa/test_chat_endpoint_contract.py qa/test_observability_request_dashboard.py qa/test_db_migration_service_contract.py qa/test_knowledge_code_query_contract.py backend/tests/unit/test_code_analysis_service_calls.py backend/tests/unit/test_knowledge_repository_code_indexing.py backend/tests/unit/test_technical_qa_eval_service.py"
```

Secure Tailscale setup script:
```powershell
powershell -File tooling/secure-tailscale-setup.ps1 -Environment production -TailnetName janus-secure
```

## Additional Scripted Workflows

Seed reproducible scenarios directly via Python (if running inside repo/app context):
```bash
python backend/scripts/seed_repro_scenarios.py --user-id seed-admin
python backend/scripts/seed_repro_scenarios.py --user-id seed-admin --no-reset
```

Benchmark complex process (token/cost/latency):
```bash
python backend/scripts/benchmark_complex_process.py --base-url http://localhost:8000 --mode chat --runs 3
python backend/scripts/benchmark_complex_process.py --base-url http://localhost:8000 --mode llm --runs 3
```

Benchmark script options often used for tuning:
```bash
python backend/scripts/benchmark_complex_process.py \
  --base-url http://localhost:8000 \
  --mode chat \
  --runs 5 \
  --sleep 1.0 \
  --timeout 120 \
  --role orchestrator \
  --priority high_quality \
  --user-id benchmark_user
```

Debate graph local test:
```bash
python tooling/test_debate_system.py
```

Scenario-1 API smoke script:
```bash
python test_scenario1_apis.py
```

Ollama init script (inside compatible environment/container):
```bash
sh backend/scripts/init-ollama.sh
```

## Key Artifacts Produced by Workflows
- `outputs/qa/api_inventory.json`
- `outputs/qa/api_test_results.json`
- `documentation/qa/api-endpoint-matrix.json`
- `documentation/qa/api-endpoint-matrix.md`
- `outputs/qa/api_coverage_report.json`
- `outputs/qa/api_coverage_report.md`
- `outputs/qa/docker_evidence.json`
- `outputs/qa/janus_api_log_tail.txt`
- `outputs/qa/domain_slo_report.json`
- `outputs/qa/async_ops_validation_report.json`
- `outputs/qa/technical-qa/runs/*/score.json`
- `outputs/qa/technical-qa/runs/*/summary.md`

## Notes
- Prefer commands explicitly documented in README/documentation/workflows over inferred commands.
- When reproducing CI behavior, use the exact command lines from `.github/workflows/quality-gates.yml`.
- Service naming differs between compose service keys and container names (for example `janus-api` service vs `janus_api` container in some scripts).
- TODO: define an official frontend E2E command alias in `frontend/package.json` (Playwright config exists in `frontend/playwright.config.ts`, but no npm script is documented for it).
- TODO: standardize backend local lint/type commands behind a local task runner (today they are CI-command based: `ruff`/`mypy` direct calls).
