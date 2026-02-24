# Janus Backend

This directory contains the Python FastAPI backend for the Janus AI system.

**For full documentation and backlog, please refer to the [root README](../README.md).**

## Quick Start

### Prerequisites
- Python 3.11+

### Setup

```bash
# Ensure you are in the backend/ directory
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`.
Docs at `http://localhost:8000/docs`.
