# Janus AI Architect

**Janus** is an advanced AI architecture designed for autonomous software development and orchestration. It leverages a hybrid agent architecture (LangGraph + PydanticAI) with multi-modal memory (Neo4j + Qdrant) and specialized workers to handle complex tasks ranging from coding to strategic planning.

## 📚 Documentation

The project documentation is organized in the `docs/` directory:

- **[Roadmap & Technical Debt](docs/ROADMAP.md)**: Critical path, backlog, scientific foundations, and infrastructure strategy.
- **[Inventory & Surveys](docs/INVENTORY.md)**: Detailed breakdown of the system, including API endpoints, infrastructure, and component analysis.

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 20+**
- **Docker** (for infrastructure services: Neo4j, Qdrant, Redis, RabbitMQ)

### 1. Infrastructure
Start the required services using Docker Compose:
```bash
docker-compose up -d
```

### 2. Backend (`janus/`)
Navigate to the backend directory and start the server:

```bash
cd janus
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*   **API Docs**: http://localhost:8000/docs
*   **Health Check**: http://localhost:8000/healthz

For more details, see [janus/README.md](janus/README.md).

### 3. Frontend (`front/`)
Navigate to the frontend directory and start the development server:

```bash
cd front
npm install
npm start
```
*   **Web Interface**: http://localhost:4200
*   **Proxy**: Requests to `/api` are proxied to the backend at `http://localhost:8000`.

For more details, see [front/README.md](front/README.md).

## 🏗️ Architecture Overview

Janus operates on a **Meta-Agent Architecture** utilizing **LangGraph** state machines:

- **Monitor**: Observes system state and inputs.
- **Diagnose**: Identifies issues or tasks.
- **Plan**: Generates execution plans (using LATS/MCTS).
- **Reflect**: Validates outcomes and learns from mistakes.
- **Execute**: Performs actions via specialized agents (Coder, Architect, etc.).

**Key Components:**
- **Memory**: Hybrid storage with Qdrant (Episodic/Vector) and Neo4j (Semantic/Graph).
- **Backend**: Python/FastAPI with Layered Architecture.
- **Frontend**: Angular 20 application with a modern SaaS aesthetic.
