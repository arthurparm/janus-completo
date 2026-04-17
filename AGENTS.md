# 🤖 AGENTS.md: AI Operational Command & Workflow Reference

> **CRITICAL INSTRUCTION FOR ALL AI AGENTS**: 
> You are operating within the `janus-completo` monorepo. This file is your ultimate source of truth for architectural constraints, operational workflows, and business rules. **You MUST read and adhere to these guidelines before proposing or making any code changes.**

## 🏢 1. Business Context & Ultimate Goal
- **Product Vision**: This application is an **Internal Corporate Tool** (Ferramenta Interna) that is currently prioritizing **absolute stability and architectural soundness**. 
- **Long-term Goal**: The system is being explicitly prepared for **Global Scale**.
- **AI Imperative**: Never sacrifice architecture, type safety, or test coverage for "quick hacks" or rapid feature delivery. Clean, refactored, and highly stable code is your #1 priority.

## ⚖️ 2. Golden Rules (NEVER BREAK THESE)
1. **Strict CI & Quality Gates**: 
   - You MUST NOT bypass or ignore type checking (`mypy`), linting (`ruff` for Python, `eslint` for Angular), or test failures. 
   - Every code change must be mentally or explicitly verified against these gates before delivery.
2. **Infrastructure Boot Order (PC2 -> PC1)**: 
   - This project strictly separates Stateful/Infrastructure services (`PC2`: Neo4j, Qdrant, Ollama, Postgres, Redis, RabbitMQ) from Stateless/App services (`PC1`: janus-api, janus-frontend).
   - You MUST respect this boot order: PC2 starts first, services are validated, and only then PC1 starts.
3. **Strict Tooling Usage**: 
   - Always prioritize the official Python scripts in the `tooling/` directory (e.g., `python tooling/dev.py up`) over raw, complex Docker or shell commands. 
   - Do not invent new deployment or validation scripts if an official tool already exists.

## 📂 3. Repository Scope & Architecture
Monorepo with two main parts:
- **Frontend**: `frontend/` (Angular 20, Node.js 20, TailwindCSS, Cytoscape, Chart.js)
- **Backend**: `backend/` (FastAPI, Python 3.11+, LangChain/LangGraph, OpenAI/Groq integration)

### 3.1 Baseline Prerequisites
- Node.js 20
- Python 3.11+
- Docker + Docker Compose
- PowerShell (for `tooling/*.ps1` workflows)

### 3.2 Build and Runtime Model
This repository has more than one valid "build" path. Do not treat them as the same thing.

- **`janus-api`**: Built from `backend/docker/Dockerfile` and runs the FastAPI app on port `8000`.
- **`janus-frontend`**: Built from `frontend/docker/Dockerfile`, installs dependencies with `npm install --legacy-peer-deps`, and runs `ng serve` on port `4300` with `proxy.docker.conf.json`.
- **`PC2` Services**: (`neo4j`, `qdrant`, `ollama`, etc.) use published images; they are pulled, not custom-built in this repo.

#### Frontend Build Modes:
- Local dev: `npm start` serves Angular on `http://localhost:4200`.
- Docker dev/runtime on `PC1`: the frontend container serves Angular on `http://localhost:4300`.
- CI quality gate build: `npm run build -- --configuration development`.
- Production static build for FTP deploy: `npm run build -- --configuration production --base-href /`.
- Production artifact directory: `frontend/dist/janus-angular/browser/`.

#### Backend Image Targets:
- Runtime image: default/final target from `backend/docker/Dockerfile`.
- Test image: `--target test`, used by the Dockerized validation flow.

---

## 🛠️ 4. Quick Start Workflows

### One-Command Local Bootstrap (Recommended)
Always prefer this command for local environment setup:
```bash
python tooling/dev.py up
```

**Auxiliary commands:**
```bash
python tooling/dev.py setup
python tooling/dev.py qa
python tooling/dev.py down
python tooling/dev.py doctor --host 100.89.17.105 --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.json
```

### Full Stack (Manual Split Deploy)
Order matters in the documented deploy flow:
1. Start `PC2`.
2. Validate `Neo4j`, `Qdrant`, and `Ollama`.
3. Build the API image on `PC1`.
4. Start `PC1`.

```bash
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d
docker build -f backend/docker/Dockerfile -t janus-completo-janus-api:latest backend
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d
```

---

## 💻 5. Command Catalog

### 5.1 Frontend Commands (`frontend/`)
Install dependencies:
```bash
cd frontend
npm install # or npm ci for CI-style install
```

Dev server:
```bash
cd frontend
npm start
npm run start:tailscale
```

Builds & Tests:
```bash
cd frontend
npm run build -- --configuration development # Matches CI quality gate
npm run build -- --configuration production --base-href / # Production static artifact
npm run test
npm run lint:fix
npm run format
```

### 5.2 Backend Commands (`backend/`)
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

### 5.3 Docker Operations
Logs:
```bash
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 logs -f janus-api
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 logs -f neo4j
```

Health checks:
```bash
curl -sf http://localhost:8000/health
curl -sf http://localhost:8000/healthz
curl -sf http://localhost:8000/api/v1/system/status
curl -sf http://localhost:8000/api/v1/workers/status
```

---

## 🛡️ 6. CI Workflow Parity & Quality Gates
If you write code, you MUST ensure it passes these exact gates locally before considering the task complete.

### Backend Lint & Type Gate
```bash
ruff check --config backend/pyproject.toml backend/app/services/db_migration_service.py qa/test_api_visibility_endpoints.py
mypy --config-file backend/pyproject.toml --follow-imports=skip backend/app/services/db_migration_service.py
```

### Frontend Quality Gate
```bash
cd frontend
npm run lint
npm run test
npm run build -- --configuration development
```

### Offline Eval Gate (MR-013)
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

---

## 🔍 7. API & QA Workflows (Manual)
Always use the official tooling scripts for API inventory and coverage.

Generate API inventory and matrix:
```bash
python tooling/extract_api_inventory.py
python tooling/generate_api_matrix.py
```

Generate coverage report:
```bash
python tooling/generate_api_coverage_report.py \
  --matrix-json documentation/qa/api-endpoint-matrix.json \
  --output-json outputs/qa/api_coverage_report.json \
  --output-md outputs/qa/api_coverage_report.md \
  --expected-endpoints 229 \
  --collect-docker-evidence \
  --docker-evidence-json outputs/qa/docker_evidence.json \
  --docker-log-tail-file outputs/qa/janus_api_log_tail.txt \
  --docker-log-tail-lines 200 \
  --fail-on-target-gap \
  --fail-on-uncovered
```

Async operational validation:
```bash
python tooling/async_ops_validation.py --base-url http://localhost:8000 --users 8 --timeout 45 --chaos-timeout 90
```

---

## 🪟 8. Windows Workflows (`tooling/*.ps1`)
For Windows environments, use the provided PowerShell scripts:

- Start infra dependencies only: `powershell -File tooling/start_services.ps1`
- Run local backend setup + launch: `powershell -File tooling/run_windows.ps1`
- Seed reproducible scenarios inside API container: `powershell -File tooling/seed-repro-scenarios.ps1 -ContainerName janus_api -UserId seed-admin`
- Secure Tailscale setup script: `powershell -File tooling/secure-tailscale-setup.ps1 -Environment production -TailnetName janus-secure`

---

## 📋 9. Trusted Sources
When in doubt, consult these files:
- `README.md`, `frontend/README.md`, `backend/README.md`
- `frontend/package.json`
- `frontend/CONTRIBUTING.md`
- `.github/workflows/quality-gates.yml`
- `.github/workflows/action-locaweb.yml`
- `documentation/development-guide-frontend.md`
- `documentation/development-guide-backend.md`
- `documentation/deployment-guide.md`
- `documentation/contribution-guide.md`
- `documentation/qa/api-test-playbook.md`
