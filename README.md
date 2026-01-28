# Janus AI Architect

**Janus** is an advanced Multi-Agent System (MAS) designed to act as an autonomous Software Engineer. It combines reasoning, planning, memory, and tool execution to solve complex coding tasks.

## 🏗️ Architecture

The system is composed of two main parts:

- **Frontend (`front/`)**: An Angular 20 web interface for interacting with the agent, visualizing thought streams, and managing settings.
- **Backend (`janus/`)**: A Python/FastAPI application orchestrating the agents (LangGraph), memory (Neo4j, Qdrant), and execution sandbox.

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose (for infrastructure)
- Node.js 20+
- Python 3.11+

### Infrastructure
Start the required databases (PostgreSQL, Neo4j, Qdrant, Redis):

```bash
docker-compose up -d
```

### Backend
See [janus/README.md](janus/README.md) for detailed setup.

```bash
cd janus
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
See [front/README.md](front/README.md) for detailed setup.

```bash
cd front
npm install
npm start
```

Access the UI at `http://localhost:4200`.

## 📚 Documentation

- **[Roadmap](docs/ROADMAP.md)**: Future plans, scientific foundation, and critical path.
- **[Inventory & History](docs/INVENTORY.md)**: Detailed system inventory, task history, and API routes.
- **Backend Docs**: Technical documentation specific to the backend is located in `janus/docs/`.

## 🧠 Core Concepts

- **Reasoning**: Uses advanced techniques like LATS (Language Agent Tree Search) and Reflexion.
- **Memory**: Hybrid architecture with Episodic (Vector/Qdrant) and Semantic (Graph/Neo4j) memory.
- **Autonomy**: Implements an OODA loop (Observe, Orient, Decide, Act) for continuous operation.
