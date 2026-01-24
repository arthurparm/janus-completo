# Janus Backend (Python)

Backend service for the Janus AI Architect, built with FastAPI, LangGraph, and SQLAlchemy.

For full project context and architecture, please refer to the **[Root README](../README.md)**.

## 🛠️ Setup

### Prerequisites
*   Python 3.11+
*   Infrastructure services running (Redis, Neo4j, Qdrant, RabbitMQ) - see root `docker-compose.yml`.

### Installation

1.  Navigate to this directory:
    ```bash
    cd janus
    ```

2.  Create and activate a virtual environment (recommended):
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Linux/Mac
    # or
    .venv\Scripts\activate     # Windows
    ```

3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Running the Server

Start the development server with hot reload:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`.
API Documentation (Swagger UI): `http://localhost:8000/docs`.

## 🧪 Testing

Run tests from the project root (recommended) or from `janus/` ensuring `PYTHONPATH` is set.

```bash
# From janus directory:
PYTHONPATH=. pytest
```
