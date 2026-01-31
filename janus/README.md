# Janus Backend

This is the backend for the Janus AI Architect system, built with Python and FastAPI.

**For full project documentation and architecture, please refer to the [Root README](../README.md).**

## 🛠️ Local Setup

### Requirements
- Python 3.11+
- Docker (for dependencies like Neo4j, Qdrant, Redis, RabbitMQ)

### Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Server

Start the development server with hot reload:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`.
Docs are available at `http://localhost:8000/docs`.
