# Janus Backend (API)

The backend for Janus AI Architect is built with **FastAPI** and follows a layered architecture to ensure separation of concerns and maintainability.

## 🏗️ Architecture

- **Kernel**: `app/core/` - Handles startup sequence, DI container, and core application processes.
- **Services**: `app/services/` - Contains business logic and orchestrates operations.
- **Repositories**: `app/repositories/` - Handles data access (SQLAlchemy, Qdrant, Neo4j).
- **API**: `app/http/` - Defines API routes and controllers.

## 🛠️ Prerequisites

- **Python**: >= 3.11 and < 3.13
- **Database**: PostgreSQL (for configuration and HITL)
- **Vector DB**: Qdrant (for episodic memory)
- **Graph DB**: Neo4j (for semantic memory)
- **Message Broker**: RabbitMQ (for event handling)
- **Cache**: Redis (for state management and rate limiting)

## 🚀 Setup & Running

### 1. Environment Setup

Create a virtual environment and install dependencies:

```bash
cd janus
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> **Note**: If you encounter issues with `ag-ui-protocol`, `pyaudio`, or `openwakeword` on Linux/Python 3.12, you may need to install system dependencies or exclude them from `requirements.txt` for basic backend functionality.

### 2. Configuration

Create a `.env` file in the `janus` directory based on `.env.example` (if available) or configure environment variables directly. See `app/config.py` for all available options.

### 3. Run the Server

Start the development server with hot reload:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`.
Documentation is available at `http://localhost:8000/docs`.

## 🧪 Testing

Run the test suite using `pytest`:

```bash
# Run all tests
PYTHONPATH=. pytest tests/

# Run a specific test file
PYTHONPATH=. pytest tests/test_circuit_breaker.py
```

Ensure you have `pytest-asyncio` and `asyncpg` installed if running async tests.

## 📚 Documentation

Detailed technical documentation can be found in the `docs/` directory:
- [RAG with HyDE](docs/RAG_HYDE.md)
- [Qdrant Resilience](docs/qdrant_resilience_improvements.md)
