# Janus AI Architect

Janus is an advanced AI architecture designed for autonomous software development and intelligent orchestration. It leverages a Meta-Agent architecture to plan, execute, and reflect on complex tasks.

## 🏗️ Architecture

Janus is built upon a foundation of state-of-the-art research in AI agents:

### Reasoning & Planning (The Brain)
- **LATS (Language Agent Tree Search)**: Utilizes a `Planner` node to simulate scenarios via Monte Carlo Tree Search (MCTS) before execution.
- **Reflexion**: Implements self-correction loops where agents verbalize errors and store lessons in short-term memory.
- **Graph of Thoughts (GoT)**: Models reasoning as a graph (DAG), allowing non-linear orchestration via LangGraph.

### Memory & Learning (The Soul)
- **Hybrid Memory**: Combines **Qdrant** for episodic/vector memory and **Neo4j** for semantic/knowledge graph memory.
- **Consolidation**: A `KnowledgeConsolidatorWorker` transforms episodic memory into semantic knowledge.

### Retrieval & RAG (The Knowledge)
- **Native GraphRAG**: Integrates retrieval with the knowledge graph.
- **HyDE (Hypothetical Document Embeddings)**: Generates hypothetical answers to improve vector search relevance.

## 📂 Repository Structure

- **`front/`**: The frontend application built with **Angular 20**.
- **`janus/`**: The backend application built with **Python (FastAPI)** and **LangGraph**.

## 🚀 Getting Started

### Prerequisites
- Python 3.11+ (< 3.13)
- Node.js 20
- PostgreSQL, Redis, Neo4j, Qdrant (Infrastructure)

### Backend Setup (`janus/`)

1. Install dependencies:
   ```bash
   cd janus
   pip install -r requirements.txt
   ```
   *Note: If you encounter issues with `ag-ui-protocol`, try removing it from `requirements.txt` before installing.*

2. Run the application:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Frontend Setup (`front/`)

1. Install dependencies:
   ```bash
   cd front
   npm install
   ```

2. Start the development server:
   ```bash
   npm start
   ```
   The application will be available at `http://localhost:4200`.

## 📚 Documentation

- **Frontend**: See [`front/README.md`](front/README.md).
- **Backend Technical Docs**: See [`janus/docs/`](janus/docs/).
- **API Documentation**: Available via Swagger UI at `/docs` when the backend is running.
