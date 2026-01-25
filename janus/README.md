# Janus Backend

Python/FastAPI backend for Janus AI Architect.

See [Root README](../README.md) for architecture overview.

## Requirements
- Python 3.11+
- Neo4j, Qdrant, Redis, RabbitMQ (usually via Docker)

## Setup

1.  Navigate to `janus/`:
    ```bash
    cd janus
    ```
2.  Install dependencies:
    *   **Note**: The package `ag-ui-protocol` might cause installation issues. If so, remove it from `requirements.txt` before running the install command.
    ```bash
    pip install -r requirements.txt
    ```
3.  Start the server:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```

## Documentation

*   [Technical Docs](./docs/): Backend-specific technical documentation (RAG, Resilience, etc.).
