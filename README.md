# Janus AI Architect

**Janus** is an advanced AI Architect platform designed to orchestrate autonomous agents, manage knowledge graphs, and provide a robust interface for interaction and monitoring. It is built on a scientific foundation of reasoning, planning, and memory management.

## 🏗️ Architecture

The project is divided into two main components:

- **[Janus Backend (`janus/`)](./janus/README.md)**: A Python/FastAPI application that serves as the core intelligence, managing agents (LangGraph), memory (Neo4j, Qdrant), and tools.
- **[Janus Frontend (`front/`)](./front/README.md)**: An Angular 20 application providing the user interface for chat, autonomy management, and system monitoring.

## 🚀 Quick Start

### Backend (`janus/`)
1.  Navigate to `janus/`
2.  Install dependencies: `pip install -r requirements.txt`
    *   *Note: See `janus/README.md` for specific package workarounds.*
3.  Start the server: `uvicorn app.main:app --reload`

### Frontend (`front/`)
1.  Navigate to `front/`
2.  Install dependencies: `npm install`
3.  Start the dev server: `npm start`

See the respective `README.md` files in each directory for detailed setup instructions.

## 📚 Documentation

Detailed documentation is available in the `docs/` directory:

- **[Roadmap & Scientific Foundation](./docs/ROADMAP.md)**: V1 critical path, technical debt, and the scientific papers backing the architecture (LATS, Reflexion, Graph of Thoughts, etc.).
- **[Inventory & Tasks](./docs/INVENTORY.md)**: Detailed lists of API routes, infrastructure components, and completed task batches.
- **[Backend Docs](./janus/docs/)**: Technical documentation specific to the backend (RAG/HyDE, Resilience).

## 🔬 Scientific Basis

Janus implements state-of-the-art concepts from 13+ seminal papers, including:
- **Reasoning**: Language Agent Tree Search (LATS), Reflexion, Graph of Thoughts.
- **Memory**: Generative Agents, MemGPT (concepts), Voyager.
- **Retrieval**: Self-RAG, HyDE, RAPTOR.

See [Scientific Foundation](./docs/ROADMAP.md#scientific-foundation-state-of-the-art) for details.
