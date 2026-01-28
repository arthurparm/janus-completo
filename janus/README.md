# Janus Backend

The backend for the Janus AI Architect, built with **FastAPI** and **Python 3.11+**.

## 🛠️ Overview

This component orchestrates the Multi-Agent System (MAS), handling reasoning, memory (Neo4j + Qdrant), and execution.

### Key Technologies
- **Framework**: FastAPI (Async)
- **Database**: PostgreSQL (Application Data), Neo4j (Knowledge Graph), Qdrant (Vector Memory)
- **AI/Agents**: LangGraph, DeepSeek, OpenRouter
- **ORM**: SQLAlchemy (Async)

## 🚀 Setup

### Requirements
- Python 3.11+
- PostgreSQL, Redis, Neo4j, and Qdrant running (see root `docker-compose.yml`)

### Installation

```bash
cd janus
pip install -r requirements.txt
```

> **Note**: If you encounter issues with `ag-ui-protocol`, you may need to exclude it or adjust the installation.

### Running

Start the development server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- API Docs (Swagger): `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/healthz`

## 📂 Documentation

- Technical details and specific architectural decisions can be found in `docs/` within this directory (e.g., RAG, Circuit Breakers).
- Project-level roadmap and inventory are in the root `docs/` folder.

## ⚙️ Configuration

Configuration is managed via environment variables (see `.env` in root) and `app/config.py`.
Dynamic settings and agent prompts are persisted in the database (Configuration-as-Data).

## 🧪 Testing

Run tests from the repository root:

```bash
# From repo root
PYTHONPATH=janus pytest tests/
```
