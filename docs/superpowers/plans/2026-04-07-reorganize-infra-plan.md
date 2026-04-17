# Reorganize Infrastructure to deploy/ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move all infrastructure and deployment configurations (Dockerfiles, docker-compose, observability tools, etc.) to a new `deploy/` directory at the project root.

**Architecture:** A cleaner root directory and better separation of concerns. `docker-compose` contexts will be adjusted to run from `deploy/` while still accessing the root folder for application code. Tooling scripts and documentation will be updated to point to the new paths.

**Tech Stack:** Docker, Docker Compose, Python, PowerShell, Bash, Git.

---

### Task 1: Create deploy directory and move observability/infra folders

**Files:**
- Create: `deploy/`
- Move: `backend/grafana/` to `deploy/grafana/`
- Move: `backend/observability/` to `deploy/observability/`
- Move: `backend/otel/` to `deploy/otel/`
- Move: `backend/prometheus/` to `deploy/prometheus/`
- Move: `backend/sql/` to `deploy/sql/`

- [ ] **Step 1: Move the directories**

```bash
mkdir -p deploy
mv backend/grafana deploy/
mv backend/observability deploy/
mv backend/otel deploy/
mv backend/prometheus deploy/
mv backend/sql deploy/
```

- [ ] **Step 2: Commit the changes**

```bash
git add deploy/ backend/
git commit -m "refactor: move observability and sql folders to deploy/"
```

### Task 2: Move Dockerfiles and docker-compose files

**Files:**
- Create: `deploy/docker/`
- Move: `backend/docker/Dockerfile` to `deploy/docker/api.Dockerfile`
- Move: `backend/docker/ollama.Dockerfile` to `deploy/docker/ollama.Dockerfile`
- Move: `frontend/docker/Dockerfile` to `deploy/docker/frontend.Dockerfile`
- Move: `docker-compose.pc1.yml` to `deploy/docker-compose.pc1.yml`
- Move: `docker-compose.pc2.yml` to `deploy/docker-compose.pc2.yml`

- [ ] **Step 1: Move the Dockerfiles**

```bash
mkdir -p deploy/docker
mv backend/docker/Dockerfile deploy/docker/api.Dockerfile
mv backend/docker/ollama.Dockerfile deploy/docker/ollama.Dockerfile
mv frontend/docker/Dockerfile deploy/docker/frontend.Dockerfile
```

- [ ] **Step 2: Move the docker-compose files**

```bash
mv docker-compose.pc1.yml deploy/
mv docker-compose.pc2.yml deploy/
```

- [ ] **Step 3: Update `deploy/docker-compose.pc1.yml` paths**

Use `sed` or manually edit `deploy/docker-compose.pc1.yml`:
1. Change `context: ./backend` to `context: ../backend`
2. Change `dockerfile: docker/Dockerfile` to `dockerfile: ../deploy/docker/api.Dockerfile`
3. Change `context: ./frontend` to `context: ../frontend`
4. Change `dockerfile: docker/Dockerfile` to `dockerfile: ../deploy/docker/frontend.Dockerfile`
5. Change volume `- ./backend/app:/app/app:ro` to `- ../backend/app:/app/app:ro`
6. Change volume `- ./backend/scripts:/app/scripts:ro` to `- ../backend/scripts:/app/scripts:ro`

- [ ] **Step 4: Update `deploy/docker-compose.pc2.yml` paths (if any)**

Edit `deploy/docker-compose.pc2.yml` to ensure any relative volume mounts (like `./backend/observability` or `./backend/grafana`) now point correctly (e.g. `./observability` or `./grafana` since they are now in the same `deploy/` directory).

- [ ] **Step 5: Commit the changes**

```bash
git add deploy/ backend/ frontend/ docker-compose.pc1.yml docker-compose.pc2.yml
git commit -m "refactor: move Dockerfiles and compose files to deploy/ and update paths"
```

### Task 3: Update Python tooling scripts

**Files:**
- Modify: `tooling/dev.py`
- Modify: `tooling/async_ops_validation.py` (if it references compose)
- Modify: `tooling/generate_api_coverage_report.py` (if it references compose)
- Modify: `backend/scripts/eval_technical_qa.py` (if it references docker)

- [ ] **Step 1: Update `tooling/dev.py`**

Edit `tooling/dev.py` to change any references from `docker-compose.pc1.yml` to `deploy/docker-compose.pc1.yml`, and `backend/docker/Dockerfile` to `deploy/docker/api.Dockerfile`. 
Also ensure any `subprocess.run` calls that run `docker compose` specify the correct working directory or file paths.

- [ ] **Step 2: Update backend/scripts and other python tooling**

Search for `docker-compose` and `backend/docker/Dockerfile` in `tooling/*.py` and `backend/scripts/*.py` and update them to the new paths.

- [ ] **Step 3: Commit the changes**

```bash
git add tooling/ backend/scripts/
git commit -m "chore: update python tooling scripts for deploy/ paths"
```

### Task 4: Update PowerShell scripts

**Files:**
- Modify: `tooling/run-top12-tests-docker.ps1`
- Modify: `tooling/start_services.ps1`

- [ ] **Step 1: Update `tooling/start_services.ps1`**

Edit `tooling/start_services.ps1` to point to `deploy/docker-compose.pc1.yml` and `deploy/docker-compose.pc2.yml`.

- [ ] **Step 2: Update `tooling/run-top12-tests-docker.ps1`**

Edit `tooling/run-top12-tests-docker.ps1` to change `-f backend/docker/Dockerfile` to `-f deploy/docker/api.Dockerfile`.

- [ ] **Step 3: Commit the changes**

```bash
git add tooling/*.ps1
git commit -m "chore: update PowerShell scripts for deploy/ paths"
```

### Task 5: Update GitHub Actions

**Files:**
- Modify: `.github/workflows/action-locaweb.yml`
- Modify: `.github/workflows/quality-gates.yml`

- [ ] **Step 1: Update GitHub Actions paths**

Edit `.github/workflows/action-locaweb.yml` and `.github/workflows/quality-gates.yml`.
Search for:
- `docker-compose.pc1.yml` -> replace with `deploy/docker-compose.pc1.yml`
- `docker-compose.pc2.yml` -> replace with `deploy/docker-compose.pc2.yml`
- `backend/docker/Dockerfile` -> replace with `deploy/docker/api.Dockerfile`
- `frontend/docker/Dockerfile` -> replace with `deploy/docker/frontend.Dockerfile`

- [ ] **Step 2: Commit the changes**

```bash
git add .github/workflows/
git commit -m "ci: update github actions for deploy/ paths"
```

### Task 6: Update Documentation

**Files:**
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `documentation/deployment-guide.md`
- Modify: `documentation/qa/api-test-playbook.md`

- [ ] **Step 1: Update AGENTS.md**

Search and replace all instances of `docker-compose.pc1.yml` with `deploy/docker-compose.pc1.yml` and `docker-compose.pc2.yml` with `deploy/docker-compose.pc2.yml`.
Update Dockerfile paths to `deploy/docker/api.Dockerfile`.

- [ ] **Step 2: Update README.md and documentation**

Search and replace the same paths in `README.md`, `documentation/deployment-guide.md`, and `documentation/qa/api-test-playbook.md`.

- [ ] **Step 3: Commit the changes**

```bash
git add AGENTS.md README.md documentation/
git commit -m "docs: update documentation for deploy/ paths"
```
