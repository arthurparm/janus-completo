# Janus Backend

This directory contains the Python/FastAPI backend for the Janus AI Architect.

## 📌 Documentation
Please refer to the **[Root README](../README.md)** for full project documentation and architecture details.

## 🚀 Local Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Server**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## 🧪 Testing
Run tests from the project root:
```bash
PYTHONPATH=janus pytest tests/
```
