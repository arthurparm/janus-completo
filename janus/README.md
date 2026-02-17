# Janus Backend (FastAPI)

Python/FastAPI backend for Janus.

See [root README](../README.md) for full project documentation and architecture.

## Setup

### Local Development

Navigate to the `janus` directory and run:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker

From the project root, run:

```bash
docker compose up -d
```
