# Janus Backend

The Python backend for the Janus AI Architect, built with FastAPI, LangGraph, and Neo4j/Qdrant.

## Overview
- **Framework**: FastAPI
- **Architecture**: Hybrid Agent (LangGraph + PydanticAI)
- **Memory**: Qdrant (Episodic/Vector) + Neo4j (Semantic/Graph)
- **Execution**: Secure Docker Sandbox

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment**:
   Copy `.env.example` to `.env` and configure your keys (OpenAI, DeepSeek, Neo4j, etc.).

3. **Run**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Documentation
For detailed documentation, see the [Root README](../README.md).
