# Janus Backend

This directory contains the FastAPI backend application.

**Full Documentation:** Please refer to the [root README](../README.md) for full project documentation, architecture, and roadmap.

## Local Development

### Prerequisites
- Python 3.11+
- Running infrastructure (Redis, RabbitMQ, Neo4j, Qdrant, Postgres) - usually via `docker compose up -d` from root.

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start API server
uvicorn app.main:app --reload
```

- API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

## Testing

```bash
# Run tests
pytest
```
