# Janus Backend

The FastAPI-based backend for the Janus AI Architect.

For full project documentation, roadmap, and architecture details, please refer to the **[root README.md](../README.md)**.

## Local Setup

### Prerequisites

- Python 3.11+
- Virtual environment (recommended)

### Installation

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Server

Start the application with Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`.
Documentation is available at `http://localhost:8000/docs`.

### Testing

Run tests with `pytest`:

```bash
pytest
```
