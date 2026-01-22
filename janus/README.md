# Janus Backend

The backend for Janus AI Architect, built with Python (FastAPI), LangGraph, and specialized agents.

## Overview
- **Framework**: FastAPI (Async)
- **Architecture**: Layered (Repositories, Services, Core)
- **Agents**: LangGraph state machines (Monitor, Diagnose, Plan, Reflect, Execute)
- **Memory**: Hybrid (Qdrant for vector, Neo4j for graph)
- **Database**: PostgreSQL (Config/Data)

## Requirements
- Python 3.11+
- Docker (for database and services)

## Setup

1. **Install Dependencies**:
   ```bash
   cd janus
   pip install -r requirements.txt
   ```
   *Note: If `ag-ui-protocol` fails to install, remove it from requirements.txt temporarily.*

2. **Environment Configuration**:
   - Ensure PostgreSQL, Redis, Qdrant, and Neo4j are running (typically via `docker-compose` in root).
   - Configure `.env` with necessary keys (OpenAI, DeepSeek, Database URLs).

3. **Run the Server**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   - API Docs: `http://localhost:8000/docs`
   - Health Check: `http://localhost:8000/healthz`

## Documentation
- Technical Docs: `docs/` (inside `janus/`)
- Root Documentation: See `../docs/` for Roadmap and Inventory.

## Testing
To run tests, set the PYTHONPATH to include the `janus` directory:
```bash
# From the root directory
PYTHONPATH=janus pytest janus/tests/
```
