# Janus Backend (Python/FastAPI)

This is the backend for the Janus AI Architect, built with Python and FastAPI.

## Prerequisites

- Python >= 3.11 and < 3.13
- Docker (for dependencies like Neo4j, Qdrant, RabbitMQ, Redis)

## Setup

1. Navigate to the `janus` directory:
   ```bash
   cd janus
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

Start the development server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Documentation

For more detailed documentation, including the project roadmap and architecture overview, please refer to the root [README.md](../README.md).
