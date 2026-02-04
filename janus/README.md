# Janus Backend

The backend for Janus AI Architect, built with Python and FastAPI. It powers the intelligent agent orchestration, memory management, and API services.

## Requirements

- Python 3.11 or higher (but less than 3.13 recommended due to some dependency constraints).
- pip

## Setup

1.  **Navigate to the backend directory:**
    ```bash
    cd janus
    ```

2.  **Create a virtual environment (optional but recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    > **Note:** If you encounter issues installing `ag-ui-protocol`, you may need to temporarily remove it from `requirements.txt` or ensure you have the necessary build tools.

4.  **Run the development server:**
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```

    The API will be available at `http://localhost:8000`.
    API Documentation (Swagger UI) is available at `http://localhost:8000/docs`.

## Configuration

Configuration is managed via environment variables. Refer to `app/config.py` for available settings. Key configurations include database connections (Neo4j, Qdrant, Postgres) and LLM provider settings.

## Testing

To run tests:
```bash
PYTHONPATH=. pytest tests/
```
