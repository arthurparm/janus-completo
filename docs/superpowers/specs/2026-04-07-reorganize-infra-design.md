# Design Doc: Reorganization of Infrastructure to `deploy/`

## Context
Currently, infrastructure configuration files, `Dockerfile`s, and `docker-compose` files are scattered across the root directory and the `backend/` and `frontend/` directories. This mixes application code with infrastructure/deployment concerns, making it harder to maintain and violating separation of concerns.

## Goal
Consolidate all infrastructure and deployment configurations into a single `deploy/` directory at the root of the project.

## Architecture & Structure Changes

### 1. `deploy/` Directory Creation
A new directory `deploy/` will be created at the repository root to house all infrastructure and deployment files.

### 2. File and Directory Moves
The following files and directories will be moved:
- `docker-compose.pc1.yml` (Root) -> `deploy/docker-compose.pc1.yml`
- `docker-compose.pc2.yml` (Root) -> `deploy/docker-compose.pc2.yml`
- `backend/grafana/` -> `deploy/grafana/`
- `backend/observability/` -> `deploy/observability/`
- `backend/otel/` -> `deploy/otel/`
- `backend/prometheus/` -> `deploy/prometheus/`
- `backend/sql/` -> `deploy/sql/`
- `backend/docker/Dockerfile` -> `deploy/docker/api.Dockerfile`
- `backend/docker/ollama.Dockerfile` -> `deploy/docker/ollama.Dockerfile`
- `frontend/docker/Dockerfile` -> `deploy/docker/frontend.Dockerfile`

### 3. Path Updates & Contexts
Because the `docker-compose` and `Dockerfile` files are moving, the context paths inside them need to be updated:
- In `deploy/docker-compose.pc1.yml` and `deploy/docker-compose.pc2.yml`:
  - Update `build: context:` paths to point to the repository root (e.g., `../`).
  - Update volume mounts to point to `../backend/...`, `../frontend/...`, or local `./grafana/` instead of `backend/grafana/`.
- In the `Dockerfile`s (`deploy/docker/api.Dockerfile`, `deploy/docker/frontend.Dockerfile`):
  - Ensure the build context works when run from the repository root or update the COPY commands to expect the correct relative paths.

### 4. Tooling and Script Updates
Many scripts rely on the current locations of the compose files. The following need to be updated to point to `deploy/`:
- `tooling/dev.py` (updates to `docker-compose` commands)
- `tooling/*.ps1` (updates to `docker-compose` commands and `Dockerfile` paths)
- `backend/scripts/*.py` (any references to compose or docker build)
- `.github/workflows/action-locaweb.yml`
- `.github/workflows/quality-gates.yml`

### 5. Documentation Updates
Update all references in:
- `AGENTS.md`
- `README.md`
- `documentation/deployment-guide.md`
- `documentation/qa/api-test-playbook.md`

## Trade-offs
- **Pros:** Total isolation of infrastructure from application code. Cleaner root directory. Standardized approach for monorepos.
- **Cons:** Developers will need to adapt their habits. The `tooling/dev.py` and GitHub actions require careful updates to ensure nothing breaks. Docker contexts become slightly more complex (e.g., `docker build -f deploy/docker/api.Dockerfile .`).

## Implementation Plan
This will be detailed in the implementation phase via `writing-plans`.
