# Janus: The AI Architect

**Janus** is a sophisticated AI system designed as a strategic supervisor and architect. It employs a hybrid agent architecture using **LangGraph**, combining a **Monitor-Diagnose-Plan-Reflect-Execute** state machine with an operational Autonomy Loop.

## 🚀 Key Features

- **Metacognition**: Uses "Reflexion" and "Graph of Thoughts" for robust reasoning and self-correction.
- **Hybrid Memory**: Combines **Qdrant** (episodic/vector memory) and **Neo4j** (semantic/knowledge graph memory) for long-term context.
- **Agentic Architecture**: Specialized agents (Monitor, Planner, Coder, etc.) orchestrated by a Meta-Agent supervisor.
- **Configuration-as-Data**: Dynamic prompts and agent settings persisted in PostgreSQL.

## 📂 Repository Structure

- `front/`: Angular 20 frontend application.
- `janus/`: Python/FastAPI backend and agent core.
- `docs/`: Project documentation and roadmap.

## 📖 Documentation

The project documentation is the **Single Source of Truth**.

- **[Roadmap & Technical Debt](docs/ROADMAP.md)**: Development plan, scientific foundations, and critical path.
- **[System Inventory](docs/INVENTORY.md)**: Detailed task lists, API inventory, and system status.
- **Backend Technical Docs**: See `janus/docs/`.

## 🛠️ Getting Started

### Prerequisites
- Node.js 20+
- Python 3.11+
- Docker & Docker Compose

### Quick Start

1. **Start Infrastructure**:
   ```bash
   docker-compose up -d
   ```

2. **Backend Setup**:
   Follow instructions in [janus/README.md](janus/README.md).
   ```bash
   cd janus
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Frontend Setup**:
   Follow instructions in [front/README.md](front/README.md).
   ```bash
   cd front
   npm install
   npm start
   ```

4. **Access**:
   - Frontend: `http://localhost:4200`
   - Backend API: `http://localhost:8000/docs`

## 🤝 Contribution

Please read the specific READMEs in `front/` and `janus/` for development guidelines.
Code quality is enforced via pre-commit hooks.

---
*Janus is an evolving AI Architect system. Check `docs/ROADMAP.md` for the latest status.*
