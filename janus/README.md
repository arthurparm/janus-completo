# Janus Backend (Python)

The brain of the Janus architecture, built with Python 3.11+ and FastAPI. It orchestrates the Multi-Agent System, manages memory (Neo4j/Qdrant), and handles API requests.

## Requirements

*   Python 3.11 or higher
*   Docker (for infrastructure services)

## Setup

1.  **Navigate to the backend directory:**
    ```bash
    cd janus
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # Linux/Mac
    source venv/bin/activate
    # Windows
    .\venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

Start the development server using Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`.
API Documentation (Swagger UI) is available at `http://localhost:8000/docs`.

## Configuration

Configuration is managed via `app/config.py` and environment variables.
Ensure the root `.env` file is properly configured with database credentials and API keys.

## Testing

Run tests using `pytest` from the root directory or `janus` directory:

```bash
pytest
```

## Documentation

*   **API Inventory**: See `../docs/INVENTORY.md` for a complete list of endpoints.
*   **Architecture**: See `../README.md` for high-level architecture details.
